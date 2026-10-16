"""Real pipe delivery, bounded progress and startup-only replay invariants."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from agy_stream import AgyStream
from worker import Manager,WorkerError,run_process


def event(kind,**values):
    return (json.dumps({'event':kind,**values},ensure_ascii=False)+'\n').encode('utf-8')


class ParserTests(unittest.TestCase):
    def test_no_task_bytes_are_written_until_official_init(self):
        code="import json,time,sys;time.sleep(.2);print(json.dumps({'event':'init'}),flush=True);d=sys.stdin.buffer.readline();print(json.dumps({'event':'result','result':{'status':'SUCCESS','response':d.decode().strip()}}),flush=True)"
        s=AgyStream();sent=[]
        def feed(data):s.feed(data);return s.result is not None
        out,err,rc=run_process([sys.executable,'-c',code],Path.home(),5,
                              input_data=b'TASK_DATA\n',on_stdout=feed,
                              input_ready=lambda:s.state.get('initialized'),startup_timeout=2,
                              on_input_sent=sent.append)
        self.assertEqual(s.finish()['response'],'TASK_DATA')
        self.assertEqual(sent,[False,True])

    def test_stalled_startup_times_out_without_submitting_any_task_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'received'
            code='import sys,time;from pathlib import Path;b=sys.stdin.buffer.read(1);Path('+repr(str(marker))+').write_bytes(b);time.sleep(30)'
            sent=[]
            with self.assertRaises(WorkerError) as caught:
                run_process([sys.executable,'-c',code],Path.home(),5,input_data=b'TASK_DATA\n',
                            input_ready=lambda:False,startup_timeout=.5,on_input_sent=sent.append)
            self.assertEqual(caught.exception.details['reported_phase'],'startup')
            self.assertFalse(caught.exception.details['task_input_sent'])
            self.assertFalse(marker.exists())
            self.assertEqual(sent,[False])

    def test_split_utf8_chunks_and_private_text_are_not_progress_metadata(self):
        s=AgyStream()
        data=event('init',conversation_id='native')+event('step_update',step_update={
            'step_index':1,'step_type':'agent_response','state':'ACTIVE','text_delta':'私密😀正文'})
        for byte in data:s.feed(bytes([byte]))
        self.assertEqual(s.state['event_count'],2)
        self.assertTrue(s.state['processing_started'])
        self.assertNotIn('私密',json.dumps(s.snapshot(),ensure_ascii=False))
        self.assertNotIn('text_delta',s.snapshot())

    def test_init_and_input_echo_do_not_count_as_processing(self):
        s=AgyStream();s.feed(event('init',conversation_id='native'))
        s.feed(event('step_update',step_update={'step_type':'user_input','step_index':0,'state':'DONE'}))
        self.assertFalse(s.state['processing_started'])
        self.assertEqual(s.state['conversation_id'],'native')
        self.assertEqual(s.state['phase'],'awaiting_model')

    def test_file_read_steps_are_counted_once_per_index(self):
        s=AgyStream()
        for status in ('ACTIVE','DONE'):
            s.feed(event('step_update',step_update={'step_index':2,'state':status,'step_type':'tool','tool_name':'view_file'}))
        self.assertEqual(s.state['file_read_steps'],1)

    def test_step_usage_is_deduplicated_and_terminal_usage_is_separate(self):
        s=AgyStream()
        for total in [12,12,10]:
            s.feed(event('step_update',step_update={'step_type':'agent_response','state':'DONE',
                'step_index':1,'usage':{'input_tokens':10,'output_tokens':2,'total_tokens':total}}))
        self.assertEqual(s.partial_usage()['total_tokens'],12)
        s.feed(event('result',result={'status':'SUCCESS','response':'OK','usage':{'total_tokens':20}}))
        self.assertEqual(s.finish()['usage']['total_tokens'],20)

    def test_invalid_or_duplicate_terminal_and_truncated_events_rejected(self):
        for raw in [b'{"event":"init","event":"result"}\n',b'{"event":',
                    event('result',result={})+event('result',result={}),b'[]\n']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                s=AgyStream();s.feed(raw);s.finish()

    def test_real_process_receives_large_stdin_without_argv_or_deadlock(self):
        prompt='中文😀\n'*30000
        body=(json.dumps({'event':'user','message':{'content':prompt}},ensure_ascii=False)+'\n').encode()
        code="import sys,json;d=json.loads(sys.stdin.buffer.readline());print(json.dumps({'event':'result','result':{'status':'SUCCESS','response':str(len(d['message']['content']))}}),flush=True)"
        s=AgyStream()
        out,err,rc=run_process([sys.executable,'-c',code],Path.home(),5,
                              input_data=body,on_stdout=s.feed)
        self.assertEqual(rc,0);self.assertEqual(s.finish()['response'],str(len(prompt)))

    def test_complete_terminal_does_not_wait_for_a_lingering_process(self):
        code="import json,time;print(json.dumps({'event':'result','result':{'status':'SUCCESS','response':'COMPLETE'}}),flush=True);time.sleep(30)"
        s=AgyStream()
        def feed(data):s.feed(data);return s.result is not None
        before=time.monotonic()
        out,err,rc=run_process([sys.executable,'-c',code],Path.home(),5,on_stdout=feed)
        self.assertLess(time.monotonic()-before,3)
        self.assertEqual(rc,0)
        self.assertEqual(s.finish()['response'],'COMPLETE')
        self.assertEqual(s.snapshot()['terminal_status'],'SUCCESS')

    def test_terminal_error_never_becomes_success_when_process_lingers(self):
        from worker import decode_result
        code="import json,time;print(json.dumps({'event':'result','result':{'status':'ERROR','error':'streamGenerateContent: EOF','response':'PARTIAL'}}),flush=True);time.sleep(30)"
        s=AgyStream()
        def feed(data):s.feed(data);return s.result is not None
        out,err,rc=run_process([sys.executable,'-c',code],Path.home(),5,on_stdout=feed)
        self.assertEqual(s.snapshot()['terminal_status'],'ERROR')
        with self.assertRaises(WorkerError):decode_result(json.dumps(s.finish()),err,rc)

    def test_terminal_success_still_rejects_cli_partial_output_warning(self):
        from worker import decode_result
        code="import json,time,sys;print('print timeout; returning partial output',file=sys.stderr,flush=True);print(json.dumps({'event':'result','result':{'status':'SUCCESS','response':'PARTIAL'}}),flush=True);time.sleep(30)"
        s=AgyStream()
        def feed(data):s.feed(data);return s.result is not None
        out,err,rc=run_process([sys.executable,'-c',code],Path.home(),5,on_stdout=feed)
        with self.assertRaises(WorkerError) as caught:decode_result(json.dumps(s.finish()),err,rc)
        self.assertEqual(caught.exception.code,'timeout')


class WorkflowStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.m=Manager(self.root/'state',agy='fake');self.addCleanup(self.m.close)
        p=mock.patch('worker.prepare_agent');p.start();self.addCleanup(p.stop)
        p=mock.patch.object(self.m,'_retry_backoff',return_value=False);p.start();self.addCleanup(p.stop)

    def task(self,run,**options):
        with mock.patch('worker.run_process',side_effect=run) as calls:
            jid=self.m.submit({'instruction':'Return OK','workspace':str(self.root),**options})['task_id']
            r=self.m.result(jid,5)
        return r,calls

    def test_live_progress_visible_to_another_manager_before_result(self):
        entered=threading.Event();release=threading.Event()
        def run(*args,**kw):
            kw['on_stdout'](event('init',conversation_id='native'))
            kw['on_stdout'](event('step_update',step_update={'step_index':1,'step_type':'agent_response','state':'ACTIVE','text_delta':'SECRET_PARTIAL'}))
            entered.set();release.wait(3)
            terminal=event('result',result={'status':'SUCCESS','response':'OK','conversation_id':'native'})
            kw['on_stdout'](terminal)
            return '', '',0
        with mock.patch('worker.run_process',side_effect=run),mock.patch('worker.schedule_title',return_value={'status':'pending'}):
            jid=self.m.submit({'instruction':'Return OK','workspace':str(self.root)})['task_id']
            self.assertTrue(entered.wait(2))
            reader=Manager(self.m.state,agy='fake')
            try:
                snapshot=reader.task_list(str(self.root))['tasks'][0]
                self.assertEqual(snapshot['progress']['phase'],'processing')
                self.assertNotIn('SECRET_PARTIAL',json.dumps(snapshot))
            finally:reader.close();release.set()
            r=self.m.result(jid,5)
        self.assertEqual(r['status'],'completed',r)
        self.assertTrue(r['progress']['processing_started'])
        self.assertEqual(r['attempts'][0]['agy_conversation_id'],'native')

    def test_early_preflight_after_init_retries_by_default_then_succeeds(self):
        count=[0]
        def run(*args,**kw):
            count[0]+=1
            kw['on_stdout'](event('init',conversation_id='init-'+str(count[0])))
            result=({'status':'ERROR','error':'Eligibility check failed: userinfo EOF'} if count[0]<3
                    else {'status':'SUCCESS','response':'OK'})
            kw['on_stdout'](event('result',result=result))
            return '','',int(count[0]<3)
        r,calls=self.task(run)
        self.assertEqual(r['status'],'completed',r);self.assertEqual(calls.call_count,3)
        self.assertTrue(all(a['retry_eligible'] for a in r['attempts'][:2]))

    def test_mid_task_eof_discards_output_and_never_retries(self):
        def run(*args,**kw):
            kw['on_stdout'](event('init',conversation_id='native'))
            kw['on_stdout'](event('step_update',step_update={'step_index':1,'state':'DONE','step_type':'agent_response',
                'text_delta':'SECRET_PARTIAL','usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}}))
            raise WorkerError('transient_error','network EOF',{'reported_phase':'startup'})
        r,calls=self.task(run)
        self.assertEqual(calls.call_count,1);self.assertEqual(r['handoff']['reason'],'mid_task_failure')
        self.assertIsNone(r['result']);self.assertEqual(r['changes'],[])
        self.assertNotIn('SECRET_PARTIAL',json.dumps(r))
        self.assertTrue(r['attempts'][0]['usage_is_partial'])
        summary=self.m.usage_summary(str(self.root))['projects'][0]
        self.assertEqual(summary['reported_usage']['total_tokens'],12)
        self.assertFalse(summary['usage_complete'])

    def test_stream_eof_without_result_never_uses_partial_text(self):
        def run(*args,**kw):
            kw['on_stdout'](event('step_update',step_update={'step_index':1,'state':'ACTIVE','step_type':'agent_response','text_delta':'PARTIAL'}))
            return '','',0
        r,calls=self.task(run)
        self.assertEqual(calls.call_count,1);self.assertEqual(r['status'],'failed')
        self.assertIsNone(r['result']);self.assertEqual(r['error']['code'],'invalid_stream')

    def test_complete_terminal_usage_does_not_double_count_step_usage(self):
        def run(*args,**kw):
            kw['on_stdout'](event('step_update',step_update={'step_index':1,'state':'DONE','step_type':'agent_response','usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}}))
            kw['on_stdout'](event('result',result={'status':'SUCCESS','response':'OK','usage':{'input_tokens':15,'output_tokens':5,'total_tokens':20}}))
            return '','',0
        r,_=self.task(run)
        self.assertEqual(r['usage']['total_tokens'],20);self.assertNotIn('usage_is_partial',r['attempts'][0])

    def test_continuous_real_progress_never_renews_the_deadline(self):
        fake=self.root/'progress.py'
        fake.write_text('''import json,sys,time
print(json.dumps({'event':'init','conversation_id':'native'}),flush=True)
json.loads(sys.stdin.readline())
for i in range(300):
 print(json.dumps({'event':'step_update','step_update':{'step_index':1,'step_type':'agent_response','state':'ACTIVE','text_delta':'PRIVATE_INTERMEDIATE'}}),flush=True)
 time.sleep(.03)
''',encoding='utf-8')
        manager=Manager(self.root/'progress-state',agy=str(fake),attempt_seconds=.3)
        try:
            before=time.monotonic()
            jid=manager.submit({'instruction':'Return OK','workspace':str(self.root),'timeout_seconds':15})['task_id']
            result=manager.result(jid,7)
            self.assertLess(time.monotonic()-before,6)
            self.assertEqual(result['status'],'failed',result)
            self.assertEqual(len(result['attempts']),1)
            self.assertTrue(result['progress']['processing_started'])
            self.assertIsNone(result['result'])
            self.assertNotIn('PRIVATE_INTERMEDIATE',json.dumps(result))
        finally:manager.close()


if __name__=='__main__':unittest.main()
