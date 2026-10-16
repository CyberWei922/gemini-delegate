import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'server'))
from accounting import summarize, numeric_usage
from host_tools import managed_process
from main import call
from worker import Manager, WorkerError


class AccountingTests(unittest.TestCase):
    def task(self, jid='one', workspace='/project', **changes):
        return dict({'id':jid,'workspace':workspace,'title':'中文整理任务',
                     'status':'completed','attempts':[{'number':1,'usage':{
                         'input_tokens':100,'output_tokens':50,'total_tokens':150,
                         'thinking_tokens':40,'cache_read_tokens':60}}]}, **changes)

    def test_totals_include_all_attempts_once_and_do_not_add_thinking_or_cache(self):
        task = self.task(usage={'total_tokens':99999})
        task['attempts'].append({'number':2,'status':'failed','usage':{
            'input_tokens':10,'output_tokens':5,'total_tokens':15}})
        project = summarize([task,task])['projects'][0]
        self.assertEqual(project['reported_usage']['total_tokens'],165)
        self.assertEqual(project['retry_count'],1)
        self.assertEqual(project['task_count'],1)
        self.assertEqual(project['reported_usage']['thinking_tokens'],40)
        self.assertTrue(project['usage_complete'])

    def test_missing_failed_attempt_is_unknown_instead_of_zero(self):
        task = self.task()
        task['attempts'].insert(0,{'number':1,'status':'failed','error_code':'timeout'})
        project = summarize([task])['projects'][0]
        self.assertEqual(project['reported_usage']['total_tokens'],150)
        self.assertEqual(project['attempts_without_usage'],1)
        self.assertFalse(project['usage_complete'])

    def test_partial_counter_report_cannot_be_declared_complete(self):
        task = self.task()
        task['attempts'].append({'number':2,'usage':{'input_tokens':20}})
        project = summarize([task])['projects'][0]
        self.assertEqual(project['attempts_with_incomplete_token_counts'],1)
        self.assertFalse(project['usage_complete'])

    def test_projects_with_same_name_stay_separate_and_history_is_supported(self):
        first = self.task(workspace='/a/demo',attempts=[],usage={'total_tokens':42})
        second = self.task('two',workspace='/b/demo')
        report = summarize([first,second])
        self.assertEqual(report['project_count'],2)
        self.assertEqual(report['projects'][0]['reported_usage']['total_tokens'],42)
        self.assertFalse(report['projects'][0]['usage_complete'])
        self.assertEqual(summarize([first,second],'/b/demo')['project_count'],1)

    def test_bad_counters_and_private_payloads_are_excluded(self):
        self.assertEqual(numeric_usage({'a':True,'b':float('nan'),'c':-5,'d':'99','e':0}),{'e':0})
        task = self.task(context='PRIVATE_CONTEXT',result='PRIVATE_RESULT',error={'message':'PRIVATE_ERROR'})
        rendered = json.dumps(summarize([task]),ensure_ascii=False)
        for value in ('PRIVATE_CONTEXT','PRIVATE_RESULT','PRIVATE_ERROR'):
            self.assertNotIn(value,rendered)
        self.assertIn('中文整理任务',rendered)

    def test_live_and_unstarted_tasks_do_not_claim_complete_usage(self):
        tasks = [self.task(status='running'),self.task('two',status='queued',attempts=[])]
        project = summarize(tasks)['projects'][0]
        self.assertFalse(project['usage_complete'])
        self.assertEqual(project['attempt_count'],1)

    def test_project_summary_is_not_limited_to_200_or_duplicated_by_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = str(Path(directory).resolve())
            manager = Manager(Path(directory)/'state')
            try:
                for index in range(205):
                    task = self.task(f'{index:016x}',workspace=directory)
                    root = manager.state/'jobs'/task['id'];root.mkdir(parents=True)
                    for name in ('progress.json','metadata.json'):
                        (root/name).write_text(json.dumps(task),encoding='utf-8')
                self.assertEqual(len(manager.task_list(directory)['tasks']),200)
                report = call(manager,'usage_summary',{'workspace':directory})
                self.assertEqual(report['projects'][0]['task_count'],205)
                self.assertEqual(report['projects'][0]['reported_usage']['total_tokens'],205*150)
            finally:
                manager.close()

    def test_cli_exports_named_report_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);state=root/'state';output=root/'中文统计.json'
            cli = Path(__file__).resolve().parents[1]/'scripts/delegate.py'
            env = dict(os.environ,GEMINI_DELEGATE_STATE_DIR=str(state))
            argv = [sys.executable,str(cli),'--usage','--workspace',str(root),'--export',str(output)]
            first = subprocess.run(argv,env=env,capture_output=True,timeout=10)
            self.assertEqual(first.returncode,0,first.stderr.decode('utf-8','replace'))
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['project_count'],0)
            before = output.read_bytes()
            second = subprocess.run(argv,env=env,capture_output=True,timeout=10)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(output.read_bytes(),before)


class ConcurrencyTests(unittest.TestCase):
    def test_configuration_is_bounded_and_parallel_by_default(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ):
            os.environ.pop('GEMINI_DELEGATE_MAX_CONCURRENCY',None)
            manager = Manager(directory)
            try:
                self.assertEqual(manager.status()['max_concurrent_agy_calls'],2)
            finally:
                manager.close()
            for value in (0,3,-1,True,'2.0','bad'):
                with self.assertRaises(WorkerError):
                    Manager(directory,max_concurrency=value)
            with mock.patch.dict(os.environ,{'GEMINI_DELEGATE_MAX_CONCURRENCY':'1'}):
                manager = Manager(directory)
                try:
                    self.assertEqual(manager.status()['max_concurrent_agy_calls'],1)
                finally:
                    manager.close()

    def test_two_slots_allow_two_managers_and_cancel_a_third_waiter(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            managers = [Manager(directory,max_concurrency=2) for _ in range(3)]
            for manager in managers:
                stack.callback(manager.close)
            jobs = [{'cancel':threading.Event(),'status':'queued'} for _ in range(3)]
            with managers[0]._agy_slot(jobs[0],time.monotonic()+3), managers[1]._agy_slot(jobs[1],time.monotonic()+3):
                self.assertNotEqual(jobs[0]['agy_slot'],jobs[1]['agy_slot'])
                timer = threading.Timer(.15,jobs[2]['cancel'].set);timer.start()
                try:
                    with self.assertRaises(WorkerError) as error:
                        with managers[2]._agy_slot(jobs[2],time.monotonic()+2):
                            self.fail('Third concurrent AGY call was allowed')
                    self.assertEqual(error.exception.code,'cancelled')
                finally:
                    timer.cancel()
            jobs[2]['cancel'].clear()
            with managers[2]._agy_slot(jobs[2],time.monotonic()+1):
                pass

    def test_serial_worker_excludes_both_slots_for_new_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            serial, parallel = Manager(directory,max_concurrency=1), Manager(directory,max_concurrency=2)
            try:
                first = {'cancel':threading.Event(),'status':'queued'}
                second = {'cancel':threading.Event(),'status':'queued'}
                with serial._agy_slot(first,time.monotonic()+2):
                    with self.assertRaises(WorkerError) as error:
                        with parallel._agy_slot(second,time.monotonic()+.1):
                            self.fail('Serial worker did not reserve both slots')
                    self.assertEqual(error.exception.code,'timeout')
            finally:
                serial.close();parallel.close()

    def test_two_processes_share_capacity_and_all_tasks_get_fresh_contexts(self):
        with tempfile.TemporaryDirectory(prefix='Gemini 并发 ') as directory:
            root = Path(directory);server=Path(__file__).resolve().parents[1]/'server'
            fake = root/'fake-agy.py';counter=root/'counter.json';gate=root/'go'
            fake.write_text('''import json,sys,time,uuid
from pathlib import Path
sys.path.insert(0,SERVER)
from host_tools import FileLock,atomic_replace
counter=Path(COUNTER);gate=Path(GATE)
assert '--continue' not in sys.argv and '--conversation' not in sys.argv
message=json.loads(sys.stdin.readline())
assert '工作名称：中文任务' in message['message']['content']
def update(delta):
 with FileLock(counter.with_suffix('.lock')) as lock:
  lock.acquire(blocking=True,timeout=5)
  d=json.loads(counter.read_text()) if counter.exists() else {'active':0,'peak':0,'started':0}
  d['active']+=delta;d['started']+=int(delta>0);d['peak']=max(d['peak'],d['active'])
  temp=counter.with_suffix('.tmp');temp.write_text(json.dumps(d));atomic_replace(temp,counter)
update(1)
deadline=time.monotonic()+8
while not gate.exists() and time.monotonic()<deadline:time.sleep(.02)
time.sleep(.1)
update(-1)
print(json.dumps({'status':'SUCCESS','response':'OK','conversation_id':str(uuid.uuid4()),'usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}}))
'''.replace('SERVER',repr(str(server))).replace('COUNTER',repr(str(counter))).replace('GATE',repr(str(gate))),encoding='utf-8')
            helper = root/'helper.py'
            helper.write_text('''import json,sys
sys.path.insert(0,SERVER)
import worker
worker.prepare_agent=lambda *args: None
worker.schedule_title=lambda *args: {'status':'pending'}
from worker import Manager
m=Manager(STATE,AGY,max_concurrency=2)
try:
 ids=[m.submit({'title':'中文任务','instruction':'Return OK','workspace':WORKSPACE,'timeout_seconds':15})['task_id'] for _ in range(2)]
 results=[m.result(jid,15) for jid in ids]
 print(json.dumps(results))
finally:m.close()
'''.replace('SERVER',repr(str(server))).replace('STATE',repr(str(root/'state'))).replace('AGY',repr(str(fake))).replace('WORKSPACE',repr(str(root))),encoding='utf-8')
            with contextlib.ExitStack() as stack:
                processes = [stack.enter_context(managed_process([sys.executable,str(helper)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)) for _ in range(2)]
                deadline = time.monotonic()+8
                counts = {}
                while time.monotonic()<deadline:
                    try:counts=json.loads(counter.read_text())
                    except (OSError,ValueError):pass
                    if counts.get('active')==2:break
                    time.sleep(.02)
                self.assertEqual(counts.get('active'),2,counts)
                time.sleep(.15)
                self.assertEqual(json.loads(counter.read_text())['started'],2)
                gate.touch()
                results = []
                for process in processes:
                    out,err=process.communicate(timeout=12)
                    self.assertEqual(process.returncode,0,err)
                    results.extend(json.loads(out))
                self.assertEqual(json.loads(counter.read_text())['peak'],2)
                self.assertTrue(all(result['status']=='completed' for result in results),results)
                self.assertEqual(len({result['attempts'][0]['agy_conversation_id'] for result in results}),4)


if __name__ == '__main__':
    unittest.main()
