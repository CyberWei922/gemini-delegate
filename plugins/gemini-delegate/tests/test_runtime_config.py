import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PLUGIN=Path(__file__).resolve().parents[1]
REPO=PLUGIN.parents[1]
sys.path.insert(0,str(PLUGIN/'server'))
from runtime_config import runtime_environment, manager_options
from worker import AGENT


class RuntimeConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='Gemini 运行配置 ')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        agent=self.root/'.agents/agents/gemini-delegate-worker.md'
        agent.parent.mkdir(parents=True);agent.write_text(AGENT,encoding='utf-8')
        self.plugin=self.root/'插件 space'
        shutil.copytree(PLUGIN,self.plugin,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        self.state=self.root/'自定义 任务'
        self.agy=self.root/'official-entry.py'
        self.make_agy(self.agy,'GEMINI_OK')
        self.write_manifest({'GEMINI_DELEGATE_AGY':str(self.agy),
                             'GEMINI_DELEGATE_STATE_DIR':str(self.state),
                             'UNRELATED_SECRET':'DO_NOT_EXPORT'})
        self.env={**os.environ,'PYTHONUTF8':'1'}
        for key in ('GEMINI_DELEGATE_AGY','GEMINI_DELEGATE_STATE_DIR','GEMINI_DELEGATE_MAX_CONCURRENCY'):
            self.env.pop(key,None)

    def make_agy(self,path,value):
        path.write_text('import json\nprint(json.dumps('+repr({'status':'SUCCESS','response':json.dumps({'check':value})})+'))\n',encoding='utf-8')
        path.chmod(0o700)

    def write_manifest(self,environment,name='mcp.json'):
        (self.plugin/name).write_text(json.dumps({'mcpServers':{'gemini-delegate':{'env':environment}}}),encoding='utf-8-sig')

    def test_installed_paths_are_loaded_but_unrelated_values_are_not_exported(self):
        environment=runtime_environment(self.plugin,environ={})
        self.assertEqual(environment,{'GEMINI_DELEGATE_AGY':str(self.agy),
                                     'GEMINI_DELEGATE_STATE_DIR':str(self.state)})
        self.assertNotIn('UNRELATED_SECRET',environment)

    def test_explicit_options_then_process_environment_take_precedence(self):
        process={'GEMINI_DELEGATE_AGY':'process-agy','GEMINI_DELEGATE_STATE_DIR':'process-state'}
        self.assertEqual(runtime_environment(self.plugin,environ=process),process)
        explicit=runtime_environment(self.plugin,'explicit-agy',Path('explicit-state'),environ=process)
        self.assertEqual(explicit,{'GEMINI_DELEGATE_AGY':'explicit-agy',
                                   'GEMINI_DELEGATE_STATE_DIR':'explicit-state'})

    def test_portable_source_and_missing_manifest_keep_platform_defaults(self):
        self.write_manifest({})
        self.assertEqual(runtime_environment(self.plugin,environ={}),{})
        (self.plugin/'mcp.json').unlink()
        (self.plugin/'.mcp.json').unlink()
        self.assertEqual(runtime_environment(self.plugin,environ={}),{})

    def test_legacy_manifest_is_supported(self):
        (self.plugin/'mcp.json').unlink()
        self.write_manifest({'GEMINI_DELEGATE_AGY':str(self.agy)},'.mcp.json')
        self.assertEqual(runtime_environment(self.plugin,environ={})['GEMINI_DELEGATE_AGY'],str(self.agy))

    def test_concurrency_obeys_explicit_process_and_manifest_precedence(self):
        self.write_manifest({'GEMINI_DELEGATE_MAX_CONCURRENCY':'1'})
        with mock.patch.dict(os.environ):
            os.environ.pop('GEMINI_DELEGATE_MAX_CONCURRENCY',None)
            self.assertEqual(manager_options(self.plugin)['max_concurrency'],'1')
            os.environ['GEMINI_DELEGATE_MAX_CONCURRENCY']='2'
            self.assertEqual(manager_options(self.plugin)['max_concurrency'],'2')
            self.assertEqual(manager_options(self.plugin,max_concurrency=1)['max_concurrency'],'1')

    def test_invalid_configuration_fails_clearly_without_opaque_content(self):
        (self.plugin/'mcp.json').write_text('SECRET_INVALID_JSON',encoding='utf-8')
        with self.assertRaises(ValueError) as error:runtime_environment(self.plugin,environ={})
        self.assertNotIn('SECRET_INVALID_JSON',str(error.exception))
        self.write_manifest({'GEMINI_DELEGATE_AGY':[]})
        with self.assertRaises(ValueError):runtime_environment(self.plugin,environ={})

    def client(self,extra=(),env=None):
        task=self.root/'task.json'
        task.write_text(json.dumps({'instruction':'Return the test value','workspace':str(self.root),
                                  'response_type':'json','timeout_seconds':15}),encoding='utf-8')
        result=subprocess.run([sys.executable,str(self.plugin/'scripts/delegate.py'),'--input',str(task),*extra],
                              env=env or self.env,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        return json.loads(result.stdout.splitlines()[-1])

    def test_client_uses_installed_cli_and_state_without_environment_exports(self):
        result=self.client()
        self.assertEqual(result['result'],{'check':'GEMINI_OK'})
        self.assertTrue((self.state/'jobs'/result['id']/'metadata.json').is_file())

    def test_client_retry_option_applies_to_input_json_and_terminal_handoff(self):
        self.agy.write_text('import json\nprint(json.dumps({"status":"SUCCESS","response":""}))',encoding='utf-8')
        task=self.root/'task.json'
        task.write_text(json.dumps({'instruction':'Return OK','workspace':str(self.root),'max_attempts':5}),encoding='utf-8')
        result=subprocess.run([sys.executable,str(self.plugin/'scripts/delegate.py'),'--input',str(task),'--max-attempts','1'],env=self.env,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        terminal=json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(len(terminal['attempts']),1)
        self.assertEqual(terminal['retry_policy']['max_attempts'],1)
        self.assertEqual(terminal['handoff']['reason'],'non_retryable_error')

    def test_fresh_mcp_retries_temporary_cli_failures_before_returning_success(self):
        counter=self.root/'calls.txt'
        self.agy.write_text('''import json
from pathlib import Path
p=Path(COUNTER);count=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(count))
if count<3:
 print(json.dumps({'status':'ERROR','error':'Eligibility check failed: userinfo request: EOF'}))
 raise SystemExit(1)
print(json.dumps({'status':'SUCCESS','response':'{"check":"GEMINI_OK"}'}))
'''.replace('COUNTER',repr(str(counter))),encoding='utf-8')
        result=subprocess.run([sys.executable,str(REPO/'scripts/smoke.py'),'--plugin-root',str(self.plugin),'--workspace',str(self.root),'--timeout','30'],env=self.env,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        terminal=json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(terminal['passed'])
        self.assertEqual(len(terminal['attempts']),3)
        self.assertEqual([a.get('error_code') for a in terminal['attempts']],['transient_error','transient_error',None])
        self.assertEqual(counter.read_text(),'3')

    def test_client_explicit_cli_and_state_overrides_are_honored(self):
        alternate=self.root/'alternate.py';self.make_agy(alternate,'OVERRIDE_OK')
        state=self.root/'alternate-state'
        result=self.client(['--agy',str(alternate),'--state-dir',str(state)])
        self.assertEqual(result['result'],{'check':'OVERRIDE_OK'})
        self.assertTrue((state/'jobs'/result['id']/'metadata.json').is_file())
        self.assertFalse(self.state.exists())

    def test_client_process_environment_overrides_installed_paths(self):
        alternate=self.root/'alternate.py';self.make_agy(alternate,'PROCESS_OK')
        state=self.root/'process-state'
        result=self.client(env={**self.env,'GEMINI_DELEGATE_AGY':str(alternate),
                               'GEMINI_DELEGATE_STATE_DIR':str(state)})
        self.assertEqual(result['result'],{'check':'PROCESS_OK'})
        self.assertTrue((state/'jobs'/result['id']/'metadata.json').is_file())

    def test_smoke_client_uses_installed_environment_without_exports(self):
        result=subprocess.run([sys.executable,str(REPO/'scripts/smoke.py'),'--plugin-root',str(self.plugin),
                               '--workspace',str(self.root),'--timeout','15'],env=self.env,
                              capture_output=True,text=True,encoding='utf-8',timeout=25)
        self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        check=json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(check['passed'])
        self.assertEqual(check['result'],{'check':'GEMINI_OK'})
        self.assertTrue((self.state/'jobs'/check['task_id']/'metadata.json').is_file())


if __name__=='__main__':unittest.main()
