import unittest
from bcto_annotation import annotate


class TestAnnotation(unittest.TestCase):
    def setUp(self):
        self.c = {'id': 'a', 'kind': 'action', 'text': 'After breakfast, meditate for five minutes.', 'probability': .5}

    def test_plan(self):
        r = annotate(self.c, ['BCIO_007010'], reviewer='fixture')
        self.assertEqual(r['coding_status'], 'PROPOSED_CODING')
        self.assertFalse(r['effect_validated'])
        self.assertEqual(self.c['probability'], .5)
        self.assertNotIn('bct_ids', self.c)

    def test_multi_label(self):
        self.assertEqual(len(annotate(self.c, ['BCIO_007010', 'BCIO_007002'], reviewer='fixture')['bct_ids']), 2)

    def test_unclassified(self):
        self.assertEqual(annotate(self.c, [], reviewer='fixture')['coding_status'], 'UNCLASSIFIED')

    def test_none(self):
        c = {'id': 'n', 'kind': 'none', 'text': ''}
        self.assertEqual(annotate(c, [], reviewer='fixture')['coding_status'], 'NO_ACTION')
        with self.assertRaises(ValueError):
            annotate(c, ['BCIO_007010'], reviewer='fixture')

    def test_unknown_and_duplicate(self):
        for ids in [['BCIO_999999'], ['BCIO_007010'] * 2, [None], 'BCIO_007010']:
            with self.assertRaises(ValueError):
                annotate(self.c, ids, reviewer='fixture')

    def test_provenance(self):
        with self.assertRaises(ValueError):
            annotate(self.c, [], reviewer=' ')

    def test_empty_content(self):
        with self.assertRaises(ValueError):
            annotate(dict(self.c, text=' '), [], reviewer='fixture')
