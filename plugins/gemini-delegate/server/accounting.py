"""Read-only project accounting; grouping never supplies model history."""
import math
from pathlib import Path

CORE_KEYS = ('input_tokens', 'output_tokens', 'total_tokens')


def numeric_usage(value):
    if not isinstance(value, dict):
        return {}
    return {key: number for key, number in value.items()
            if isinstance(number, (int, float)) and not isinstance(number, bool)
            and (isinstance(number, int) or math.isfinite(number)) and number >= 0}


def task_usage(task):
    attempts = task.get('attempts') or []
    reported = {}
    known_attempts = 0
    incomplete_attempts = 0
    for attempt in attempts:
        values = numeric_usage(attempt.get('usage'))
        incomplete_attempts += int(bool(attempt.get('usage_is_partial')) or not all(key in values for key in CORE_KEYS))
        if values:
            known_attempts += 1
            for key, value in values.items():
                reported[key] = reported.get(key, 0) + value
    # Some historical records contain only the aggregate. Count it once,
    # without inventing usage for an attempt that did not report any.
    if not reported:
        reported = numeric_usage(task.get('usage'))
    missing = len(attempts) - known_attempts
    historical_unknown = bool(reported) and not attempts
    return reported, known_attempts, missing, historical_unknown, incomplete_attempts


def summarize(tasks, workspace=None, include_tasks=True):
    projects = {}
    seen = set()
    for task in tasks:
        identity = task.get('id')
        if not identity or identity in seen:
            continue
        seen.add(identity)
        path = task.get('workspace') or ''
        if workspace is not None and path != workspace:
            continue
        name = Path(path).name or '未指定项目'
        project = projects.setdefault(path, {
            'workspace': path, 'project_name': name, 'task_count': 0,
            'status_counts': {}, 'attempt_count': 0, 'retry_count': 0,
            'attempts_with_reported_usage': 0, 'attempts_without_usage': 0,
            'attempts_with_incomplete_token_counts': 0,
            'tasks_without_usage': 0,
            'historical_tasks_without_attempt_details': 0,
            'reported_usage': {}, 'usage_complete': True, 'tasks': []})
        values, known, missing, historical_unknown, partial = task_usage(task)
        attempts = task.get('attempts') or []
        status = task.get('status', 'unknown')
        # Finished tasks without any usage may have failed before starting
        # AGY; leave this explicit rather than calling them zero-cost.
        incomplete = (partial > 0 or historical_unknown or not values or
                      status not in ('completed', 'failed', 'cancelled', 'interrupted') or
                      bool(values) and 'total_tokens' not in values)
        project['task_count'] += 1
        project['status_counts'][status] = project['status_counts'].get(status, 0) + 1
        project['attempt_count'] += len(attempts)
        project['retry_count'] += max(0, len(attempts)-1)
        project['attempts_with_reported_usage'] += known
        project['attempts_without_usage'] += missing
        project['attempts_with_incomplete_token_counts'] += partial
        project['tasks_without_usage'] += int(not values)
        project['historical_tasks_without_attempt_details'] += int(historical_unknown)
        project['usage_complete'] &= not incomplete
        for key, value in values.items():
            project['reported_usage'][key] = project['reported_usage'].get(key, 0) + value
        # No prompts, source files, output bodies or provider error text.
        if include_tasks:
            project['tasks'].append({
                'task_id': identity, 'title': task.get('title', '历史任务'),
                'display_name': task.get('display_name') or name+' · '+task.get('title', '历史任务'),
                'status': status, 'reported_usage': values,
                'agy_working_directory':task.get('agy_working_directory'),
                'native_title':task.get('native_title'),
                'attempts_without_usage': missing, 'usage_complete': not incomplete,
                'attempts': [{key: attempt[key] for key in (
                    'number', 'started_at', 'finished_at', 'elapsed_seconds',
                    'status', 'error_code', 'agy_conversation_id', 'agy_session_id', 'native_title') if key in attempt}
                    for attempt in attempts]})
    if not include_tasks:
        for project in projects.values():
            project.pop('tasks')
    return {'group_by': 'workspace', 'context_mode': 'independent',
            'usage_note': 'Reported usage only; missing usage is unknown. Thinking/cache counts are included as reported, never added again to total_tokens.',
            'project_count': len(projects),
            'projects': [projects[path] for path in sorted(projects)]}
