"""Runtime-wiring contract for TODO #4.

`LaneStateMachine` proved its at-most-once semantics in
`test_four_lane_state_machine.py`, but until a production entrypoint drives it
the four-lane envelope has no runtime caller.  This contract fixes that gap:

1. `scripts/lane_action_runtime.py` is the single thin seam every lane uses to
   drive `LaneStateMachine` (observe -> run_once); it is not a generalized
   framework, just the shared caller.
2. The production pass (`gig_pass.sh`) closes all four lanes
   (listing/application/reply/delivery) in the unified ledger through that seam.
3. Driving the seam through the four injected failure fixtures
   (process crash / model refusal / send timeout / ACK loss) still recovers each
   lane to a verified side effect with no blind retry and no manual terminal
   state -- the same guarantees, now exercised through the production caller.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


GIG_WORK = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_WORK / "scripts"
RUNTIME_PATH = SCRIPTS / "lane_action_runtime.py"
GIG_PASS = GIG_WORK / "gig_pass.sh"

LANES = ("listing", "application", "reply", "delivery")

# Import both modules by name off the scripts dir so the runtime and this test
# share a single lane_state_machine instance -- otherwise the injected
# ModelRefusal/UnknownOutcome classes would not match the ones run_once catches.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import lane_state_machine  # noqa: E402
import lane_action_runtime  # noqa: E402


class LaneRuntimeSeamTest(unittest.TestCase):
    def setUp(self):
        self.runtime = lane_action_runtime
        self.state_machine = lane_state_machine
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_dir = Path(self.temp.name)
        self.machine = self.runtime.open_state_machine(self.state_dir)

    def test_open_state_machine_uses_shared_lane_actions_database(self):
        self.assertIsInstance(self.machine, self.state_machine.LaneStateMachine)
        self.assertEqual(
            Path(self.machine.database),
            self.state_dir / "lane-actions.sqlite3",
        )

    def test_run_lane_action_drives_the_four_lane_failure_lifecycles(self):
        cases = (
            ("listing", "publish", "process_crash"),
            ("application", "apply", self.state_machine.ModelRefusal("model_refusal")),
            ("reply", "reply", self.state_machine.UnknownOutcome("send_timeout")),
            ("delivery", "formal_delivery", self.state_machine.UnknownOutcome("ack_loss")),
        )
        effects = []

        for index, (lane, action_kind, injected) in enumerate(cases, 1):
            with self.subTest(lane=lane):
                event_key = f"{lane}:pass-1"
                entity_key = f"{lane}:entity-1"

                def do_success(now):
                    return self.runtime.run_lane_action(
                        self.machine,
                        lane=lane,
                        event_key=event_key,
                        entity_key=entity_key,
                        action_kind=action_kind,
                        owner=f"worker-{lane}",
                        now=now,
                        compose=lambda _a: f"intent-{lane}",
                        execute=lambda _a, _i: effects.append(lane),
                        verify=lambda _a: {"evidence_hash": f"evidence-{lane}"},
                    )

                observed = self.machine.observe(
                    lane=lane,
                    event_key=event_key,
                    entity_key=entity_key,
                    action_kind=action_kind,
                    observed_at=100 + index,
                )

                if injected == "process_crash":
                    dead = self.machine.claim(
                        observed["action_id"],
                        owner=f"dead-{lane}",
                        now=200 + index,
                        lease_seconds=10,
                    )
                    self.assertEqual(dead["state"], "claimed")
                    self.assertEqual(dead["side_effect_count"], 0)
                    final = do_success(400 + index)
                    self.assertGreater(final["fencing_token"], dead["fencing_token"])
                elif isinstance(injected, self.state_machine.ModelRefusal):
                    failed = self.runtime.run_lane_action(
                        self.machine,
                        lane=lane,
                        event_key=event_key,
                        entity_key=entity_key,
                        action_kind=action_kind,
                        owner=f"fault-{lane}",
                        now=200 + index,
                        compose=lambda _a: (_ for _ in ()).throw(injected),
                        execute=lambda _a, _i: self.fail("refusal must not send"),
                        verify=lambda _a: None,
                    )
                    self.assertEqual(failed["state"], "retry_wait")
                    self.machine.release_retry(observed["action_id"], now=300 + index)
                    final = do_success(400 + index)
                else:
                    failed = self.runtime.run_lane_action(
                        self.machine,
                        lane=lane,
                        event_key=event_key,
                        entity_key=entity_key,
                        action_kind=action_kind,
                        owner=f"fault-{lane}",
                        now=200 + index,
                        compose=lambda _a: f"intent-{lane}",
                        execute=lambda _a, _i: (
                            effects.append(lane),
                            (_ for _ in ()).throw(injected),
                        ),
                        verify=lambda _a: None,
                    )
                    self.assertEqual(failed["state"], "reconcile_pending")
                    final = self.runtime.run_lane_action(
                        self.machine,
                        lane=lane,
                        event_key=event_key,
                        entity_key=entity_key,
                        action_kind=action_kind,
                        owner=f"reconcile-{lane}",
                        now=400 + index,
                        compose=lambda _a: self.fail("reconcile must not compose"),
                        execute=lambda _a, _i: self.fail("reconcile must not resend"),
                        verify=lambda _a: {"evidence_hash": f"evidence-{lane}"},
                    )

                self.assertEqual(final["state"], "verified")
                self.assertEqual(final["side_effect_count"], 1)
                self.assertEqual(final["blind_retry_count"], 0)
                self.assertNotEqual(final["state"], "manual")

        self.assertEqual(len(effects), 4)
        self.assertNotIn(
            "manual",
            {row["state"] for row in self.machine.list_actions()},
        )

    def test_cli_records_a_verified_noop_lane_closure(self):
        for lane in LANES:
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNTIME_PATH),
                    "record",
                    "--state-dir",
                    str(self.state_dir),
                    "--lane",
                    lane,
                    "--action-kind",
                    "verified_noop",
                    "--event-key",
                    f"{lane}:cli-pass",
                    "--entity-key",
                    f"{lane}:cli-entity",
                    "--owner",
                    "gig-pass-cli",
                    "--now",
                    "1000",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            row = json.loads(result.stdout)
            self.assertEqual(row["lane"], lane)
            self.assertEqual(row["state"], "verified_noop")
            self.assertEqual(row["side_effect_count"], 0)

        recorded = {row["lane"] for row in self.machine.list_actions()}
        self.assertEqual(recorded, set(LANES))


class GigPassProductionCallerTest(unittest.TestCase):
    """Source-level proof that the production pass drives the runtime seam."""

    def setUp(self):
        self.source = GIG_PASS.read_text(encoding="utf-8")

    def test_gig_pass_invokes_the_lane_runtime_seam(self):
        self.assertIn("scripts/lane_action_runtime.py", self.source)

    def test_gig_pass_closes_every_lane_in_the_unified_ledger(self):
        for lane in LANES:
            self.assertIn(
                lane,
                self.source,
                f"gig_pass.sh must close the {lane} lane through LaneStateMachine",
            )

    def test_poll_controlled_pass_records_lane_closures_before_exiting(self):
        # The normal production pass (GIG_LEGACY_MAINTENANCE_ENABLED != 1)
        # finalizes and exits inside the poll-controlled block, never reaching
        # the bottom of the script.  The lane closures must be recorded on that
        # path too, or LaneStateMachine has no caller on any natural pass.
        marker = 'poll_outcome="no_change"'
        self.assertIn(marker, self.source)
        block_start = self.source.index(marker)
        block_end = self.source.index("exit 0", block_start)
        poll_controlled_block = self.source[block_start:block_end]
        self.assertIn(
            "record_lane_closures",
            poll_controlled_block,
            "the poll-controlled success path must record the four lane closures "
            "before it exits",
        )

    def test_successful_queue_inspection_closes_delivery_even_when_empty(self):
        self.assertIn("DELIVERY_LANE_INSPECTED=1", self.source)
        closure = self.source[
            self.source.index("record_lane_closures()"):
            self.source.index("record_lane_productivity()")
        ]
        self.assertIn("DELIVERY_LANE_INSPECTED", closure)


if __name__ == "__main__":
    unittest.main(verbosity=2)
