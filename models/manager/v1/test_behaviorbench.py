import unittest
from eval_behaviorbench import parse_answer, summarize, select_indices


class BehaviorBenchTests(unittest.TestCase):
    def test_invalid_outputs_count_as_wrong(self):
        result = summarize([1, 3, 5], [1, None, 4])
        self.assertEqual(result['accuracy'], 1 / 3)
        self.assertEqual(result['invalid'], 1)
        self.assertEqual(result['n'], 3)

    def test_strict_bracketed_scale(self):
        self.assertEqual(parse_answer(' [3] '), 3)
        for text in ('3', '[6]', '[2] or [3]', 'Answer: [1]', ''):
            self.assertIsNone(parse_answer(text))

    def test_subset_is_repeatable_and_disjoint(self):
        selected, rest = select_indices(1000, 100, 42)
        self.assertEqual((selected, rest), select_indices(1000, 100, 42))
        self.assertEqual(len(selected), 100)
        self.assertFalse(set(selected) & set(rest))
        self.assertEqual(len(selected) + len(rest), 1000)
        with self.assertRaises(ValueError):
            select_indices(10, 11, 42)


if __name__ == '__main__':
    unittest.main()
