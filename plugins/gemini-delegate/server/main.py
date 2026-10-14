#!/usr/bin/env python3
"""Dependency-free MCP stdio entry point. Protocol only on stdout."""
import json
import sys
from worker import Manager, WorkerError, VERSION
from host_tools import configure_stdio

OBJECT = {'type':'object'}
TASK_SCHEMA = {'type':'object','properties':{
    'title':{'type':'string','minLength':1,'maxLength':160,'description':'Short user-visible task name for the right-side Gemini task monitor. Do not include secrets.'},
    'instruction':{'type':'string','description':'One explicit, bounded task. Keep complex planning and judgments in the primary agent.'},
    'context':{'type':'string','description':'Supplied task data; up to 48000 characters. Split independent large jobs.'},
    'workspace':{'type':'string','description':'Absolute directory containing the explicitly supplied files.'},
    'input_files':{'type':'array','items':{'type':'string'},'maxItems':8,'description':'Explicit UTF-8 files inside workspace. Originals are read only.'},
    'web_urls':{'type':'array','items':{'type':'string'},'maxItems':4,'description':'Public pages to fetch through the plugin read-only adapter before AGY runs.'},
    'search_query':{'type':'string','description':'Optional public web research query through the existing Agent Reach Exa backend.'},
    'response_type':{'type':'string','enum':['text','json','edit'],'default':'text','description':'edit returns staged replacements of explicit input files; apply after primary review.'},
    'result_schema':{'type':'object','description':'Optional JSON result contract. Supports type/properties/required/additionalProperties/items/minItems/maxItems/enum/const/minimum/maximum/minLength/maxLength/pattern. No $ref or combinators.'},
    'timeout_seconds':{'type':'integer','minimum':15,'maximum':600,'default':180,'description':'Overall execution budget for source retrieval, shared AGY slot waiting and all attempts; begins when the queued worker starts.'},
    'attempt_timeout_seconds':{'type':'integer','minimum':15,'maximum':600,'description':'Optional first-attempt cap. Default uses the remaining overall budget, without a hidden 75-second cap. One timeout retry is allowed only with a larger budget.'}
},'required':['instruction'],'additionalProperties':False}

TOOLS = [
    {'name':'list_tasks','description':'Show actual Gemini Delegate task records, live state, project, attempts, usage and bounded results across chats. Filter by the current project to check whether it used Gemini. No task means no delegation through this plugin.', 'inputSchema':{'type':'object','properties':{'workspace':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':200,'default':200}},'additionalProperties':False},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
    {'name':'task_monitor','description':'Start or reuse the local read-only Gemini task monitor and return dashboard_url. Open it with open_in_codex in the right-side browser panel. It shows real external Gemini jobs, not native GPT subagents.', 'inputSchema':{'type':'object','properties':{'workspace':{'type':'string'}},'additionalProperties':False},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}},
    {'name':'gemini_status','description':'Inspect Gemini Delegate configuration and AGY availability. Default model is Gemini 3.8 Flash High; planning remains in GPT.', 'inputSchema':{'type':'object','properties':{},'additionalProperties':False},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
    {'name':'delegate_task','description':'Delegate bounded research, text/file processing, code inventory or specified mechanical edits to Gemini High using the official AGY membership session. Returns an asynchronous task ID. Web access uses a controlled read-only adapter; AGY has a scoped read grant for the plugin task directory and no global browsing grant. Never delegates complex planning or final judgments.','inputSchema':TASK_SCHEMA,'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':True}},
    {'name':'get_task_result','description':'Read task status, validated result, evidence URLs, attempts, token usage and staged artifacts. Incomplete/empty/permission-denied AGY success is treated as failure. Read edits before applying.','inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'wait_seconds':{'type':'number','minimum':0,'maximum':20,'default':0},'max_chars':{'type':'integer','minimum':500,'maximum':16000,'default':6000}},'required':['task_id'],'additionalProperties':False},'annotations':{'readOnlyHint':True,'openWorldHint':False}},
    {'name':'cancel_task','description':'Cancel a queued/running Gemini task and stop its CLI process group. Completed work is preserved.','inputSchema':{'type':'object','properties':{'task_id':{'type':'string'}},'required':['task_id'],'additionalProperties':False},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}},
    {'name':'apply_task_changes','description':'After primary-agent review, apply staged replacements only to originally supplied files. Reject source conflicts or tampered artifacts, retain backups, and roll back write failures. Requires existing user authorization for those edits.','inputSchema':{'type':'object','properties':{'task_id':{'type':'string'},'reviewed':{'type':'boolean','const':True}},'required':['task_id','reviewed'],'additionalProperties':False},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}}
]


def call(manager, name, args):
    spec = next((t for t in TOOLS if t['name']==name),None)
    if not spec:
        raise WorkerError('unknown_tool','Unknown tool')
    from worker import validate_schema
    validate_schema(args,spec['inputSchema'])
    if name=='list_tasks':
        return manager.task_list(args.get('workspace'),args.get('limit',200))
    if name=='task_monitor':
        return manager.task_monitor(args.get('workspace'))
    if name=='gemini_status':
        return manager.status()
    if name=='delegate_task':
        return manager.submit(args)
    if name=='cancel_task':
        return manager.cancel(args['task_id'])
    if name=='apply_task_changes':
        if args.get('reviewed') is not True:
            raise WorkerError('review_required','Primary-agent review is required before applying changes')
        return manager.apply(args['task_id'])
    result = manager.result(args['task_id'],args.get('wait_seconds',0))
    value = result.get('result')
    if result.get('changes') and isinstance(value,dict) and 'files' in value:
        result['result'] = {'summary':value.get('summary'),'files':[{'path':f['path']}for f in value['files']]}
    encoded = json.dumps(result.get('result'),ensure_ascii=False)
    limit = args.get('max_chars',6000)
    if len(encoded)>limit:
        result['result'] = {'preview':encoded[:limit],'truncated':True,'complete_result_path':str(manager.state/'jobs'/args['task_id']/'result.json')}
    return result


def serve():
    configure_stdio()
    manager = Manager()
    try:
        for raw in sys.stdin.buffer:
            message = None
            try:
                if len(raw)>4*1024*1024:
                    raise ValueError('MCP request exceeds 4 MiB')
                message = json.loads(raw)
                ident = message.get('id')
                method, params = message.get('method'),message.get('params') or {}
                if ident is None:
                    continue
                if method=='initialize':
                    result = {'protocolVersion':params.get('protocolVersion','2024-11-05'),'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'gemini-delegate','version':VERSION}}
                elif method=='ping':
                    result = {}
                elif method=='tools/list':
                    result = {'tools':TOOLS}
                elif method=='tools/call':
                    try:
                        data = call(manager,params.get('name'),params.get('arguments') or {})
                        result = {'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'structuredContent':data,'isError':False}
                    except WorkerError as e:
                        data = {'error':{'code':e.code,'message':str(e),'details':e.details}}
                        result = {'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'structuredContent':data,'isError':True}
                else:
                    response = {'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}
                    sys.stdout.write(json.dumps(response)+'\n');sys.stdout.flush();continue
                response = {'jsonrpc':'2.0','id':ident,'result':result}
            except Exception as e:
                response = {'jsonrpc':'2.0','id':message.get('id')if isinstance(message,dict)else None,'error':{'code':-32600,'message':f'Invalid MCP request: {type(e).__name__}'}}
            sys.stdout.write(json.dumps(response,ensure_ascii=False)+'\n')
            sys.stdout.flush()
    finally:
        manager.close()


if __name__=='__main__':
    serve()
