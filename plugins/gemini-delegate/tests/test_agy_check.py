import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import agy_check


class PrerequisiteTests(unittest.TestCase):
    def probe(self, models=None, help_text=None, version='1.3.5', check_models=True, help_on_stderr=False):
        calls=[]
        def run(argv,timeout):
            calls.append(argv[1])
            if argv[1]=='--version':return subprocess.CompletedProcess(argv,0,version,'')
            if argv[1]=='--help':
                text=help_text if help_text is not None else ' '.join(agy_check.REQUIRED_FLAGS)
                return subprocess.CompletedProcess(argv,0,'' if help_on_stderr else text,text if help_on_stderr else '')
            if isinstance(models,Exception):raise models
            return models or subprocess.CompletedProcess(argv,0,agy_check.MODEL+'\tGemini High','')
        with mock.patch.object(agy_check,'command_argv'),mock.patch.object(agy_check,'run_command',run):
            report=agy_check.probe_agy('official-agy',check_models=check_models)
        return report,calls

    def test_supported_cli_checks_version_options_and_exact_model(self):
        report,calls=self.probe()
        self.assertEqual(report['agy_version'],'1.3.5')
        self.assertTrue(report['agy_capabilities_supported'])
        self.assertTrue(report['model_available'])
        self.assertEqual(report['models_command_exit_code'],0)
        self.assertEqual(calls,['--version','--help','models'])

    def test_official_help_on_stderr_is_supported(self):
        report,_=self.probe(help_on_stderr=True)
        self.assertTrue(report['agy_capabilities_supported'])
        self.assertTrue(report['model_available'])

    def test_old_cli_requests_update_without_attempting_login_check(self):
        report,calls=self.probe(help_text='--print --agent --model',version='1.1.5')
        self.assertEqual(report['diagnostic_code'],'unsupported_agy_cli')
        self.assertIn('--output-format',report['missing_agy_flags'])
        self.assertIn('--disable-slash-commands',report['missing_agy_flags'])
        self.assertEqual(calls,['--version','--help'])
        self.assertNotIn('sign-in',report['action'])

    def test_print_timeout_prefix_is_not_mistaken_for_print_option(self):
        report,_=self.probe(help_text=' '.join(flag for flag in agy_check.REQUIRED_FLAGS if flag!='--print'))
        self.assertIn('--print',report['missing_agy_flags'])

    def test_capability_only_preflight_does_not_query_account(self):
        report,calls=self.probe(check_models=False)
        self.assertTrue(report['agy_capabilities_supported'])
        self.assertEqual(calls,['--version','--help'])
        self.assertIsNone(report['models_command_succeeded'])

    def test_native_json_schema_support_is_required_before_installing(self):
        report,calls=self.probe(help_text=' '.join(f for f in agy_check.REQUIRED_FLAGS if f!='--json-schema'))
        self.assertEqual(report['diagnostic_code'],'unsupported_agy_cli')
        self.assertEqual(report['missing_agy_flags'],['--json-schema'])
        self.assertEqual(calls,['--version','--help'])

    def test_model_timeout_is_distinct_from_login_failure(self):
        report,_=self.probe(models=subprocess.TimeoutExpired('agy models',30))
        self.assertEqual(report['diagnostic_code'],'agy_check_timeout')
        self.assertTrue(report['models_timed_out'])
        self.assertIsNone(report['models_command_exit_code'])
        self.assertNotIn('sign-in',report['action'])

    def test_login_and_network_errors_are_distinct_and_redacted(self):
        for message,code in [('Please sign in to view available models.','authentication_required'),
                             ('request failed: TLS EOF SECRET_TOKEN','agy_network_error')]:
            with self.subTest(code=code):
                report,_=self.probe(models=subprocess.CompletedProcess([],1,'',message))
                self.assertEqual(report['diagnostic_code'],code)
                self.assertEqual(report['models_command_exit_code'],1)
                self.assertNotIn('SECRET_TOKEN',json.dumps(report))

    def test_similar_model_name_does_not_pass_fixed_model_check(self):
        report,_=self.probe(models=subprocess.CompletedProcess([],0,agy_check.MODEL+'-other',''))
        self.assertEqual(report['diagnostic_code'],'model_unavailable')
        self.assertFalse(report['model_available'])

    def test_help_timeout_and_unsupported_launcher_keep_stage(self):
        with mock.patch.object(agy_check,'command_argv',side_effect=OSError(13,'SECRET_TOKEN')):
            report=agy_check.probe_agy('official-agy')
        self.assertEqual(report['diagnostic_code'],'agy_launcher_error')
        self.assertEqual(report['check_stage'],'launcher')
        self.assertNotIn('SECRET_TOKEN',json.dumps(report))
        responses=[subprocess.CompletedProcess([],0,'1.3.5',''),subprocess.TimeoutExpired('agy --help',10)]
        with mock.patch.object(agy_check,'command_argv'),mock.patch.object(agy_check,'run_command',side_effect=responses):
            report=agy_check.probe_agy('official-agy')
        self.assertEqual(report['check_stage'],'help')
        self.assertEqual(report['diagnostic_code'],'agy_check_timeout')


if __name__=='__main__':unittest.main()
