# Capafy Report Schedules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install durable launchd schedules that invoke the verified Capafy owner reporter every hour at `HH:00` and once daily at `23:50 JST`.

**Architecture:** Add two source-controlled launchd plists that both call the existing `capafy-goal-monitor.sh`. Each plist supplies only its report kind (`hourly` or `daily_close`); the existing monitor derives the JST period key, shares the locked delivery ledger, renders the Japanese report, and deduplicates retries. Do not add a wrapper, scheduler daemon, database, or second reporting path.

**Tech Stack:** macOS launchd property lists, Bash, Python `plistlib`, pytest, existing Capafy goal monitor.

## Global Constraints

- Source of truth stays under `skills/earn/capafy-marketing/launchd/`; installed copies go only to `/Users/anicca/Library/LaunchAgents/`.
- Exact labels are `ai.anicca.capafy-goal-monitor-hourly` and `ai.anicca.capafy-goal-monitor-daily-close`.
- Both jobs call `/bin/bash /Users/anicca/anicca/skills/earn/capafy-marketing/capafy-goal-monitor.sh` directly.
- Hourly uses `StartCalendarInterval = {Minute = 0}` and `CAPAFY_REPORT_KIND=hourly`.
- Daily close uses `StartCalendarInterval = {Hour = 23, Minute = 50}` and `CAPAFY_REPORT_KIND=daily_close`.
- `HOME=/Users/anicca`, the existing explicit `PATH`, `RunAtLoad=false`, no `KeepAlive`, and unique stdout/stderr paths are mandatory.
- The jobs share the verified delivery state and send lock through the existing monitor; do not create per-job ledgers.
- Item 7 owns the existing `09:30` morning job. Do not change or reload it in this item.
- Production soft target: three files, about 40 source lines plus about 60 test lines.

---

### Task 1: Source-controlled hourly and daily-close jobs

**Files:**
- Create: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-hourly.plist`
- Create: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-daily-close.plist`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py`

**Interfaces:**
- Consumes: the existing `capafy-goal-monitor.sh` environment contract `CAPAFY_REPORT_KIND=hourly|daily_close`.
- Produces: two launchd jobs with exact calendar triggers and unique logs; both continue to use the monitor's shared period-keyed delivery ledger.

- [ ] **Step 1: Add failing source-plist contract tests**

Extend `test_capafy_p1_launchd.py` with these exact schedule expectations:

```python
REPORT_LABELS = {
    "ai.anicca.capafy-goal-monitor-hourly": {
        "kind": "hourly",
        "schedule": {"Minute": 0},
    },
    "ai.anicca.capafy-goal-monitor-daily-close": {
        "kind": "daily_close",
        "schedule": {"Hour": 23, "Minute": 50},
    },
}


def test_owner_report_jobs_use_the_existing_monitor_with_exact_schedules():
    for label, expected in REPORT_LABELS.items():
        data = load(label)
        assert data["Label"] == label
        assert data["ProgramArguments"] == [
            "/bin/bash",
            "/Users/anicca/anicca/skills/earn/capafy-marketing/capafy-goal-monitor.sh",
        ]
        assert data["StartCalendarInterval"] == expected["schedule"]
        assert data["EnvironmentVariables"]["CAPAFY_REPORT_KIND"] == expected["kind"]
        assert data["RunAtLoad"] is False
        assert "KeepAlive" not in data
```

Also assert all five Capafy P1/report jobs have unique labels and log paths, and both new jobs retain `HOME=/Users/anicca` plus a `PATH` containing `/opt/homebrew/bin`.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py
```

Expected: FAIL because the two source plists do not exist.

- [ ] **Step 3: Add the two minimal source plists**

Create both XML plists using the exact labels, program arguments, environment, schedules, and unique log names from Global Constraints. Use:

```text
/Users/anicca/.openclaw/logs/capafy-goal-monitor-hourly.out
/Users/anicca/.openclaw/logs/capafy-goal-monitor-hourly.err
/Users/anicca/.openclaw/logs/capafy-goal-monitor-daily-close.out
/Users/anicca/.openclaw/logs/capafy-goal-monitor-daily-close.err
```

Do not add `RunAtLoad=true`, `KeepAlive`, `StartInterval`, a wrapper script, or a separate state path.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py
python3 -m pytest -q -n 4 skills/earn/capafy-marketing/tests
plutil -lint skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-hourly.plist
plutil -lint skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-daily-close.plist
git diff --check
```

Expected: all PASS.

- [ ] **Step 5: Commit and push the implementation branch**

Commit only the two plists and the focused test:

```bash
git add skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-hourly.plist \
  skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-daily-close.plist \
  skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py
git commit -m "feat(capafy): schedule owner reports"
git push -u origin feature/capafy-report-schedules
```

- [ ] **Step 6: Run one fresh adversarial review and at most one correction**

Review the exact implementation commit read-only. Attack wrong wall-clock semantics, a daily job accidentally firing hourly, missing report-kind environment, collisions with the 09:30 job, duplicate labels/log paths, `RunAtLoad`/`KeepAlive` surprise sends, divergent state files, invalid plist syntax, and retry duplication. Send Critical/Important findings to the same Luna implementer once, rerun Step 4, and do not start a second review cycle.

- [ ] **Step 7: Merge, install, and read back production launchd state**

After parent verification and merge, install the exact source bytes with mode `0644`, then bootstrap only the two new labels:

```bash
install -m 644 skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-hourly.plist \
  /Users/anicca/Library/LaunchAgents/ai.anicca.capafy-goal-monitor-hourly.plist
install -m 644 skills/earn/capafy-marketing/launchd/ai.anicca.capafy-goal-monitor-daily-close.plist \
  /Users/anicca/Library/LaunchAgents/ai.anicca.capafy-goal-monitor-daily-close.plist
launchctl bootstrap gui/$(id -u) /Users/anicca/Library/LaunchAgents/ai.anicca.capafy-goal-monitor-hourly.plist
launchctl bootstrap gui/$(id -u) /Users/anicca/Library/LaunchAgents/ai.anicca.capafy-goal-monitor-daily-close.plist
```

Require `cmp -s` for source versus installed bytes. `launchctl print` must show hourly `Minute=0`, daily close `Hour=23/Minute=50`, the exact report kind, inactive state, and no unexpected run from installation.

- [ ] **Step 8: Prove each job and period dedupe with the existing loop**

Kickstart the hourly label with one valid unused hourly period key, repeat it, and require exactly one new real Telegram message ID. Kickstart the daily-close label with the current JST date, repeat it, and require exactly one new real Telegram message ID. Set a temporary manager-level `CAPAFY_REPORT_PERIOD_KEY` only around each pair and unset it in an EXIT trap. Across both pairs require exit `0`, byte-identical delivery state on each repeated key, no new stderr, a 409-row revenue ledger with unchanged SHA-256, and Japanese 5 / 2 / `$19.98` content. Do not kickstart Builder or Marketer.

- [ ] **Step 9: Close Item 6 in the authoritative spec**

Record implementation/merge commits, focused/full test counts, source-installed hashes, launchctl calendar/environment readback, real Telegram IDs, dedupe hashes, and remaining stale sources. Commit and push the spec before Item 7.
