"""Single operational Manager cursor: no parallel curriculum/model/product NEXTs."""
from pathlib import Path
import unittest
from manager_core.single_cursor import parse_manager_queue, read_current_manager_task

ROOT=Path(__file__).resolve().parents[3]
SSOT=ROOT/"docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md"


def toy(current="01",second="未"):
    return (
        "# Company\n\n"
        "## MANAGER｜唯一の順番付き実装TODO（P00〜P12を全統合、2026-11-07）\n\n"
        "| 一意ID | 進捗 | 一つの仕事 | DONE | \n"
        "|---|---|---|---|\n"
        f"| **MG-01{' ← NOW' if current=='01' else ''}** | {'**進行中・残**' if current=='01' else '完了'} | 最初 | 証拠A |\n"
        f"| MG-02{' ← NOW' if current=='02' else ''} | {second} | 次 | 証拠B |\n"
        "| MG-03 | 未 | 後続 | 証拠C |\n"
        "\n**唯一のカーソル：MG-01。**\n\n---\n"
        "## Other company project's own historical table\n"
        "| LC01 | 未 | 別製品 | その他 |\n"
    )


class SingleManagerCursorTests(unittest.TestCase):
    def test_reads_only_one_real_current_manager_task(self):
        info=read_current_manager_task(SSOT)
        self.assertEqual(info["schema"],"manager.single_cursor.v1")
        self.assertEqual(info["current_id"],"MG-01")
        self.assertEqual(info["total_ordered_items"],18)
        self.assertIn("G3",info["task"])
        self.assertEqual(info["done"],False)

    def test_duplicate_now_is_invalid(self):
        bad=toy().replace("| MG-02 |","| MG-02 ← NOW |")
        with self.assertRaisesRegex(ValueError,"one current"):
            parse_manager_queue(bad)

    def test_missing_or_duplicate_id_is_invalid(self):
        bad=toy().replace("| MG-02 |","| MG-04 |")
        with self.assertRaises(ValueError):parse_manager_queue(bad)
        bad=toy().replace("| MG-03 |","| MG-02 |")
        with self.assertRaises(ValueError):parse_manager_queue(bad)

    def test_completed_first_can_advance_only_to_next_id(self):
        result=parse_manager_queue(toy(current="02",second="進行中・残"))
        self.assertEqual(result["current_id"],"MG-02")
        self.assertEqual(result["task"],"次")
        self.assertEqual(result["total_ordered_items"],3)

    def test_future_already_complete_without_current_is_invalid(self):
        bad=toy().replace("| MG-03 | 未 |","| MG-03 | 完了 |")
        with self.assertRaises(ValueError):parse_manager_queue(bad)

    def test_missing_queue_or_no_current_is_invalid(self):
        with self.assertRaises(ValueError):parse_manager_queue("## another unrelated TODO\n")
        with self.assertRaises(ValueError):parse_manager_queue(toy().replace(" ← NOW",""))

if __name__=="__main__":
    unittest.main()
