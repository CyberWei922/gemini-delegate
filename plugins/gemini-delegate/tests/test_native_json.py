"""Native schema transport, fail-closed validation and private-file lifetime."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from worker import Manager, WorkerError, decode_result


class NativeJSONTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.manager=Manager(self.root/'state',agy='fake-agy')
        self.addCleanup(self.manager.close)
        patch=mock.patch('worker.prepare_agent');patch.start();self.addCleanup(patch.stop)

    def run_task(self,process,**options):
        with mock.patch('worker.run_process',side_effect=process) as calls:
            jid=self.manager.submit({'instruction':'Return the requested value','workspace':str(self.root),**options})['task_id']
            result=self.manager.result(jid,5)
        return result,calls

    def test_schema_file_passed_privately_and_removed_after_success(self):
        schema={'type':'object','properties':{'中文':{'type':'integer'}},'required':['中文'],'additionalProperties':False}
        paths=[]
        def process(argv,*args,**kwargs):
            path=Path(argv[argv.index('--json-schema')+1]);paths.append(path)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),schema)
            if os.name!='nt':self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertNotIn('--print',argv)
            self.assertNotIn('Return the requested value',' '.join(argv))
            return json.dumps({'status':'SUCCESS','response':'irrelevant prose','structured_output':{'中文':3}}),'',0
        result,calls=self.run_task(process,response_type='json',result_schema=schema)
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['result'],{'中文':3})
        self.assertEqual(calls.call_count,1)
        self.assertTrue(result['attempts'][0]['native_json_schema'])
        self.assertTrue(result['attempts'][0]['structured_output_reported'])
        self.assertEqual(result['output_contract']['mode'],'agy_json_schema')
        self.assertFalse(paths[0].exists())
        self.assertIn('output_contract',self.manager.task_list(str(self.root))['tasks'][0])

    def test_missing_native_payload_is_not_accepted_as_text_fallback(self):
        envelope=json.dumps({'status':'SUCCESS','response':'{"n":3}'})
        result,calls=self.run_task(lambda *a,**kw:(envelope,'',0),response_type='json')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error']['code'],'invalid_result')
        self.assertIsNone(result['result']);self.assertEqual(calls.call_count,1)
        self.assertFalse(result['attempts'][0]['structured_output_reported'])
        self.assertFalse((self.manager.state/'jobs'/result['id']/'output-schema.json').exists())

    def test_invalid_native_value_still_fails_local_validation_without_retry(self):
        envelope=json.dumps({'status':'SUCCESS','response':'{"n":3}','structured_output':{'n':'wrong'}})
        result,calls=self.run_task(lambda *a,**kw:(envelope,'',0),response_type='json',
            result_schema={'type':'object','properties':{'n':{'type':'integer'}}})
        self.assertEqual(result['status'],'failed');self.assertEqual(calls.call_count,1)
        self.assertIsNone(result['result'])

    def test_json_without_explicit_schema_preserves_arbitrary_values_in_native_wrapper(self):
        def process(argv,*args,**kwargs):
            schema=json.loads(Path(argv[argv.index('--json-schema')+1]).read_text())
            self.assertEqual(schema['type'],'object');self.assertEqual(schema['properties'],{'value':{}})
            return json.dumps({'status':'SUCCESS','structured_output':{'value':[1,False,None]}}),'',0
        result,_=self.run_task(process,response_type='json')
        self.assertEqual(result['result'],[1,False,None]);self.assertEqual(result['status'],'completed')
        self.assertTrue(result['output_contract']['wrapped_value'])

    def test_non_object_schema_is_wrapped_and_still_enforced_locally(self):
        def process(argv,*args,**kwargs):
            schema=json.loads(Path(argv[argv.index('--json-schema')+1]).read_text())
            self.assertEqual(schema['properties']['value'],{'type':'integer','minimum':1})
            return json.dumps({'status':'SUCCESS','structured_output':{'value':7}}),'',0
        result,_=self.run_task(process,response_type='json',result_schema={'type':'integer','minimum':1})
        self.assertEqual(result['status'],'completed');self.assertEqual(result['result'],7)

    def test_malformed_native_wrapper_is_rejected(self):
        for value in [7,{}, {'value':7,'extra':1}]:
            with self.subTest(value=value):
                with self.assertRaises(WorkerError):
                    decode_result(json.dumps({'status':'SUCCESS','structured_output':value}),'',0,'json',{},
                                  require_structured=True,unwrap_native=True)

    def test_native_scalars_and_empty_containers_are_values_not_empty_transport(self):
        for value in [0,False,None,{},[],""]:
            with self.subTest(value=value):
                envelope=json.dumps({'status':'SUCCESS','structured_output':value})
                actual,_=decode_result(envelope,'',0,'json',{},require_structured=True)
                self.assertEqual(actual,value)

    def test_text_mode_has_no_native_schema_flag(self):
        def process(argv,*args,**kwargs):
            self.assertNotIn('--json-schema',argv)
            return json.dumps({'status':'SUCCESS','response':'OK'}),'',0
        result,_=self.run_task(process)
        self.assertEqual(result['result'],'OK');self.assertNotIn('output_contract',result)

    def test_unsupported_schema_in_unused_branch_rejected_before_model_call(self):
        with mock.patch('worker.run_process') as process:
            with self.assertRaises(WorkerError) as caught:
                self.manager.submit({'instruction':'Return JSON','response_type':'json',
                    'result_schema':{'type':'object','properties':{'unused':{'$ref':'file:///private'}}}})
        self.assertEqual(caught.exception.code,'unsupported_schema');process.assert_not_called()

    def test_cli_schema_rejection_is_actionable_and_does_not_echo_private_schema(self):
        with self.assertRaises(WorkerError) as caught:
            decode_result('', 'Error: invalid --json-schema: PRIVATE_SCHEMA_CONTENT',1,'json',{},require_structured=True)
        self.assertEqual(caught.exception.code,'native_schema_unsupported')
        self.assertNotIn('PRIVATE_SCHEMA_CONTENT',str(caught.exception))


if __name__=='__main__':unittest.main()
