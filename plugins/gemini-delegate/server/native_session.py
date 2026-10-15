"""Official AGY agent configuration; never edit native conversation storage."""
from pathlib import Path
import errno
import os
import re
import time
import uuid
from host_tools import FileLock, atomic_replace, managed_process

AGENT_NAME = 'gemini-delegate-worker'


def prepare_agent(workspace, definition):
    """Keep the restricted agent discoverable when AGY starts in the project."""
    local = Path(workspace)/'.agents/agents'
    local_found=[]
    for path in (local/(AGENT_NAME+'.md'), local/AGENT_NAME/'agent.md'):
        if path.exists() or path.is_symlink():
            if path.is_symlink() or path.read_text(encoding='utf-8') != definition:
                raise ValueError('Workspace defines a different gemini-delegate-worker; existing configuration preserved')
            local_found.append(path)
    if local_found:
        return local_found[0]
    directory = Path.home()/'.gemini/config/agents'
    directory.mkdir(parents=True,exist_ok=True)
    path = directory/(AGENT_NAME+'.md')
    # Different chats/state directories may initialize the one global worker.
    with FileLock(directory/'.gemini-delegate-worker.lock') as lock:
        lock.acquire(blocking=True,timeout=5)
        found=[]
        for candidate in (path,directory/AGENT_NAME/'agent.md'):
            if candidate.exists() or candidate.is_symlink():
                if candidate.is_symlink() or candidate.read_text(encoding='utf-8') != definition:
                    raise ValueError('Global gemini-delegate-worker differs; existing configuration preserved')
                found.append(candidate)
        if found:
            return found[0]
        temporary = directory/('.gemini-delegate-worker-'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_text(definition,encoding='utf-8')
            temporary.chmod(0o600)
            atomic_replace(temporary,path)
        finally:
            temporary.unlink(missing_ok=True)
        return path


def rename_conversation(agy, workspace, conversation, title, timeout, cancel, on_process):
    """Run the official /rename from a ready TUI, never as a model prompt."""
    result = {'status':'failed','title':title,'conversation_id':conversation,
              'method':'official-tui-rename'}
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',conversation) or not title or any(ord(c)<32 or ord(c)==127 for c in title):
        return dict(result,reason='Invalid native title arguments')
    if os.name == 'nt':
        return dict(result,status='unsupported',reason='AGY print mode cannot rename; Windows interactive transport is not yet verified')
    import fcntl
    import pty
    import select
    import struct
    import termios
    master,slave=pty.openpty()
    deadline=time.monotonic()+timeout
    command_sent=False
    exiting=False
    output=bytearray()
    try:
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,160,0,0))
        argv=[agy,'--conversation',conversation,'--model','gemini-3.8-flash-high','--sandbox']
        with managed_process(argv,cwd=workspace,stdin=slave,stdout=slave,stderr=slave,
                             env={**os.environ,'TERM':'xterm-256color'}) as process:
            os.close(slave);slave=None
            on_process(process)
            while time.monotonic()<deadline and not cancel.is_set():
                readable,_,_=select.select([master],[],[],min(.1,max(0,deadline-time.monotonic())))
                if not readable:
                    if process.poll() is not None:break
                    continue
                try:
                    chunk=os.read(master,16384)
                except OSError as error:
                    if error.errno==errno.EIO:break
                    raise
                if not chunk:break
                output.extend(chunk)
                if len(output)>2*1024*1024:
                    result['reason']='Native TUI output limit reached';break
                plain=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',output.decode('utf-8','replace'))
                if not command_sent and 'Do you trust the contents of this project?' in plain:
                    # Trust grants project-wide read/edit/execute permissions.
                    # A metadata rename must never approve that on its own.
                    result.update(status='requires_trust',
                                  reason='Official AGY requires project trust. Open agy in this workspace and review its trust prompt before retrying the native title update.')
                    break
                if not command_sent and '? for shortcuts' in plain:
                    # Startup prompts (-i) bypass slash dispatch in AGY 1.3.5.
                    # Only send input after the actual editor is ready.
                    os.write(master,('/rename '+title+'\r').encode('utf-8'))
                    command_sent=True;output.clear()
                elif command_sent and not exiting and 'Conversation renamed to: '+title in plain:
                    result['status']='set'
                    os.write(master,b'/exit\r')
                    exiting=True;output.clear()
            if cancel.is_set() and result['status']!='set':
                result['reason']='Cancelled during native title update'
            elif result['status']!='set':
                result.setdefault('reason','Official TUI did not acknowledge the rename within budget')
    except OSError as error:
        result.update(reason='Native TUI operation failed',errno=error.errno)
    finally:
        if slave is not None:os.close(slave)
        os.close(master)
    return result
