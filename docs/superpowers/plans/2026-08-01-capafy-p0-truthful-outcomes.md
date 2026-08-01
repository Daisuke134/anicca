# Capafy P0 Truthful Outcomes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Use `superpowers:test-driven-development` for every behavior change and `superpowers:verification-before-completion` before claiming P0 complete.

**Goal:** Make every Capafy failure, repair, and verified business outcome resolve into one coherent natural-language Telegram story with real evidence and honest money labels.

**Architecture:** Add a small deterministic P0 reporting boundary around the existing Builder, self-fixer, Marketer, and goal monitor. The agents continue making product and creative decisions, but shell/Python code owns incident identity, terminal-state classification, evidence validation, idempotency, and message rendering. P0 stores only the minimal incident/outcome state required for closure; the full shared revenue event ledger remains P2.

**Tech stack:** Bash, Python 3 standard library, launchd, existing `skills/_shared/send-telegram.sh`, pytest/shell tests.

## Scope and safety constraints

- Implement only P0 from the approved design spec. Do not change Marketer timeouts, account creation policy, marketplace research, product pricing, or the public dashboard in this plan.
- Preserve the active uncommitted Telegram transport work in `skills/_shared/telegram.py`, `skills/_shared/send-telegram.sh`, and their tests. Consume `send-telegram.sh` as an interface; do not rewrite its transport internals.
- Never render `loaded`, `scheduled`, `calendar day 3`, or an agent exit code as a business success.
- A listing success requires an `https://capafy.ai/...` evidence URL and verified remote fields. A content success requires a public content URL. A repair success requires a changed business observable.
- Store runtime state beneath `~/.openclaw/state`; do not commit runtime incidents, credentials, logs, or Telegram receipts.
- All sends are idempotent. Re-running a monitor must not send the same terminal report twice.
- Update the design spec's execution log after each task is verified, with test commands and evidence. Commit one task at a time.

## Target file structure

```text
skills/earn/capafy-marketing/
├── scripts/
│   └── capafy_outcome.py                    # schema, validation, render, state CLI
├── tests/
│   ├── test_capafy_outcome.py               # pure contract tests
│   ├── test_capafy_outcome_monitor.sh        # idempotent closure integration
│   └── test_capafy_goal_monitor_report.py    # truthful morning labels
└── capafy-outcome-monitor.sh                 # detect terminal repair and deliver once

skills/self/capafy-loop/
├── capafy-loop-daily.sh                      # deterministic terminal outcome handoff
├── capafy-loop-healthcheck.sh                # business-outcome health contract
└── launchd/
    ├── ai.anicca.capafy-loop-healthcheck.plist
    └── ai.anicca.capafy-outcome-monitor.plist

skills/earn/capafy-marketing/
├── capafy-goal-monitor.sh                    # natural-language consolidated state
└── capafy-ig-marketing-daily.sh              # deterministic terminal outcome handoff

docs/superpowers/specs/
└── 2026-08-01-capafy-self-improving-revenue-loop-design.md
```

## Runtime contracts

### Incident record

`~/.openclaw/state/capafy-incidents/<incident_id>.json`:

```json
{
  "schema_version": 1,
  "incident_id": "capafy-builder-20260801T081400Z-a1b2c3d4",
  "owner": "builder",
  "phase": "repair_started",
  "detected_at": "2026-08-01T08:14:00+09:00",
  "summary": "Builder could not submit because browser ownership collided",
  "repair_result_path": "/Users/anicca/.openclaw/state/.self-fix-capafy-loop.result",
  "attempts": 1,
  "next_retry_at": null,
  "terminal_message_key": null
}
```

Allowed phases are `detected`, `repair_started`, `repaired`, `verified`, and `unresolved`. Transitions are monotonic except that an unresolved incident may enter a later retry attempt using the same incident id.

### Outcome envelope

The deterministic CLI accepts a JSON object through stdin:

```json
{
  "schema_version": 1,
  "kind": "repair_closure",
  "incident_id": "capafy-builder-20260801T081400Z-a1b2c3d4",
  "owner": "builder",
  "title": "Portfolio Tracker — Daily Position Review",
  "agent_id": "9480246345",
  "remote_status": 1,
  "skills_confirmed": true,
  "config_confirmed": true,
  "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
  "gross_usd": 9.99,
  "pending_usd": 8.00,
  "realized_usd": 0.00,
  "mrr_usd": 0.00,
  "cost_usd": 4.777,
  "contribution_usd": -4.777,
  "next_action": "Watch for approval and hand the public listing to Marketing"
}
```

`capafy_outcome.py validate` exits non-zero for missing evidence, literal `{placeholder}` tokens, invalid URLs, contradictory success states, or collapsed money fields. `render` produces one-screen natural language. `record-terminal` atomically records the delivery key after a real Telegram message id is returned.

---

## Task 1: Lock the reporting contract with failing tests

**Files:**

- Create: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Create: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`

**Step 1: Write failing contract tests**

Cover these exact cases:

- Builder success without `listing_url` is rejected.
- Marketing success without `reel_url` is rejected.
- A rendered message containing a literal `{verified_reel_url}` is rejected.
- `scheduler_loaded=true` never renders as `live` or `published`.
- `calendar_warmup_day=3` renders as account age, not warmup completion.
- Gross, pending, realized, MRR, cost, and contribution remain separate values.
- The approved Aug 1 repair fixture renders the real review URL, agent id, verified remote state, and “no action needed”.
- Re-rendering the same envelope produces the same delivery key.

Use a fixture factory, then assert semantic sentences instead of one fragile full-string snapshot.

**Step 2: Run the test and prove RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
```

Expected: failure because the CLI/module contract does not exist.

**Step 3: Implement the smallest pure module**

Implement:

```python
def validate_outcome(data: dict) -> list[str]: ...
def render_outcome(data: dict) -> str: ...
def delivery_key(data: dict) -> str: ...
def load_json_stdin() -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

Use `urllib.parse.urlparse`, `decimal.Decimal`, stable JSON serialization, and SHA-256. Do not perform network or Telegram I/O in this module.

**Step 4: Run the test and prove GREEN**

Run the same pytest command. Expected: all contract tests pass.

**Step 5: Update the spec and commit**

Append Task 1 status, exact test command, and commit hash to the execution log in the design spec.

Commit:

```bash
git add skills/earn/capafy-marketing/scripts/capafy_outcome.py skills/earn/capafy-marketing/tests/test_capafy_outcome.py docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md
git commit -m "feat(capafy): define truthful outcome contract"
```

## Task 2: Add one incident id from detection through repair

**Files:**

- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Modify: `skills/self/self-fix.sh`
- Modify: `skills/self/test-self-fix.sh`

**Step 1: Add failing tests**

Test that:

- `start-incident --owner builder --summary ...` creates an atomic JSON record and returns its id.
- Starting the same active owner/fingerprint returns the existing id instead of creating a duplicate.
- `self-fix.sh` accepts `CAPAFY_INCIDENT_ID` and writes it into the result marker's JSON sidecar without changing the existing one-line `SUCCESS|FAIL` compatibility marker.
- A generic non-Capafy self-fix remains unchanged.

**Step 2: Prove RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
bash skills/self/test-self-fix.sh
```

**Step 3: Implement atomic incident state**

Add CLI operations `start-incident`, `get-active-incident`, and `transition-incident`. Write to a same-directory temporary file, `fsync`, then `os.replace`. Reject backwards transitions.

In `self-fix.sh`, preserve the current result path and prompt contract. When `CAPAFY_INCIDENT_ID` is present, pass it into the self-fixer prompt and write the association to `~/.openclaw/state/.self-fix-<loop>.incident.json`. Do not make Telegram delivery the self-fixer's responsibility.

**Step 4: Prove GREEN and regression safety**

Run both commands from Step 2. Also run:

```bash
bash skills/self/capafy-loop/test-loop.sh
```

**Step 5: Update the spec and commit**

Record the verified incident lifecycle in the execution log.

Commit only the files from this task.

## Task 3: Deliver repair closure exactly once

**Files:**

- Create: `skills/earn/capafy-marketing/capafy-outcome-monitor.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh`
- Create: `skills/self/capafy-loop/launchd/ai.anicca.capafy-outcome-monitor.plist`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`

**Step 1: Write a failing integration test**

Use a temporary HOME, fake `send-telegram.sh`, seeded incident, and seeded self-fix result. Assert:

- `RUNNING` sends nothing.
- `SUCCESS` without verified business evidence sends an unresolved message, never a success claim.
- `SUCCESS` plus the Aug 1 verified listing fixture sends one closure containing the real URL.
- A second monitor run sends nothing.
- `FAIL` sends the attempted repair, remaining blocker, and next retry time.
- A fake sender response without a real message id does not mark delivery complete.

**Step 2: Prove RED**

Run:

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh
```

**Step 3: Implement monitor and receipt gate**

The monitor reads active incidents and their associated self-fix markers, asks `capafy_outcome.py` to validate/render, invokes the shared Telegram shell interface, extracts the returned message id, then records the stable delivery key. It must use a lock directory with stale-lock recovery and exit 0 when there is no new terminal outcome.

The LaunchAgent runs every 60 seconds with explicit HOME/PATH and logs to the existing OpenClaw log directory.

**Step 4: Prove GREEN**

Run the integration test twice. Both invocations must pass and the fixture sender count must remain one.

**Step 5: Update the spec and commit**

Record the exact seeded detect-to-closure evidence and commit the task.

## Task 4: Make Builder terminal reporting deterministic

**Files:**

- Modify: `skills/self/capafy-loop/capafy-loop-daily.sh`
- Create: `skills/self/tests/test_capafy_builder_outcome.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`

**Step 1: Write failing shell tests**

With fake runner output/state, assert:

- A verified `status=1`, skills/config confirmed, and review URL emits `builder_submitted`.
- A runner exit of zero without remote readback is not success.
- A browser/tool failure starts or reuses one incident id and invokes self-fix with that id.
- A cap-full or drained pass is an honest no-op, not failure and not revenue.
- Telegram wording is created by the deterministic renderer, not by agent-authored STEP5 prose.

**Step 2: Prove RED**

Run the new shell test.

**Step 3: Add a deterministic post-run handoff**

Keep the agent responsible for building and publishing. After the runner returns, make the shell read the authoritative remote-result artifact, build an outcome envelope, validate it, and send it through the shared transport. On failure, create the incident before spawning/resuming repair. Remove the prompt requirement that the agent itself compose and send the final Telegram report.

**Step 4: Prove GREEN and run regressions**

Run:

```bash
bash skills/self/tests/test_capafy_builder_outcome.sh
bash skills/self/capafy-loop/test-loop.sh
bash skills/self/test-self-fix.sh
```

**Step 5: Update the spec and commit**

Attach the test fixture's rendered message to the execution log and commit.

## Task 5: Correct Marketer terminal labels without changing its execution lane

**Files:**

- Modify: `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`

**Step 1: Write failing tests**

Assert:

- `--live` plus scheduler loaded but no public URL renders “scheduled, no verified post”.
- A dry pass is labeled dry and may attach media but never claims published.
- A live success requires Reel URL, promoted listing URL, campaign URL, caption, and media path.
- A challenge creates/reuses an incident and reports account lifecycle state honestly.
- The current 180-second timeout fixture renders an unresolved technical outcome, not an account ban.

**Step 2: Prove RED**

Run the new shell test.

**Step 3: Add the deterministic post-run handoff**

Retain creative generation inside the agent. Move terminal classification and message body generation to the shell/Python boundary. Remove the agent-authored STEP7 delivery responsibility. Do not change `tool-agent` to the 900-second lane in P0; that is P1.

**Step 4: Prove GREEN and regressions**

Run the new test plus existing Capafy marketing pytest tests.

**Step 5: Update the spec and commit**

Record truthful examples for dry, scheduled/no-post, published, and unresolved states.

## Task 6: Replace the cryptic goal dump with the 09:30 consolidated report

**Files:**

- Modify: `skills/earn/capafy-marketing/capafy-goal-monitor.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py`
- Modify: the installed/source LaunchAgent that schedules `capafy-goal-monitor.sh` after locating it with `rg`

**Step 1: Write failing report tests**

Feed the verified Aug 1 baseline and assert natural-language output contains:

- 27 online and 1 under review as inventory state, not “health”.
- 1 lifetime order / $9.99 gross; $8 pending; $0 realized; $0 MRR.
- OpenRouter cost as a separate cost and contribution value.
- `@capafy.skills10491` as calendar day 3, session not established, ban unproven.
- IG LaunchAgent loaded as “scheduled”, not `already_live`.
- Any open incident and its current repair/next retry.
- Real listing/dashboard links when available.

**Step 2: Prove RED**

Run the new pytest test.

**Step 3: Refactor parse versus render**

Keep collection deterministic. Emit the existing JSON for machine consumers, but pass its normalized data through `capafy_outcome.py` for human rendering. Remove `goal(a)`/`goal(b)` labels from Telegram. Preserve them only in machine JSON if downstream code still reads them.

Move the LaunchAgent schedule to 09:30 JST after verifying the installed job label/path. Do not create a second duplicate schedule.

**Step 4: Prove GREEN**

Run the new test and `skills/self/tests/test_capafy_ig_account_state.sh`.

**Step 5: Update the spec and commit**

Paste the exact fixture-rendered morning brief into the execution log and commit.

## Task 7: Load the watchdogs and prove the seeded end-to-end story

**Files:**

- Modify: `skills/self/capafy-loop/capafy-loop-healthcheck.sh`
- Modify: `skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Step 1: Add failing health behavior tests**

Extend the Capafy loop tests so scheduler presence alone is insufficient. A healthy verdict requires a recent terminal business outcome: verified listing, explicit bounded no-op, or honest unresolved incident with a scheduled retry. A stale in-progress incident must wake self-heal within five minutes.

**Step 2: Prove RED, then implement the smallest health change**

Keep the shared healthcheck compatibility intact. Point Capafy health at the deterministic outcome timestamp/state rather than only `.capafy-healthy-pass`.

**Step 3: Run the complete offline suite**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
bash skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh
bash skills/self/tests/test_capafy_builder_outcome.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
bash skills/self/capafy-loop/test-loop.sh
bash skills/self/test-self-fix.sh
bash skills/self/tests/test_capafy_ig_account_state.sh
```

**Step 4: Load and verify LaunchAgents**

Resolve the current GUI domain with `id -u`, then bootstrap/kickstart the healthcheck and outcome monitor using their exact plist paths. Verify with `launchctl print`, not merely `launchctl list`. Confirm the monitor is silent while there is no new terminal event.

**Step 5: Seed one non-production incident lifecycle**

Use a temporary state root and fake sender first. Produce:

```text
detected -> repair_started -> repaired -> verified -> one Telegram closure
```

Then run one read-only production reconciliation. Do not manufacture or resend the historical Aug 1 message unless the current verified state still supports every field.

**Step 6: Final acceptance check**

P0 is complete only if:

- the seeded lifecycle sends exactly one coherent closure;
- no contradictory stale failure remains terminal;
- the report contains a real evidence URL;
- money fields are separate;
- `loaded` is not called `live`;
- both watchdog jobs are loaded and their latest exit status is zero;
- the full suite is green.

**Step 7: Update the living spec and commit**

Mark P0 complete only with command output, LaunchAgent evidence, and the rendered closure example. Set P1 as the next single active priority; do not begin it in the same change.

Commit:

```bash
git add skills/earn/capafy-marketing skills/self/capafy-loop skills/self/self-fix.sh skills/self/test-self-fix.sh skills/self/tests docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md
git commit -m "feat(capafy): close truthful outcome loop"
```

Before committing, inspect `git diff --cached --name-only` and unstage any pre-existing or unrelated dirty files.

## Rollback and failure policy

- A failed Telegram send leaves the terminal delivery key unset so the monitor retries safely.
- A malformed outcome is recorded as unresolved and never silently discarded.
- If production reconciliation disagrees with the fixture, production evidence wins and the message is regenerated.
- If the shared Telegram transport is still under active modification when execution begins, run its existing tests and treat transport stabilization as a prerequisite; do not overwrite that work.
- If any LaunchAgent load changes runtime behavior unexpectedly, boot it out by exact label, preserve logs/state, and keep the code/tests for diagnosis. Do not delete evidence.
