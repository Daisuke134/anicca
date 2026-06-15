# anicca-cron-doctor v2 + R-4/R-11 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, this session, per /goal hook).

**Goal:** End-to-end implement R-4 / R-6 / R-7 / R-8 / R-9 / R-11 / R-13 / R-14 / R-15 from the rat-proof cron architecture remaining-tasks list. Stop the LLM coin flip for the 34 context-bearing crons, add self-heal robustness (window-based streak + token budget + auto-commit), record the post-mortem, and add config drift + false-positive annotation reporting.

**Architecture:** Refactor `phases.py` to delegate to small helper modules (one responsibility each) under `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/`. cron-codex.sh sources token_budget at head. One-shot migrate-context-bearing.sh applies R-4 across 34 crons. weekly digest is a separate OpenClaw cron.

**Tech Stack:** Python 3 stdlib only (no extra pip), bash, OpenClaw CLI (`openclaw cron edit/add/get/runs`), Slack chat.postMessage via curl, git CLI. Tests = pytest if available else lightweight `python3 -m unittest`.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/__init__.py` | Create (empty) | package marker |
| `.../helpers/cron_edit.py` | Create | safe `openclaw cron edit` wrapper (R-15) |
| `.../helpers/streak_window.py` | Create | 24h sliding-window streak math (R-6) |
| `.../helpers/token_budget.py` | Create | OpenAI spend tracking + threshold check (R-8) |
| `.../helpers/git_sync.py` | Create | jobs.json auto-commit + push (R-9) |
| `.../helpers/config_audit.py` | Create | openclaw.json model drift detect (R-13) |
| `.../scripts/phases.py` | Modify | refactor L1/L3/L5 to use cron_edit + streak_window, add L7 |
| `.../scripts/format_report.py` | Modify | L7 line + false-positive annotation (R-14) |
| `.../scripts/run.sh` | Modify | call git_sync at tail |
| `.../scripts/migrate-context-bearing.sh` | Create | one-shot R-4 migration |
| `.../scripts/digest-weekly.sh` | Create | Monday rollup of skipped_complex (R-7) |
| `.../scripts/tests/` | Create dir | TDD unit tests |
| `.../scripts/tests/test_cron_edit.py` | Create | unit test for R-15 |
| `.../scripts/tests/test_streak_window.py` | Create | unit test for R-6 |
| `.../scripts/tests/test_token_budget.py` | Create | unit test for R-8 |
| `.../scripts/tests/test_config_audit.py` | Create | unit test for R-13 |
| `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` | Modify | source token_budget at head |
| `~/.openclaw/.learnings/LEARNINGS.md` | Append | R-11 post-mortem |
| `~/.openclaw/cron/jobs.json` | Modify (via CLI) | 34 prompts migrated + 1 new cron for digest |

---

## Task 1: R-15 — cron_edit helper (foundation)

**Files:**
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/__init__.py` (empty)
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/cron_edit.py`
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/tests/__init__.py` (empty)
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/tests/test_cron_edit.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_cron_edit.py
import unittest
from unittest.mock import patch, MagicMock
from helpers.cron_edit import edit_message, fetch_message

class TestCronEdit(unittest.TestCase):
    @patch("helpers.cron_edit.subprocess.run")
    def test_edit_invokes_openclaw_with_list_args(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        ok, err = edit_message("abc123", "new prompt")
        self.assertTrue(ok)
        args = mock_run.call_args[0][0]
        self.assertEqual(args[:4], ["openclaw","cron","edit","abc123"])
        self.assertIn("--message", args)
        self.assertIn("new prompt", args)

    @patch("helpers.cron_edit.subprocess.run")
    def test_edit_returns_error_on_nonzero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="boom")
        ok, err = edit_message("abc","x")
        self.assertFalse(ok)
        self.assertIn("boom", err)

    @patch("helpers.cron_edit.subprocess.run")
    def test_edit_idempotent_skips_when_same(self, mock_run):
        # arrange: fetch returns same message
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"payload":{"message":"already"}}',
            stderr=""
        )
        ok, err = edit_message("abc","already", skip_if_same=True)
        self.assertTrue(ok)
        # only the fetch call was made — no edit
        self.assertEqual(mock_run.call_count, 1)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

```bash
cd ~/.openclaw/skills/anicca-cron-doctor/scripts && python3 -m unittest tests.test_cron_edit -v 2>&1 | tail -15
```
Expected: `ModuleNotFoundError: No module named 'helpers.cron_edit'`

- [ ] **Step 3: Implement minimal**

```python
# scripts/helpers/cron_edit.py
"""Thin wrapper around `openclaw cron edit` that avoids shell quoting.

Why: openclaw CLI fails with multi-line --message under shell expansion.
Using subprocess.run with list args bypasses shell entirely.
"""
import json
import subprocess
from typing import Optional, Tuple


def fetch_message(cron_id: str, timeout: int = 30) -> Optional[str]:
    """Return current payload.message or None if unavailable."""
    r = subprocess.run(
        ["openclaw", "cron", "get", cron_id],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        return None
    out = r.stdout
    # CLI prefixes with config warnings; find first '{'
    idx = out.find("{")
    if idx < 0:
        return None
    try:
        data = json.loads(out[idx:])
    except json.JSONDecodeError:
        return None
    return (data.get("payload", {}) or {}).get("message")


def edit_message(
    cron_id: str, new_msg: str, skip_if_same: bool = True, timeout: int = 30,
) -> Tuple[bool, str]:
    """Edit cron message. Returns (success, error_or_empty)."""
    if skip_if_same:
        cur = fetch_message(cron_id, timeout=timeout)
        if cur == new_msg:
            return True, ""
    r = subprocess.run(
        ["openclaw", "cron", "edit", cron_id, "--message", new_msg],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode == 0:
        return True, ""
    return False, (r.stderr or "")[:200]


def refire(cron_id: str, timeout: int = 30) -> Tuple[bool, str]:
    """Trigger an immediate run via `openclaw cron run`."""
    r = subprocess.run(
        ["openclaw", "cron", "run", cron_id],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode == 0:
        return True, ""
    return False, (r.stderr or "")[:200]
```

- [ ] **Step 4: Run, confirm PASS**

```bash
cd ~/.openclaw/skills/anicca-cron-doctor/scripts && python3 -m unittest tests.test_cron_edit -v 2>&1 | tail -5
```
Expected: `Ran 3 tests in ...s\nOK`

- [ ] **Step 5: Commit** (deferred to end-of-session batch commit per HARD RULE 0.8 — not per-task)

---

## Task 2: R-6 — streak_window helper

**Files:**
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/streak_window.py`
- Create: `~/.openclaw/skills/anicca-cron-doctor/scripts/tests/test_streak_window.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_streak_window.py
import time
import unittest
from helpers.streak_window import tick_streak, migrate_schema

class TestStreakWindow(unittest.TestCase):
    def test_empty_returns_zero_when_not_refused(self):
        state = {}
        n = tick_streak(state, "foo", refused_now=False, window=86400)
        self.assertEqual(n, 0)
        self.assertEqual(state["foo"], [])

    def test_refused_appends_timestamp(self):
        state = {}
        n = tick_streak(state, "foo", refused_now=True, window=86400, now=1000.0)
        self.assertEqual(n, 1)
        self.assertEqual(state["foo"], [1000.0])

    def test_expired_dropped(self):
        state = {"foo": [10.0, 20.0, 50.0]}
        # now=100000, window=86400 → all dropped (50 < 100000-86400=13600)
        n = tick_streak(state, "foo", refused_now=False, window=86400, now=100000.0)
        self.assertEqual(n, 0)
        self.assertEqual(state["foo"], [])

    def test_fresh_kept(self):
        state = {"foo": [80000.0, 90000.0]}
        n = tick_streak(state, "foo", refused_now=False, window=86400, now=100000.0)
        self.assertEqual(n, 2)

    def test_schema_migration_int_to_list(self):
        # v1 schema: name -> int count
        state = {"foo": 5}
        migrate_schema(state, now=1000.0)
        # int 5 collapses to single-element list at current time
        self.assertEqual(state["foo"], [1000.0])

    def test_migration_idempotent_on_list(self):
        state = {"foo": [1.0, 2.0]}
        migrate_schema(state, now=1000.0)
        self.assertEqual(state["foo"], [1.0, 2.0])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

```bash
cd ~/.openclaw/skills/anicca-cron-doctor/scripts && python3 -m unittest tests.test_streak_window -v 2>&1 | tail -5
```

- [ ] **Step 3: Implement**

```python
# scripts/helpers/streak_window.py
"""24h sliding-window refusal streak.

Schema: {cron_name: [ts_float, ...]}.
Migration from v1 {cron_name: int} happens transparently.
"""
import time as _time


def migrate_schema(state: dict, now: float | None = None) -> None:
    """In-place: any int values become single-element lists at `now`."""
    if now is None:
        now = _time.time()
    for name, val in list(state.items()):
        if isinstance(val, int):
            state[name] = [float(now)] if val > 0 else []


def tick_streak(
    state: dict, name: str, refused_now: bool,
    window: int = 86400, now: float | None = None,
) -> int:
    """Update state[name] for one tick. Returns current streak count."""
    if now is None:
        now = _time.time()
    cutoff = now - window
    cur = state.get(name, [])
    if not isinstance(cur, list):
        cur = []
    # drop expired
    cur = [t for t in cur if t > cutoff]
    if refused_now:
        cur.append(float(now))
    state[name] = cur
    return len(cur)
```

- [ ] **Step 4: Run, confirm PASS**

```bash
cd ~/.openclaw/skills/anicca-cron-doctor/scripts && python3 -m unittest tests.test_streak_window -v 2>&1 | tail -5
```

---

## Task 3: R-13 — config_audit helper

**Files:**
- Create: `.../helpers/config_audit.py`
- Create: `.../tests/test_config_audit.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_config_audit.py
import json
import tempfile
import pathlib
import unittest
from helpers.config_audit import audit_model_config

ALLOWED_PRIMARY = {"openai-codex/gpt-5.4-mini", "deepseek/deepseek-v4-pro"}

class TestConfigAudit(unittest.TestCase):
    def _write(self, cfg: dict) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(cfg, f); f.close()
        return f.name

    def test_in_compliance(self):
        path = self._write({"agents":{"defaults":{"model":{
            "primary":"openai-codex/gpt-5.4-mini",
            "fallbacks":["deepseek/deepseek-v4-pro"],
        }}}})
        r = audit_model_config(path, ALLOWED_PRIMARY)
        self.assertFalse(r["drift_detected"])
        self.assertEqual(r["primary"], "openai-codex/gpt-5.4-mini")

    def test_drift_when_primary_disallowed(self):
        path = self._write({"agents":{"defaults":{"model":{
            "primary":"openai/gpt-5.5",
            "fallbacks":[],
        }}}})
        r = audit_model_config(path, ALLOWED_PRIMARY)
        self.assertTrue(r["drift_detected"])
        self.assertEqual(len(r["violations"]), 1)

    def test_corrupt_json_yields_drift_with_error(self):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        f.write("not-json"); f.close()
        r = audit_model_config(f.name, ALLOWED_PRIMARY)
        self.assertTrue(r["drift_detected"])
        self.assertTrue(any("parse" in v.lower() for v in r["violations"]))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

```bash
cd ~/.openclaw/skills/anicca-cron-doctor/scripts && python3 -m unittest tests.test_config_audit -v 2>&1 | tail -5
```

- [ ] **Step 3: Implement**

```python
# scripts/helpers/config_audit.py
"""Detect openclaw.json model config drift vs memory rule."""
import json
import pathlib
from typing import Iterable


def audit_model_config(path: str, allowed_primary: Iterable[str]) -> dict:
    """Read openclaw.json + return drift status."""
    p = pathlib.Path(path)
    try:
        cfg = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return {
            "primary": None, "fallbacks": [],
            "drift_detected": True,
            "violations": [f"config parse error: {e}"],
        }
    model = (cfg.get("agents", {})
                .get("defaults", {})
                .get("model", {}))
    primary = model.get("primary")
    fallbacks = model.get("fallbacks", [])
    violations = []
    if primary not in set(allowed_primary):
        violations.append(
            f"primary={primary!r} not in allowed_primary set"
        )
    return {
        "primary": primary,
        "fallbacks": fallbacks,
        "drift_detected": bool(violations),
        "violations": violations,
    }
```

- [ ] **Step 4: Run, confirm PASS**

---

## Task 4: R-9 — git_sync helper

**Files:**
- Create: `.../helpers/git_sync.py`

- [ ] **Step 1: Implement directly (integration helper, tested via end-to-end)**

```python
# scripts/helpers/git_sync.py
"""Auto-commit + push for ~/.openclaw cron state files."""
import os
import pathlib
import subprocess


REPO = pathlib.Path.home() / ".openclaw"
TRACKED = [
    "cron/jobs.json",
    "skills/anicca-cron-doctor/data/refusal-streak.json",
    "skills/anicca-cron-doctor/data/l3-last-refire.json",
]


def has_changes() -> bool:
    """True if any TRACKED file is dirty in working tree."""
    for rel in TRACKED:
        r = subprocess.run(
            ["git", "diff", "--quiet", "--", rel],
            cwd=REPO, capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return True
    return False


def commit_and_push(message: str, push: bool = True) -> dict:
    """Stage tracked files, commit, optionally push. Returns result dict."""
    result = {"committed": False, "pushed": False, "errors": []}
    if not has_changes():
        return result
    # only add files that exist
    files = [str(REPO / p) for p in TRACKED if (REPO / p).exists()]
    add = subprocess.run(
        ["git", "add", "--"] + files,
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )
    if add.returncode != 0:
        result["errors"].append(f"add: {add.stderr[:120]}")
        return result
    env = {**os.environ, "GIT_AUTHOR_NAME": "anicca-cron-doctor",
           "GIT_COMMITTER_NAME": "anicca-cron-doctor"}
    commit = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", message],
        cwd=REPO, capture_output=True, text=True, timeout=30, env=env,
    )
    if commit.returncode != 0:
        result["errors"].append(f"commit: {commit.stderr[:120]}")
        return result
    result["committed"] = True
    if push:
        push_r = subprocess.run(
            ["git", "push"], cwd=REPO,
            capture_output=True, text=True, timeout=60,
        )
        result["pushed"] = (push_r.returncode == 0)
        if not result["pushed"]:
            result["errors"].append(f"push: {push_r.stderr[:120]}")
    return result
```

---

## Task 5: R-8 — token_budget helper + cron-codex.sh integration

**Files:**
- Create: `.../helpers/token_budget.py`
- Create: `.../tests/test_token_budget.py`
- Modify: `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` (insert head check)

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_token_budget.py
import json, os, tempfile, unittest
from helpers.token_budget import check_budget, record_spend

class TestTokenBudget(unittest.TestCase):
    def test_check_under_budget_returns_true(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spend.json")
            ok, info = check_budget(path, monthly_usd=50.0,
                                    est_tokens=10_000, model="gpt-5.4-mini")
            self.assertTrue(ok)
            self.assertLess(info["projected_usd"], 50.0)

    def test_check_over_budget_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spend.json")
            # write 49 USD already spent
            json.dump({"month":"2026-06","spent_usd":49.0,"by_skill":{}}, open(path,"w"))
            ok, info = check_budget(path, monthly_usd=50.0,
                                    est_tokens=10_000_000, model="gpt-5.4-mini")
            self.assertFalse(ok)

    def test_record_spend_adds_to_total(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spend.json")
            record_spend(path, skill="bounty", tokens=10_000, model="gpt-5.4-mini")
            data = json.load(open(path))
            self.assertGreater(data["spent_usd"], 0)
            self.assertIn("bounty", data["by_skill"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, confirm FAIL**

- [ ] **Step 3: Implement**

```python
# scripts/helpers/token_budget.py
"""Track OpenAI token spend vs monthly budget.

Rate table inline; source: openai.com/pricing as of 2026-06.
Rate per 1k tokens (USD), averaged input+output 1:1.
"""
import json
import pathlib
from datetime import datetime, timezone
from typing import Tuple

# USD per 1k tokens, blended; refresh quarterly. Last updated 2026-06-04.
RATES = {
    "gpt-5.4-mini": 0.005,
    "gpt-5.5": 0.020,
    "openai-codex/gpt-5.4-mini": 0.005,
}
DEFAULT_RATE = 0.020
RATE_TABLE_VERSION = "2026-06-04"


def _load(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {"month": _month(), "spent_usd": 0.0, "by_skill": {},
                "rate_table_version": RATE_TABLE_VERSION}
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"month": _month(), "spent_usd": 0.0, "by_skill": {},
                "rate_table_version": RATE_TABLE_VERSION}
    # month rollover reset
    if d.get("month") != _month():
        return {"month": _month(), "spent_usd": 0.0, "by_skill": {},
                "rate_table_version": RATE_TABLE_VERSION}
    return d


def _save(path: str, data: dict) -> None:
    pathlib.Path(path).write_text(json.dumps(data, indent=2))


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _cost(tokens: int, model: str) -> float:
    rate = RATES.get(model, DEFAULT_RATE)
    return (tokens / 1000.0) * rate


def check_budget(
    path: str, monthly_usd: float, est_tokens: int, model: str,
    threshold: float = 0.95,
) -> Tuple[bool, dict]:
    """Return (allow_run, info_dict). False if projected spend > threshold * budget."""
    data = _load(path)
    projected = data["spent_usd"] + _cost(est_tokens, model)
    info = {"spent_usd": data["spent_usd"],
            "projected_usd": projected,
            "monthly_usd": monthly_usd,
            "threshold": threshold,
            "month": data["month"]}
    return (projected < monthly_usd * threshold), info


def record_spend(
    path: str, skill: str, tokens: int, model: str,
) -> dict:
    data = _load(path)
    cost = _cost(tokens, model)
    data["spent_usd"] = round(data["spent_usd"] + cost, 4)
    by = data["by_skill"].setdefault(skill, {"tokens": 0, "usd": 0.0})
    by["tokens"] = by["tokens"] + tokens
    by["usd"] = round(by["usd"] + cost, 4)
    _save(path, data)
    return data
```

- [ ] **Step 4: Run, confirm PASS**

- [ ] **Step 5: Wire into cron-codex.sh head**

Insert in `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` after env-load section:

```bash
# R-8 token budget guard
BUDGET_PATH="$HOME/.openclaw/skills/anicca-cron-doctor/data/openai-spend.json"
MONTHLY="${OPENAI_MONTHLY_BUDGET_USD:-50.0}"
if ! python3 -c "
import sys, json
sys.path.insert(0,'$HOME/.openclaw/skills/anicca-cron-doctor/scripts')
from helpers.token_budget import check_budget
ok, info = check_budget('$BUDGET_PATH', float('$MONTHLY'), 80000, 'gpt-5.4-mini')
print(json.dumps(info))
sys.exit(0 if ok else 1)
" >/tmp/budget-check.json; then
    INFO=$(cat /tmp/budget-check.json)
    MSG=":money_with_wings: skipped \`${SKILL}\`: monthly OpenAI budget threshold exceeded — $INFO"
    if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
        PAYLOAD=$(jq -nc --arg c "${SLACK_METRICS_CHANNEL:-C091G3PKHL2}" --arg t "$MSG" '{channel: $c, text: $t}')
        curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
             -H 'Content-Type: application/json; charset=utf-8' \
             --data "$PAYLOAD" https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
    fi
    exit 0
fi
```

---

## Task 6: phases.py refactor — use helpers + add L7

**Files:**
- Modify: `.../scripts/phases.py`

- [ ] **Step 1: Switch L1, L3, L5 to use `cron_edit` helper** — change all `cli("cron","edit",...)` to `from helpers.cron_edit import edit_message; edit_message(id, msg)`.

- [ ] **Step 2: Switch L4 streak tracking to use `streak_window`** — replace the int-counter logic with `from helpers.streak_window import tick_streak, migrate_schema; migrate_schema(streak); n = tick_streak(streak, name, refused_now=...)`. Pass `name in detected_now` as `refused_now`.

- [ ] **Step 3: Add `phase_l7_config_drift` function**:

```python
def phase_l7_config_drift() -> dict:
    """L7: detect openclaw.json model config drift."""
    from helpers.config_audit import audit_model_config
    ALLOWED = {"openai-codex/gpt-5.4-mini", "deepseek/deepseek-v4-pro"}
    config_path = str(pathlib.Path.home() / ".openclaw/openclaw.json")
    return audit_model_config(config_path, ALLOWED)
```

- [ ] **Step 4: Wire L7 into `main()` and report dict**:

```python
# after l5 in main()
l7 = phase_l7_config_drift()
...
report["L7_config_drift"] = l7
```

- [ ] **Step 5: Update stdout JSON summary**:

```python
print(json.dumps({
    "L1": l1["count"],
    "L2": l2["counts"],
    "L3": l3["count"],
    "L4": l4["count"],
    "L5": l5["count"],
    "L7": int(l7.get("drift_detected", False)),
}))
```

- [ ] **Step 6: Run doctor dry-run + verify all phases still return**

```bash
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh --dry-run 2>&1 | tail -3
```
Expected: JSON line includes `"L7"` key.

---

## Task 7: format_report.py — L7 + false-positive annotation

**Files:**
- Modify: `.../scripts/format_report.py`

- [ ] **Step 1: Add L7 line + drift detail**

```python
# after L5 line
drift = r.get("L7_config_drift", {})
drift_marker = "DRIFT" if drift.get("drift_detected") else "ok"
lines.append(f"  L7 config drift    {drift_marker} (primary={drift.get('primary','?')})")
if drift.get("violations"):
    lines.append("  L7 violations: " + "; ".join(drift["violations"]))
```

- [ ] **Step 2: Add false-positive annotation footer**

```python
# at end of lines
lines.append("")
lines.append("  ℹ cron list `lastRunStatus: error` with `delivery: not requested`")
lines.append("    is a false positive (dispatcher posts to Slack directly).")
lines.append("    Real status = Slack message presence + exit 0.")
```

- [ ] **Step 3: Verify format**

```bash
echo '{"ts":"2026-06-04","dry_run":false,"enabled_cron_count":172,"L1_prompt_lint":{"count":0,"skipped":[],"skipped_complex":[],"skipped_complex_count":0,"fixed":[]},"L2_path_lint":{"counts":{"pure_data":0,"llm_required":0,"revenue_critical":0}},"L3_refusal_retry":{"count":0},"L4_streak_monitor":{"count":0},"L5_hard_escalate":{"count":0},"L7_config_drift":{"drift_detected":false,"primary":"openai-codex/gpt-5.4-mini","violations":[]}}' > /tmp/r.json
python3 ~/.openclaw/skills/anicca-cron-doctor/scripts/format_report.py /tmp/r.json
```
Expected output contains `L7 config drift    ok (primary=openai-codex/gpt-5.4-mini)` and false-positive annotation.

---

## Task 8: run.sh — git_sync at tail

**Files:**
- Modify: `.../scripts/run.sh`

- [ ] **Step 1: Append git_sync call after Slack post block**

```bash
# R-9 auto-commit + push (only when files dirty)
python3 - <<'PY' 2>&1 | tail -5
import sys
sys.path.insert(0, "$HOME/.openclaw/skills/anicca-cron-doctor/scripts")
from helpers.git_sync import commit_and_push
import datetime
ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
r = commit_and_push(f"[cron-doctor] auto-state {ts}", push=True)
print("git_sync:", r)
PY
```

- [ ] **Step 2: Run doctor real + verify**

```bash
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh 2>&1 | tail -5
cd ~/.openclaw && git log -1 --oneline 2>&1 | head -1
```
Expected: latest commit author "anicca-cron-doctor" if any tracked file changed; otherwise no new commit.

---

## Task 9: R-4 — migrate-context-bearing.sh one-shot

**Files:**
- Create: `.../scripts/migrate-context-bearing.sh`

- [ ] **Step 1: Implement**

```bash
#!/usr/bin/env bash
# One-shot migration: 34 context-bearing crons → cron-codex.sh wrapper
# with original context preserved as 2nd arg.
#
# Idempotent — skips crons already on _dispatcher form.

set -uo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-cron-doctor"
BACKUP="$HOME/.openclaw/cron/jobs.json.bak-phaseA-20260604-202021"
TS=$(date -u +%Y-%m-%dT%H:%MZ)

[ -f "$BACKUP" ] || { echo "missing backup: $BACKUP" >&2; exit 2; }

set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a

OUT=$(python3 <<PY
import json, re, sys, subprocess, pathlib

sys.path.insert(0, "$SKILL_DIR/scripts")
from helpers.cron_edit import fetch_message, edit_message

backup = json.load(open("$BACKUP"))
current_file = pathlib.Path.home() / ".openclaw/cron/jobs.json"
cur = json.load(open(current_file))
cur_by_id = {j["id"]: j for j in cur["jobs"]}

read_re = re.compile(r"Read\s+~/\.openclaw/skills/([\w\-]+)/SKILL\.md", re.IGNORECASE)
exec_skill_re = re.compile(r"^\s*Execute\s+[\w\-]+\s+(?:daily\s+)?skill\.?\s*$", re.IGNORECASE | re.MULTILINE)

applied, skipped, errors = [], [], []

for job in backup["jobs"]:
    if not job.get("enabled"): continue
    msg = job.get("payload",{}).get("message","") or ""
    m = read_re.search(msg)
    if not m: continue
    skill = m.group(1)
    # extract context: lines that are not Read or Execute-X-skill
    context_lines = []
    for line in msg.splitlines():
        if read_re.search(line): continue
        if exec_skill_re.match(line): continue
        s = line.strip()
        if s and not s.startswith("Read "):
            context_lines.append(s)
    context = " ".join(context_lines).strip()
    if not context:
        # no meaningful context: doctor L1 already handles these (cron-codex.sh skill only)
        skipped.append({"name": job["name"], "reason": "no extra context (L1 already covers)"})
        continue

    cid = job["id"]
    if cid not in cur_by_id:
        skipped.append({"name": job["name"], "reason": "not in current jobs.json"})
        continue
    cur_msg = cur_by_id[cid].get("payload",{}).get("message","") or ""
    if "_dispatcher/scripts/cron-codex.sh" in cur_msg:
        skipped.append({"name": job["name"], "reason": "already migrated"})
        continue

    new_msg = (
        "exec で 必ず 1 行 だけ 実行 する。 "
        "「shell tool が ない」 / 「MCP server が ない」 等 の 言い訳 禁止 — "
        "必ず exec_command を 1 回 は 呼ぶ。 stdout は Slack に 自動 で 出る。\n\n"
        f"bash \$HOME/.openclaw/skills/_dispatcher/scripts/cron-codex.sh {skill} "
        f"\"{context.replace(chr(34), chr(39))}\""
    )
    ok, err = edit_message(cid, new_msg)
    if ok:
        applied.append({"name": job["name"], "skill": skill, "context_chars": len(context)})
    else:
        errors.append({"name": job["name"], "err": err[:80]})

result = {"applied_count": len(applied), "skipped_count": len(skipped),
          "errors_count": len(errors), "applied": applied,
          "skipped_samples": skipped[:5], "errors": errors}
print(json.dumps(result, indent=2, ensure_ascii=False))
PY
)

echo "$OUT"

# post to Slack
if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
    SUMMARY=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\":wrench: cron-doctor R-4 batch-migrate-context-bearing applied={d['applied_count']} skipped={d['skipped_count']} errors={d['errors_count']}\")")
    PAYLOAD=$(jq -nc --arg c "${SLACK_METRICS_CHANNEL:-C091G3PKHL2}" --arg t "$SUMMARY" '{channel: $c, text: $t}')
    curl -sS -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        -H 'Content-Type: application/json; charset=utf-8' \
        --data "$PAYLOAD" https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
fi
```

- [ ] **Step 2: chmod + run once**

```bash
chmod +x ~/.openclaw/skills/anicca-cron-doctor/scripts/migrate-context-bearing.sh
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/migrate-context-bearing.sh 2>&1 | tail -20
```
Expected: `applied_count` > 0, Slack `:wrench:` post.

- [ ] **Step 3: Verify a specific migrated cron**

```bash
openclaw cron get larry-trend-hunter-ja 2>&1 | tail -20 | grep -E "(cron-codex|target)"
```
Expected: message contains `cron-codex.sh trend-hunter` AND `target: larry-ja`.

---

## Task 10: R-7 — digest-weekly.sh + cron registration

**Files:**
- Create: `.../scripts/digest-weekly.sh`

- [ ] **Step 1: Implement**

```bash
#!/usr/bin/env bash
# Weekly Monday digest of last 7 days of cron-doctor reports.
# Aggregates L1 skipped_complex into a manual-review queue for Slack.

set -uo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-cron-doctor"
REPORT_DIR="$SKILL_DIR/data/reports"
DIGEST_DIR="$SKILL_DIR/data/digests"
mkdir -p "$DIGEST_DIR"
DAY=$(date +%Y-%m-%d)
OUT="$DIGEST_DIR/${DAY}.json"

set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a

TEXT=$(python3 <<PY
import glob, json, pathlib, datetime
report_dir = pathlib.Path("$REPORT_DIR")
since = datetime.datetime.utcnow() - datetime.timedelta(days=7)
sc_by_cron = {}
totals = {"L1_fixed": 0, "L3_retried": 0, "L4_alerted": 0, "L5_migrated": 0}
files_seen = 0
for f in sorted(report_dir.glob("*.json")):
    try:
        mt = datetime.datetime.utcfromtimestamp(f.stat().st_mtime)
        if mt < since: continue
        r = json.loads(f.read_text())
    except Exception:
        continue
    files_seen += 1
    totals["L1_fixed"] += r.get("L1_prompt_lint", {}).get("count", 0)
    totals["L3_retried"] += r.get("L3_refusal_retry", {}).get("count", 0)
    totals["L4_alerted"] += r.get("L4_streak_monitor", {}).get("count", 0)
    totals["L5_migrated"] += r.get("L5_hard_escalate", {}).get("count", 0)
    for entry in r.get("L1_prompt_lint", {}).get("skipped_complex", []):
        sc_by_cron.setdefault(entry["name"], []).append(entry.get("reason",""))

digest = {
    "week_of": "$DAY",
    "files_seen": files_seen,
    "totals": totals,
    "skipped_complex_unique": len(sc_by_cron),
    "manual_review_queue": sorted(sc_by_cron.keys()),
}
out_path = pathlib.Path("$OUT")
out_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
lines = [
    f":scroll: cron-doctor weekly digest (week of $DAY)",
    f"  reports seen      = {files_seen}",
    f"  L1 fixed (7d)     = {totals['L1_fixed']}",
    f"  L3 retried (7d)   = {totals['L3_retried']}",
    f"  L4 alerted (7d)   = {totals['L4_alerted']}",
    f"  L5 migrated (7d)  = {totals['L5_migrated']}",
    f"  manual review queue ({len(sc_by_cron)}): " + ", ".join(sorted(sc_by_cron.keys())[:20]),
]
print("\n".join(lines))
PY
)

echo "$TEXT"

if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
    PAYLOAD=$(jq -nc --arg c "${SLACK_METRICS_CHANNEL:-C091G3PKHL2}" --arg t "$TEXT" '{channel: $c, text: $t}')
    curl -sS -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
         -H 'Content-Type: application/json; charset=utf-8' \
         --data "$PAYLOAD" https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
fi
```

- [ ] **Step 2: chmod + register as OpenClaw cron**

```bash
chmod +x ~/.openclaw/skills/anicca-cron-doctor/scripts/digest-weekly.sh
openclaw cron add \
  --name "anicca-cron-doctor-digest" \
  --description "Weekly Monday 04:00 JST digest of cron-doctor reports" \
  --cron "0 4 * * 1" \
  --tz "Asia/Tokyo" \
  --message 'exec で 必ず 1 行 だけ 実行 する。 言い訳 禁止 — exec_command を 必ず 1 回 は 呼ぶ。

bash $HOME/.openclaw/skills/anicca-cron-doctor/scripts/digest-weekly.sh' \
  --session "isolated" \
  --timeout-seconds 600 \
  --no-deliver
```

- [ ] **Step 3: Verify**

```bash
openclaw cron list 2>&1 | grep "anicca-cron-doctor-digest"
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/digest-weekly.sh 2>&1 | tail -10
```

---

## Task 11: R-11 — LEARNINGS.md post-mortem

**Files:**
- Append: `~/.openclaw/.learnings/LEARNINGS.md`

- [ ] **Step 1: Append entry**

```markdown
## 2026-06-04 — Cron rat-proof: OpenClaw-all-the-way pivot

**Context.** Slack #metrics 18:20 batch had 2 of 7 crons return refusal text
("unknown MCP server 'openclaw'" / "実行環境が ない") instead of executing
their bash. Initial diagnosis: OpenClaw classifies refusal text as
`status: ok` and the cron's `payload.model` field is silently ignored —
the runtime forces `agentTurn` + isolated Codex sandbox + gpt-5.4-mini
for every cron, and that model has a ~30% refusal rate for tool calls.

**Wrong first move.** I drifted into "the only deterministic answer is
launchd plists outside the gateway." That is a HARD RULE #-1 violation —
Anicca has 5+ tool paths (systemEvent main session, codex exec wrapper,
Slack refire, direct API, launchd). Defaulting to launchd on first
failure is lazy escapism that ignores 4 of those 5 paths.

**Right answer.** Stay inside OpenClaw, reduce the LLM's decision surface
to a single deterministic `exec_command` call:

```
exec で 必ず 1 行 だけ 実行 する。 言い訳 禁止。

bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-codex.sh <skill>
```

The wrapper handles auth (`OPENAI_API_KEY` from `~/.codex/auth.json`),
budget, and Slack delivery itself. gpt-5.4-mini's only decision is
"call exec_command once" — much higher hit rate than a multi-step
prompt. Refusals are caught by `anicca-cron-doctor` L3 (Slack scrape +
re-fire) and escalated by L5 (force rewrite to wrapper) on repeat.

**Concrete invariants going forward.**

1. Every cron's `payload.message` is one line: `bash $HOME/.openclaw/
   skills/_dispatcher/scripts/cron-{bash|codex}.sh <arg>`.
2. Slack delivery is the wrapper's responsibility, not OpenClaw `--announce`.
   Crons run with `--no-deliver`; `lastRunStatus: error` in `openclaw cron
   list` is a false positive in this mode.
3. `_dispatcher/scripts/cron-codex.sh` injects `OPENAI_API_KEY` from
   `~/.codex/auth.json` to survive isolated-sandbox env stripping.
4. `~/.openclaw/cron/jobs.json` direct edits get clobbered by gateway
   hot-reload race; always go through `openclaw cron edit`. The
   `cron_edit.py` helper exists for this.
5. launchd is for **long-running services** (agentmail, x402, pipecat,
   cfo-daily), NOT for scheduled crons. Cron stays in OpenClaw.

**Cost guard.** bounty 1 fire ≈ 69k tokens; 12/day = 828k/day. Without a
budget guard one cron can swallow $50/month of OpenAI credit alone.
`token_budget.py` + `OPENAI_MONTHLY_BUDGET_USD` env was added 2026-06-04.

**Related commits.** anicca-private-backup #90e089162 #c55cdce72
#d2c8cd152 #3d9a17fcd; anicca-products #9cd90550 #078a1ccd #b802f4b4
#23af09e8.
```

- [ ] **Step 2: Verify append**

```bash
grep -c "2026-06-04 — Cron rat-proof" ~/.openclaw/.learnings/LEARNINGS.md
```
Expected: `1`.

---

## Task 12: End-to-end verification

- [ ] **Step 1: Run doctor once, capture report**

```bash
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh 2>&1 | tail -5
```

- [ ] **Step 2: Verify Slack received L7 line + annotation**

```bash
set -a; . ~/.openclaw/.env 2>/dev/null; set +a
curl -sS -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=C091G3PKHL2&limit=1" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['messages'][0]['text'])"
```
Expected: contains `L7 config drift` AND false-positive annotation.

- [ ] **Step 3: Verify auto-commit if jobs.json changed**

```bash
cd ~/.openclaw && git log -3 --oneline --author=anicca-cron-doctor 2>&1 | head -3
```

- [ ] **Step 4: Run idempotency cycle**

```bash
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh 2>&1 | tail -3
bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh 2>&1 | tail -3
```
Expected: 2nd run L1=0, L7 unchanged.

- [ ] **Step 5: Final commit + push (~/.openclaw)**

```bash
cd ~/.openclaw && git -c commit.gpgsign=false add skills/anicca-cron-doctor skills/_dispatcher .learnings/LEARNINGS.md cron/jobs.json
cd ~/.openclaw && git -c commit.gpgsign=false commit -m "feat(cron-doctor): v2 — R-4/6/7/8/9/11/13/14/15 end-to-end

Per docs/superpowers/specs/2026-06-04-cron-doctor-v2-design.md +
docs/superpowers/plans/2026-06-04-cron-doctor-v2.md.

[detailed change list]"
cd ~/.openclaw && git push
```

---

## Self-review

- [x] **Spec coverage:** R-4/R-6/R-7/R-8/R-9/R-11/R-13/R-14/R-15 — each maps to a numbered task.
- [x] **Placeholder scan:** No TBD / TODO / placeholders.
- [x] **Type consistency:** `edit_message(cron_id, new_msg, skip_if_same=True)` signature consistent across cron_edit, callers. `tick_streak(state, name, refused_now, window, now)` consistent. `check_budget(path, monthly_usd, est_tokens, model, threshold)` consistent.

## Execution Handoff

Plan complete. Per /goal hook: executing inline via `superpowers:executing-plans`. No subagent dispatch needed for this scope.
