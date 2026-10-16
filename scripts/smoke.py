#!/usr/bin/env python3
"""Actual MCP/AGY check. Run only when the user authorizes Gemini quota use."""
import argparse
import json
from pathlib import Path
import collections
import os
import queue
import subprocess
import sys
import time
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'plugins/gemini-delegate/server'))
from runtime_config import runtime_environment
from worker import DEFAULT_TIMEOUT_SECONDS


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root',type=Path,default=Path(__file__).resolve().parents[1]/'plugins/gemini-delegate')
    parser.add_argument('--file-task',action='store_true',help='Verify two real plugin manifests delivered in one stdin prompt')
    parser.add_argument('--workspace',type=Path,help='Real workspace containing the supplied plugin source files')
    parser.add_argument('--timeout',type=int,default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument('--attempt-timeout',type=int,help='Explicit fixed per-call cap for longer file checks')
    parser.add_argument('--agy',help='Override the installed official AGY path')
    parser.add_argument('--state-dir',type=Path,help='Override the installed task directory')
    args=parser.parse_args()
    environment=runtime_environment(args.plugin_root, args.agy, args.state_dir)
    p=subprocess.Popen([sys.executable,str(args.plugin_root.resolve()/'server/main.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1,env={**os.environ,**environment,'PYTHONUTF8':'1'})
    replies=queue.Queue();diagnostics=collections.deque(maxlen=40)
    def read_stdout():
        for line in p.stdout:
            replies.put(line)
        replies.put(None)
    def read_stderr():
        for line in p.stderr:
            diagnostics.append(line)
    readers=[threading.Thread(target=read_stdout,daemon=True),threading.Thread(target=read_stderr,daemon=True)]
    for reader in readers:reader.start()
    ident=0
    def rpc(method,params=None):
        nonlocal ident
        ident+=1
        p.stdin.write(json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}})+'\n');p.stdin.flush()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            try:line=replies.get(timeout=min(2,max(0,deadline-time.monotonic())))
            except queue.Empty:continue
            if line is None:raise RuntimeError('MCP server exited: '+''.join(diagnostics)[-2000:])
            data=json.loads(line)
            if data.get('id')==ident:
                if 'error' in data:raise RuntimeError(data['error'])
                return data['result']
        raise TimeoutError(method)
    def tool(name,arguments):
        r=rpc('tools/call',{'name':name,'arguments':arguments})
        if r.get('isError'):raise RuntimeError(r['structuredContent'])
        return r['structuredContent']
    try:
        init=rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'gemini-delegate-release-check','version':'1.0'}})
        tools=[x['name'] for x in rpc('tools/list')['tools']]
        assert len(tools)==8 and 'usage_summary' in tools
        status=tool('gemini_status',{})
        assert status['agy_available'] and status['model']=='gemini-3.8-flash-high'
        workspace=(args.workspace or args.plugin_root).resolve()
        task={'title':'开源包实际连接检查','instruction':'只返回 JSON 对象 {"check":"GEMINI_OK"}。不要调用其他工具。','workspace':str(workspace),'response_type':'json','result_schema':{'type':'object','properties':{'check':{'type':'string','enum':['GEMINI_OK']}},'required':['check'],'additionalProperties':False},'timeout_seconds':args.timeout}
        if args.attempt_timeout is not None:task['attempt_timeout_seconds']=args.attempt_timeout
        expected={'check':'GEMINI_OK'}
        if args.file_task:
            files=[args.plugin_root.resolve()/'plugin.json',args.plugin_root.resolve()/'.codex-plugin/plugin.json']
            item={'type':'object','properties':{'name':{'type':'string'},'version':{'type':'string'}},
                  'required':['name','version'],'additionalProperties':False}
            task.update(title='真实双文件一次性输入检查',
                        instruction='只读提取所提供两份 manifest 的 name 和 version，按文件顺序返回 entries 数组。内容已在提示中，无需再读取文件，不运行工具、不编辑文件、不联网。',
                        input_files=[str(path) for path in files],
                        result_schema={'type':'object','properties':{'entries':{'type':'array','items':item,'minItems':2,'maxItems':2}},
                                       'required':['entries'],'additionalProperties':False})
            expected={'entries':[{key:json.loads(path.read_text(encoding='utf-8'))[key] for key in ('name','version')} for path in files]}
        job=tool('delegate_task',task)
        print(json.dumps({'phase':'submitted','task_id':job['task_id'],'model':job['model']}),flush=True)
        while True:
            r=tool('get_task_result',{'task_id':job['task_id'],'wait_seconds':20,'max_chars':1000})
            if r['status'] in ('completed','failed','cancelled'):
                if r['status']!='completed':raise RuntimeError(r.get('error',{}))
                assert r['result']==expected,r['result']
                print(json.dumps({'passed':True,'version':init['serverInfo']['version'],'tools':tools,'task_id':r['id'],'model':r['model'],'seconds':r['elapsed_seconds'],'input_transport':r.get('input_transport'),'progress':r.get('progress'),'attempts':r['attempts'],'usage':r['usage'],'result':r['result']},ensure_ascii=False),flush=True)
                return
            print(json.dumps({'status':r['status']}),flush=True)
    finally:
        p.stdin.close()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
        for reader in readers:reader.join(timeout=3)
        p.stdout.close();p.stderr.close()


if __name__=='__main__':main()
