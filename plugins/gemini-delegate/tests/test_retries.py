"""Behavioral checks for bounded automatic retries and primary-agent handoff."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from worker import Manager, WorkerError, decode_result
from main import call


def startup_error():
    return WorkerError('transient_error','Preflight connection failed',{'reported_phase':'startup'})


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        patch=mock.patch('worker.prepare_agent');patch.start();self.addCleanup(patch.stop)
        self.manager=Manager(self.root/'state',agy='fake-agy')
        self.addCleanup(self.manager.close)
        patch=mock.patch.object(self.manager,'_retry_backoff',return_value=False)
        self.backoff=patch.start();self.addCleanup(patch.stop)

    def task(self,**options):
        jid=call(self.manager,'delegate_task',{'instruction':'Return OK','workspace':str(self.root),**options})['task_id']
        return self.manager.result(jid,10)

    def envelope(self,response='OK',**extra):
        return json.dumps({'status':'SUCCESS','response':response,**extra}),'',0

    def test_two_startup_disconnects_then_success_use_fixed_short_caps(self):
        with mock.patch('worker.run_process',side_effect=[startup_error(),startup_error(),self.envelope()]) as process:
            result=self.task()
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual([a['status'] for a in result['attempts']],['failed','failed','validated'])
        self.assertNotIn('handoff',result)
        budgets=[c.args[2] for c in process.call_args_list]
        self.assertEqual([round(b) for b in budgets],[27,27,27])
        self.assertEqual([c.args[1] for c in process.call_args_list],[self.root]*3)
        for c in process.call_args_list:
            self.assertNotIn('--continue',c.args[0]);self.assertNotIn('--conversation',c.args[0])
        self.assertEqual([c.args[1] for c in self.backoff.call_args_list],[.25,.5])

    def test_exhaustion_stops_at_three_and_survives_reopening_with_unknown_usage(self):
        with mock.patch('worker.run_process',side_effect=startup_error()) as process:
            result=self.task(context='PRIVATE INPUT')
        self.assertEqual(process.call_count,3)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['handoff']['reason'],'attempts_exhausted')
        self.assertEqual(result['handoff']['attempt_count'],3)
        self.assertTrue(result['handoff']['ready'])
        listing=self.manager.task_list(str(self.root))['tasks'][0]
        self.assertEqual(listing['handoff'],result['handoff'])
        self.assertNotIn('PRIVATE INPUT',json.dumps(listing))
        report=self.manager.usage_summary(str(self.root))['projects'][0]
        self.assertEqual(report['retry_count'],2)
        self.assertEqual(report['attempts_without_usage'],3)
        self.assertFalse(report['usage_complete'])
        reopened=Manager(self.manager.state,agy='fake-agy')
        try:self.assertEqual(reopened.result(result['id'])['handoff'],result['handoff'])
        finally:reopened.close()

    def test_mid_task_eof_is_discarded_without_replay_and_usage_is_kept(self):
        usage={'input_tokens':10,'output_tokens':2,'total_tokens':12}
        failure=(json.dumps({'status':'ERROR','error':'streamGenerateContent: EOF',
                            'response':'PARTIAL','usage':usage,'conversation_id':'failed-session'}),'',1)
        with mock.patch('worker.run_process',return_value=failure) as process,mock.patch('worker.schedule_title') as naming:
            result=self.task()
        self.assertEqual(process.call_count,1)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['handoff']['reason'],'mid_task_failure')
        self.assertTrue(result['handoff']['discard_result'])
        self.assertIsNone(result['result']);self.assertEqual(result['changes'],[])
        self.assertEqual(result['usage']['total_tokens'],12)
        naming.assert_not_called()
        report=self.manager.usage_summary(str(self.root))['projects'][0]
        self.assertEqual(report['reported_usage']['total_tokens'],12)

    def test_real_preflight_eof_retries_but_usage_or_ids_override_startup_label(self):
        failure={'status':'ERROR','error':'Eligibility check failed: userinfo EOF'}
        with mock.patch('worker.run_process',side_effect=[(json.dumps(failure),'',1),self.envelope()]) as process:
            result=self.task()
        self.assertEqual(result['status'],'completed');self.assertEqual(process.call_count,2)
        for extra in ({'usage':{'total_tokens':1}},{'conversation_id':'started'},
                      {'session_id':'started'},{'response':'partial'}):
            with self.subTest(extra=extra),mock.patch('worker.run_process',return_value=(json.dumps({**failure,**extra}),'',1)) as process:
                result=self.task()
                self.assertEqual(process.call_count,1)
                self.assertEqual(result['handoff']['reason'],'mid_task_failure')

    def test_unknown_phase_does_not_replay_even_fast_failure(self):
        with mock.patch('worker.run_process',side_effect=WorkerError('timeout','Hard deadline')) as process:
            result=self.task()
        self.assertEqual(process.call_count,1)
        self.assertEqual(result['handoff']['reason'],'startup_not_confirmed')

    def test_confirmed_17_second_startup_failure_retries_with_remaining_budget(self):
        clock=[0];count=[0]
        def slow(*args,**kwargs):
            count[0]+=1
            if count[0]==1:
                clock[0]=17.53
                raise startup_error()
            clock[0]+=16
            return self.envelope()
        with mock.patch('worker.time.monotonic',side_effect=lambda:clock[0]),mock.patch('worker.run_process',side_effect=slow) as process:
            result=self.task()
        self.assertEqual(process.call_count,2)
        self.assertEqual(result['status'],'completed',result)
        self.assertTrue(result['attempts'][0]['retry_eligible'])
        self.assertAlmostEqual(result['attempts'][1]['timeout_seconds'],22.47,places=2)
        self.assertLess(result['elapsed_seconds'],40)

    def test_slow_startup_failure_does_not_retry_without_useful_remaining_budget(self):
        clock=[0]
        def slow(*args,**kwargs):clock[0]=36;raise startup_error()
        with mock.patch('worker.time.monotonic',side_effect=lambda:clock[0]),mock.patch('worker.run_process',side_effect=slow) as process:
            result=self.task()
        self.assertEqual(process.call_count,1)
        self.assertEqual(result['handoff']['reason'],'time_budget_exhausted')

    def test_17_second_generation_failure_is_never_replayed(self):
        clock=[0]
        def slow(*args,**kwargs):
            clock[0]=17.53
            return json.dumps({'status':'ERROR','error':'streamGenerateContent: EOF'}),'',1
        with mock.patch('worker.time.monotonic',side_effect=lambda:clock[0]),mock.patch('worker.run_process',side_effect=slow) as process:
            result=self.task()
        self.assertEqual(process.call_count,1)
        self.assertEqual(result['handoff']['reason'],'mid_task_failure')

    def test_auth_quota_and_permission_failures_do_not_retry_even_with_eof(self):
        for message in ('401 unauthenticated EOF','quota exhausted: EOF','permission denied: EOF','429 rate limit: EOF'):
            with self.subTest(message=message),mock.patch('worker.run_process',return_value=(json.dumps({'status':'ERROR','error':message}),'',1)) as process:
                result=self.task()
                self.assertEqual(result['status'],'failed',result)
                self.assertEqual(process.call_count,1)
                self.assertEqual(result['handoff']['reason'],'non_retryable_error')

    def test_cancel_during_backoff_does_not_run_another_attempt_or_handoff(self):
        self.backoff.side_effect=lambda job,seconds:job['cancel'].set() or True
        with mock.patch('worker.run_process',side_effect=startup_error()) as process:
            result=self.task()
        self.assertEqual(result['status'],'cancelled',result)
        self.assertEqual(process.call_count,1)
        self.assertNotIn('handoff',result)

    def test_total_deadline_still_wins_over_remaining_attempt_count(self):
        clock=[0.0]
        def expired(*args,**kwargs):
            clock[0]=40
            raise startup_error()
        with mock.patch('worker.time.monotonic',side_effect=lambda:clock[0]),mock.patch('worker.run_process',side_effect=expired) as process:
            result=self.task()
        self.assertEqual(process.call_count,1)
        self.assertEqual(result['handoff']['reason'],'time_budget_exhausted')

    def test_slot_timeout_is_not_a_model_attempt_or_retried(self):
        @contextlib.contextmanager
        def no_slot(*args):
            raise WorkerError('timeout','Waiting for slot exhausted the total budget')
            yield
        with mock.patch.object(self.manager,'_agy_slot',no_slot),mock.patch('worker.run_process') as process:
            result=self.task()
        self.assertEqual(result['attempts'],[])
        self.assertEqual(result['handoff']['reason'],'time_budget_exhausted')
        process.assert_not_called()

    def test_explicit_max_attempts_one_and_five_are_respected(self):
        for maximum in (1,5):
            with self.subTest(maximum=maximum),mock.patch('worker.run_process',side_effect=startup_error()) as process:
                result=self.task(max_attempts=maximum)
                self.assertEqual(process.call_count,maximum)
                self.assertEqual(result['handoff']['reason'],'attempts_exhausted')
        for invalid in (0,6,True,'3'):
            with self.assertRaises(WorkerError):self.manager.submit({'instruction':'OK','max_attempts':invalid})

    def test_progress_reports_retrying_before_primary_takeover(self):
        def inspect(job,seconds):
            snapshot=self.manager.task_list(str(self.root))['tasks'][0]
            self.assertEqual(snapshot['status'],'retrying')
            self.assertNotIn('handoff',snapshot)
            self.assertEqual(snapshot['retry_policy']['next_attempt'],2)
            # The first call released its slot before waiting for backoff.
            second=Manager(self.manager.state,agy='fake-agy',max_concurrency=1)
            try:
                with second._agy_slot({'cancel':threading.Event(),'status':'queued'},time.monotonic()+1):pass
            finally:second.close()
            return False
        self.backoff.side_effect=inspect
        with mock.patch('worker.run_process',side_effect=[startup_error(),self.envelope()]):
            result=self.task()
        self.assertEqual(result['status'],'completed',result)


class FailureClassificationTests(unittest.TestCase):
    def test_startup_failure_keeps_safe_stage_without_provider_urls_or_tokens(self):
        with self.assertRaises(WorkerError) as caught:
            decode_result('', 'Eligibility check failed: GET https://private.example/?token=DO_NOT_STORE: EOF', 1)
        e=caught.exception
        self.assertEqual(e.details,{'reported_phase':'startup','failure_stage':'eligibility','failure_kind':'eof'})
        self.assertNotIn('DO_NOT_STORE',str(e)+json.dumps(e.details))

    def test_cli_stderr_network_failure_is_retryable_but_auth_is_not(self):
        for stderr,expected in [('request: EOF','transient_error'),('connection reset by peer','transient_error'),('503 Service Unavailable','transient_error'),('context deadline exceeded','timeout'),('401 permission denied; EOF','agy_failed')]:
            with self.subTest(stderr=stderr),self.assertRaises(WorkerError) as caught:
                decode_result('',stderr,1)
            self.assertEqual(caught.exception.code,expected)

    def test_successful_text_mentioning_errors_is_not_a_failure(self):
        result,_=decode_result(json.dumps({'status':'SUCCESS','response':'An EOF or quota error was documented.'}),'',0)
        self.assertIn('documented',result)


if __name__=='__main__':unittest.main()
