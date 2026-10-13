#!/usr/bin/env python3
"""Read-only prerequisite and model availability checks; no inference quota used."""
import json
import os
import shutil
import subprocess
import sys


def main():
    report = {'python_supported': sys.version_info >= (3, 9),
              'platform_supported': os.name == 'posix',
              'codex_available': bool(shutil.which('codex')),
              'agy_available': bool(shutil.which('agy')),
              'model': 'gemini-3.8-flash-high', 'model_available': False,
              'inference_tested': False}
    if report['agy_available']:
        try:
            r = subprocess.run([shutil.which('agy'), 'models'], capture_output=True,
                               text=True, timeout=30)
            report['models_command_succeeded'] = r.returncode == 0
            report['model_available'] = r.returncode == 0 and report['model'] in r.stdout
        except subprocess.TimeoutExpired:
            report['models_command_succeeded'] = False
    report['ready_for_install'] = all(report[k] for k in
        ('python_supported', 'platform_supported', 'codex_available', 'agy_available', 'model_available'))
    if not report['model_available']:
        report['action'] = 'Open the official agy CLI, complete your own Google sign-in, and verify agy models includes gemini-3.8-flash-high. Do not extract credentials or switch to paid API billing.'
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ready_for_install'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
