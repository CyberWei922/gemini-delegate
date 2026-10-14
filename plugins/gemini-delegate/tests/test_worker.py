import json
import contextlib
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
from worker import (Manager, WorkerError, decode_result, digest, run_process,
                    validate_schema, public_url, text_chunks, write_input_bundle,
                    INPUT_CHUNK_BYTES, MODEL)
from main import call
from host_tools import WINDOWS, process_alive


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
    def test_output_limit_stops_streaming_producer(self):
        code='import sys,time;sys.stdout.buffer.write(b"x"*3000000);sys.stdout.flush();time.sleep(30)'
        started=time.monotonic()
        with self.assertRaises(WorkerError) as caught:
            run_process([sys.executable,'-c',code],Path.home(),10)
        self.assertEqual(caught.exception.code,'output_limit')
        self.assertLess(time.monotonic()-started,5)

    def test_timeout_keeps_safe_output_size_diagnostics(self):
        code='import sys,time; print("partial",flush=True); print("diagnostic",file=sys.stderr,flush=True); time.sleep(30)'
        with self.assertRaises(WorkerError) as caught:
            run_process([sys.executable,'-c',code],Path.home(),.4)
        self.assertEqual(caught.exception.code,'timeout')
        self.assertGreater(caught.exception.details['stdout_bytes'],0)
        self.assertGreater(caught.exception.details['stderr_bytes'],0)
        self.assertNotIn('partial',json.dumps(caught.exception.details))

    def test_hard_timeout_reaps_descendants(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'pid'
            code='import subprocess,time,pathlib,sys; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); pathlib.Path('+repr(str(marker))+').write_text(str(p.pid)); time.sleep(30)'
            start=time.monotonic()
            with self.assertRaises(WorkerError)as c:run_process([sys.executable,'-c',code],d,.6)
            self.assertEqual(c.exception.code,'timeout')
            self.assertLess(time.monotonic()-start,5)
            if marker.exists():
                pid=int(marker.read_text(encoding='utf-8'))
                # ps can briefly report a zombie while the OS reaps it; it must not be running.
                if WINDOWS:
                    self.assertFalse(process_alive(pid))
                else:
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
    def test_os_error_preserves_codes_without_private_command_data(self):
        error=OSError(13,'PRIVATE_COMMAND_DATA')
        error.winerror=5
        with mock.patch('worker.run_process',side_effect=error):
            jid=self.manager.submit({'instruction':'return OK','workspace':str(self.workspace)})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error']['code'],'os_error')
        self.assertEqual(result['error']['details'],{'errno':13,'winerror':5})
        self.assertNotIn('PRIVATE_COMMAND_DATA',json.dumps(result))

    def setUp(self):
        self.monitor = mock.patch.object(Manager,'task_monitor',return_value={'dashboard_url':'http://127.0.0.1/example'})
        self.monitor.start()
        self.addCleanup(self.monitor.stop)
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.source=self.workspace/'sample.txt';self.source.write_text('old\n', encoding='utf-8')
        self.worker=self.root/'fake-agy.py'
        self.worker.write_text('#!'+sys.executable+'\nimport json,sys\nprint(json.dumps({"status":"SUCCESS","response":json.dumps({"summary":"Changed sample","files":[{"path":"sample.txt","content":"new\\n"}]}),"usage":{"input_tokens":100,"output_tokens":20}}))\n', encoding='utf-8')
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
        self.assertEqual(self.source.read_text(encoding='utf-8'),'old\n')
        self.assertEqual(result['model'],MODEL)
        with self.assertRaises(WorkerError):call(self.manager,'apply_task_changes',{'task_id':jid,'reviewed':False})
        applied=call(self.manager,'apply_task_changes',{'task_id':jid,'reviewed':True})
        self.assertEqual(self.source.read_text(encoding='utf-8'),'new\n')
        self.assertEqual((Path(applied['backup_directory'])/'sample.txt').read_text(encoding='utf-8'),'old\n')

    def test_conflict_and_tamper_fail_without_overwrite(self):
        jid,result=self.task()
        self.source.write_text('user changed\n', encoding='utf-8')
        with self.assertRaises(WorkerError)as c:self.manager.apply(jid)
        self.assertEqual(c.exception.code,'conflict')
        self.assertEqual(self.source.read_text(encoding='utf-8'),'user changed\n')
        self.source.write_text('old\n', encoding='utf-8')
        Path(result['changes'][0]['artifact']).write_text('tampered\n', encoding='utf-8')
        with self.assertRaises(WorkerError)as c:self.manager.apply(jid)
        self.assertEqual(c.exception.code,'invalid_changes')
        self.assertEqual(self.source.read_text(encoding='utf-8'),'old\n')

    def test_inputs_outside_scope_and_secrets_rejected(self):
        outsider=self.root/'outside.txt';outsider.write_text('outside', encoding='utf-8')
        for filename in [str(outsider),'.env']:
            (self.workspace/'.env').write_text('SECRET=x', encoding='utf-8')
            with self.assertRaises(WorkerError):self.manager.submit({'instruction':'read','workspace':str(self.workspace),'input_files':[filename]})

    def test_bad_output_retries_once_then_fails(self):
        self.worker.write_text('#!'+sys.executable+'\nimport json\nprint(json.dumps({"status":"SUCCESS","response":""}))\n', encoding='utf-8')
        jid=self.manager.submit({'instruction':'extract','timeout_seconds':15})['task_id']
        result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(result['attempts']),2)
        self.assertEqual(result['error']['code'],'empty_result')

    def test_default_attempt_can_use_more_than_75_seconds(self):
        self.manager.attempt_seconds=None
        envelope=json.dumps({'status':'SUCCESS','response':'OK'})
        # With no elapsed clock tick, (76.013+180)-76.013 rounds above 180.
        with mock.patch('worker.time.monotonic',return_value=76.013), mock.patch('worker.run_process',return_value=(envelope,'',0)) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':180})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        self.assertGreater(process.call_args.args[2],175)
        self.assertLessEqual(process.call_args.args[2],180)
        self.assertGreater(result['attempts'][0]['timeout_seconds'],175)

    def test_execution_budget_is_calculated_after_slot_wait(self):
        self.manager.attempt_seconds=None
        original_slot=self.manager._agy_slot
        @contextlib.contextmanager
        def delayed_slot(job,deadline):
            time.sleep(.2)
            with original_slot(job,deadline):
                yield
        envelope=json.dumps({'status':'SUCCESS','response':'OK'})
        with mock.patch.object(self.manager,'_agy_slot',delayed_slot), mock.patch('worker.run_process',return_value=(envelope,'',0)) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        self.assertLess(process.call_args.args[2],14.9)
        self.assertLess(result['attempts'][0]['timeout_seconds'],14.9)

    def test_timeout_does_not_retry_the_same_default_budget(self):
        self.manager.attempt_seconds=None
        with mock.patch('worker.run_process',side_effect=WorkerError('timeout','deadline')) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error']['code'],'timeout')
        self.assertEqual(process.call_count,1)
        self.assertFalse(result['attempts'][0]['usage_reported'])

    def test_explicit_timeout_retry_gets_a_larger_bounded_budget(self):
        envelope=json.dumps({'status':'SUCCESS','response':'OK'})
        with mock.patch('worker.run_process',side_effect=[WorkerError('timeout','deadline'),(envelope,'',0)]) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':45,'attempt_timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        limits=[entry.args[2] for entry in process.call_args_list]
        self.assertAlmostEqual(limits[0],17,places=2)
        self.assertAlmostEqual(limits[1],32,places=2)
        self.assertEqual(len(result['attempts']),2)
        self.assertLess(sum(item['elapsed_seconds'] for item in result['attempts']),45)

    def test_retry_slot_wait_cannot_create_a_shorter_timeout_attempt(self):
        clock=[0]
        slots=[0]
        original_slot=self.manager._agy_slot
        @contextlib.contextmanager
        def contended_slot(job,deadline):
            slots[0]+=1
            if slots[0]==2:
                clock[0]=25
            with original_slot(job,deadline):
                yield
        def timed_out(*args):
            clock[0]=12
            raise WorkerError('timeout','deadline')
        with mock.patch('worker.time.monotonic',side_effect=lambda:clock[0]), mock.patch.object(self.manager,'_agy_slot',contended_slot), mock.patch('worker.run_process',side_effect=timed_out) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':30,'attempt_timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error']['code'],'timeout')
        self.assertEqual(process.call_count,1)
        self.assertEqual(len(result['attempts']),1)
        self.assertEqual(slots[0],2)

    def test_timeout_does_not_retry_with_an_equal_or_shorter_budget(self):
        with mock.patch('worker.run_process',side_effect=WorkerError('timeout','deadline')) as process:
            jid=self.manager.submit({'instruction':'Return OK','timeout_seconds':15,'attempt_timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(process.call_count,1)

    def test_json_retry_explains_the_validation_error(self):
        bad=json.dumps({'status':'SUCCESS','response':'{"check":'})
        good=json.dumps({'status':'SUCCESS','response':'{"check":"OK"}'})
        with mock.patch('worker.run_process',side_effect=[(bad,'',0),(good,'',0)]) as process:
            jid=call(self.manager,'delegate_task',{'instruction':'Return JSON','response_type':'json','timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        second=process.call_args_list[1].args[0]
        prompt=second[second.index('-p')+1]
        self.assertIn('invalid_result',prompt)
        self.assertIn('Expected a complete JSON response',prompt)

    def test_file_snapshots_are_lossless_bounded_and_cleaned_on_timeout(self):
        original=('一段原始代码\n' * 2500 + '无换行😀' * 3500).encode('utf-8')
        self.source.write_bytes(original)
        self.manager.attempt_seconds=None
        def inspect(argv,root,*args):
            root=Path(root)
            manifest=json.loads((root/'input.json').read_text(encoding='utf-8'))
            self.assertGreater(len((root/'input.json').read_text(encoding='utf-8').splitlines()),1)
            self.assertNotIn('content',manifest['files'][0])
            self.assertLessEqual((root/'input.json').stat().st_size,INPUT_CHUNK_BYTES)
            parts=manifest['files'][0]['parts']
            self.assertGreater(len(parts),1)
            restored=b''
            for item in parts:
                path=root/item['file'];body=path.read_bytes()
                self.assertEqual(item['byte_offset'],len(restored))
                self.assertLessEqual(len(body),INPUT_CHUNK_BYTES)
                self.assertEqual(body.decode('utf-8').encode('utf-8'),body)
                if not WINDOWS:self.assertEqual(path.stat().st_mode & 0o777,0o600)
                self.assertEqual(item['sha256'],digest(body))
                restored+=body
            self.assertEqual(restored,original)
            raise WorkerError('timeout','deadline')
        with mock.patch('worker.run_process',side_effect=inspect):
            jid=self.manager.submit({'instruction':'Read the file','workspace':str(self.workspace),'input_files':['sample.txt'],'timeout_seconds':15})['task_id']
            result=self.manager.result(jid,10)
        self.assertEqual(result['error']['code'],'timeout',result)
        self.assertFalse((self.manager.state/'jobs'/jid/'inputs').exists())
        self.assertFalse((self.manager.state/'jobs'/jid/'input.json').exists())
        self.assertEqual(self.source.read_bytes(),original)

    def test_empty_and_unicode_text_chunks_round_trip(self):
        self.assertEqual(list(text_chunks('')),[])
        original='头部\r\n'+'😀中文' * 300
        chunks=list(text_chunks(original,97))
        self.assertEqual(b''.join(body for offset,body in chunks).decode('utf-8'),original)
        self.assertTrue(all(len(body)<=97 for offset,body in chunks))
        self.assertTrue(all(body.decode('utf-8') for offset,body in chunks))

    def test_manifest_parts_cover_context_web_and_search(self):
        root=self.root/'bundle';root.mkdir()
        bundle={'instruction':'Extract data','context':'上下文\n'*5000,
                'files':[],'web_sources':[{'url':'https://example.com','text':'网页\n'*10000,'sha256':'hash'}],
                'search_results':'Source A\nSource B'}
        manifest=write_input_bundle(root,bundle)
        def restore(parts):
            return b''.join((root/p['file']).read_bytes() for p in parts).decode('utf-8')
        self.assertEqual(restore(manifest['context_parts']),bundle['context'])
        self.assertEqual(restore(manifest['search_result_parts']),bundle['search_results'])
        self.assertEqual(restore(manifest['web_sources'][0]['parts']),bundle['web_sources'][0]['text'])
        self.assertEqual(manifest['web_sources'][0]['url'],'https://example.com')

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
            self.assertEqual(self.source.read_text(encoding='utf-8'),'new\n')
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
        self.worker.write_text('#!'+sys.executable+'\nimport time,json\ntime.sleep(.4)\nprint(json.dumps({"status":"SUCCESS","response":"DONE"}))\n', encoding='utf-8')
        info=call(self.manager,'delegate_task',{'title':'Visible task','instruction':'Return DONE','context':'PRIVATE_CONTEXT','workspace':str(self.workspace),'timeout_seconds':15})
        early=call(self.manager,'list_tasks',{'workspace':str(self.workspace)})
        self.assertEqual(len(early['tasks']),1)
        self.assertEqual(early['tasks'][0]['title'],'Visible task')
        self.assertNotEqual(early['tasks'][0]['status'],'completed')
        self.assertEqual(call(self.manager,'list_tasks',{'workspace':str(self.root)})['tasks'],[])
        result=self.manager.result(info['task_id'],10)
        self.assertEqual(result['status'],'completed',result.get('error'))
        later=call(self.manager,'list_tasks',{'workspace':str(self.workspace)})
        self.assertEqual(later['tasks'][0]['result_preview'],'"DONE"')
        text=(self.manager.state/'jobs'/info['task_id']/'progress.json').read_text(encoding='utf-8')
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
