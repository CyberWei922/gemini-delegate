"""Small stdlib-only OS adapters. Never pass task data through a shell."""
import contextlib
import ctypes
import errno
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import threading

WINDOWS = sys.platform == 'win32'


def configure_stdio():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')


def default_state_dir():
    override = os.environ.get('GEMINI_DELEGATE_STATE_DIR')
    if override:
        return Path(override).expanduser().resolve()
    if WINDOWS:
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))/'GeminiDelegate'
    return Path.home()/'.local/share/gemini-delegate'


def find_program(value, name):
    if value and Path(value).expanduser().is_file():
        return str(Path(value).expanduser().resolve())
    found = shutil.which(value or name)
    return str(Path(found).resolve()) if found else None


def command_argv(argv):
    argv = [str(value) for value in argv]
    path = Path(argv[0])
    if path.suffix.lower() == '.py':
        return [sys.executable, *argv]
    if WINDOWS and path.suffix.lower() in ('.cmd', '.bat'):
        # npm's shim invokes Node with a literal entrypoint and forwards %*.
        # Resolve that entrypoint so quotes, %, &, | and Unicode stay arguments.
        text = path.read_text(encoding='utf-8', errors='replace')
        entries = re.findall(r'"%(?:dp0%|~dp0)[\\/]([^"\r\n%]+\.(?:js|cjs|mjs))"', text, re.I)
        existing = list(dict.fromkeys(str((path.parent/entry.replace('\\', os.sep)).resolve())
                                     for entry in entries if (path.parent/entry.replace('\\', os.sep)).is_file()))
        node = path.parent/'node.exe'
        node = str(node) if node.is_file() else find_program(None, 'node')
        if len(existing) != 1 or not node or Path(node).suffix.lower() != '.exe':
            raise OSError('Unsupported Windows batch launcher. Use a native .exe or an npm Node .cmd entrypoint.')
        return [node, existing[0], *argv[1:]]
    return argv


class FileLock:
    """One shared lock byte on Windows; advisory flock on POSIX."""
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open('a+b')
        path.chmod(0o600)
        if self.stream.seek(0, os.SEEK_END) == 0:
            self.stream.write(b'\0'); self.stream.flush()
        self.locked = False

    def acquire(self, blocking=False, timeout=None):
        deadline = time.monotonic()+timeout if timeout is not None else None
        while True:
            try:
                if WINDOWS:
                    import msvcrt
                    self.stream.seek(0)
                    msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.locked = True
                return True
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if not blocking:
                    return False
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError('Timed out waiting for local file lock')
                time.sleep(.05)

    def release(self):
        if self.locked:
            if WINDOWS:
                import msvcrt
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_UN)
            self.locked = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.release()
        finally:
            self.stream.close()


def _kernel():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    handle = ctypes.c_void_p
    dword = ctypes.c_uint32
    signatures = {
        'CreateJobObjectW': ([handle, ctypes.c_wchar_p], handle),
        'SetInformationJobObject': ([handle, ctypes.c_int, handle, dword], ctypes.c_int),
        'AssignProcessToJobObject': ([handle, handle], ctypes.c_int),
        'TerminateJobObject': ([handle, ctypes.c_uint], ctypes.c_int),
        'OpenProcess': ([dword, ctypes.c_int, dword], handle),
        'GetExitCodeProcess': ([handle, ctypes.POINTER(dword)], ctypes.c_int),
        'CloseHandle': ([handle], ctypes.c_int),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name); function.argtypes = args; function.restype = result
    return kernel


class WindowsJob:
    def __init__(self):
        self.api = _kernel()
        self.lock = threading.RLock()
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', ctypes.c_uint32), ('min_working', ctypes.c_size_t),
                        ('max_working', ctypes.c_size_t), ('active_limit', ctypes.c_uint32),
                        ('affinity', ctypes.c_size_t), ('priority', ctypes.c_uint32),
                        ('scheduling', ctypes.c_uint32)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('reads','writes','other','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                        ('peak_job', ctypes.c_size_t)]
        limits = Extended(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error()); self.close(); raise error

    def assign(self, pid):
        process = self.api.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def terminate(self):
        with self.lock:
            if self.handle and not self.api.TerminateJobObject(self.handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        with self.lock:
            if self.handle:
                self.api.CloseHandle(self.handle); self.handle = None


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0 or pid > 0xffffffff:
        return False
    if not WINDOWS:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass
        return True
    api = _kernel()
    handle = api.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return ctypes.get_last_error() == 5  # Access denied still implies existence.
    try:
        code = ctypes.c_uint32()
        if not api.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return code.value == 259  # STILL_ACTIVE
    finally:
        api.CloseHandle(handle)


def stop_process(proc):
    lock = getattr(proc, '_delegate_stop_lock', None)
    if lock is None:
        lock = proc._delegate_stop_lock = threading.RLock()
    with lock:
        if getattr(proc, '_delegate_stopped', False):
            return
        _stop_process(proc)
        proc._delegate_stopped = True


def _stop_process(proc):
    if WINDOWS:
        job = getattr(proc, '_delegate_job', None)
        if job:
            job.terminate()
        elif proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=3)
        return
    if proc.poll() is not None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return
    for sig, delay in [(signal.SIGINT, 1.5), (signal.SIGTERM, .5), (signal.SIGKILL, .5)]:
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        try:
            proc.wait(timeout=delay); break
        except subprocess.TimeoutExpired:
            continue
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


@contextlib.contextmanager
def managed_process(argv, **kwargs):
    """Windows launcher cannot start the target until it belongs to our job."""
    argv = command_argv(argv)
    kwargs.setdefault('env', {**os.environ, 'PYTHONUTF8':'1'})
    job = None
    if WINDOWS:
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        kwargs['stdin'] = subprocess.PIPE
        launcher = [sys.executable, str(Path(__file__).resolve()), '--guarded-launch', *argv]
        proc = subprocess.Popen(launcher, **kwargs)
        try:
            job = WindowsJob(); job.assign(proc.pid); proc._delegate_job = job
            proc.stdin.write(b'\1'); proc.stdin.flush(); proc.stdin.close(); proc.stdin = None
        except BaseException:
            try:
                if job:
                    job.close()
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
            finally:
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if stream:
                        stream.close()
            raise
    else:
        kwargs['start_new_session'] = True
        proc = subprocess.Popen(argv, **kwargs)
    proc._delegate_stop_lock = threading.RLock()
    try:
        yield proc
    finally:
        try:
            stop_process(proc)
        finally:
            if job:
                job.close(); proc._delegate_job = None
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    stream.close()


def run_command(argv, timeout=45, check=False):
    with managed_process(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_process(proc); raise
        result = subprocess.CompletedProcess(argv, proc.returncode,
                                             out.decode('utf-8','replace'), err.decode('utf-8','replace'))
        if check:
            result.check_returncode()
        return result


def detached_flags():
    return {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if WINDOWS else {'start_new_session':True}


if __name__ == '__main__':
    if sys.argv[1:2] != ['--guarded-launch'] or sys.stdin.buffer.read(1) != b'\1':
        raise SystemExit(2)
    child = subprocess.Popen(command_argv(sys.argv[2:]), stdin=subprocess.DEVNULL)
    raise SystemExit(child.wait())
