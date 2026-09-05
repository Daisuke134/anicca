# Alpaca L01 Portable Finite Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and implement this single task only.

**Goal:** Make the existing finite Alpaca paper pass portable by removing the hackathon dashboard publisher from both successful and terminal-failure execution paths.

**Architecture:** Keep the existing `run.py` entrypoint, environment-injected credential path, CLI path, mutable state path, shared agent runner, effect fence, reconciliation, and Telegram reporter. Delete only the dashboard child-process dependency; do not introduce an interface, replacement publisher, deployment profile, or live behavior.

**Tech Stack:** Python 3 standard library and existing `unittest` suite.

## Global Constraints

- One active atom: L01 only.
- No new dependency, framework, scheduler, queue, ledger, adapter, or directory.
- Do not change Alpaca paper credentials, order behavior, risk policy, Telegram behavior, launchd state, or dashboard application files.
- Target: two changed production/test files and net deletion in production.

---

### Task 1: Remove dashboard effects from the portable pass

**Files:**
- Modify: `skills/alpaca-investment/test_run.py`
- Modify: `skills/alpaca-investment/run.py`

**Interfaces:**
- Consumes: existing `main(*, attempt=0, wake_id=None) -> int` and environment-injected state/credential/CLI boundaries.
- Produces: the same finite pass result and Telegram behavior with no dashboard child process or `public_snapshot_published` summary field.

- [ ] **Step 1: Write the failing behavior test**

Replace publisher-unit tests and publisher mocks with these focused success/failure pass tests (keeping the existing retry/effect tests):

```python
def _publisher_probe(root: Path) -> tuple[Path, Path]:
    marker = root / "publisher-called"
    executable = root / "node"
    executable.write_text('#!/bin/sh\n: > "$ALPACA_MARKER"\n', encoding="utf-8")
    executable.chmod(0o700)
    return executable, marker


class PortablePassTest(unittest.TestCase):
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe")
    @patch.object(MODULE, "read_campaign_snapshot", return_value={})
    @patch.object(MODULE, "reconcile")
    @patch.object(MODULE, "read_allocator_snapshot", return_value={})
    @patch.object(MODULE, "build_candidates", return_value=[])
    @patch.object(MODULE, "choose")
    @patch.object(MODULE, "record_no_trade")
    @patch.object(MODULE, "deliver", return_value={"message_id": "123"})
    def test_success_has_no_dashboard_effect_or_public_summary(
        self, _deliver, _record, choose, _build, _allocator, reconcile,
        _campaign, observe, _reconcile_started,
    ):
        observe.return_value = {
            "account": {"cash": "100000", "equity": "100000"},
            "activities_count": 0, "clock": {"observed_at": "2026-09-05T00:00:00Z"},
            "open_and_closed_orders_count": 0, "positions": [],
        }
        reconcile.return_value = {"exit_status": "CLOSED", "unrealized_pnl_usd": "0"}
        choose.return_value = {
            "approved": False, "candidate_ref": "NO_TRADE", "gate": "model_no_trade",
            "observed_at": "2026-09-05T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, marker = _publisher_probe(root)
            with patch.dict(MODULE.os.environ, {
                "ALPACA_INVESTMENT_STATE_DIR": str(root / "state"),
                "NODE_BIN": str(executable), "ALPACA_MARKER": str(marker),
            }), redirect_stdout(StringIO()) as output:
                self.assertEqual(MODULE.main(wake_id="wake-success"), 0)
            self.assertFalse(marker.exists())
            self.assertNotIn("public_snapshot_published", json.loads(output.getvalue()))

    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider unavailable"))
    @patch.object(MODULE, "deliver_failure", return_value={"message_id": "123", "status": "delivered"})
    def test_terminal_failure_has_no_dashboard_effect(self, _deliver, _observe, _reconcile):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, marker = _publisher_probe(root)
            with patch.dict(MODULE.os.environ, {
                "ALPACA_INVESTMENT_STATE_DIR": str(root / "state"),
                "NODE_BIN": str(executable), "ALPACA_MARKER": str(marker),
            }), redirect_stdout(StringIO()):
                self.assertEqual(MODULE.main(wake_id="wake-failure"), 78)
            self.assertFalse(marker.exists())
```

Add `json`, `tempfile`, `redirect_stdout`, and `StringIO` imports required by these tests. The tests fail if either portable-pass path starts the fake dashboard publisher; the assertions observe the marker rather than asserting on a mock.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest skills.alpaca-investment.test_run
```

Expected: the new tests fail because current `run.py` invokes `_publish_public_snapshot()` on success and after a delivered terminal failure.

- [ ] **Step 3: Implement the minimum deletion**

In `skills/alpaca-investment/run.py`:

- delete `shutil` and `subprocess` imports;
- delete `_publish_public_snapshot()`;
- delete the success-path publisher call and `public_snapshot_published` summary field;
- delete the terminal-failure publisher call;
- preserve observation, allocation, effect fencing, reconciliation, state writes, Telegram delivery, retry rules, output status, and return codes unchanged.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest skills.alpaca-investment.test_run skills.alpaca-investment.test_reporter
git diff --check
```

Expected: all focused tests pass and the diff check reports no errors.

- [ ] **Step 5: Primary verification and state update**

The primary agent runs the applicable existing Alpaca and loop-runtime tests, confirms the pass remains paper-only and production is not mutated, obtains a fresh adversarial review, then marks L01 DONE and L02 active in the Alpaca live-product spec. Commit, push, merge, and production deployment are separate primary-owned gates.
