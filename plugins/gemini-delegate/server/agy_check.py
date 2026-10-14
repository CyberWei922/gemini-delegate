"""Read-only official CLI checks with safe, specific diagnostics."""
import re
import subprocess

from host_tools import command_argv, run_command

MODEL = 'gemini-3.8-flash-high'
REQUIRED_FLAGS = ('--print', '--agent', '--model', '--output-format',
                  '--print-timeout', '--sandbox', '--disable-slash-commands')


def probe_agy(agy, check_models=True, timeout=30):
    report = {'agy_version': None, 'agy_capabilities_supported': False,
              'missing_agy_flags': [], 'model': MODEL, 'model_available': False,
              'models_command_succeeded': None, 'models_command_exit_code': None,
              'models_timed_out': False}

    def failure(code, stage, action):
        report.update(diagnostic_code=code, check_stage=stage, action=action)
        return report

    stage = 'launcher'
    try:
        command_argv([agy])
        for stage, argument in (('version', '--version'), ('help', '--help')):
            result = run_command([agy, argument], timeout=min(10, timeout))
            report[stage + '_command_exit_code'] = result.returncode
            if result.returncode:
                return failure('agy_command_failed', stage,
                               'Check the official AGY CLI ' + argument + ' command in your terminal.')
            if stage == 'version':
                version = re.search(r'(?<![\w.])v?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)',
                                    result.stdout + '\n' + result.stderr)
                report['agy_version'] = version.group(1) if version else None
            else:
                report['missing_agy_flags'] = [flag for flag in REQUIRED_FLAGS
                    if not re.search(r'(?<![\w-])' + re.escape(flag) + r'(?![\w-])',
                                     result.stdout + '\n' + result.stderr)]
        if report['missing_agy_flags']:
            return failure('unsupported_agy_cli', 'help',
                           'Update the official AGY CLI: required print-mode options are missing. '
                           'Use https://antigravity.google/docs/cli/.')
        report['agy_capabilities_supported'] = True
        if not check_models:
            return report
        stage = 'models'
        result = run_command([agy, 'models'], timeout=timeout)
        report['models_command_exit_code'] = result.returncode
        report['models_command_succeeded'] = result.returncode == 0
        if result.returncode:
            # Classify known failures without returning opaque CLI output,
            # account identifiers or any authentication material.
            message = (result.stdout + '\n' + result.stderr).lower()
            if re.search(r'please sign in|not authenticated|authentication required|unauthenticated', message):
                return failure('authentication_required', stage,
                               'Open the official AGY CLI and complete your own Google sign-in.')
            if re.search(r'\beof\b|tls|handshake|connection|network|request failed|timed? out|dns|dial tcp|proxy', message):
                return failure('agy_network_error', stage,
                               'Check the network connection for the official AGY CLI, then rerun agy models.')
            return failure('agy_command_failed', stage,
                           'Run the official agy models command in your terminal to inspect the failure.')
        report['model_available'] = MODEL in result.stdout.split()
        if not report['model_available']:
            return failure('model_unavailable', stage,
                           'AGY models succeeded but ' + MODEL + ' is unavailable. '
                           'Check account model access; do not downgrade or switch to paid API billing.')
        return report
    except subprocess.TimeoutExpired:
        report['check_timed_out'] = True
        if stage == 'models':
            report.update(models_timed_out=True, models_command_succeeded=False)
        return failure('agy_check_timeout', stage,
                       'The official AGY ' + stage + ' check timed out. '
                       'Check CLI responsiveness and network connectivity, then retry the check.')
    except OSError as error:
        report['launcher_error'] = {'errno': error.errno,
                                    'winerror': getattr(error, 'winerror', None)}
        return failure('agy_launcher_error', stage,
                       'Check the official AGY path. On Windows use a native .exe or standard npm Node .cmd entrypoint.')
