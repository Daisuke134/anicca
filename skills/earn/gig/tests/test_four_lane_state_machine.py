import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "lane_state_machine.py"


def load_module():
    spec = importlib.util.spec_from_file_location("lane_state_machine", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load lane_state_machine")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FourLaneStateMachineTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.machine = self.module.LaneStateMachine(
            Path(self.temp.name) / "lane-actions.sqlite3"
        )

    def run_success(self, action_id, effects, now):
        return self.machine.run_once(
            action_id=action_id,
            owner=f"worker-{action_id}",
            now=now,
            compose=lambda _action: f"intent-{action_id}",
            execute=lambda _action, _intent: effects.append(action_id)
            or {"receipt": f"receipt-{action_id}"},
            verify=lambda _action: {"evidence_hash": f"evidence-{action_id}"},
        )

    def test_four_lanes_recover_without_duplicate_or_manual_terminal_state(self):
        cases = (
            ("listing", "publish", "process_crash"),
            ("application", "apply", self.module.ModelRefusal("model_refusal")),
            ("reply", "reply", self.module.UnknownOutcome("timeout")),
            ("delivery", "formal_delivery", self.module.UnknownOutcome("ack_loss")),
        )
        effects = []

        for index, (lane, action_kind, injected) in enumerate(cases, 1):
            with self.subTest(lane=lane, failure=type(injected).__name__):
                event_key = f"{lane}:event-1"
                first = self.machine.observe(
                    lane=lane,
                    event_key=event_key,
                    entity_key=f"{lane}:entity-1",
                    action_kind=action_kind,
                    observed_at=100 + index,
                )
                duplicate = self.machine.observe(
                    lane=lane,
                    event_key=event_key,
                    entity_key=f"{lane}:entity-1",
                    action_kind=action_kind,
                    observed_at=200 + index,
                )
                self.assertEqual(duplicate["action_id"], first["action_id"])

                def fail_once(_action, _intent=None):
                    if isinstance(injected, self.module.UnknownOutcome):
                        effects.append(first["action_id"])
                    raise injected

                if injected == "process_crash":
                    failed = self.machine.claim(
                        first["action_id"],
                        owner=f"dead-{lane}",
                        now=300 + index,
                        lease_seconds=10,
                    )
                    self.assertEqual(failed["state"], "claimed")
                    self.assertEqual(failed["side_effect_count"], 0)
                else:
                    failed = self.machine.run_once(
                        action_id=first["action_id"],
                        owner=f"fault-{lane}",
                        now=300 + index,
                        compose=(
                            fail_once
                            if isinstance(injected, self.module.ModelRefusal)
                            else lambda _action: f"intent-{lane}"
                        ),
                        execute=fail_once,
                        verify=lambda _action: None,
                    )

                if injected == "process_crash":
                    final = self.run_success(
                        first["action_id"],
                        effects,
                        400 + index,
                    )
                    self.assertGreater(
                        final["fencing_token"],
                        failed["fencing_token"],
                    )
                elif isinstance(injected, self.module.ModelRefusal):
                    self.assertEqual(failed["state"], "retry_wait")
                    self.machine.release_retry(
                        first["action_id"],
                        now=400 + index,
                    )
                    final = self.run_success(
                        first["action_id"],
                        effects,
                        500 + index,
                    )
                else:
                    self.assertEqual(failed["state"], "reconcile_pending")
                    final = self.machine.run_once(
                        action_id=first["action_id"],
                        owner=f"reconcile-{lane}",
                        now=500 + index,
                        compose=lambda _action: self.fail(
                            "reconcile must not compose"
                        ),
                        execute=lambda _action, _intent: self.fail(
                            "reconcile must not retry the side effect"
                        ),
                        verify=lambda _action: {
                            "evidence_hash": f"evidence-{lane}"
                        },
                    )

                self.assertEqual(final["state"], "verified")
                self.assertEqual(final["side_effect_count"], 1)
                self.assertEqual(final["blind_retry_count"], 0)
                self.assertNotEqual(final["state"], "manual")

                repeated = self.machine.run_once(
                    action_id=first["action_id"],
                    owner=f"repeat-{lane}",
                    now=600 + index,
                    compose=lambda _action: self.fail(
                        "verified action must not compose"
                    ),
                    execute=lambda _action, _intent: self.fail(
                        "verified action must not execute"
                    ),
                    verify=lambda _action: self.fail(
                        "verified action must not reverify"
                    ),
                )
                self.assertEqual(repeated["state"], "verified")
                self.assertEqual(repeated["side_effect_count"], 1)

        self.assertEqual(len(effects), 4)
        self.assertEqual(
            {row["lane"] for row in self.machine.list_actions()},
            {"listing", "application", "reply", "delivery"},
        )
        self.assertNotIn(
            "manual",
            {row["state"] for row in self.machine.list_actions()},
        )

    def test_lane_action_contract_includes_full_daily_loop(self):
        # not_run belongs to every lane: any lane can be passed over by a pass, and
        # saying so is the only way a skipped lane stops masquerading as a verified
        # no-op. It is terminal -- no side effect is coming -- so it must not park a
        # pending row that nothing will ever settle.
        expected = {
            "listing": {"draft", "publish", "update", "verified_noop", "not_run"},
            "application": {"apply", "verified_noop", "not_run"},
            "reply": {"reply", "verified_noop", "not_run"},
            "delivery": {
                "build",
                "progress",
                "formal_delivery",
                "revision",
                "acceptance",
                "payout",
                "verified_noop",
                "not_run",
            },
        }
        self.assertEqual(self.module.LANE_ACTIONS, expected)
        for lane in expected:
            skipped = self.machine.observe(
                lane=lane,
                event_key=f"{lane}:skipped-pass",
                entity_key=f"{lane}:entity",
                action_kind="not_run",
                observed_at=1_785_000_000,
            )
            self.assertEqual(skipped["state"], "not_run", lane)

        for lane, action_kinds in expected.items():
            for action_kind in action_kinds:
                with self.subTest(lane=lane, action_kind=action_kind):
                    action = self.machine.observe(
                        lane=lane,
                        event_key=f"{lane}:{action_kind}",
                        entity_key=f"{lane}:entity",
                        action_kind=action_kind,
                        observed_at=1,
                    )
                    if action_kind in ("verified_noop", "not_run"):
                        # Both are terminal and effect-free; they differ only in whether
                        # the lane was driven at all.
                        self.assertEqual(action["state"], action_kind)
                        self.assertEqual(action["side_effect_count"], 0)
                    else:
                        self.assertEqual(action["state"], "pending")

        with self.assertRaisesRegex(ValueError, "invalid lane action"):
            self.machine.observe(
                lane="listing",
                event_key="listing:invalid",
                entity_key="listing:entity",
                action_kind="reply",
                observed_at=1,
            )

    def test_process_crash_after_side_effect_fence_reconciles_without_reexecution(self):
        action = self.machine.observe(
            lane="delivery",
            event_key="delivery:crash-after-fence",
            entity_key="order:42",
            action_kind="formal_delivery",
            observed_at=10,
        )
        claimed = self.machine.claim(
            action["action_id"],
            owner="dead-after-fence",
            now=11,
            lease_seconds=10,
        )
        fenced = self.machine.fence_side_effect(
            claimed,
            intent="formal-delivery-v1",
            now=12,
        )
        self.assertEqual(fenced["state"], "reconcile_pending")
        self.assertEqual(fenced["side_effect_count"], 0)
        self.assertEqual(fenced["effect_attempt_count"], 1)

        final = self.machine.run_once(
            action_id=action["action_id"],
            owner="reconciler",
            now=100,
            compose=lambda _action: self.fail("must not compose after fence"),
            execute=lambda _action, _intent: self.fail(
                "must not repeat side effect after fence"
            ),
            verify=lambda _action: {"evidence_hash": "formal-delivery-proof"},
        )

        self.assertEqual(final["state"], "verified")
        self.assertEqual(final["side_effect_count"], 1)
        self.assertEqual(final["effect_attempt_count"], 1)
        self.assertEqual(final["blind_retry_count"], 0)

    def test_authoritative_absence_after_fence_creates_new_revision_not_blind_retry(self):
        action = self.machine.observe(
            lane="listing",
            event_key="listing:crash-before-browser-effect",
            entity_key="service:42",
            action_kind="publish",
            observed_at=10,
        )
        claimed = self.machine.claim(
            action["action_id"],
            owner="dead-before-browser-effect",
            now=11,
            lease_seconds=10,
        )
        fenced = self.machine.fence_side_effect(
            claimed,
            intent="publish-service-42-v1",
            now=12,
        )
        self.assertEqual(fenced["state"], "reconcile_pending")

        absent = self.machine.run_once(
            action_id=action["action_id"],
            owner="absence-verifier",
            now=100,
            compose=lambda _action: self.fail("must reconcile first"),
            execute=lambda _action, _intent: self.fail("must reconcile first"),
            verify=lambda _action: {
                "authoritative_absent": True,
                "evidence_hash": "public-service-42-absent",
            },
        )
        self.assertEqual(absent["state"], "pending")
        self.assertEqual(absent["revision"], 2)
        self.assertEqual(absent["side_effect_count"], 0)
        self.assertEqual(absent["effect_attempt_count"], 1)
        self.assertEqual(absent["blind_retry_count"], 0)

        effects = []
        final = self.run_success(action["action_id"], effects, 101)
        self.assertEqual(final["state"], "verified")
        self.assertEqual(final["revision"], 2)
        self.assertEqual(final["side_effect_count"], 1)
        self.assertEqual(final["effect_attempt_count"], 2)
        self.assertEqual(final["blind_retry_count"], 0)
        self.assertEqual(effects, [action["action_id"]])

    def test_live_lease_cannot_be_entered_by_another_owner(self):
        action = self.machine.observe(
            lane="reply",
            event_key="reply:live-owner",
            entity_key="thread:42",
            action_kind="reply",
            observed_at=10,
        )
        claimed = self.machine.claim(
            action["action_id"],
            owner="live-owner",
            now=11,
            lease_seconds=100,
        )

        unchanged = self.machine.run_once(
            action_id=action["action_id"],
            owner="competing-owner",
            now=12,
            compose=lambda _action: self.fail(
                "another owner must not enter a live lease"
            ),
            execute=lambda _action, _intent: self.fail(
                "another owner must not execute a live lease"
            ),
            verify=lambda _action: self.fail(
                "another owner must not verify a live lease"
            ),
        )

        self.assertEqual(unchanged["state"], "claimed")
        self.assertEqual(unchanged["owner"], claimed["owner"])
        self.assertEqual(unchanged["fencing_token"], claimed["fencing_token"])
        self.assertEqual(unchanged["effect_attempt_count"], 0)

    def test_expired_owner_cannot_fence_side_effect(self):
        action = self.machine.observe(
            lane="application",
            event_key="application:expired-owner",
            entity_key="request:42",
            action_kind="apply",
            observed_at=10,
        )
        claimed = self.machine.claim(
            action["action_id"],
            owner="expired-owner",
            now=11,
            lease_seconds=10,
        )

        with self.assertRaisesRegex(RuntimeError, "side-effect fence rejected"):
            self.machine.fence_side_effect(
                claimed,
                intent="apply-request-42",
                now=22,
            )

        unchanged = self.machine.get_action(action["action_id"])
        self.assertEqual(unchanged["state"], "claimed")
        self.assertIsNone(unchanged["effect_started_at"])
        self.assertEqual(unchanged["effect_attempt_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
