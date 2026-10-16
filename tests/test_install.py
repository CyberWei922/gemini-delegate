import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugins/gemini-delegate/server'))
from worker import AGENT
sys.path.insert(0,str(ROOT/'scripts'))
import install
import uninstall


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='Gemini 安装测试 ')
        self.root=Path(self.tmp.name)
        self.home=self.root/'home';self.home.mkdir()
        self.target=self.home/'.codex/plugins/sources'/install.MARKETPLACE
        self.settings=self.root/'settings.json'
        self.settings.write_text(json.dumps({'permissions':{'allow':['read_file(/existing)'],'deny':['write_file(/existing)']},'theme':'keep','useG1Credits':True}), encoding='utf-8')
        self.state=self.root/'runtime'
        self.registry=self.root/'registry.json'
        self.registry.write_text('{}', encoding='utf-8')
        self.cli=self.root/'fake-codex.py'
        code='''import json,sys,pathlib
p=pathlib.Path(REGISTRY);d=json.loads(p.read_text());a=sys.argv[1:]
if a[:2]==['mcp','get']:
    if not d.get('mcp'):
        print("Error: No MCP server named 'gemini_delegate' found.",file=sys.stderr);sys.exit(1)
    print(json.dumps(d['mcp']));sys.exit()
if a[:2]==['mcp','add']:
    split=a.index('--');env={};i=3
    while i<split:
        if a[i]=='--env':
            key,value=a[i+1].split('=',1);env[key]=value;i+=2
        else:i+=1
    d['mcp']={'enabled':True,'transport':{'command':a[split+1],'args':a[split+2:],'env':env}}
elif a[:2]==['mcp','remove']:d.pop('mcp',None)
elif a[:3]==['plugin','marketplace','add']:d['marketplace']=a[3]
elif a[:2]==['plugin','add']:
    if pathlib.Path(FAIL).exists():print('controlled failure',file=sys.stderr);sys.exit(1)
    d['plugin']=a[2]
elif a[:2]==['plugin','remove']:d.pop('plugin',None)
elif a[:3]==['plugin','marketplace','remove']:d.pop('marketplace',None)
else:raise RuntimeError(a)
p.write_text(json.dumps(d));print('{}')
'''
        code=code.replace('REGISTRY',repr(str(self.registry))).replace('FAIL',repr(str(self.root/'fail')))
        self.cli.write_text('#!'+sys.executable+'\n'+code, encoding='utf-8');self.cli.chmod(0o700)
        self.agy=self.root/'fake-agy.py'
        self.agy.write_text('import sys\nif "--version" in sys.argv: print("1.3.5")\nelif "--help" in sys.argv: print("--print --agent --model --output-format --print-timeout --sandbox --disable-slash-commands --json-schema --input-format")\nelse: print("gemini-3.8-flash-high")\n',encoding='utf-8')
        self.agy.chmod(0o700)
        self.home_patch=mock.patch.object(Path,'home',return_value=self.home)
        self.home_patch.start();self.addCleanup(self.home_patch.stop)
        for module in (install,uninstall):
            patch=mock.patch.object(module,'default_codex_home',return_value=self.home/'.codex')
            patch.start();self.addCleanup(patch.stop)
        # Do not change HOME/CODEX_HOME or mutate the user's real config.
        self.addCleanup(self.tmp.cleanup)

    def run_install(self,extra=()):
        args=['install','--codex',str(self.cli),'--agy',str(self.agy),
              '--agy-settings',str(self.settings),'--state-dir',str(self.state),*extra]
        with mock.patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()) as output:
            install.main()
        return json.loads(output.getvalue())

    def test_complete_install_is_idempotent_and_uninstall_is_scoped(self):
        self.assertTrue(self.run_install()['registered'])
        first=json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertFalse(first['useG1Credits'])
        self.assertEqual(first['theme'],'keep')
        self.assertEqual(first['permissions']['deny'],['write_file(/existing)'])
        self.assertTrue(self.run_install()['registered'])
        self.assertEqual(first,json.loads(self.settings.read_text(encoding='utf-8')))
        receipt=json.loads((self.target/'.install-state.json').read_text(encoding='utf-8'))
        self.assertTrue(receipt['read_grant_added'])
        self.assertEqual(len(list((self.state/'config-backups').glob('*.json'))),1)
        with mock.patch.object(sys,'argv',['uninstall','--codex',str(self.cli)]),contextlib.redirect_stdout(io.StringIO()):uninstall.main()
        self.assertFalse(self.target.exists())
        remaining=json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertEqual(remaining['permissions']['allow'],['read_file(/existing)'])
        self.assertFalse(remaining['useG1Credits'])
        self.assertEqual(json.loads(self.registry.read_text(encoding='utf-8')),{})

    def test_windows_utf8_bom_settings_are_preserved(self):
        before={'permissions':{'allow':[]},'theme':'中文设置','useG1Credits':True}
        self.settings.write_text(json.dumps(before,ensure_ascii=False),encoding='utf-8-sig')
        self.assertTrue(self.run_install()['registered'])
        after=json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertEqual(after['theme'],'中文设置')
        self.assertFalse(after['useG1Credits'])

    def test_prepare_only_works_in_path_with_spaces_and_no_registration(self):
        out=self.run_install(['--prepare-only','--codex-home',str(self.root/'配置 space')])
        target=Path(out['target'])
        manifest=json.loads((target/'plugin/.mcp.json').read_text(encoding='utf-8'))
        args=manifest['mcpServers']['gemini-delegate']['args']
        self.assertEqual(args,[str(target/'plugin/server/main.py')])
        self.assertTrue(Path(args[0]).is_file())
        self.assertEqual(json.loads(self.registry.read_text(encoding='utf-8')),{})
        self.assertTrue(json.loads(self.settings.read_text(encoding='utf-8'))['useG1Credits'])

    def test_foreign_mcp_is_not_overwritten_without_explicit_flag(self):
        foreign={'enabled':True,'transport':{'command':'foreign','args':['other.py']}}
        self.registry.write_text(json.dumps({'mcp':foreign}), encoding='utf-8')
        before=self.settings.read_bytes()
        with self.assertRaises(install.InstallError):self.run_install()
        self.assertEqual(self.settings.read_bytes(),before)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.run_install(['--replace-existing'])['registered'])

    def test_unmanaged_destination_is_preserved(self):
        self.target.mkdir(parents=True);p=self.target/'user.txt';p.write_text('KEEP', encoding='utf-8')
        with self.assertRaises(install.InstallError):self.run_install()
        self.assertEqual(p.read_text(encoding='utf-8'),'KEEP')

    def test_invalid_permission_format_is_not_modified(self):
        self.settings.write_text('{"permissions":{"allow":"invalid"}}', encoding='utf-8')
        before=self.settings.read_bytes()
        with self.assertRaises(install.InstallError):self.run_install()
        self.assertEqual(self.settings.read_bytes(),before)
        self.assertEqual(json.loads(self.registry.read_text(encoding='utf-8')),{})

    def test_partial_cli_failure_has_receipt_and_can_recover(self):
        (self.root/'fail').touch()
        with self.assertRaises(install.InstallError):self.run_install()
        receipt=json.loads((self.target/'.install-state.json').read_text(encoding='utf-8'))
        self.assertFalse(receipt['registered'])
        self.assertEqual(receipt['completed_steps'],['marketplace'])
        (self.root/'fail').unlink()
        self.assertTrue(self.run_install()['registered'])

    def test_foreign_replacement_after_install_survives_uninstall(self):
        self.run_install()
        registry=json.loads(self.registry.read_text(encoding='utf-8'));foreign={'enabled':True,'transport':{'command':'foreign','args':[]}}
        registry['mcp']=foreign;self.registry.write_text(json.dumps(registry), encoding='utf-8')
        with mock.patch.object(sys,'argv',['uninstall','--codex',str(self.cli)]),contextlib.redirect_stdout(io.StringIO()):uninstall.main()
        self.assertEqual(json.loads(self.registry.read_text(encoding='utf-8'))['mcp'],foreign)

    def test_dry_run_makes_no_changes(self):
        before=self.settings.read_bytes()
        out=self.run_install(['--dry-run'])
        self.assertTrue(out['dry_run'])
        self.assertEqual(self.settings.read_bytes(),before)
        self.assertFalse(self.target.exists())

    def test_old_agy_is_rejected_before_settings_or_registration_changes(self):
        self.agy.write_text('import sys\nprint("1.1.5" if "--version" in sys.argv else "--print --model")',encoding='utf-8')
        before=self.settings.read_bytes()
        with self.assertRaisesRegex(install.InstallError,'unsupported_agy_cli'):
            self.run_install()
        self.assertEqual(self.settings.read_bytes(),before)
        self.assertFalse(self.target.exists())
        self.assertEqual(json.loads(self.registry.read_text(encoding='utf-8')), {})


class PackageTests(unittest.TestCase):
    def test_doctor_accepts_custom_cli_paths_and_help_on_stderr(self):
        with tempfile.TemporaryDirectory(prefix='Gemini 依赖检查 ') as directory:
            root=Path(directory)
            codex=root/'codex.py';codex.write_text('print("unused")',encoding='utf-8')
            agy=root/'agy.py'
            agy.write_text('import sys\nif "--version" in sys.argv: print("1.3.5")\nelif "--help" in sys.argv: print("--print --agent --model --output-format --print-timeout --sandbox --disable-slash-commands --json-schema --input-format",file=sys.stderr)\nelse: print("gemini-3.8-flash-high")',encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/doctor.py'),'--codex',str(codex),'--agy',str(agy)],
                                  capture_output=True,text=True,encoding='utf-8',timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertTrue(report['ready_for_install'])
            self.assertEqual(report['agy_version'],'1.3.5')
            self.assertFalse(report['inference_tested'])

    def test_doctor_missing_agy_reports_dependency_not_login(self):
        with tempfile.TemporaryDirectory() as directory:
            codex=Path(directory)/'codex.py';codex.write_text('print("unused")',encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/doctor.py'),'--codex',str(codex),
                                   '--agy',str(Path(directory)/'missing-agy')],
                                  capture_output=True,text=True,encoding='utf-8',timeout=10)
            self.assertEqual(result.returncode,1)
            report=json.loads(result.stdout)
            self.assertFalse(report['agy_available'])
            self.assertIn('Install',report['action'])
            self.assertNotIn('sign-in',report['action'])

    def test_mcp_protocol_uses_utf8_despite_legacy_console_encoding(self):
        with tempfile.TemporaryDirectory(prefix='Gemini 协议 ') as directory:
            root=Path(directory)
            agent=root/'.agents/agents/gemini-delegate-worker.md'
            agent.parent.mkdir(parents=True)
            agent.write_text(AGENT,encoding='utf-8')
            fake=root/'fake-agy.py'
            fake.write_text('import json;print(json.dumps({"status":"SUCCESS","response":"OK"}))',encoding='utf-8')
            request={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'delegate_task','arguments':{
                'title':'中文协议检查','instruction':'只返回 OK','workspace':str(root)}}}
            env={**os.environ,'PYTHONIOENCODING':'cp1252','PYTHONUTF8':'0',
                 'GEMINI_DELEGATE_AGY':str(fake),'GEMINI_DELEGATE_STATE_DIR':str(root/'state')}
            result=subprocess.run([sys.executable,str(ROOT/'plugins/gemini-delegate/server/main.py')],
                input=(json.dumps(request,ensure_ascii=False)+'\n').encode('utf-8'),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
            submitted=json.loads(result.stdout.decode('utf-8'))['result']['structuredContent']
            self.assertEqual(submitted['title'],'中文协议检查')
            self.assertEqual(submitted['workspace'],str(root.resolve()))

    def test_portable_manifests_and_version_match(self):
        root=ROOT/'plugins/gemini-delegate'
        manifest=json.loads((root/'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'],json.loads((root/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version'])
        self.assertIn(manifest['version'],(ROOT/'README.md').read_text(encoding='utf-8'))
        for rel in ('.mcp.json','mcp.json'):
            data=json.loads((root/rel).read_text(encoding='utf-8'))
            self.assertEqual(data['mcpServers']['gemini-delegate']['command'],'python3')
            self.assertIn('${PLUGIN_ROOT}',data['mcpServers']['gemini-delegate']['args'][0])
        self.assertTrue((ROOT/'LICENSE').is_file())
        self.assertTrue((ROOT/'AGENTS.md').is_file())


if __name__=='__main__':unittest.main()
