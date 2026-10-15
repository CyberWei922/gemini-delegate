#!/usr/bin/env python3
"""Compatibility client for desktop sessions without refreshed MCP tools."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from main import call
from worker import Manager, DEFAULT_TIMEOUT_SECONDS
from host_tools import configure_stdio
from runtime_config import manager_options


def run():
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument('--monitor', action='store_true')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--usage', action='store_true', help='Summarize all project tasks and retries without supplying model history')
    parser.add_argument('--all-projects', action='store_true', help='With --usage, include every recorded workspace')
    parser.add_argument('--include-tasks', action='store_true', help='With --usage, include named task details and native conversation mappings')
    parser.add_argument('--export', help='With --usage, write a UTF-8 JSON report with readable task names')
    parser.add_argument('--max-concurrency', type=int, choices=(1,2), help='AGY concurrency; default 2, explicitly choose 1 for serial execution')
    parser.add_argument('--workspace', default=str(Path.cwd()))
    parser.add_argument('--title')
    parser.add_argument('--instruction')
    parser.add_argument('--context', default='')
    parser.add_argument('--input', help='JSON file containing delegate_task arguments')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument('--max-attempts',type=int,choices=range(1,6),help='Total attempts including the first; default 3, 1 disables retries')
    parser.add_argument('--attempt-timeout', type=int, help='Fixed per-call cap, default 25 seconds; only confirmed startup failures retry')
    parser.add_argument('--agy', help='Override the installed official AGY path')
    parser.add_argument('--state-dir', type=Path, help='Override the installed task directory')
    args = parser.parse_args()
    if (args.all_projects or args.export or args.include_tasks) and not args.usage:
        parser.error('--all-projects, --export and --include-tasks require --usage')
    if sum((args.monitor, args.list, args.usage)) > 1:
        parser.error('choose one of --monitor, --list or --usage')
    manager = Manager(**manager_options(Path(__file__).resolve().parents[1],
                                       args.agy, args.state_dir, args.max_concurrency))
    try:
        if args.monitor:
            print(json.dumps(call(manager, 'task_monitor', {'workspace':args.workspace}),ensure_ascii=False),flush=True)
            return
        if args.list:
            print(json.dumps(call(manager, 'list_tasks', {'workspace':args.workspace}),ensure_ascii=False),flush=True)
            return
        if args.usage:
            summary_args = {'include_tasks':bool(args.include_tasks or args.export)}
            if not args.all_projects:
                summary_args['workspace'] = args.workspace
            summary = call(manager, 'usage_summary', summary_args)
            if args.export:
                # Never silently overwrite a user file or follow an export symlink.
                with Path(args.export).expanduser().open('x', encoding='utf-8') as output:
                    json.dump(summary, output, ensure_ascii=False, indent=2)
                Path(args.export).expanduser().chmod(0o600)
            print(json.dumps(summary,ensure_ascii=False),flush=True)
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
        if args.max_attempts is not None:
            task['max_attempts'] = args.max_attempts
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
