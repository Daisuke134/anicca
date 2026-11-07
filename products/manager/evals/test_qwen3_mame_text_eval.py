"""BFM-02 pilot software tests. Fake tiny fixtures, no human performance claims."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from qwen3_mame_text_eval import (
    human_preference, parse_llama_reply, score_pairs, pair_from_meta,
    prompt_from_text_only, frozen_split,
)


class TextOnlyHumanMemeTests(unittest.TestCase):
    def test_frozen_study_split_is_disjoint(self):
        a,b,c=frozen_split()
        self.assertEqual((len(a),len(b),len(c)),(160,40,50))
        self.assertEqual(len(set(a+b+c)),250)
        self.assertEqual(len(set(a)&set(c)),0)

    def test_parse_uses_generated_answer_not_echoed_prompt(self):
        text="Prompt follows: Joke A or Joke B?\n<|im_start|>assistant\nB\n\n[ Prompt: 8 t/s ]"
        self.assertEqual(parse_llama_reply(text),"B")
        self.assertEqual(parse_llama_reply("<|im_start|>assistant\nA\n"),"A")

    def test_invalid_generation_is_not_auto_correct(self):
        self.assertIsNone(parse_llama_reply("<|im_start|>assistant\nI think A is funnier\n"))
        self.assertIsNone(parse_llama_reply("<|im_start|>assistant\n"))
        self.assertIsNone(parse_llama_reply("Just a transcript without assistant marker"))

    def test_prompt_uses_only_permitted_descriptions(self):
        phrase="仕事の後どうする"
        a="二人が同じ方向を見る"
        b="公園の椅子と人が見える"
        p=prompt_from_text_only(phrase,a,b)
        for v in (phrase,a,b):
            self.assertIn(v,p)
        self.assertIn("A",p)
        self.assertIn("B",p)
        self.assertNotIn("caption_underlying_comic_text",p)

    def test_deterministic_prelabel_pair_selection(self):
        meta=[.15,.30,.16,.31,.23,.25,.26,.24,.28,.18]
        # same source item means, changing test labels cannot alter pair selection
        a=pair_from_meta(meta,5,seed=40,mode="separated")
        b=pair_from_meta(meta,5,seed=40,mode="separated")
        self.assertEqual(a,b)
        self.assertNotEqual(a[0],a[1])

    def test_ties_not_counted_as_positive(self):
        self.assertIsNone(human_preference(.4,.4))
        self.assertEqual(human_preference(.8,.2),"A")
        self.assertEqual(human_preference(.0,.4),"B")

    def test_invalid_counted_and_regret_not_suppressed(self):
        items=[
            {"model":"A","baseline":"A","human_a":.8,"human_b":.2},
            {"model":"B","baseline":"A","human_a":.8,"human_b":.2},
            {"model":None,"baseline":"B","human_a":.6,"human_b":.2},
            {"model":"A","baseline":"A","human_a":.4,"human_b":.4}
        ]
        s=score_pairs(items)
        self.assertEqual(s["n_total"],4)
        self.assertEqual(s["n_ties"],1)
        self.assertEqual(s["n_model_invalid"],1)
        self.assertAlmostEqual(s["model_strict_win_accuracy_including_invalid"],1/3)
        self.assertAlmostEqual(s["baseline_strict_win_accuracy"],2/3)
        self.assertGreater(s["mean_model_regret_invalid_counted"],0)

    def test_do_not_leak_test_labels_in_prompt(self):
        p=prompt_from_text_only("状況","漫画の説明A","漫画の説明B")
        self.assertNotIn("0.8",p)
        self.assertNotIn("評価点",p)


if __name__=="__main__":
    unittest.main()
