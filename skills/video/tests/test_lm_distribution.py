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
        self.approvals = self.root / "approvals.jsonl"
        self.approve()

    def approve(self, *, creative_id="A03", video=None, caption=None):
        """Record the receipt that lets distribution run, bound to the exact bytes."""
        video = self.video if video is None else video
        caption = self.caption if caption is None else caption
        row = {
            "approved_at": "2026-07-25T04:00:00Z",
            "approver": "dais",
            "creative_id": creative_id,
            "video_sha256": hashlib.sha256(Path(video).read_bytes()).hexdigest(),
            "caption_sha256": hashlib.sha256(Path(caption).read_bytes()).hexdigest(),
        }
        with self.approvals.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return row

    def tearDown(self):
        self.tmp.cleanup()

    def adapters(self, *, ig_outcome="published", tt_state="PUBLISHED", tt_extra=None):
        tt_result = {
            "state": tt_state,
            "post_url": "https://www.tiktok.com/@life/video/123",
            "post_id": "postiz-real",
            **(tt_extra or {}),
        }
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
            f"print(json.dumps({tt_result!r}))\n",
        )
        return ig, tt

    def run_distribution(self, **overrides):
        ig, tt = self.adapters(
            ig_outcome=overrides.pop("ig_outcome", "published"),
            tt_state=overrides.pop("tt_state", "PUBLISHED"),
            tt_extra=overrides.pop("tt_extra", None),
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
            approvals=overrides.pop("approvals", self.approvals),
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

    def test_direct_route_cost_and_logged_out_provenance_survive_into_ledger(self):
        self.run_distribution(
            tt_extra={
                "route": "direct_browser",
                "provider_cost_usd": 0,
                "logged_out_readback": True,
                "migration_date": "2026-07-24",
            }
        )
        row = [
            item
            for item in map(json.loads, self.ledger.read_text().splitlines())
            if item["platform"] == "tiktok"
        ][0]
        self.assertEqual(row["route"], "direct_browser")
        self.assertEqual(row["provider_cost_usd"], 0)
        self.assertEqual(row["logged_out_readback"], True)
        self.assertEqual(row["migration_date"], "2026-07-24")

    def test_postiz_remains_default_until_explicit_direct_migration_gate(self):
        here = self.root / "lm-distribution"
        self.assertEqual(
            lm_distribution.default_tiktok_adapter(here, {}),
            here / "postiz_video.py",
        )
        self.assertEqual(
            lm_distribution.default_tiktok_adapter(
                here,
                {"LM_TIKTOK_DIRECT_MIGRATION": "1"},
            ),
            here / "tiktok_direct.mjs",
        )
        self.assertEqual(
            lm_distribution.default_tiktok_adapter(
                here,
                {"LM_TIKTOK_DIRECT_MIGRATION": "true"},
            ),
            here / "postiz_video.py",
        )

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


class ApprovalGateTests(DistributionTests):
    """9c: nothing reaches Instagram or TikTok until Dais approves that exact video and caption."""

    def assert_no_provider_was_touched(self):
        self.assertFalse(self.calls.exists(), "no adapter may run before approval")
        self.assertFalse(self.ledger.exists(), "an unapproved run must not write the ledger")

    def test_a_missing_approvals_file_refuses_and_touches_no_provider(self):
        self.approvals.unlink()
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_an_empty_approvals_file_refuses_and_touches_no_provider(self):
        self.approvals.write_text("", encoding="utf-8")
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_an_approval_for_a_different_creative_does_not_authorise_this_one(self):
        self.approvals.write_text("", encoding="utf-8")
        self.approve(creative_id="SOME-OTHER")
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_editing_the_video_after_approval_invalidates_the_receipt(self):
        self.video.write_bytes(b"a-different-cut")
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_editing_the_caption_after_approval_invalidates_the_receipt(self):
        self.caption.write_text("A rewritten caption", encoding="utf-8")
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_a_malformed_approval_line_is_ignored_rather_than_trusted(self):
        self.approvals.write_text("{not json\n", encoding="utf-8")
        with self.assertRaises(lm_distribution.DistributionError):
            self.run_distribution()
        self.assert_no_provider_was_touched()

    def test_the_matching_receipt_lets_the_same_bytes_through(self):
        result = self.run_distribution()
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([row["platform"] for row in calls], ["instagram", "tiktok"])
        self.assertEqual(result["creative_id"], "A03")
