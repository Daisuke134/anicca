#!/usr/bin/env python3
"""Synthetic offline regression for the literal callback probe."""
import unittest
from audit_improv_relevance import audit

TASK = {'id':'stage1','category':'phone_ai_stage','max_chars':96,
        'cue_ack_any_of':['通知'],'any_of':['会田アイタロウ'],
        'action_any_of':['転送','手配'], 'forbidden':['深呼吸']}
GENERAL = {'id':'g1','category':'oogiri','max_chars':30}
GOOD = '会田アイタロウの通知を式場へ転送しました。本人はまだ誰にも会えていません。'


def rows(text=GOOD, text2=GOOD):
    return [{'task_id':'stage1','candidate':'A','response':text},
            {'task_id':'stage1','candidate':'B','response':text2}]

class RelevanceTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual('PASS',audit([TASK],rows())['gate'])
    def test_name_only_not_a_callback(self):
        result=audit([TASK],rows('会田アイタロウです。'))
        self.assertEqual('FAIL',result['gate'])
        self.assertIn('NO_EXPLICIT_CUE_ACKNOWLEDGEMENT',result['items'][0]['reasons'])
        self.assertIn('NO_EXPLICIT_ACTION_MARKER',result['items'][0]['reasons'])
    def test_cue_without_named_world(self):
        self.assertIn('NO_KNOWN_WORLD_ANCHOR',audit([TASK],rows('通知を転送しました。'))['items'][0]['reasons'])
    def test_action_missing(self):
        self.assertIn('NO_EXPLICIT_ACTION_MARKER',audit([TASK],rows('会田アイタロウの通知です。'))['items'][0]['reasons'])
    def test_forbidden(self):
        self.assertIn('FORBIDDEN_LITERAL',audit([TASK],rows(GOOD+'深呼吸'))['items'][0]['reasons'])
    def test_question(self):
        self.assertIn('NEW_QUESTION_AFTER_OPENING',audit([TASK],rows(GOOD+'？'))['items'][0]['reasons'])
    def test_char_limit(self):
        self.assertIn('EXCEEDS_CHAR_BUDGET',audit([TASK],rows('長'*97))['items'][0]['reasons'])
    def test_missing_candidate(self):
        self.assertEqual('FAIL',audit([TASK],rows()[:1])['gate'])
    def test_duplicate_candidate(self):
        with self.assertRaises(ValueError): audit([TASK], rows()+rows()[:1])
    def test_unknown_task(self):
        with self.assertRaises(ValueError): audit([GENERAL],rows())
    def test_bad_task_schema(self):
        with self.assertRaises(ValueError): audit([{**TASK,'action_any_of':'手配'}],rows())
    def test_general_no_stage_lexicon(self):
        submissions=[{'task_id':'g1','candidate':'A','response':'机が走った。'},
                     {'task_id':'g1','candidate':'B','response':'椅子が叫んだ。'}]
        self.assertEqual('PASS',audit([GENERAL],submissions)['gate'])
    def test_empty_general(self):
        self.assertEqual('FAIL',audit([GENERAL],[{'task_id':'g1','candidate':'A','response':''},
               {'task_id':'g1','candidate':'B','response':'文字あり'}])['gate'])
    def test_candidate_count_overflow(self):
        self.assertEqual('FAIL',audit([TASK],rows()+[{'task_id':'stage1','candidate':'C','response':GOOD}])['gate'])
    def test_bool_is_not_positive_int(self):
        with self.assertRaises(ValueError): audit([TASK], rows(),candidates_per_task=True)

if __name__ == '__main__': unittest.main()
