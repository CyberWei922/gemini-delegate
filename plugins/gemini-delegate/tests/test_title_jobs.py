import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from worker import Manager
from title_jobs import merge_title, write_private, run


class TitleJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.state=self.root/'state'
        self.job=self.state/'jobs'/'aaaaaaaaaaaaaaaa'
        self.job.mkdir(parents=True)

    def task(self):
        return {'id':'aaaaaaaaaaaaaaaa','title':'中文任务','status':'completed','result':'OK',
                'attempts':[{'agy_conversation_id':'native-id'}],'usage':{'total_tokens':12}}

    def test_sidecar_updates_only_matching_title_and_conversation(self):
        data=self.task()
        for title,cid in [('OTHER','native-id'),('中文任务','other')]:
            write_private(self.job/'native-title.json',{'status':'set','title':title,'conversation_id':cid})
            self.assertNotIn('native_title',merge_title(self.job,data))
        write_private(self.job/'native-title.json',{'status':'set','title':'中文任务','conversation_id':'native-id'})
        updated=merge_title(self.job,data)
        self.assertEqual(updated['native_title']['status'],'set')
        self.assertEqual(updated['result'],'OK');self.assertEqual(updated['usage'],data['usage'])
        self.assertNotIn('native_title',data['attempts'][0])

    def test_background_helper_has_no_model_prompt_or_model_slot(self):
        request=self.job/'native-title-request.json'
        write_private(request,{'agy':'fake','workspace':str(self.root),'conversation_id':'native-id','title':'中文任务'})
        def rename(*args):
            manager=Manager(self.state,agy='fake',max_concurrency=1)
            try:
                import threading
                with manager._agy_slot({'cancel':threading.Event(),'status':'queued'},time.monotonic()+1):pass
            finally:manager.close()
            return {'status':'set','title':'中文任务','conversation_id':'native-id'}
        with mock.patch('title_jobs.rename_conversation',side_effect=rename) as operation:
            run(request)
        self.assertFalse(request.exists())
        self.assertEqual(operation.call_count,1)
        self.assertEqual(json.loads((self.job/'native-title.json').read_text())['status'],'set')

    def test_lost_helper_does_not_leave_pending_forever_or_fail_model_work(self):
        data=self.task()
        data['native_title']={'status':'pending','title':data['title'],
            'conversation_id':'native-id','queued_at':time.time()-36}
        result=merge_title(self.job,data)
        self.assertEqual(result['native_title']['status'],'failed')
        self.assertEqual(result['attempts'][0]['native_title']['status'],'failed')
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['result'],'OK')
        self.assertEqual(data['native_title']['status'],'pending')

    @unittest.skipIf(os.name=='nt','Windows native naming is explicitly unsupported')
    def test_model_result_and_client_shutdown_do_not_wait_for_naming(self):
        fake=self.root/'fake-tui.py'
        fake.write_text('''import sys,time
assert '--conversation' in sys.argv and '-p' not in sys.argv
time.sleep(2)
print('? for shortcuts',flush=True)
assert sys.stdin.readline().strip()=='/rename 中文任务'
print('Conversation renamed to: 中文任务',flush=True)
assert sys.stdin.readline().strip()=='/exit'
''',encoding='utf-8')
        manager=Manager(self.state,agy=str(fake))
        envelope=json.dumps({'status':'SUCCESS','response':'OK','conversation_id':'native-id'})
        before=time.monotonic()
        try:
            with mock.patch('worker.prepare_agent'),mock.patch('worker.run_process',return_value=(envelope,'',0)):
                jid=manager.submit({'title':'中文任务','instruction':'Return OK','workspace':str(self.root)})['task_id']
                result=manager.result(jid,5)
            manager.close()
            self.assertLess(time.monotonic()-before,1.5)
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['native_title']['status'],'pending')
            end=time.monotonic()+8
            while time.monotonic()<end:
                result=manager.result(jid)
                if result['native_title']['status']!='pending':break
                time.sleep(.05)
            self.assertEqual(result['native_title']['status'],'set',result)
            reopened=Manager(self.state,agy=str(fake))
            try:
                self.assertEqual(reopened.result(jid)['native_title']['status'],'set')
                self.assertEqual(reopened.task_list(str(self.root))['tasks'][0]['native_title']['status'],'set')
            finally:reopened.close()
        finally:manager.close()

    def test_naming_spawn_failure_does_not_fail_valid_model_result(self):
        manager=Manager(self.state,agy='fake');self.addCleanup(manager.close)
        envelope=json.dumps({'status':'SUCCESS','response':'OK','conversation_id':'native-id'})
        with mock.patch('worker.prepare_agent'),mock.patch('worker.run_process',return_value=(envelope,'',0)),mock.patch('worker.schedule_title',side_effect=OSError('denied')):
            jid=manager.submit({'title':'中文任务','instruction':'Return OK','workspace':str(self.root)})['task_id']
            result=manager.result(jid,5)
        self.assertEqual(result['status'],'completed');self.assertEqual(result['result'],'OK')
        self.assertEqual(result['native_title']['status'],'failed')


if __name__=='__main__':unittest.main()
