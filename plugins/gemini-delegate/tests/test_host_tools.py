import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import host_tools
from host_tools import FileLock, WINDOWS, WindowsJob, atomic_replace, command_argv, process_alive, run_command
from worker import WorkerError, run_process


class HostTests(unittest.TestCase):
    def test_posix_read_denial_is_not_retried(self):
        with mock.patch.object(host_tools,'WINDOWS',False),mock.patch.object(Path,'read_text',side_effect=PermissionError(13,'Denied')) as read,mock.patch.object(host_tools.time,'sleep') as sleep:
            with self.assertRaises(PermissionError):host_tools.read_text('progress.json')
        self.assertEqual(read.call_count,1)
        sleep.assert_not_called()

    def test_windows_read_retry_has_a_deadline(self):
        started=time.monotonic()
        with mock.patch.object(host_tools,'WINDOWS',True),mock.patch.object(Path,'read_text',side_effect=PermissionError(13,'Denied')) as read:
            with self.assertRaises(PermissionError):host_tools.read_text('progress.json',timeout=.03)
        self.assertGreater(read.call_count,1)
        self.assertLess(time.monotonic()-started,.5)

    @unittest.skipUnless(WINDOWS,'Real Windows file sharing required')
    def test_atomic_replace_waits_for_a_reader_to_release_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'progress.json';source=Path(directory)/'new.tmp'
            target.write_bytes(b'old');source.write_bytes(b'new')
            stream=target.open('rb')
            timer=threading.Timer(.2,stream.close);timer.start()
            try:
                atomic_replace(source,target)
                self.assertEqual(target.read_bytes(),b'new')
                self.assertFalse(source.exists())
            finally:
                timer.join();stream.close()

    def test_lock_excludes_another_process_and_releases(self):
        with tempfile.TemporaryDirectory(prefix='Gemini 锁 ') as directory:
            path=Path(directory)/'shared.lock'
            server=str(Path(host_tools.__file__).parent)
            code='import sys;sys.path.insert(0,sys.argv[1]);from host_tools import FileLock\nwith FileLock(sys.argv[2]) as lock: print(lock.acquire())'
            with FileLock(path) as owner:
                self.assertTrue(owner.acquire())
                result=run_command([sys.executable,'-c',code,server,str(path)],timeout=10)
                self.assertEqual(result.stdout.strip(),'False')
            result=run_command([sys.executable,'-c',code,server,str(path)],timeout=10)
            self.assertEqual(result.stdout.strip(),'True')

    def test_alive_probe_does_not_terminate_the_process(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            for _ in range(3):
                self.assertTrue(process_alive(child.pid))
                self.assertIsNone(child.poll())
        finally:
            child.terminate();child.wait(timeout=3)
        self.assertFalse(process_alive(child.pid))
        self.assertFalse(process_alive(0))
        self.assertFalse(process_alive(0x100000000))

    def test_unicode_and_shell_characters_remain_literal_arguments(self):
        values=['中文 路径','a&b','100%PATH%','"quoted" | echo bad','$()']
        code='import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=False))'
        result=run_command([sys.executable,'-c',code,*values])
        self.assertEqual(json.loads(result.stdout),values)

    def test_python_script_entrypoint_does_not_need_shebang_execution(self):
        with tempfile.TemporaryDirectory(prefix='Gemini 脚本 ') as directory:
            path=Path(directory)/'fake cli.py'
            path.write_text('print("OK")\n',encoding='utf-8')
            self.assertEqual(run_command([str(path)]).stdout.strip(),'OK')

    def test_windows_state_directory_uses_current_user_localappdata(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(host_tools,'WINDOWS',True), mock.patch.dict(os.environ,{'LOCALAPPDATA':directory,'GEMINI_DELEGATE_STATE_DIR':''}):
                self.assertEqual(host_tools.default_state_dir(),Path(directory)/'GeminiDelegate')

    def test_unknown_batch_launcher_is_rejected_without_shell_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.cmd';path.write_text('@echo off\necho unsupported\n',encoding='utf-8')
            with mock.patch.object(host_tools,'WINDOWS',True), self.assertRaises(OSError) as caught:
                command_argv([str(path),'%PATH% & echo bad'])
            self.assertIn('Unsupported Windows batch launcher',str(caught.exception))

    @unittest.skipUnless(WINDOWS,'Real Windows job assignment required')
    def test_target_cannot_start_before_job_assignment(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'started'
            original=WindowsJob.assign
            def assign(job,pid):
                time.sleep(.2)
                self.assertFalse(marker.exists())
                return original(job,pid)
            code='import pathlib;pathlib.Path('+repr(str(marker))+').write_text("started")'
            with mock.patch.object(WindowsJob,'assign',assign):
                self.assertEqual(run_command([sys.executable,'-c',code]).returncode,0)
            self.assertTrue(marker.exists())

    @unittest.skipUnless(WINDOWS and shutil.which('node'),'Real Windows Node launcher required')
    def test_npm_cmd_launcher_preserves_untrusted_arguments(self):
        with tempfile.TemporaryDirectory(prefix='Gemini Node 路径 ') as directory:
            root=Path(directory);entry=root/'entry.js'
            entry.write_text('console.log(JSON.stringify(process.argv.slice(2)));',encoding='utf-8')
            shim=root/'test.cmd';shim.write_text('@echo off\n"%dp0%\\entry.js" %*\n',encoding='utf-8')
            values=['a&b','%PATH%','中文 空格','"quoted" | echo bad']
            result=run_command([str(shim),*values])
            self.assertEqual(json.loads(result.stdout),values)

    @unittest.skipUnless(WINDOWS,'Real Windows job assignment required')
    def test_assignment_failure_does_not_start_target(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'started'
            code='import pathlib;pathlib.Path('+repr(str(marker))+').write_text("started")'
            with mock.patch.object(WindowsJob,'assign',side_effect=OSError('assignment rejected')):
                with self.assertRaisesRegex(OSError,'assignment rejected'):
                    run_command([sys.executable,'-c',code])
            self.assertFalse(marker.exists())

    def test_timeout_kills_descendant_after_parent_already_exited(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'pid'
            code='import subprocess,sys,pathlib;p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);pathlib.Path('+repr(str(marker))+').write_text(str(p.pid))'
            started=time.monotonic()
            with self.assertRaises(WorkerError) as caught:
                run_process([sys.executable,'-c',code],directory,2)
            self.assertEqual(caught.exception.code,'timeout')
            self.assertLess(time.monotonic()-started,7)
            self.assertTrue(marker.exists())
            pid=int(marker.read_text(encoding='utf-8'))
            if WINDOWS:
                self.assertFalse(process_alive(pid))
            else:
                result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
                self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith('Z'))


if __name__=='__main__':unittest.main()
