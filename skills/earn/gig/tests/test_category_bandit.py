"""arm = category, reward = funnel depth -- the numbers pick the category, not the agent.

Why this file exists: strategy.json's priority_categories/skip_categories were written
entirely from LLM hypotheses across 537 passes and were never tied to measured outcome.
X8 makes category selection a bandit whose arms are categories.

The measurement that shaped these tests (2026-07-27, real ledgers):
  applied.jsonl  224 rows,  27 with a category (12%)
  shuppin.jsonl  104 rows,   4 with a category (4%)
  earnings.jsonl   2 rows, joinable to applied only by title (earnings.requestId is a
                   talkroom id, applied.requestId is a posting id -- they never match)
  of the 27 categorised rows, 2 are not categories at all ("thread_closeout",
  "nurture_sweep") -- both carry requestId "N/A"
  the remaining 25 clean rows have 0 replies, 0 deliveries, 0 payments

So the honest state is: zero reward-bearing observations today. The fallback path is not
an edge case, it is the current default, and these tests treat it as a first-class
behaviour: the bandit must never be the reason the loop stops applying.

Spec: docs/loop-engineering/28-gig-category-bandit-spec.md
"""

import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

DAY = 86400.0


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bandit = load(SCRIPTS / "category_bandit.py", "category_bandit")


class BanditFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = 1785100000.0

    def write(self, name, rows):
        path = self.root / name
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                        encoding="utf-8")
        return path

    def strategy(self, priority, skip=()):
        path = self.root / "strategy.json"
        path.write_text(json.dumps({
            "priority_categories": list(priority),
            "skip_categories": list(skip),
        }, ensure_ascii=False), encoding="utf-8")
        return path

    def applied(self, name, rows):
        return self.write(name, rows)

    def row(self, rid, category, status="applied", age_days=30.0, **extra):
        r = {"requestId": rid, "category": category, "status": status,
             "ts": self.now - age_days * DAY}
        r.update(extra)
        return r

    def chain(self, pairs):
        """(募集 id, talkroom id) pairs as coconala_queue_snapshot.py proved them."""
        return self.write("identity_chain.jsonl", [
            {"request_id": rid, "talkroom_id": tid, "lane": "orders",
             "source": "queue_snapshot", "evidence": "test"}
            for rid, tid in pairs])

    def select(self, applied_rows, priority, *, skip=(), earnings_rows=(),
               chain_pairs=(), seed=7, **kwargs):
        return bandit.select(
            applied_path=self.applied("applied.jsonl", applied_rows),
            earnings_path=self.write("earnings.jsonl", list(earnings_rows)),
            strategy_path=self.strategy(priority, skip),
            chain_path=self.chain(chain_pairs),
            now=self.now,
            seed=seed,
            **kwargs,
        )


class ArmAndRewardTest(BanditFixture):
    def test_same_seed_gives_identical_ranking(self):
        """Selection must be reproducible so a pass can be explained after the fact."""
        rows = [self.row(f"51000{i}", "A" if i % 2 else "B", status="replied")
                for i in range(12)]
        first = self.select(rows, ["A", "B", "C"], seed=1234)
        second = self.select(rows, ["A", "B", "C"], seed=1234)
        self.assertEqual([a["arm"] for a in first["ranking"]],
                         [a["arm"] for a in second["ranking"]])
        self.assertEqual(first["status"], "ok")

    def test_deeper_funnel_stage_earns_more_posterior_mass(self):
        """paid > contracted > engaged > applied -- downstream is worth more."""
        rows = []
        rows += [self.row(f"5200{i}", "paid-arm", status="applied") for i in range(3)]
        rows += [self.row(f"5300{i}", "engaged-arm", status="replied") for i in range(3)]
        rows += [self.row(f"5400{i}", "flat-arm", status="applied") for i in range(3)]
        earnings = [{"requestId": "18000000", "title": "paid job", "jpy": 50000.0,
                     "status": "検収完了"}]
        result = self.select(rows, ["paid-arm", "engaged-arm", "flat-arm"],
                             earnings_rows=earnings,
                             chain_pairs=[("52000", "18000000")])
        means = {a["arm"]: a["posterior_mean"] for a in result["ranking"]}
        self.assertGreater(means["paid-arm"], means["engaged-arm"])
        self.assertGreater(means["engaged-arm"], means["flat-arm"])

    def test_earnings_join_goes_through_the_identity_chain(self):
        """Measured: earnings.requestId is a talkroom id and never equals a posting id.

        Was: joined on an exact title string, because the ids did not match. A title is
        not an identity -- two clients can post the same words. The chain records the
        real (募集 -> talkroom) pair that coconala_queue_snapshot.py already reads off
        the offer page, and the payment is attributed through that or not at all.
        """
        rows = [self.row("5167108", "minecraft", title="銃アドオンのバグ修正")]
        rows += [self.row(f"5500{i}", "minecraft") for i in range(7)]
        earnings = [{"requestId": "18011694", "title": "銃アドオンのバグ修正",
                     "jpy": 13260.0, "status": "検収完了"}]
        result = self.select(rows, ["minecraft"], earnings_rows=earnings,
                             chain_pairs=[("5167108", "18011694")])
        arm = next(a for a in result["ranking"] if a["arm"] == "minecraft")
        self.assertEqual(arm["paid_trials"], 1)

    def test_identical_title_without_a_chain_link_earns_no_reward(self):
        """The removed fallback, pinned shut: a coincidence must not become a reward."""
        rows = [self.row("5167108", "minecraft", title="銃アドオンのバグ修正")]
        rows += [self.row(f"5500{i}", "minecraft") for i in range(7)]
        earnings = [{"requestId": "18011694", "title": "銃アドオンのバグ修正",
                     "jpy": 13260.0, "status": "検収完了"}]
        result = self.select(rows, ["minecraft"], earnings_rows=earnings)
        arm = next(a for a in result["ranking"] if a["arm"] == "minecraft")
        self.assertEqual(arm["paid_trials"], 0)

    def test_an_application_and_its_reply_are_one_trial_not_two(self):
        """Row-per-trial double-counted: the same 募集 scored applied AND engaged."""
        rows = [self.row("5167108", "minecraft"),
                self.row("5167108", "minecraft", status="replied")]
        rows += [self.row(f"5500{i}", "minecraft") for i in range(7)]
        result = self.select(rows, ["minecraft"])
        arm = next(a for a in result["ranking"] if a["arm"] == "minecraft")
        self.assertEqual(arm["trials"], 8)

    def test_placeholder_identity_rows_do_not_become_arms(self):
        """thread_closeout/nurture_sweep leaked into the category field on requestId N/A."""
        rows = [self.row("N/A", "thread_closeout", status="replied"),
                self.row("N/A", "nurture_sweep"),
                *[self.row(f"5600{i}", "real-category") for i in range(8)]]
        result = self.select(rows, ["real-category"])
        arms = {a["arm"] for a in result["ranking"]}
        self.assertNotIn("thread_closeout", arms)
        self.assertNotIn("nurture_sweep", arms)
        self.assertIn("real-category", arms)

    def test_in_flight_applications_do_not_count_against_their_arm(self):
        """A category tried yesterday must not look bad for not having paid yet."""
        rows = [self.row(f"5700{i}", "fresh-arm", age_days=0.5) for i in range(5)]
        rows += [self.row(f"5800{i}", "old-arm", status="replied", age_days=30.0)
                 for i in range(8)]
        result = self.select(rows, ["fresh-arm", "old-arm"])
        fresh = next(a for a in result["ranking"] if a["arm"] == "fresh-arm")
        self.assertEqual(fresh["trials"], 0)
        self.assertEqual(fresh["in_flight"], 5)


class ExplorationTest(BanditFixture):
    def test_cold_start_arms_stay_in_the_ranking(self):
        """If exploration dies, a new category is never tried again."""
        rows = [self.row(f"5900{i}", "known", status="replied") for i in range(20)]
        result = self.select(rows, ["known", "never-tried"])
        arms = {a["arm"]: a for a in result["ranking"]}
        self.assertIn("never-tried", arms)
        self.assertEqual(arms["never-tried"]["trials"], 0)

    def test_cold_start_arm_wins_under_some_seed(self):
        """Zero-observation arms must be reachable, not merely listed."""
        rows = [self.row(f"6000{i}", "known", status="applied") for i in range(20)]
        tops = set()
        for seed in range(60):
            result = self.select(rows, ["known", "never-tried"], seed=seed)
            tops.add(result["ranking"][0]["arm"])
        self.assertIn("never-tried", tops)

    def test_all_zero_rewards_is_flagged_not_silently_optimised(self):
        """Real state 2026-07-27: 23 resolved trials, every one of them reward 0.

        That is real negative evidence and must still steer, but a consumer must be
        able to see that no arm has ever produced a positive outcome -- otherwise the
        ranking reads like a confident recommendation built on nothing.
        """
        rows = [self.row(f"6300{i}", "tried") for i in range(10)]
        result = self.select(rows, ["tried", "untried"])
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["no_positive_reward_observed"])

        good = rows + [self.row("64000", "tried", status="replied")]
        self.assertFalse(self.select(good, ["tried"])["no_positive_reward_observed"])

    def test_skip_categories_are_never_selected(self):
        """Capability/ethics exclusions are not a performance question."""
        rows = [self.row(f"6100{i}", "イラスト", status="replied") for i in range(10)]
        result = self.select(rows, ["safe-arm"], skip=["イラスト (art skill required)"])
        arms = {a["arm"] for a in result["ranking"]}
        self.assertNotIn("イラスト", arms)
        self.assertIn("safe-arm", arms)


class FailSafeTest(BanditFixture):
    def test_no_observations_falls_back_to_priority_categories(self):
        """Today's real state: zero reward-bearing observations."""
        result = self.select([], ["A", "B", "C"])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual([a["arm"] for a in result["ranking"]], ["A", "B", "C"])

    def test_missing_ledger_falls_back_without_raising(self):
        result = bandit.select(
            applied_path=self.root / "nope.jsonl",
            earnings_path=self.root / "nope-earnings.jsonl",
            strategy_path=self.strategy(["A", "B"]),
            now=self.now,
            seed=1,
        )
        self.assertEqual(result["status"], "ledger_unavailable")
        self.assertEqual([a["arm"] for a in result["ranking"]], ["A", "B"])

    def test_corrupt_ledger_lines_are_skipped_not_fatal(self):
        path = self.root / "applied.jsonl"
        good = [self.row(f"6200{i}", "survivor", status="replied") for i in range(9)]
        path.write_text(
            "{not json\n"
            + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in good)
            + "[1,2,3]\n",
            encoding="utf-8")
        result = bandit.select(
            applied_path=path,
            earnings_path=self.write("earnings.jsonl", []),
            strategy_path=self.strategy(["survivor"]),
            now=self.now,
            seed=1,
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["ranking"])
        arm = next(a for a in result["ranking"] if a["arm"] == "survivor")
        self.assertEqual(arm["trials"], 9)

    def test_ranking_is_never_empty_even_with_nothing_readable(self):
        """The bandit failing must never mean the loop applies to nothing."""
        result = bandit.select(
            applied_path=self.root / "gone.jsonl",
            earnings_path=self.root / "gone2.jsonl",
            strategy_path=self.root / "gone3.json",
            now=self.now,
            seed=1,
        )
        self.assertIsInstance(result["ranking"], list)
        self.assertNotEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
