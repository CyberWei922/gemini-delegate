import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from dashboard import CHILDREN, ensure_dashboard, public_task, read_tasks


class DashboardTests(unittest.TestCase):
    def test_loopback_server_reuses_instance_and_requires_token(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)
            pid=None
            try:
                url=ensure_dashboard(state)
                config=json.loads((state/'dashboard.json').read_text())
                pid=config['pid']
                self.assertEqual(url,ensure_dashboard(state))
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                base=url.split('?',1)[0]
                with opener.open(url) as response:
                    html=response.read().decode()
                    self.assertIn('Gemini 子任务',html)
                    self.assertEqual(response.headers['Cache-Control'],'no-store')
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(base+'api/tasks')
                self.assertEqual(error.exception.code,403)
                error.exception.close()
                api=base+'api/tasks?'+url.split('?',1)[1]
                with opener.open(api) as response:
                    self.assertEqual(json.load(response)['tasks'],[])
                request=urllib.request.Request(api,headers={'Origin':'https://example.com'})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(request)
                self.assertEqual(error.exception.code,403)
                error.exception.close()
            finally:
                if pid:
                    os.kill(pid,signal.SIGTERM)
                    for child in CHILDREN:
                        if child.pid==pid:child.wait(timeout=3)

    def test_interrupted_owner_and_bounded_result_preview(self):
        task=public_task({'id':'a','status':'running','owner_pid':999999999,
                          'result':'x'*5000,'context':'SECRET'})
        self.assertEqual(task['status'],'interrupted')
        self.assertEqual(len(task['result_preview']),4000)
        self.assertTrue(task['result_truncated'])
        self.assertNotIn('context',task)

    def test_historical_records_and_corrupt_snapshot_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'jobs'/'abcdef0123456789';root.mkdir(parents=True)
            (root/'progress.json').write_text('{bad')
            (root/'metadata.json').write_text(json.dumps({'id':root.name,'status':'completed','workspace':'/project','created_at':1,'result':{'n':3}}))
            tasks=read_tasks(d,'/project')
            self.assertEqual(len(tasks),1)
            self.assertIn('历史任务',tasks[0]['title'])
            self.assertEqual(json.loads(tasks[0]['result_preview']),{'n':3})


if __name__=='__main__':unittest.main()
