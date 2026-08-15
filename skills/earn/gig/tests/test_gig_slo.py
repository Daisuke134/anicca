import json
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gig_slo.py"


def load():
    spec = importlib.util.spec_from_file_location("gig_slo_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load gig_slo")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GigSloTest(unittest.TestCase):
    def setUp(self):
        self.slo = load()
        self.now = 2_000_000
        self.healthy = {
            "last_pass_at": self.now - 1800,
            "lanes": {
                lane: {
                    "last_attempt_at": self.now - 1800,
                    "last_productive_at": self.now - 7200,
                    "barren_streak": 0,
                }
                for lane in ("apply", "reply", "fulfill", "list")
            },
            "telegram": {
                "latest_pass_created_at": self.now - 1700,
                "latest_pass_state": "sent",
                "delivery_unknown": 0,
                "delivery_unknown_active": 0,
            },
            "recent_failures": [],
            "disk": {
                "hard_stop": False,
                "free_gb": 8,
                "minimum_free_gb": 5,
            },
        }

    def fingerprints(self, snapshot):
        return {row["fingerprint"] for row in self.slo.evaluate(snapshot, now=self.now)}

    def test_healthy_snapshot_has_no_incident(self):
        self.assertEqual(self.slo.evaluate(self.healthy, now=self.now), [])

    def test_scheduler_silence_is_separate_from_lane_silence(self):
        snapshot = dict(self.healthy, last_pass_at=self.now - 8000)
        self.assertEqual(self.fingerprints(snapshot), {"scheduler:missed_hourly_pass"})

    def test_one_dead_lane_is_not_masked_by_the_other_three(self):
        snapshot = dict(self.healthy)
        snapshot["lanes"] = {name: dict(value) for name, value in self.healthy["lanes"].items()}
        snapshot["lanes"]["apply"]["last_attempt_at"] = self.now - 8000
        self.assertEqual(self.fingerprints(snapshot), {"lane:apply:attempt_silence"})

    def test_productivity_silence_requires_measured_barren_streak(self):
        snapshot = dict(self.healthy)
        snapshot["lanes"] = {name: dict(value) for name, value in self.healthy["lanes"].items()}
        snapshot["lanes"]["apply"]["barren_streak"] = 3
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(
            self.fingerprints(snapshot),
            {"application:barren_streak"},
        )
        self.assertEqual(incidents[0]["repair_class"], "application_expand")

    def test_no_demand_is_not_ledger_silence_for_reply_fulfill_or_list(self):
        snapshot = dict(self.healthy)
        snapshot["lanes"] = {
            name: dict(value) for name, value in self.healthy["lanes"].items()
        }
        for lane in ("reply", "fulfill", "list"):
            snapshot["lanes"][lane]["barren_streak"] = 99
        self.assertEqual(self.fingerprints(snapshot), set())

    def test_telegram_delivery_unknown_is_not_called_a_send_failure(self):
        snapshot = dict(self.healthy, telegram={
            "latest_pass_created_at": self.now - 1700,
            "latest_pass_state": "delivery_unknown",
            "delivery_unknown": 1,
            "delivery_unknown_active": 1,
        })
        self.assertEqual(self.fingerprints(snapshot), {"telegram:delivery_unknown"})

    def test_historical_unknown_stays_visible_but_is_not_an_active_incident(self):
        snapshot = dict(self.healthy, telegram={
            "latest_pass_created_at": self.now - 1700,
            "latest_pass_state": "sent",
            "delivery_unknown": 5,
            "delivery_unknown_active": 0,
        })
        self.assertEqual(self.fingerprints(snapshot), set())

    def test_fresh_scheduler_does_not_mask_a_missing_pass_report(self):
        snapshot = dict(self.healthy)
        snapshot["telegram"] = {
            "latest_pass_created_at": self.now - 8000,
            "latest_pass_state": "sent",
            "delivery_unknown": 0,
            "delivery_unknown_active": 0,
        }
        self.assertEqual(
            self.fingerprints(snapshot),
            {"telegram:pass_report_silence"},
        )

    def test_stuck_pending_pass_report_is_a_backlog_incident(self):
        snapshot = dict(self.healthy)
        snapshot["telegram"] = {
            "latest_pass_created_at": self.now - 1200,
            "latest_pass_state": "pending",
            "delivery_unknown": 0,
            "delivery_unknown_active": 0,
        }
        self.assertEqual(
            self.fingerprints(snapshot),
            {"telegram:pass_report_backlog"},
        )

    def test_browser_failure_gets_its_own_repair_class(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "browser_cdp_unavailable",
            "failed_step": "QUEUE",
        }])
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(self.fingerprints(snapshot), {"browser:cdp_unavailable"})
        self.assertEqual(incidents[0]["repair_class"], "browser_restart")

    def test_recent_schema_failure_is_classified_from_the_pass_ledger(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "reply_queue_schema_failed",
            "failed_step": "REPLY_QUEUE",
        }])
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(
            self.fingerprints(snapshot),
            {"schema:invalid_result:REPLY_QUEUE"},
        )
        self.assertEqual(incidents[0]["repair_class"], "schema_diagnose")

    def test_generic_agent_failure_is_not_assumed_to_be_provider_outage(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "agent_step_failed",
            "failed_step": "B0",
        }])
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(
            self.fingerprints(snapshot),
            {"task:unclassified:B0"},
        )
        self.assertEqual(incidents[0]["repair_class"], "task_diagnose")

    def test_paid_work_infra_failure_routes_to_existing_sandbox_healer(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "paid_work_infra_unavailable",
            "failed_step": "PAID_WORK",
        }])
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(
            self.fingerprints(snapshot),
            {"sandbox:infra_unavailable"},
        )
        self.assertEqual(incidents[0]["repair_class"], "sandbox_recover")

    def test_application_ledger_write_failure_gets_reconcile_class(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "b2_application_ledger_write_failed",
            "failed_step": "B2",
            "pass_id": "pass-2",
            "evidence_dir": "/tmp/evidence/gig-pass-pass-2",
            "ledger_missing_request_ids": ["91000074"],
        }])
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(
            self.fingerprints(snapshot),
            {"ledger:application_write_failed:B2"},
        )
        self.assertEqual(incidents[0]["repair_class"], "ledger_reconcile")
        self.assertEqual(incidents[0]["evidence"]["pass_id"], "pass-2")

    def test_reconciled_application_ledger_failure_no_longer_fires(self):
        snapshot = dict(self.healthy, recent_failures=[{
            "ts": self.now - 60,
            "reason": "b2_application_ledger_write_failed",
            "failed_step": "B2",
            "pass_id": "pass-2",
            "evidence_dir": "/tmp/evidence/gig-pass-pass-2",
            "ledger_missing_request_ids": [],
        }])
        self.assertEqual(self.fingerprints(snapshot), set())

    def test_disk_hard_stop_is_an_independent_repair_class(self):
        snapshot = dict(self.healthy, disk={
            "hard_stop": True,
            "free_gb": 8,
            "minimum_free_gb": 5,
        })
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertEqual(self.fingerprints(snapshot), {"disk:hard_stop"})
        self.assertEqual(incidents[0]["repair_class"], "disk_recover")

    def test_advisory_pressure_above_hard_minimum_is_not_an_incident(self):
        snapshot = dict(self.healthy, disk={
            "hard_stop": False,
            "pressure_advisory": True,
            "free_gb": 8,
            "minimum_free_gb": 5,
        })
        self.assertEqual(self.fingerprints(snapshot), set())

    def test_disk_below_hard_minimum_is_an_incident_without_a_flag(self):
        snapshot = dict(self.healthy, disk={
            "hard_stop": False,
            "free_gb": 4,
            "minimum_free_gb": 5,
        })
        self.assertEqual(
            self.fingerprints(snapshot),
            {"disk:space_below_minimum"},
        )

    def test_terminal_hermes_red_projects_stable_lane_cause_incidents(self):
        snapshot = dict(self.healthy, hermes_audit={
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "terminal",
            "verdict": "RED",
            "result": {
              "invariants": {
                "no_missing_due": False,
                "no_bad_receipts": False,
                "no_blocked_tasks": False,
                "no_stale_active": False,
                "no_duplicate_applications": False,
                "all_applications_reported": False,
                "no_excess_storefront_effects": False,
                "all_lanes_nonstarved": False,
              },
              "version": 1,
              "since": 1786365299,
              "until": 1786451699,
              "window_complete": True,
              "verdict": "RED",
              "lanes": {
                "paid": {"missing_slots": 2, "nonzero_or_invalid_receipts": 1, "blocked": 0, "stale_active": 0, "executed": 0, "expected_due": 2},
                "reply": {"missing_slots": 0, "nonzero_or_invalid_receipts": 0, "blocked": 1, "stale_active": 0, "executed": 1, "expected_due": 2},
                "apply": {"missing_slots": 0, "nonzero_or_invalid_receipts": 0, "blocked": 0, "stale_active": 1, "executed": 1, "expected_due": 2},
                "storefront": {"missing_slots": 0, "nonzero_or_invalid_receipts": 0, "blocked": 0, "stale_active": 0, "executed": 2, "expected_due": 2},
              },
              "applications": {"duplicate_request_ids": ["9001", "9002"]},
              "telegram": {"unreported_application_ids": ["9003"]},
              "storefront": {"effect_count": 3},
            },
        })

        incidents = self.slo.evaluate(snapshot, now=self.now)

        self.assertEqual(
            {incident["fingerprint"] for incident in incidents},
            {
                "hermes24:1786365299-1786451699:paid:missing_slots",
                "hermes24:1786365299-1786451699:paid:invalid_receipts",
                "hermes24:1786365299-1786451699:paid:nonstarved",
                "hermes24:1786365299-1786451699:reply:blocked_tasks",
                "hermes24:1786365299-1786451699:apply:stale_active",
                "hermes24:1786365299-1786451699:apply:duplicate_applications",
                "hermes24:1786365299-1786451699:apply:unreported_applications",
                "hermes24:1786365299-1786451699:storefront:excess_storefront_effects",
            },
        )
        self.assertTrue(all(incident["repair_class"] == "task_diagnose" for incident in incidents))
        self.assertEqual(
            next(
                incident["evidence"]
                for incident in incidents
                if incident["fingerprint"].endswith(":paid:missing_slots")
            ),
            {
                "audit_id": "1786365299-1786451699",
                "since": 1786365299,
                "until": 1786451699,
                "lane": "paid",
                "cause": "missing_slots",
                "count": 2,
            },
        )
        self.assertEqual(
            next(
                incident["evidence"]
                for incident in incidents
                if incident["fingerprint"].endswith(":storefront:excess_storefront_effects")
            )["count"],
            1,
        )

    def test_hermes_active_pending_and_green_do_not_project_incidents(self):
        for phase, verdict in (("active", "PENDING"), ("terminal", "GREEN")):
            snapshot = dict(self.healthy, hermes_audit={
                "audit_id": "1786365299-1786451699",
                "since": 1786365299,
                "until": 1786451699,
                "phase": phase,
                "verdict": verdict,
            })
            self.assertEqual(self.slo.evaluate(snapshot, now=self.now), [])

    def test_collect_snapshot_reads_nested_hermes_audit_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            state = {
            "version": 1,
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "active",
            "verdict": "PENDING",
            "raw_verdict": "RED",
            "last_checked_at": 1786365300,
            "terminal_at": None,
            "result": {"verdict": "RED", "lanes": {"paid": {"missing_slots": 1}}},
        }
            (tmp_path / "hermes-canary-24h-audit.json").write_text(
                json.dumps(state), encoding="utf-8"
            )
            snapshot = self.slo.collect_snapshot(
                state_dir=tmp_path,
                telegram_database=tmp_path / "telegram.sqlite3",
                now=self.now,
                host_state_dir=tmp_path / "host-state",
            )
            self.assertEqual(snapshot["hermes_audit"]["result"]["verdict"], "RED")

    def test_terminal_hermes_red_with_invalid_nested_result_has_no_incident(self):
        snapshot = dict(self.healthy, hermes_audit={
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "terminal",
            "verdict": "RED",
            "result": {"version": 1, "window_complete": False, "verdict": "RED"},
        })
        self.assertEqual(self.slo.evaluate(snapshot, now=self.now), [])

    def test_terminal_hermes_red_with_forged_audit_identity_has_no_incident(self):
        snapshot = dict(self.healthy, hermes_audit={
            "audit_id": "forged-baseline",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "terminal",
            "verdict": "RED",
            "result": {
                "version": 1,
                "since": 1786365299,
                "until": 1786451699,
                "window_complete": True,
                "verdict": "RED",
                "invariants": {"no_missing_due": False},
                "lanes": {"paid": {"missing_slots": 1, "expected_due": 1}},
            },
        })
        self.assertEqual(self.slo.evaluate(snapshot, now=self.now), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
