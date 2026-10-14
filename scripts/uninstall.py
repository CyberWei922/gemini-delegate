#!/usr/bin/env python3
"""Remove this install's registrations while retaining local jobs and backups."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from install import (InstallError, MARKETPLACE, SELECTOR, SERVER, command,
                     compatible_server, default_codex_home, resolve_program, write_json, run_command, configure_stdio)


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', help='Codex executable')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    root = default_codex_home()
    target = (root/'plugins/sources'/MARKETPLACE).resolve()
    marker = target/'.install-state.json'
    if not marker.is_file():
        raise InstallError('No managed installation receipt found.')
    receipt = json.loads(marker.read_text(encoding='utf-8'))
    cli = resolve_program(args.codex, 'codex')
    current = command(cli, ['mcp','get',SERVER,'--json'], allow_missing=True)
    owned = current is not None and compatible_server(current,receipt['python'],target)
    if args.dry_run:
        print(json.dumps({'remove_mcp':owned,'plugin':SELECTOR,'retain_job_results':True}))
        return
    if owned:
        run_command([cli,'mcp','remove',SERVER],check=True)
    steps = receipt.get('completed_steps', [])
    if 'plugin' in steps:
        command(cli,['plugin','remove',SELECTOR,'--json'])
    if 'marketplace' in steps:
        command(cli,['plugin','marketplace','remove',MARKETPLACE,'--json'])
    if receipt.get('read_grant_added') and (owned or current is None):
        settings = Path(receipt['agy_settings'])
        if settings.is_file() and not settings.is_symlink():
            data=json.loads(settings.read_text(encoding='utf-8-sig'))
            allow=data.get('permissions',{}).get('allow',[])
            if isinstance(allow,list) and receipt['read_grant'] in allow:
                allow.remove(receipt['read_grant'])
                write_json(settings,data)
    # Never automatically enable additional paid credits during uninstall.
    shutil.rmtree(target)
    print(json.dumps({'uninstalled':True,'foreign_mcp_preserved':current is not None and not owned,
                      'retained':'Gemini job results, backups and paid-credit preference'}))


if __name__=='__main__':
    try:
        main()
    except (InstallError,OSError,ValueError,subprocess.SubprocessError) as error:
        print(str(error),file=sys.stderr)
        raise SystemExit(1)
