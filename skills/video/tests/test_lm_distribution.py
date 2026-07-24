#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "lm-distribution" / "distribute.py"
SPEC = importlib.util.spec_from_file_location("lm_distribution", MODULE_PATH)
lm_distribution = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(lm_distribution)


def executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.video = self.root / "creative.mp4"
        self.video.write_bytes(b"exact-video")
        self.caption = self.root / "caption.txt"
        self.caption.write_text("Exact caption\n#line", encoding="utf-8")
        self.ledger = self.root / "distribution.jsonl"
        self.calls = self.root / "calls.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def adapters(self, *, ig_outcome="published", tt_state="PUBLISHED"):
        ig = executable(
            self.root / "ig.py",
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "open(os.environ['CALLS'],'a').write(json.dumps({'platform':'instagram','argv':sys.argv[1:]})+'\\n')\n"
            f"print(json.dumps({{'outcome':'{ig_outcome}','post_url':'https://www.instagram.com/reel/IGREAL/'}}))\n",
        )
        tt = executable(
            self.root / "tt.py",
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "open(os.environ['CALLS'],'a').write(json.dumps({'platform':'tiktok','argv':sys.argv[1:]})+'\\n')\n"
            f"print(json.dumps({{'state':'{tt_state}','post_url':'https://www.tiktok.com/@life/video/123','post_id':'postiz-real'}}))\n",
        )
        return ig, tt

    def run_distribution(self, **overrides):
        ig, tt = self.adapters(
            ig_outcome=overrides.pop("ig_outcome", "published"),
            tt_state=overrides.pop("tt_state", "PUBLISHED"),
        )
        env = dict(os.environ, CALLS=str(self.calls))
        config = lm_distribution.DistributionConfig(
            creative_id="A03",
            video=self.video,
            caption=self.caption,
            ledger=self.ledger,
            instagram_adapter=ig,
            tiktok_adapter=tt,
            instagram_handle="anicca.affirms2",
            instagram_accounts=self.root / "accounts.json",
            tiktok_integration="cmp9txjdp01c8oh0yb6dhlarr",
            env=env,
            **overrides,
        )
        return lm_distribution.distribute(config)

    def test_both_adapters_receive_the_exact_same_video_and_caption(self):
        result = self.run_distribution()
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([row["platform"] for row in calls], ["instagram", "tiktok"])
        for call in calls:
            self.assertIn(str(self.video), call["argv"])
            self.assertIn(str(self.caption), call["argv"])
        self.assertEqual(result["creative_id"], "A03")

    def test_ledger_binds_both_public_urls_to_identical_hash_contract(self):
        self.run_distribution()
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual({row["platform"] for row in rows}, {"instagram", "tiktok"})
        self.assertEqual({row["creative_id"] for row in rows}, {"A03"})
        self.assertEqual({row["video_sha256"] for row in rows}, {hashlib.sha256(b"exact-video").hexdigest()})
        expected_caption = hashlib.sha256(self.caption.read_bytes()).hexdigest()
        self.assertEqual({row["caption_sha256"] for row in rows}, {expected_caption})
        self.assertTrue(all(row["public_url"].startswith("https://") for row in rows))

    def test_instagram_non_publish_fails_closed_and_tiktok_is_not_called(self):
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution(ig_outcome="failed")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([row["platform"] for row in calls], ["instagram"])

    def test_tiktok_non_published_state_fails_closed(self):
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution(tt_state="ERROR")
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["platform"], "instagram")

    def test_rerun_is_idempotent_per_exact_contract(self):
        first = self.run_distribution()
        first_call_count = len(self.calls.read_text().splitlines())
        second = self.run_distribution()
        self.assertEqual(len(self.calls.read_text().splitlines()), first_call_count)
        self.assertEqual(second["instagram_url"], first["instagram_url"])
        self.assertEqual(second["tiktok_url"], first["tiktok_url"])
        self.assertEqual(len(self.ledger.read_text().splitlines()), 2)

    def test_tiktok_profile_url_never_counts_as_a_published_artifact(self):
        video_hash = hashlib.sha256(self.video.read_bytes()).hexdigest()
        caption_hash = hashlib.sha256(self.caption.read_bytes()).hexdigest()
        self.ledger.write_text(
            json.dumps(
                {
                    "platform": "tiktok",
                    "status": "published",
                    "creative_id": "A03",
                    "video_sha256": video_hash,
                    "caption_sha256": caption_hash,
                    "public_url": "https://www.tiktok.com/@life",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.run_distribution()
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        exact_rows = [row for row in rows if row.get("public_url", "").find("/video/") >= 0]
        self.assertEqual(len(exact_rows), 1)

    def test_rejects_missing_or_empty_inputs_before_any_provider_call(self):
        self.video.unlink()
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assertFalse(self.calls.exists())

    def test_caption_is_deterministically_derived_from_the_selected_bank_row(self):
        bank = self.root / "bank.jsonl"
        bank.write_text(
            json.dumps(
                {
                    "id": "A03",
                    "pain": "時計を見る仕事",
                    "moment": "T-10 / T-5 の2段階 call",
                    "punchline": "頭から消える",
                    "material_hint": "unused",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        output = self.root / "generated-caption.txt"
        lm_distribution.render_caption(bank, "A03", output)
        text = output.read_text(encoding="utf-8")
        self.assertIn("時計を見る仕事", text)
        self.assertIn("T-10 / T-5 の2段階 call", text)
        self.assertIn("頭から消える", text)
        self.assertIn("aniccaai.com/life-manager", text)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
