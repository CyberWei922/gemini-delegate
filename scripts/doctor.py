#!/usr/bin/env python3
"""Read-only prerequisite and model availability checks; no inference quota used."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugins/gemini-delegate/server'))
from host_tools import command_argv, configure_stdio, default_state_dir, find_program, run_command


def main():
    configure_stdio()
    report = {'python_supported': sys.version_info >= (3, 9),
              'platform_supported': os.name in ('posix','nt'),
              'platform': sys.platform, 'state_directory':str(default_state_dir()),
              'codex_available': bool(find_program(None,'codex')),
              'agy_available': bool(find_program(None,'agy')),
              'model': 'gemini-3.8-flash-high', 'model_available': False,
              'inference_tested': False}
    if report['agy_available']:
        try:
            command_argv([find_program(None,'codex')]) if report['codex_available'] else None
            r = run_command([find_program(None,'agy'), 'models'], timeout=30)
            report['models_command_succeeded'] = r.returncode == 0
            report['model_available'] = r.returncode == 0 and report['model'] in r.stdout
        except subprocess.TimeoutExpired:
            report['models_command_succeeded'] = False
        except OSError as e:
            report['models_command_succeeded'] = False
            report['launcher_error'] = str(e)
    report['ready_for_install'] = all(report[k] for k in
        ('python_supported', 'platform_supported', 'codex_available', 'agy_available', 'model_available'))
    if not report['model_available']:
        report['action'] = 'Open the official agy CLI, complete your own Google sign-in, and verify agy models includes gemini-3.8-flash-high. Do not extract credentials or switch to paid API billing.'
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ready_for_install'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
