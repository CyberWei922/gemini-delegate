#!/usr/bin/env python3
"""Compatibility client for desktop sessions without refreshed MCP tools."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from main import call
from worker import Manager
from host_tools import configure_stdio
from runtime_config import manager_options


def run():
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument('--monitor', action='store_true')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--workspace', default=str(Path.cwd()))
    parser.add_argument('--title')
    parser.add_argument('--instruction')
    parser.add_argument('--context', default='')
    parser.add_argument('--input', help='JSON file containing delegate_task arguments')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--attempt-timeout', type=int, help='Optional first-attempt cap; total timeout still bounds all attempts')
    parser.add_argument('--agy', help='Override the installed official AGY path')
    parser.add_argument('--state-dir', type=Path, help='Override the installed task directory')
    args = parser.parse_args()
    manager = Manager(**manager_options(Path(__file__).resolve().parents[1],
                                       args.agy, args.state_dir))
    try:
        if args.monitor:
            print(json.dumps(call(manager, 'task_monitor', {'workspace':args.workspace}),ensure_ascii=False),flush=True)
            return
        if args.list:
            print(json.dumps(call(manager, 'list_tasks', {'workspace':args.workspace}),ensure_ascii=False),flush=True)
            return
        if args.input:
            task = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
            task.setdefault('workspace', args.workspace)
        else:
            if not args.instruction:
                parser.error('--instruction or --input is required')
            task = {'instruction':args.instruction,'context':args.context,
                    'workspace':args.workspace,'timeout_seconds':args.timeout}
            if args.title:
                task['title'] = args.title
        if args.attempt_timeout is not None:
            task['attempt_timeout_seconds'] = args.attempt_timeout
        submitted = call(manager, 'delegate_task', task)
        print(json.dumps(submitted,ensure_ascii=False),flush=True)
        while True:
            result = call(manager, 'get_task_result',
                          {'task_id':submitted['task_id'],'wait_seconds':20,'max_chars':6000})
            if result['status'] in ('completed','failed','cancelled'):
                print(json.dumps(result,ensure_ascii=False),flush=True)
                if result['status'] != 'completed':
                    raise SystemExit(1)
                return
            print(json.dumps({'task_id':submitted['task_id'],'status':result['status']},ensure_ascii=False),flush=True)
    finally:
        manager.close()


if __name__=='__main__':
    run()
