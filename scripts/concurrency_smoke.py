#!/usr/bin/env python3
"""Live, isolated two-task AGY acceptance test. Uses the caller's membership."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'plugins/gemini-delegate/server'))
from host_tools import configure_stdio, default_state_dir
from worker import Manager, MODEL, VERSION


def run():
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--state-dir', help='Fresh isolated runtime directory; never reuse the installed runtime')
    parser.add_argument('--output', required=True, help='New JSON report file; existing files are preserved')
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        parser.error('--output must be a new file')
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        parser.error('--workspace must be an existing project directory')
    state = Path(args.state_dir).expanduser().resolve() if args.state_dir else default_state_dir()/'trials'/uuid.uuid4().hex
    if state.exists() and any(state.iterdir()):
        parser.error('--state-dir must be a fresh isolated directory')
    marker_a, marker_b = 'A_'+uuid.uuid4().hex[:12], 'B_'+uuid.uuid4().hex[:12]
    samples = [
        ('并发验收：商品数量汇总', '按类别汇总数量，类别按字母顺序排列。原样返回本任务标记。',
         '本任务标记：'+marker_a+'\n类别,数量\nbook,3\npen,7\nbook,5\npen,2\ncard,4',
         {'marker':marker_a,'totals':[{'category':'book','quantity':8},{'category':'card','quantity':4},{'category':'pen','quantity':9}]}),
        ('并发验收：中文名称去重', '提取唯一名称，保持第一次出现的顺序，忽略空行。原样返回本任务标记。',
         '本任务标记：'+marker_b+'\n名称列表：\n苹果\n香蕉\n苹果\n\n梨\n香蕉\n桃',
         {'marker':marker_b,'names':['苹果','香蕉','梨','桃']})]
    manager = Manager(state, max_concurrency=2)
    submitted, results = [], []
    try:
        for title, instruction, context, expected in samples:
            submitted.append(manager.submit({
                'title':title, 'workspace':str(workspace), 'instruction':instruction,
                'context':context, 'timeout_seconds':180, 'response_type':'json',
                'result_schema':{'const':expected}}))
        print(json.dumps({'event':'submitted','plugin_version':VERSION,'model':MODEL,
                          'state_directory':str(state),'tasks':submitted},ensure_ascii=False),flush=True)
        while True:
            results = [manager.result(item['task_id']) for item in submitted]
            if all(result['status'] in ('completed','failed','cancelled') for result in results):
                break
            time.sleep(.25)
        # Ensure final metadata/input cleanup has completed before accounting.
        for item in submitted:
            manager.jobs[item['task_id']]['done'].wait(5)
        attempts = [result.get('attempts',[]) for result in results]
        overlap = 0
        for first in attempts[0]:
            for second in attempts[1]:
                overlap = max(overlap, min(first.get('finished_at',0),second.get('finished_at',0))-
                              max(first.get('started_at',0),second.get('started_at',0)))
        valid = all(result.get('result') == sample[3] and result['status']=='completed'
                    for result, sample in zip(results,samples))
        native_ids = [attempt.get('agy_conversation_id') for group in attempts for attempt in group]
        native_distinct = len(native_ids) == len(set(native_ids)) if native_ids and all(native_ids) else None
        if native_distinct is False:
            valid = False
        report = {'plugin_version':VERSION,'model':MODEL,'workspace':str(workspace),
                  'state_directory':str(state),'validated':valid,
                  'process_overlap_seconds':round(max(0,overlap),3),
                  'fresh_context_requested':True, 'native_conversation_ids_distinct':native_distinct,
                  'context_evidence':'Separate task input roots and fresh model agy -p invocations in the real project; no history continuation for model tasks. Native metadata renaming resumes only its own ID without a model turn. Each result matched its own unique marker and exact result contract.',
                  'tasks':results,'usage_summary':manager.usage_summary(str(workspace),include_tasks=True)}
        with output.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2)
        output.chmod(0o600)
        print(json.dumps({'event':'completed','validated':valid,
                          'process_overlap_seconds':report['process_overlap_seconds'],
                          'report':str(output),
                          'tasks':[{'id':r['id'],'title':r['title'],'status':r['status'],
                                    'attempts':len(r['attempts']),'usage':r['usage'],
                                    'error_code':r.get('error',{}).get('code')} for r in results]},ensure_ascii=False),flush=True)
        return 0 if valid and overlap > 0 else 1
    finally:
        manager.close()


if __name__ == '__main__':
    raise SystemExit(run())
