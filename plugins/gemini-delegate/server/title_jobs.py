"""Bounded background native naming; never runs a model prompt."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid
from host_tools import FileLock, atomic_replace, detached_flags, read_text
from native_session import rename_conversation


def write_private(path, data):
    temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    try:
        temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        temporary.chmod(0o600)
        atomic_replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def schedule_title(root, agy, workspace, conversation, title):
    result={'status':'pending','title':title,'conversation_id':conversation,
            'method':'background-official-tui-rename','queued_at':time.time()}
    if os.name=='nt':
        return dict(result,status='unsupported',reason='Windows native title transport is not implemented')
    request=Path(root)/'native-title-request.json'
    write_private(request,{'agy':agy,'workspace':str(workspace),
                           'conversation_id':conversation,'title':title})
    try:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(request)],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            **detached_flags())
        threading.Thread(target=process.wait,daemon=True).start()
        return dict(result,worker_pid=process.pid)
    except OSError as error:
        request.unlink(missing_ok=True)
        return dict(result,status='failed',reason='Unable to start native title helper',errno=error.errno)


def merge_title(root, data):
    pending=data.get('native_title') or {}
    queued=pending.get('queued_at')
    if pending.get('status')=='pending' and isinstance(queued,(int,float)) and time.time()-queued>35:
        value=dict(pending,status='failed',reason='Background naming did not finish within its deadline')
        data=dict(data,native_title=value,attempts=[dict(a) for a in data.get('attempts',[])])
        for attempt in data['attempts']:
            if attempt.get('agy_conversation_id')==value.get('conversation_id'):
                attempt['native_title']=value
    path=Path(root)/'native-title.json'
    if path.is_symlink():return data
    try:
        value=json.loads(read_text(path))
        if not isinstance(value,dict) or value.get('title')!=data.get('title'):
            return data
        attempts=data.get('attempts') or []
        matches=[i for i,a in enumerate(attempts) if a.get('agy_conversation_id')==value.get('conversation_id')]
        if not matches:return data
        result=dict(data,native_title=value,attempts=[dict(a) for a in attempts])
        result['attempts'][matches[-1]]['native_title']=value
        return result
    except (OSError,ValueError,TypeError):
        return data


def run(request):
    request=Path(request).resolve();root=request.parent
    if request.name!='native-title-request.json' or not re.fullmatch(r'[0-9a-f]{16}',root.name):
        raise ValueError('Invalid native title request')
    data=json.loads(read_text(request))
    result={'status':'failed','title':data['title'],'conversation_id':data['conversation_id'],
            'method':'background-official-tui-rename'}
    started=time.monotonic();deadline=started+30
    try:
        # Metadata has its own lock; it cannot hold a model execution slot.
        with FileLock(root.parent.parent/'native-title.lock') as lock:
            if not lock.acquire(blocking=True,timeout=20):
                result.update(status='skipped',reason='Background naming is busy')
            else:
                result=rename_conversation(data['agy'],Path(data['workspace']),
                    data['conversation_id'],data['title'],min(10,max(0,deadline-time.monotonic())),
                    threading.Event(),lambda process:None)
                result['method']='background-official-tui-rename'
    except (OSError,ValueError) as error:
        result.update(reason='Background native title operation failed',error_type=type(error).__name__)
    finally:
        result['elapsed_seconds']=round(time.monotonic()-started,2)
        result['finished_at']=time.time()
        write_private(root/'native-title.json',result)
        request.unlink(missing_ok=True)


if __name__=='__main__':
    run(sys.argv[1])
