import concurrent.futures
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from native_session import prepare_agent, rename_conversation, AGENT_NAME
import native_session
from worker import Manager, AGENT, WorkerError


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve()
        self.workspace=self.root/'项目';self.workspace.mkdir()
        patch=mock.patch('native_session.Path.home',return_value=self.root/'home')
        patch.start();self.addCleanup(patch.stop)

    def test_global_agent_is_official_discoverable_and_initialization_is_idempotent(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            paths=list(pool.map(lambda _:prepare_agent(self.workspace,AGENT),range(2)))
        self.assertEqual(paths[0],self.root/'home/.gemini/config/agents'/f'{AGENT_NAME}.md')
        self.assertEqual(paths[0],paths[1])
        self.assertEqual(paths[0].read_text(encoding='utf-8'),AGENT)
        self.assertFalse((self.workspace/'.agents').exists())

    def test_workspace_agent_conflict_is_preserved(self):
        path=self.workspace/'.agents/agents'/f'{AGENT_NAME}.md'
        path.parent.mkdir(parents=True);path.write_text('USER_CONFIGURATION',encoding='utf-8')
        with self.assertRaises(ValueError):prepare_agent(self.workspace,AGENT)
        self.assertEqual(path.read_text(encoding='utf-8'),'USER_CONFIGURATION')

    def test_global_agent_conflict_is_preserved(self):
        path=self.root/'home/.gemini/config/agents'/f'{AGENT_NAME}.md'
        path.parent.mkdir(parents=True);path.write_text('USER_CONFIGURATION',encoding='utf-8')
        with self.assertRaises(ValueError):prepare_agent(self.workspace,AGENT)
        self.assertEqual(path.read_text(encoding='utf-8'),'USER_CONFIGURATION')

    def test_duplicate_agent_locations_cannot_hide_a_conflicting_definition(self):
        directory=self.workspace/'.agents/agents'
        file=directory/f'{AGENT_NAME}.md';file.parent.mkdir(parents=True)
        file.write_text(AGENT,encoding='utf-8')
        nested=directory/AGENT_NAME/'agent.md';nested.parent.mkdir()
        nested.write_text('OTHER_AGENT',encoding='utf-8')
        with self.assertRaises(ValueError):prepare_agent(self.workspace,AGENT)
        self.assertEqual(nested.read_text(encoding='utf-8'),'OTHER_AGENT')

    def test_project_cwd_fresh_task_and_native_rename_dont_double_count_usage(self):
        manager=Manager(self.root/'state',agy='fake-agy')
        self.addCleanup(manager.close)
        envelope=json.dumps({'status':'SUCCESS','conversation_id':'native-session-123',
                             'response':'OK','usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}})
        with mock.patch('worker.run_process',return_value=(envelope,'',0)) as process, mock.patch('worker.schedule_title',return_value={'status':'set'}) as rename:
            jid=manager.submit({'title':'中文名称','instruction':'Return OK','workspace':str(self.workspace)})['task_id']
            result=manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['native_title']['status'],'set')
        self.assertEqual(result['usage']['total_tokens'],12)
        self.assertEqual(len(result['attempts']),1)
        work=process.call_args
        self.assertEqual(Path(work.args[1]),self.workspace)
        self.assertEqual(Path(rename.call_args.args[2]),self.workspace)
        self.assertNotIn('--continue',work.args[0]);self.assertNotIn('--conversation',work.args[0])
        self.assertIn('--disable-slash-commands',work.args[0])
        self.assertEqual(rename.call_args.args[3:5],('native-session-123','中文名称'))
        self.assertEqual(process.call_count,1)

    def test_rename_failure_does_not_rerun_a_successful_model_task(self):
        manager=Manager(self.root/'state',agy='fake-agy');self.addCleanup(manager.close)
        envelope=json.dumps({'status':'SUCCESS','conversation_id':'native-session-123','response':'OK'})
        with mock.patch('worker.run_process',return_value=(envelope,'',0)) as process, mock.patch('worker.schedule_title',return_value={'status':'failed'}):
            jid=manager.submit({'title':'中文名称','instruction':'Return OK','workspace':str(self.workspace)})['task_id']
            result=manager.result(jid,10)
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['native_title']['status'],'failed')
        self.assertEqual(process.call_count,1)
        self.assertEqual(len(result['attempts']),1)

    def test_control_characters_in_names_are_rejected(self):
        manager=Manager(self.root/'state',agy='fake-agy');self.addCleanup(manager.close)
        for title in ('任务\n/command','任务\x1b[31m'):
            with self.assertRaises(WorkerError):manager.submit({'title':title,'instruction':'Return OK'})

    def test_failed_model_response_is_discarded_without_metadata_delay(self):
        manager=Manager(self.root/'state',agy='fake-agy');self.addCleanup(manager.close)
        envelope=json.dumps({'status':'ERROR','conversation_id':'failed-native-session','error':'inference failed'})
        with mock.patch('worker.run_process',return_value=(envelope,'',1)), mock.patch('worker.schedule_title',return_value={'status':'set'}) as rename:
            jid=manager.submit({'title':'失败任务的中文名称','instruction':'Return OK','workspace':str(self.workspace)})['task_id']
            result=manager.result(jid,10)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['attempts'][0]['native_title']['status'],'skipped')
        rename.assert_not_called()

    @unittest.skipIf(os.name=='nt','POSIX pseudo-terminal transport')
    def test_interactive_rename_waits_for_editor_and_exits_without_startup_prompt(self):
        fake=self.root/'fake-tui.py'
        fake.write_text('''import sys
assert '-p' not in sys.argv and '--prompt-interactive' not in sys.argv
assert '--conversation' in sys.argv
print('? for shortcuts',flush=True)
command=sys.stdin.readline().strip()
assert command=='/rename 中文工作名称',repr(command)
print('  ⎿  Conversation renamed to: 中文工作名称',flush=True)
assert sys.stdin.readline().strip()=='/exit'
''',encoding='utf-8')
        result=rename_conversation(str(fake),self.workspace,'test-session','中文工作名称',3,threading.Event(),lambda p:None)
        self.assertEqual(result['status'],'set',result)

    @unittest.skipIf(os.name=='nt','POSIX pseudo-terminal transport')
    def test_project_trust_prompt_is_reported_without_approval_or_model_input(self):
        fake=self.root/'fake-tui.py';received=self.root/'unexpected-input'
        fake.write_text('''import sys
from pathlib import Path
print('Do you trust the contents of this project?',flush=True)
line=sys.stdin.readline()
if line:Path(RECEIVED).write_text(line)
'''.replace('RECEIVED',repr(str(received))),encoding='utf-8')
        original=native_session.managed_process
        @contextlib.contextmanager
        def cleanup_error(*args,**kwargs):
            with original(*args,**kwargs) as process:
                yield process
            raise PermissionError(1,'Simulated cleanup denial')
        for process_manager in (original,cleanup_error):
            with self.subTest(cleanup_failure=process_manager is cleanup_error),mock.patch('native_session.managed_process',process_manager):
                result=rename_conversation(str(fake),self.workspace,'test-session','中文工作名称',3,threading.Event(),lambda p:None)
                self.assertEqual(result['status'],'requires_trust',result)
                self.assertIn('review its trust prompt',result['reason'])
                self.assertFalse(received.exists())

    @unittest.skipIf(os.name=='nt','POSIX pseudo-terminal transport')
    def test_interactive_timeout_and_cancel_are_bounded(self):
        fake=self.root/'fake-tui.py'
        fake.write_text('import time; time.sleep(30)',encoding='utf-8')
        cancel=threading.Event();cancel.set()
        result=rename_conversation(str(fake),self.workspace,'test-session','中文工作名称',.2,cancel,lambda p:None)
        self.assertEqual(result['status'],'failed')
        self.assertIn('Cancelled',result['reason'])


if __name__=='__main__':unittest.main()
