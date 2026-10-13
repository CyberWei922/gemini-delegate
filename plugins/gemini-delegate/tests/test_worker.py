import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from worker import Manager, WorkerError, decode_result, digest, run_process, validate_schema, public_url, MODEL
from main import call


class ResultTests(unittest.TestCase):
    def error(self,code,fn,*args):
        with self.assertRaises(WorkerError) as c:fn(*args)
        self.assertEqual(c.exception.code,code)

    def test_rejects_false_success_and_partial_output(self):
        self.error('empty_result',decode_result,json.dumps({'status':'SUCCESS','response':''}),'',0)
        self.error('permission_denied',decode_result,json.dumps({'status':'SUCCESS','response':'hello','denied_actions':[{'action':'read_url'}]}),'',0)
        self.error('timeout',decode_result,json.dumps({'status':'SUCCESS','response':'partial'}),'[agy] print timeout after 1m; returning partial output',0)
        self.error('agy_failed',decode_result,json.dumps({'status':'ERROR','response':'partial'}),'',0)

    def test_exact_json_coverage_and_missing_fields(self):
        schema={'type':'object','properties':{'names':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'string'}}},'required':['names'],'additionalProperties':False}
        env={'status':'SUCCESS','response':'```json\n{"names":["Alice","Bob"]}\n```'}
        value,_=decode_result(json.dumps(env),'',0,'json',schema)
        self.assertEqual(value,{'names':['Alice','Bob']})
        self.error('invalid_result',validate_schema,{'names':['Alice']},schema)
        self.error('invalid_result',validate_schema,{},schema)
        self.error('invalid_result',decode_result,json.dumps({'status':'SUCCESS','response':'{"names":['}),'',0,'json',schema)

    def test_structured_output_used_and_unsupported_schema_rejected(self):
        env={'status':'SUCCESS','response':'explanatory text','structured_output':{'n':3}}
        result,_=decode_result(json.dumps(env),'',0,'json',{'type':'object','properties':{'n':{'type':'integer'}},'required':['n']})
        self.assertEqual(result,{'n':3})
        self.error('unsupported_schema',validate_schema,{}, {'$ref':'#/$defs/x'})

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        self.error('invalid_envelope',decode_result,'{"status":"ERROR","status":"SUCCESS","response":"ok"}','',0)
        self.error('invalid_result',decode_result,json.dumps({'status':'SUCCESS','response':'{"n":NaN}'}),'',0,'json')

    def test_private_and_credential_urls_rejected(self):
        self.error('invalid_url',public_url,'http://127.0.0.1/')
        self.error('invalid_url',public_url,'https://user:password@example.com/')
        self.error('invalid_url',public_url,'https://example.com/?api_key=x')
        self.error('invalid_url',public_url,'file:///etc/passwd')


class ProcessTests(unittest.TestCase):
    def test_hard_timeout_reaps_descendants(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'pid'
            code='import subprocess,time,pathlib; p=subprocess.Popen(["'+sys.executable+'","-c","import time; time.sleep(30)"]); pathlib.Path("'+str(marker)+'").write_text(str(p.pid)); time.sleep(30)'
            start=time.monotonic()
            with self.assertRaises(WorkerError)as c:run_process([sys.executable,'-c',code],d,.6)
            self.assertEqual(c.exception.code,'timeout')
            self.assertLess(time.monotonic()-start,5)
            if marker.exists():
                pid=int(marker.read_text())
                # ps can briefly report a zombie while the OS reaps it; it must not be running.
                result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
                self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith('Z'))

    def test_cancel_stops_inflight_process(self):
        event=threading.Event()
        timer=threading.Timer(.3,event.set);timer.start()
        try:
            with self.assertRaises(WorkerError)as c:run_process([sys.executable,'-c','import time;time.sleep(30)'],Path.home(),20,event)
            self.assertEqual(c.exception.code,'cancelled')
        finally:timer.cancel()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.monitor = mock.patch.object(Manager,'task_monitor',return_value={'dashboard_url':'http://127.0.0.1/example'})
        self.monitor.start()
        self.addCleanup(self.monitor.stop)
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.source=self.workspace/'sample.txt';self.source.write_text('old\n')
        self.worker=self.root/'fake-agy'
        self.worker.write_text('#!'+sys.executable+'\nimport json,sys\nprint(json.dumps({"status":"SUCCESS","response":json.dumps({"summary":"Changed sample","files":[{"path":"sample.txt","content":"new\\n"}]}),"usage":{"input_tokens":100,"output_tokens":20}}))\n')
        self.worker.chmod(0o700)
        self.manager=Manager(self.root/'state',str(self.worker),attempt_seconds=2)

    def tearDown(self):
        self.manager.close();self.temp.cleanup()

    def task(self):
        info=call(self.manager,'delegate_task',{'instruction':'Replace old with new','workspace':str(self.workspace),'input_files':['sample.txt'],'response_type':'edit','timeout_seconds':15})
        result=self.manager.result(info['task_id'],10)
        self.assertEqual(result['status'],'completed',result)
        return info['task_id'],result

    def test_edit_is_staged_then_applied_with_backup(self):
        jid,result=self.task()
        self.assertEqual(self.source.read_text(),'old\n')
        self.assertEqual(result['model'],MODEL)
        with self.assertRaises(WorkerError):call(self.manager,'apply_task_changes',{'task_id':jid,'reviewed':False})
        applied=call(self.manager,'apply_task_changes',{'task_id':jid,'reviewed':True})
        self.assertEqual(self.source.read_text(),'new\n')
        self.assertEqual((Path(applied['backup_directory'])/'sample.txt').read_text(),'old\n')

    def test_conflict_and_tamper_fail_without_overwrite(self):
        jid,result=self.task()
        self.source.write_text('user changed\n')
        with self.assertRaises(WorkerError)as c:self.manager.apply(jid)
        self.assertEqual(c.exception.code,'conflict')
        self.assertEqual(self.source.read_text(),'user changed\n')
        self.source.write_text('old\n')
        Path(result['changes'][0]['artifact']).write_text('tampered\n')
        with self.assertRaises(WorkerError)as c:self.manager.apply(jid)
        self.assertEqual(c.exception.code,'invalid_changes')
        self.assertEqual(self.source.read_text(),'old\n')

    def test_inputs_outside_scope_and_secrets_rejected(self):
        outsider=self.root/'outside.txt';outsider.write_text('outside')
        for filename in [str(outsider),'.env']:
            (self.workspace/'.env').write_text('SECRET=x')
            with self.assertRaises(WorkerError):self.manager.submit({'instruction':'read','workspace':str(self.workspace),'input_files':[filename]})

    def test_bad_output_retries_once_then_fails(self):
        self.worker.write_text('#!'+sys.executable+'\nimport json\nprint(json.dumps({"status":"SUCCESS","response":""}))\n')
        jid=self.manager.submit({'instruction':'extract','timeout_seconds':15})['task_id']
        result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(result['attempts']),2)
        self.assertEqual(result['error']['code'],'empty_result')

    def test_metadata_survives_server_restart_without_input_bundle(self):
        jid,result=self.task()
        # Completion notification can precede the final metadata write briefly.
        path=self.manager.state/'jobs'/jid/'metadata.json'
        for _ in range(50):
            if path.exists():break
            time.sleep(.01)
        reopened=Manager(self.manager.state,str(self.worker))
        try:
            self.assertEqual(reopened.result(jid)['status'],'completed')
            reopened.apply(jid)
            self.assertEqual(self.source.read_text(),'new\n')
        finally:reopened.close()
        self.assertFalse((path.parent/'input.json').exists())

    def test_shared_agy_slot_wait_is_cancellable_across_managers(self):
        second=Manager(self.manager.state,str(self.worker))
        owner={'cancel':threading.Event(),'status':'running'}
        waiting={'cancel':threading.Event(),'status':'queued'}
        try:
            with self.manager._agy_slot(owner,time.monotonic()+3):
                timer=threading.Timer(.2,waiting['cancel'].set);timer.start()
                try:
                    with self.assertRaises(WorkerError)as c:
                        with second._agy_slot(waiting,time.monotonic()+2):
                            self.fail('Concurrent AGY slot was granted')
                    self.assertEqual(c.exception.code,'cancelled')
                finally:timer.cancel()
        finally:second.close()

    def test_live_task_records_are_project_scoped_and_keep_preview(self):
        self.worker.write_text('#!'+sys.executable+'\nimport time,json\ntime.sleep(.4)\nprint(json.dumps({"status":"SUCCESS","response":"DONE"}))\n')
        info=call(self.manager,'delegate_task',{'title':'Visible task','instruction':'Return DONE','context':'PRIVATE_CONTEXT','workspace':str(self.workspace),'timeout_seconds':15})
        early=call(self.manager,'list_tasks',{'workspace':str(self.workspace)})
        self.assertEqual(len(early['tasks']),1)
        self.assertEqual(early['tasks'][0]['title'],'Visible task')
        self.assertNotEqual(early['tasks'][0]['status'],'completed')
        self.assertEqual(call(self.manager,'list_tasks',{'workspace':str(self.root)})['tasks'],[])
        result=self.manager.result(info['task_id'],10)
        self.assertEqual(result['status'],'completed')
        later=call(self.manager,'list_tasks',{'workspace':str(self.workspace)})
        self.assertEqual(later['tasks'][0]['result_preview'],'"DONE"')
        text=(self.manager.state/'jobs'/info['task_id']/'progress.json').read_text()
        self.assertNotIn('PRIVATE_CONTEXT',text)
        self.assertIn('agy_started_at',later['tasks'][0])

    def test_explicit_runtime_environment_paths_are_honored(self):
        state=self.root/'custom-runtime'
        with mock.patch.dict(os.environ,{'GEMINI_DELEGATE_STATE_DIR':str(state),'GEMINI_DELEGATE_AGY':str(self.worker)}):
            configured=Manager()
        try:
            self.assertEqual(configured.state,state.resolve())
            self.assertEqual(configured.agy,str(self.worker))
        finally:configured.close()

    def test_edit_preview_excludes_full_replacement(self):
        jid,result=self.task()
        self.manager.apply(jid)
        task=call(self.manager,'list_tasks',{})['tasks'][0]
        self.assertNotIn('new\\n',task['result_preview'])
        self.assertIn('sample.txt',task['result_preview'])
        self.assertIn('applied_at',task)


if __name__=='__main__':unittest.main()
