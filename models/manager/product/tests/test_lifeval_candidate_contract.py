"""Regression for observed Run32 literal placeholder and fail-closed persistence."""
import tempfile
import unittest
import uuid
from pathlib import Path
from models.manager.product.interventions import InterventionStore, validate_candidates
from models.manager.product.export_cases import export_cases

def candidates(text):
    return [{'id':'a','kind':'reflection','text':text,'probability':.5},
            {'id':'b','kind':'none','text':'','probability':.5}]

class LifeValCandidateContract(unittest.TestCase):
    def test_rejects_literal_prompt_placeholder_and_whitespace(self):
        for text in ('...', '…', '  ...  ', '  ', '\n\t'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'blank or placeholder'):
                validate_candidates(candidates(text))

    def test_real_text_and_no_send_remain_valid(self):
        validate_candidates(candidates('Take one minute to settle.'))
        validate_candidates(candidates('考える時間を少し取ろう。'))
        validate_candidates(candidates('What would help right now?'))

    def test_invalid_candidate_never_commits_a_decision(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / 'cases.db')
            store = InterventionStore(path, lambda _: candidates('...'), draw=lambda: .1)
            ctx = dict(source='daily_home',language='en',desired_state='calm',time_band='morning',
                       synthetic_user={'answer_ids':{'desired_state':['calm']},'answer_version':4})
            with self.assertRaisesRegex(ValueError, 'blank or placeholder'):
                store.decide('fixture-person', str(uuid.uuid4()), ctx)
            self.assertEqual(list(export_cases(path)), [])

if __name__ == '__main__':
    unittest.main()
