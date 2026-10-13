#!/usr/bin/env python3
"""Portable installer. No login/token extraction, shell pipelines or pip packages."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
MARKETPLACE = 'gemini-delegate-community'
SELECTOR = 'gemini-delegate@' + MARKETPLACE
SERVER = 'gemini_delegate'


class InstallError(RuntimeError):
    pass


def default_codex_home():
    return Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')).expanduser().resolve()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if Path(name).exists():
            Path(name).unlink()


def resolve_program(value, name):
    path = shutil.which(value or name)
    if not path:
        raise InstallError('Missing executable: ' + (value or name))
    return str(Path(path).resolve())


def command(cli, args, allow_missing=False):
    run = subprocess.run([cli, *args], capture_output=True, text=True, timeout=45)
    if run.returncode:
        if allow_missing and 'no mcp server named' in run.stderr.lower():
            return None
        # Do not dump configuration or opaque command output into public logs.
        raise InstallError('Codex command failed: ' + ' '.join(args[:3]) +
                           '. Run the same command in your terminal for diagnostics.')
    if not run.stdout.strip():
        return {}
    try:
        return json.loads(run.stdout)
    except ValueError:
        raise InstallError('Codex did not return JSON; update the Codex CLI.')


def compatible_server(existing, python, target):
    if existing is None:
        return True
    transport = existing.get('transport', {})
    return (transport.get('command') == python and
            transport.get('args') == [str(target / 'plugin/server/main.py')])


def prepare(target, python, env=None):
    target = Path(target)
    marker = target / '.install-state.json'
    if target.exists() and not marker.is_file():
        raise InstallError('Destination is not owned by this installer: ' + str(target))
    if target.is_symlink():
        raise InstallError('Installation destination must not be a symlink.')
    old = json.loads(marker.read_text()) if marker.exists() else {}
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.gemini-stage-', dir=target.parent) as staging:
        stage = Path(staging) / 'package'
        plugin = stage / 'plugin'
        shutil.copytree(REPO / 'plugins/gemini-delegate', plugin,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'VALIDATION*.json'))
        actual = {'mcpServers': {'gemini-delegate': {
            'type': 'stdio', 'command': python,
            'args': [str(target / 'plugin/server/main.py')],
            'cwd': str(target / 'plugin'), 'env': env or {}}}}
        write_json(plugin / '.mcp.json', actual)
        write_json(plugin / 'mcp.json', actual)
        catalog = json.loads((REPO / '.agents/plugins/marketplace.json').read_text())
        catalog['plugins'][0]['source']['path'] = './plugin'
        write_json(stage / '.agents/plugins/marketplace.json', catalog)
        receipt = {**old, 'version': json.loads((plugin / 'plugin.json').read_text())['version'],
                   'python': python, 'target': str(target), 'marketplace': MARKETPLACE,
                   'server': SERVER, 'prepared': True}
        write_json(stage / '.install-state.json', receipt)
        backup = None
        if target.exists():
            backup = Path(staging) / 'previous'
            os.replace(target, backup)
        try:
            os.replace(stage, target)
        except OSError:
            if backup:
                os.replace(backup, target)
            raise
    return receipt


def configure_agy(path, state, keep_credit_setting=False):
    path = Path(path)
    if path.is_symlink():
        raise InstallError('AGY settings must not be a symlink.')
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise InstallError('AGY settings must be a JSON object.')
    permissions = data.setdefault('permissions', {})
    if not isinstance(permissions, dict):
        raise InstallError('Unsupported AGY permissions format; settings left unchanged.')
    allow = permissions.setdefault('allow', [])
    if not isinstance(allow, list):
        raise InstallError('Unsupported AGY allow-list format; settings left unchanged.')
    grant = 'read_file(' + str(Path(state).resolve() / 'jobs') + ')'
    added = grant not in allow
    changed = added or (not keep_credit_setting and data.get('useG1Credits') is not False)
    if changed:
        if path.exists():
            backups = Path(state) / 'config-backups'
            backups.mkdir(parents=True, exist_ok=True, mode=0o700)
            backups.chmod(0o700)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            backup = backups / ('settings-' + stamp + '.json')
            shutil.copyfile(path, backup)
            backup.chmod(0o600)
        if added:
            allow.append(grant)
        if not keep_credit_setting:
            data['useG1Credits'] = False
        write_json(path, data)
    return {'agy_settings': str(path), 'read_grant': grant, 'read_grant_added': added}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path,
                        default=default_codex_home())
    parser.add_argument('--codex', help='Codex executable (defaults to PATH)')
    parser.add_argument('--agy', help='Official AGY executable (defaults to PATH)')
    parser.add_argument('--agy-settings', type=Path,
                        default=Path.home() / '.gemini/antigravity-cli/settings.json')
    parser.add_argument('--state-dir', type=Path,
                        default=Path(os.environ.get('GEMINI_DELEGATE_STATE_DIR', Path.home() / '.local/share/gemini-delegate')))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--prepare-only', action='store_true',
                        help='Stage files only; do not change Codex or AGY settings')
    parser.add_argument('--replace-existing', action='store_true',
                        help='Explicitly replace an existing gemini_delegate MCP registration')
    parser.add_argument('--keep-credit-setting', action='store_true',
                        help='Preserve AGY additional-credit preference instead of disabling it')
    args = parser.parse_args()
    if os.name != 'posix' or sys.version_info < (3, 9):
        raise InstallError('macOS/Linux and Python 3.9+ are required. Windows is not supported.')
    python = str(Path(sys.executable).resolve())
    target = args.codex_home.expanduser().resolve() / 'plugins/sources' / MARKETPLACE
    plan = {'target': str(target), 'python': python, 'plugin': SELECTOR,
            'model': 'gemini-3.8-flash-high', 'automatic_webpage': False}
    if args.dry_run:
        print(json.dumps({**plan, 'dry_run': True}, ensure_ascii=False))
        return
    cli = None
    if not args.prepare_only:
        cli = resolve_program(args.codex, 'codex')
        agy = resolve_program(args.agy, 'agy')
        if args.codex_home.resolve() != default_codex_home().resolve():
            raise InstallError('--codex-home differs from the Codex CLI home. Use --prepare-only for isolated staging.')
        existing = command(cli, ['mcp', 'get', SERVER, '--json'], allow_missing=True)
        if not compatible_server(existing, python, target) and not args.replace_existing:
            raise InstallError('An existing gemini_delegate MCP registration points elsewhere. '
                               'Inspect it first; use --replace-existing only for an authorized replacement.')
    env = {'GEMINI_DELEGATE_STATE_DIR': str(args.state_dir.expanduser().resolve())}
    if not args.prepare_only:
        env['GEMINI_DELEGATE_AGY'] = agy
    receipt = prepare(target, python, env)
    if args.prepare_only:
        print(json.dumps({**plan, 'prepared': True, 'registered': False}, ensure_ascii=False))
        return
    # Save a recoverable receipt after each step. Never erase existing user config.
    steps = receipt.get('completed_steps', [])
    try:
        grant = configure_agy(args.agy_settings.expanduser(), args.state_dir.expanduser(), args.keep_credit_setting)
        old_added = receipt.get('read_grant_added', False)
        receipt.update(grant)
        receipt['read_grant_added'] = old_added or grant['read_grant_added']
        write_json(target / '.install-state.json', receipt)
        for label, argv in [
            ('marketplace', ['plugin', 'marketplace', 'add', str(target), '--json']),
            ('plugin', ['plugin', 'add', SELECTOR, '--json']),
            ('mcp', ['mcp', 'add', SERVER, '--env', 'GEMINI_DELEGATE_STATE_DIR='+env['GEMINI_DELEGATE_STATE_DIR'],
                     '--env', 'GEMINI_DELEGATE_AGY='+env['GEMINI_DELEGATE_AGY'], '--', python, str(target / 'plugin/server/main.py')])]:
            command(cli, argv) if label != 'mcp' else subprocess.run([cli, *argv], check=True, timeout=45, capture_output=True)
            if label not in steps:
                steps.append(label)
            receipt['completed_steps'] = steps
            write_json(target / '.install-state.json', receipt)
        registered = command(cli, ['mcp', 'get', SERVER, '--json'])
        if not compatible_server(registered, python, target) or not registered.get('enabled', False):
            raise InstallError('MCP registration verification failed.')
        receipt['registered'] = True
        write_json(target / '.install-state.json', receipt)
    except Exception:
        receipt['registered'] = False
        write_json(target / '.install-state.json', receipt)
        raise
    print(json.dumps({**plan, 'registered': True,
                      'next': 'Start a new Codex chat and run the AGENTS.md smoke check. Login, model access and actual inference must be verified separately.'}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (InstallError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
