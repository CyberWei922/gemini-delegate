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


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root',type=Path,default=Path(__file__).resolve().parents[1]/'plugins/gemini-delegate')
    parser.add_argument('--file-task',action='store_true',help='Verify real reading of chunked worker/test source snapshots')
    parser.add_argument('--workspace',type=Path,help='Real workspace containing the supplied plugin source files')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args()
    p=subprocess.Popen([sys.executable,str(args.plugin_root.resolve()/'server/main.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1,env={**os.environ,'PYTHONUTF8':'1'})
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
        assert len(tools)==7
        status=tool('gemini_status',{})
        assert status['agy_available'] and status['model']=='gemini-3.8-flash-high'
        workspace=(args.workspace or args.plugin_root).resolve()
        task={'title':'开源包实际连接检查','instruction':'只返回 JSON 对象 {"check":"GEMINI_OK"}。不要调用其他工具。','workspace':str(workspace),'response_type':'json','result_schema':{'type':'object','properties':{'check':{'type':'string','enum':['GEMINI_OK']}},'required':['check'],'additionalProperties':False},'timeout_seconds':args.timeout}
        expected={'check':'GEMINI_OK'}
        if args.file_task:
            fields={'model':{'type':'string'},'chunk_bytes':{'type':'integer'},'default_attempt_cap':{'type':'string'},'retry_error_codes':{'type':'array','items':{'type':'string'}},'test_name':{'type':'string'}}
            task.update(title='修复后真实文件读取检查',instruction='只读完成源码提取，不运行测试、不编辑文件、不联网、不制定方案。读取索引及所列文件的所有文本块，从 worker.py 提取 MODEL 字符串、INPUT_CHUNK_BYTES 整数、Manager.__init__ 的 attempt_seconds 默认值（None 写成字符串 none）、允许一次重试的四个错误代码（保持源码元组顺序）；从 test_worker.py 提取证明默认超时不重复重试的测试函数名。只返回 JSON，字段依次为 model、chunk_bytes、default_attempt_cap、retry_error_codes、test_name。不要输出分析。',input_files=[str(args.plugin_root.resolve()/'server/worker.py'),str(args.plugin_root.resolve()/'tests/test_worker.py')],result_schema={'type':'object','properties':fields,'required':list(fields),'additionalProperties':False})
            expected={'model':'gemini-3.8-flash-high','chunk_bytes':24576,'default_attempt_cap':'none','retry_error_codes':['timeout','empty_result','invalid_result','invalid_envelope'],'test_name':'test_timeout_does_not_retry_the_same_default_budget'}
        job=tool('delegate_task',task)
        print(json.dumps({'phase':'submitted','task_id':job['task_id'],'model':job['model']}),flush=True)
        while True:
            r=tool('get_task_result',{'task_id':job['task_id'],'wait_seconds':20,'max_chars':1000})
            if r['status'] in ('completed','failed','cancelled'):
                if r['status']!='completed':raise RuntimeError(r.get('error',{}))
                assert r['result']==expected,r['result']
                print(json.dumps({'passed':True,'version':init['serverInfo']['version'],'tools':tools,'task_id':r['id'],'model':r['model'],'seconds':r['elapsed_seconds'],'input_parts':r.get('input_parts',0),'attempts':r['attempts'],'usage':r['usage'],'result':r['result']},ensure_ascii=False),flush=True)
                return
            print(json.dumps({'status':r['status']}),flush=True)
    finally:
        p.stdin.close()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
        for reader in readers:reader.join(timeout=3)
        p.stdout.close();p.stderr.close()


if __name__=='__main__':main()
