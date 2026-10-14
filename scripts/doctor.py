#!/usr/bin/env python3
"""Read-only prerequisite and model availability checks; no inference quota used."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugins/gemini-delegate/server'))
from host_tools import command_argv, configure_stdio, default_state_dir, find_program
from agy_check import MODEL, probe_agy


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', help='Codex executable (defaults to PATH)')
    parser.add_argument('--agy', help='Official AGY executable (defaults to PATH)')
    args = parser.parse_args()
    codex = find_program(args.codex, 'codex')
    agy = find_program(args.agy, 'agy')
    report = {'python_supported': sys.version_info >= (3, 9),
              'platform_supported': os.name in ('posix','nt'),
              'platform': sys.platform, 'state_directory':str(default_state_dir()),
              'codex_available': bool(codex), 'codex_launcher_supported': False,
              'agy_available': bool(agy), 'agy_capabilities_supported': False,
              'model': MODEL, 'model_available': False,
              'inference_tested': False}
    if codex:
        try:
            command_argv([codex])
            report['codex_launcher_supported'] = True
        except OSError:
            report['codex_launcher_error'] = True
    if agy:
        report.update(probe_agy(agy))
    report['ready_for_install'] = all(report[k] for k in
        ('python_supported', 'platform_supported', 'codex_available', 'codex_launcher_supported',
         'agy_available', 'agy_capabilities_supported', 'model_available'))
    if not report['python_supported'] or not report['platform_supported']:
        report['action'] = 'Use macOS, Linux or Windows with Python 3.9+.'
    elif not report['codex_available'] or not report['codex_launcher_supported']:
        report['action'] = 'Install or select a supported official Codex CLI with --codex.'
    elif not agy:
        report['action'] = 'Install the official AGY CLI or select its path with --agy.'
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ready_for_install'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
