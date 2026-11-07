import importlib.util
import io
import json
from pathlib import Path
import unittest

MODULE = Path(__file__).parents[1] / 'scripts/dupgate_cloud_runner.py'

CONFIG = {
    'version': 1,
    'providers': {'codex': {
        'model_provider': 'maritime',
        'model_providers': {'maritime': {
            'name': 'Maritime', 'base_url': 'https://model.example/v1',
            'env_key': 'LM_CLOUD_MODEL_API_KEY', 'wire_api': 'responses'}}}},
    'task_classes': {'application-lane-agent': {
        'candidates': [{'provider': 'codex', 'model': 'gpt-fixture'}]}},
}


class FakeResponse(io.BytesIO):
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class DupgateCloudRunnerTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'dupgate_cloud_runner.py must implement the tenant model runner')
        spec = importlib.util.spec_from_file_location('dupgate_cloud_runner', MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / 'runner.json'
        self.config.write_text(json.dumps(CONFIG))
        self.env = {'AGENT_RUNNER_CONFIG': str(self.config),
                    'LM_CLOUD_MODEL_API_KEY': 'fixture-tenant-model'}
        self.requests = []

    def opener(self, payload):
        def open_url(request, timeout=None):
            self.requests.append((request, timeout))
            return FakeResponse(payload)
        return open_url

    def argv(self):
        # The exact argv duplicate_gate.default_runner builds for the claude CLI.
        return ['-p', 'Judge this candidate.', '--setting-sources', '',
                '--system-prompt', 'Reply with exactly one line of JSON.',
                '--model', 'haiku']

    def test_calls_the_runner_config_responses_route_and_prints_output_text(self):
        code, out = self.module.run(self.argv(), env=self.env, opener=self.opener(
            {'output_text': '{"verdict": "distinct", "closest": "", "why": "different"}'}))
        self.assertEqual(code, 0)
        self.assertEqual(out, '{"verdict": "distinct", "closest": "", "why": "different"}')
        request, _timeout = self.requests[0]
        self.assertEqual(request.full_url, 'https://model.example/v1/responses')
        self.assertEqual(request.get_header('Authorization'), 'Bearer fixture-tenant-model')
        body = json.loads(request.data.decode())
        self.assertEqual(body['model'], 'gpt-fixture')
        self.assertEqual(body['input'], 'Judge this candidate.')
        self.assertEqual(body['instructions'], 'Reply with exactly one line of JSON.')

    def test_extracts_text_from_the_output_content_shape(self):
        payload = {'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': '{"verdict": "near_duplicate"}'}]}]}
        code, out = self.module.run(self.argv(), env=self.env, opener=self.opener(payload))
        self.assertEqual(code, 0)
        self.assertEqual(out, '{"verdict": "near_duplicate"}')

    def test_missing_tenant_model_key_fails_without_a_request(self):
        env = {'AGENT_RUNNER_CONFIG': str(self.config)}
        code, out = self.module.run(self.argv(), env=env, opener=self.opener({'output_text': 'x'}))
        self.assertNotEqual(code, 0)
        self.assertEqual(out, '')
        self.assertEqual(self.requests, [])

    def test_http_failure_is_a_nonzero_exit_with_no_stdout(self):
        def failing(request, timeout=None):
            raise OSError('connection refused')
        code, out = self.module.run(self.argv(), env=self.env, opener=failing)
        self.assertNotEqual(code, 0)
        self.assertEqual(out, '')


if __name__ == '__main__':
    unittest.main()
