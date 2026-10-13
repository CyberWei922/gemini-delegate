#!/usr/bin/env python3
"""Actual MCP/AGY check. Run only when the user authorizes Gemini quota use."""
import argparse
import json
from pathlib import Path
import selectors
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root',type=Path,default=Path(__file__).resolve().parents[1]/'plugins/gemini-delegate')
    args=parser.parse_args()
    p=subprocess.Popen([sys.executable,str(args.plugin_root.resolve()/'server/main.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
    ident=0
    def rpc(method,params=None):
        nonlocal ident
        ident+=1
        p.stdin.write(json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}})+'\n');p.stdin.flush()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if selector.select(min(2,max(0,deadline-time.monotonic()))):
                line=p.stdout.readline()
                if not line:raise RuntimeError('MCP server exited')
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
        job=tool('delegate_task',{'title':'开源包实际连接检查','instruction':'只返回 JSON 对象 {"check":"GEMINI_OK"}。不要调用其他工具。','workspace':str(args.plugin_root.resolve()),'response_type':'json','result_schema':{'type':'object','properties':{'check':{'type':'string','enum':['GEMINI_OK']}},'required':['check'],'additionalProperties':False},'timeout_seconds':180})
        print(json.dumps({'phase':'submitted','task_id':job['task_id'],'model':job['model']}),flush=True)
        while True:
            r=tool('get_task_result',{'task_id':job['task_id'],'wait_seconds':20,'max_chars':1000})
            if r['status'] in ('completed','failed','cancelled'):
                if r['status']!='completed':raise RuntimeError(r.get('error',{}))
                assert r['result']=={'check':'GEMINI_OK'}
                print(json.dumps({'passed':True,'version':init['serverInfo']['version'],'tools':tools,'task_id':r['id'],'model':r['model'],'seconds':r['elapsed_seconds'],'attempts':r['attempts'],'usage':r['usage'],'result':r['result']},ensure_ascii=False),flush=True)
                return
            print(json.dumps({'status':r['status']}),flush=True)
    finally:
        p.stdin.close()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
        selector.close()


if __name__=='__main__':main()
