import json
import unittest
from pathlib import Path
from compare import parse_action, grade, run
from unittest.mock import patch
import tempfile
import os

class ContractTests(unittest.TestCase):
    def test_valid_action(self):
        self.assertEqual(parse_action('{"id":"a","action":"pass"}', 'a'), 'pass')
    def test_bad_outputs_are_not_scored_as_correct(self):
        for raw in ['', 'pass', '{}', '{"id":"b","action":"pass"}', '{"id":"a","action":"PASS"}', '{"id":"a","action":"pass","action":"intervene"}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_action(raw, 'a')
    def test_correct_and_incorrect_and_missing(self):
        case={'id':'a','situation':'synthetic'}
        self.assertEqual(grade(case,'pass')['correct'], True)
        self.assertEqual(grade(case,'intervene')['correct'], False)
        self.assertIsNone(grade(case,None)['correct'])
        self.assertIsNone(grade(case,'pass')['observed_causal_effect'])
    def test_completed_and_uncertain_requests_are_never_replayed(self):
        models=json.loads(Path(__file__).with_name('models.json').read_text())
        cases=json.loads(Path(__file__).with_name('cases.json').read_text())['cases']
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            for m in models:
                d=out/m['id'].replace('/','__')
                d.mkdir()
                for i,c in enumerate(cases):
                    (d/(c['id']+('.json' if i else '.intent'))).write_text('{}')
            original_exists=Path.exists
            # Simulate a rival creating intent after the earlier existence probe.
            with patch.object(Path, 'exists', lambda p: False if p.suffix == '.intent' else original_exists(p)), patch.dict(os.environ, {'OPENROUTER_API_KEY':'synthetic-test-only'}), patch('compare.request_json', return_value={'error': {'message': 'synthetic'}}) as request, patch('builtins.print'):
                run(out)
                request.assert_not_called()

    def test_output_directory_rejects_mixed_run_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            (out/'RUN.json').write_text('{}')
            with patch.dict(os.environ, {'OPENROUTER_API_KEY':'synthetic-test-only'}), patch('compare.request_json') as request:
                with self.assertRaisesRegex(ValueError, 'different frozen run'):
                    run(out)
                request.assert_not_called()

    def test_published_cases_are_ten_unique_synthetic_situations(self):
        d=json.loads(Path(__file__).with_name('cases.json').read_text())
        self.assertEqual(len(d['cases']),10)
        self.assertEqual(len({x['id'] for x in d['cases']}),10)
        self.assertEqual(d['scoring']['correct_action'],'pass')

if __name__ == '__main__': unittest.main()
