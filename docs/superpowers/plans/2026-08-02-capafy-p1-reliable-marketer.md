# Capafy P1 Reliable Marketer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take a fresh Capafy Instagram account from verified browser-owned creation through two real warmup successes to one verified public non-commercial Reel, with immediate account replacement and truthful Telegram links.

**Architecture:** A deterministic lifecycle controller owns state, legal transitions, evidence counting, capability gates, and idempotency. Bounded agents own only account-creation/browser judgment and creative judgment; repository-owned adapters own warmup dispatch, browser-direct Reel publication, public URL verification, and P0 outcome delivery. P1 keeps its small mutable lifecycle snapshot separate from P2's future append-only revenue ledger.

**Tech Stack:** Python 3 standard library, Bash, launchd, existing `agent-runner`, isolated CloakBrowser CDP, `ig-account-create`, `ig-account-warmer`, pytest/unittest and shell fixtures.

## Global Constraints

- Implement only P1 Section 8 of `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`; do not pull the P2 shared revenue ledger into this plan.
- The first non-commercial Reel requires two distinct verified warmup dates. Calendar age alone never advances capability.
- Commercial CTA and bio links remain prohibited until seven verified warmups and healthy measured reach; P1 does not claim this later commercial gate is complete.
- The Instagram browser session remains the owner. Never run the old day-3 private-API golden login and never retry credentials for `@capafy.skills10491`.
- Agent judgment is limited to account-creation UI decisions and creative selection/copy. Deterministic code owns parsing fixed JSON, bookkeeping, capability checks, URL validation, atomic writes, retries, and receipts.
- A public post requires a newly observed URL matching the fixed Instagram Reel URL shape, for example `https://www.instagram.com/reel/REAL123/`. `--live`, exit code zero, and scheduler presence are not publication.
- P0 remains the sole Telegram boundary. Every delivery is idempotent and a published message must contain real Reel, public Capafy skill, and campaign URLs.
- Preserve all unrelated dirty work. In particular, do not stage Marketing Engine Gate 6 files, shared Telegram transport files, site changes, or the pre-existing Builder task-class change in `test_gpt_first_runner_wiring.py`.
- The documented `ig-reels-poster/scripts/post_reel.py` source is absent. Build and test the repository-owned Capafy Reel adapter below; do not execute the orphaned `.pyc`.
- After each task: run its focused tests, update the living spec execution log with evidence, commit only that task, then record the commit hash in a separate spec evidence commit.

---

## Target File Structure

```text
skills/earn/capafy-marketing/
├── scripts/
│   ├── capafy_ig_lifecycle.py          # pure lifecycle + atomic state CLI
│   └── capafy_reel_poster.py           # browser-direct Reel adapter/verifier
├── tests/
│   ├── test_capafy_ig_lifecycle.py
│   ├── test_capafy_ig_account_manager.sh
│   ├── test_capafy_ig_warmup.sh
│   ├── test_capafy_reel_poster.py
│   ├── test_capafy_marketing_controller.sh
│   └── test_capafy_p1_launchd.py
├── launchd/
│   ├── ai.anicca.capafy-ig-account-manager.plist
│   ├── ai.anicca.capafy-marketing-warmup.plist
│   └── ai.anicca.capafy-ig-marketing-daily.plist
├── capafy-ig-account-manager.sh
├── capafy-ig-marketing-daily.sh
├── capafy-marketing-handoff.sh
└── warm_jitter.sh

docs/superpowers/specs/
└── 2026-08-01-capafy-self-improving-revenue-loop-design.md
```

## Runtime Contracts

`~/.openclaw/state/capafy-ig-lifecycle.json` is an atomic P1 snapshot:

```json
{
  "schema_version": 1,
  "status": "warmup_1_of_2",
  "handle": "capafy.skills25042",
  "session_owner": "browser",
  "session_established": true,
  "warmup_success_dates": ["2026-08-02"],
  "warmup_successes": 1,
  "capability": "warmup_only",
  "last_public_reel_url": null,
  "reach_healthy": false,
  "replacement_requested": false,
  "incident_id": null,
  "updated_at": "2026-08-02T03:15:00Z"
}
```

Allowed capabilities are `none`, `warmup_only`, `noncommercial_post`, and `commercial_post`. Allowed P1 statuses are `needed`, `replacement_requested`, `provisioning`, `created_session_verified`, `warmup_0_of_2`, `warmup_1_of_2`, `noncommercial_ready`, `first_noncommercial_post_verified`, `reach_observing`, `commercial_ready`, and `healthy`.

The creative candidate at `~/.openclaw/state/capafy-marketing-creative.json` is:

```json
{
  "schema_version": 1,
  "title": "Portfolio Tracker — Daily Position Review",
  "agent_id": "9480246345",
  "listing_url": "https://capafy.ai/agent/9480246345",
  "campaign_url": "https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram&utm_medium=reel&utm_campaign=portfolio-tracker-launch",
  "caption": "Your portfolio changed today. Your old review did not.",
  "media_path": "/tmp/capafy-portfolio-tracker.mp4",
  "commercial_intent": false
}
```

The agent writes creative evidence only. The shell adds `result=published` and `reel_url` only after the browser adapter returns a new verified public URL.

---

### Task 1: Implement the deterministic lifecycle controller

**Files:**

- Create: `skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: account registry list, per-handle `ig-warmup-$HANDLE.json`, the P1 lifecycle snapshot, and fixed timestamps.
- Produces: `successful_warmup_dates(data: dict) -> list[str]`, `derive_snapshot(accounts: list[dict], warmup: dict, prior: dict, now: datetime) -> dict`, `retire_account(path: Path, handle: str, reason: str, incident_id: str) -> dict`, `record_public_reel(path: Path, handle: str, reel_url: str) -> dict`, and CLI commands `snapshot`, `retire`, `record-reel`, `request-replacement`.

- [ ] **Step 1: Write failing pure lifecycle tests**

```python
def test_calendar_age_without_verified_actions_stays_warmup_zero():
    account = {"handle": "capafy.new", "status": "warming", "session_owner": "browser", "created": "2026-07-01"}
    snapshot = derive_snapshot([account], {"log": []}, {}, now("2026-08-02T10:00:00Z"))
    assert snapshot["status"] == "warmup_0_of_2"
    assert snapshot["capability"] == "warmup_only"

def test_two_distinct_verified_dates_grant_only_noncommercial_capability():
    warmup = {"log": [warm("2026-08-01", 6, 5), warm("2026-08-02", 8, 6)]}
    snapshot = derive_snapshot([active_account()], warmup, {}, now("2026-08-02T10:00:00Z"))
    assert snapshot["warmup_successes"] == 2
    assert snapshot["status"] == "noncommercial_ready"
    assert snapshot["capability"] == "noncommercial_post"

def test_later_abort_or_ban_requests_replacement():
    warmup = {"log": [warm("2026-08-01", 6, 5)], "aborts": [{"date": "2026-08-02", "ABORT": "not logged in"}]}
    assert derive_snapshot([active_account()], warmup, {}, now("2026-08-02T10:00:00Z"))["replacement_requested"] is True

def test_seven_warmups_without_reach_are_not_commercial():
    snapshot = derive_snapshot([active_account()], seven_warmups(), {"reach_healthy": False}, now("2026-08-08T10:00:00Z"))
    assert snapshot["capability"] == "noncommercial_post"

def test_retire_is_atomic_and_preserves_every_other_registry_row(tmp_path):
    result = retire_account(registry(tmp_path), "capafy.failed", "challenge", "capafy-marketer-1")
    assert result["retired_handle"] == "capafy.failed"
    assert load_registry(tmp_path)[0]["status"] == "session_failed"
    assert len(load_registry(tmp_path)) == 3
```

- [ ] **Step 2: Run the test and prove RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py
```

Expected: collection failure because `capafy_ig_lifecycle.py` does not exist.

- [ ] **Step 3: Implement the pure state functions and atomic CLI**

Use this module boundary:

```python
def is_verified_warmup(entry: dict) -> bool:
    verified = entry.get("verified") or {}
    actions = entry.get("actions") or {}
    return (
        isinstance(entry.get("date"), str)
        and int(verified.get("reels_played") or 0) > 0
        and int(actions.get("scrolls") or 0) > 0
        and not entry.get("ban")
        and not entry.get("ban_signal")
        and not entry.get("ABORT")
    )

VALID_CAPABILITIES = frozenset({"none", "warmup_only", "noncommercial_post", "commercial_post"})
ACTIVE_STATUSES = frozenset({"warming", "ready_browser", "noncommercial_ready", "reach_observing", "commercial_ready"})
INSTAGRAM_REEL_HOST = "www.instagram.com"
INSTAGRAM_REEL_PATH_PREFIX = "/reel/"
```

Expose the five exact function signatures listed in the Interfaces block. `successful_warmup_dates` returns sorted unique dates. `derive_snapshot` selects the newest usable browser-owned row, treats a same-or-later abort/ban as replacement-required, derives the capability from evidence count and reach, and preserves an already verified Reel only for the same handle. The three mutators call `atomic_json` and return the fully written value after readback.

Reject non-Instagram Reel URLs in `record_public_reel`. Use same-directory temp file, `flush`, `fsync`, and `os.replace`. Preserve registry order and row count.

- [ ] **Step 4: Prove GREEN and CLI behavior**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py
python3 -m py_compile skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py
```

- [ ] **Step 5: Update the P1 execution log and commit**

Commit only the controller, test, and spec update:

```bash
git commit -m "feat(capafy): define Instagram lifecycle capabilities"
```

---

### Task 2: Route Capafy creative work to the real marketing lane

**Files:**

- Modify: `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_marketing_lane.py`
- Carefully modify without staging the pre-existing Builder hunk: `skills/earn/marketing-engine/test_gpt_first_runner_wiring.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: `marketing-agent` from `~/profitable-claude/skills/agent-runner/config.json`.
- Produces: Capafy daily runner invocation `--task-class marketing-agent`, whose current configured timeout is `900` and token reservation is `49152`.

- [ ] **Step 1: Add the failing routing test**

```python
def test_capafy_marketer_has_required_runtime_and_token_reservation():
    task_class = declared_task_class(CAPAFY_DAILY)
    config = json.loads(CONFIG.read_text())
    assert task_class == "marketing-agent"
    assert config["task_classes"][task_class]["timeout_seconds"] >= 900
    assert config["task_classes"][task_class]["token_reservation"] >= 49152
```

- [ ] **Step 2: Prove RED**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_marketing_lane.py
```

Expected: the current script declares `tool-agent`, configured for 180 seconds.

- [ ] **Step 3: Change only the Marketer task class**

Change the daily invocation to:

```bash
--task-class marketing-agent
```

Update only the Capafy Marketer expectation in `test_gpt_first_runner_wiring.py`. Preserve its existing uncommitted Builder expectation (`application-lane-agent`) in the worktree. Stage the Marketer expectation as an index-only patch against `HEAD`, then inspect both cached and uncached diffs before committing.

- [ ] **Step 4: Prove GREEN and runner compatibility**

```bash
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_marketing_lane.py \
  skills/earn/marketing-engine/test_gpt_first_runner_wiring.py
bash -n skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh
```

- [ ] **Step 5: Update the spec and commit only P1 hunks**

```bash
git diff --cached --name-only
git commit -m "fix(capafy): give Marketer a complete execution lane"
```

---

### Task 3: Build the immediate replacement account manager

**Files:**

- Create: `skills/earn/capafy-marketing/capafy-ig-account-manager.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh`
- Create: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-ig-account-manager.plist`
- Modify: `skills/earn/capafy-marketing/capafy-marketing-handoff.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: lifecycle CLI, `ensure_provision_browser.sh`, `render_ig_provision_prompt`, `run_agent.sh --task-class marketing-agent`, account registry and credentials.
- Produces: account-manager terminal JSON with `result=account_created|replacement_waiting|failure`, verified handle/session evidence, and a LaunchAgent label `ai.anicca.capafy-ig-account-manager` running every 300 seconds plus event kickstart.

- [ ] **Step 1: Write a fake-browser/fake-runner integration test**

The fixture must assert:

```bash
CAPAFY_IG_ACCOUNT_MANAGER_PROBE_ONLY=1 bash "$MANAGER"
# output contains: task_class=marketing-agent interval=300 terminal_owner=capafy-marketing-handoff.sh

# needed -> one provision invocation -> verified new row
eq "one provision invocation" "$(wc -l < "$RUNNER_CALLS")" "1"
has "new account message has handle" "$TELEGRAM_BODY" "@capafy.skills25042"
has "new account is browser owned" "$TELEGRAM_BODY" "browser session"

# second pass sees the active row and does not provision again
eq "idempotent manager" "$(wc -l < "$RUNNER_CALLS")" "1"
```

Also cover missing credential file, unverified session, malformed appended row, lock recovery, and a failed sender receipt.

- [ ] **Step 2: Prove RED**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
```

- [ ] **Step 3: Implement the bounded account manager**

The manager must:

```text
lock -> lifecycle snapshot -> no-op if capability is active
     -> mark provisioning -> launch isolated browser
     -> render provision prompt with no agent-owned Telegram
     -> run marketing-agent
     -> compare registry before/after
     -> verify new row + credential file + browser-owned session
     -> persist created_session_verified
     -> call P0 handoff once
```

Use injectable commands for tests:

```bash
RUN_AGENT="${CAPAFY_RUN_AGENT:-$MARKETING_ENGINE_DIR/run_agent.sh}"
BROWSER="${CAPAFY_PROVISION_BROWSER:-$SCRIPT_DIR/../../browser/ensure_provision_browser.sh}"
VERIFY_SESSION="${CAPAFY_IG_SESSION_VERIFY:-$SCRIPT_DIR/scripts/capafy_ig_session_verify.py}"
KICKSTART="${CAPAFY_LAUNCHCTL:-launchctl}"
```

Add `account_created` rendering that states the handle, verified browser session, `0/2` warmups, no public post, and next automatic warmup. It must never call the account `live`.

- [ ] **Step 4: Make challenge handoff retire and wake replacement**

When `result=challenge`, `capafy-marketing-handoff.sh` must call:

```bash
python3 "$LIFECYCLE" retire --accounts "$ACCOUNTS" --handle "$HANDLE" \
  --reason "$REASON" --incident-id "$INCIDENT_ID"
"$KICKSTART" kickstart -k "gui/$(id -u)/ai.anicca.capafy-ig-account-manager"
```

The test must prove the failed handle is no longer selectable and the fake kickstarter is called once. It must also prove no password/private-login command is invoked.

- [ ] **Step 5: Prove GREEN**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
plutil -lint skills/earn/capafy-marketing/launchd/ai.anicca.capafy-ig-account-manager.plist
```

- [ ] **Step 6: Update the spec and commit**

```bash
git commit -m "feat(capafy): replace failed Instagram accounts immediately"
```

---

### Task 4: Count real browser warmups and grant capabilities

**Files:**

- Modify: `skills/earn/capafy-marketing/warm_jitter.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_ig_warmup.sh`
- Create: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-marketing-warmup.plist`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: an active browser-owned account, its live isolated CDP port, `ig-account-warmer/scripts/warm.py`, and lifecycle CLI.
- Produces: one verified warmup date at most per day and lifecycle messages only when the capability changes (`0/2 -> 1/2`, `1/2 -> noncommercial_ready`, `6/7 -> commercial check`).

- [ ] **Step 1: Write failing warmup integration tests**

Assert these cases with temporary HOME and fake `warm.py`:

```text
no account -> replacement requested, warm.py not called
warm.py rc=0 but no new verified log -> nonzero terminal, success count unchanged
new log with reels_played>0 and scrolls>0 -> success count increments once
same date rerun -> count unchanged and no duplicate Telegram
second distinct success -> capability=noncommercial_post
later not-logged-in abort -> failed account retired and replacement manager kicked
seven successes with reach_healthy=false -> no commercial capability
```

- [ ] **Step 2: Prove RED**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_ig_warmup.sh
```

- [ ] **Step 3: Replace calendar-day promotion with evidence readback**

`warm_jitter.sh` must use the account's live isolated browser identity/port, invoke browser `warm.py` directly, then compare lifecycle snapshots before and after. Keep jitter injectable:

```bash
JITTER_MAX_SECONDS="${CAPAFY_WARMUP_JITTER_MAX_SECONDS:-10800}"
[ "$JITTER_MAX_SECONDS" -gt 0 ] && sleep $((RANDOM % (JITTER_MAX_SECONDS + 1)))
```

Do not invoke `marketing-engine/warmer.py`; that path attempts the failed day-3 private session. A valid warmup terminal sends the normalized lifecycle envelope through P0 handoff; an unchanged same-day rerun stays silent.

- [ ] **Step 4: Prove GREEN and account regression safety**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_ig_warmup.sh
bash skills/self/tests/test_capafy_ig_account_state.sh
plutil -lint skills/earn/capafy-marketing/launchd/ai.anicca.capafy-marketing-warmup.plist
```

- [ ] **Step 5: Update the spec and commit**

```bash
git commit -m "feat(capafy): gate Instagram posting on verified warmups"
```

---

### Task 5: Restore a source-controlled browser-direct Reel poster

**Files:**

- Create: `skills/earn/capafy-marketing/scripts/capafy_reel_poster.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: `--video`, `--caption-file`, `--handle`, `--port`, `--tid`, `--expected-capability`, and `--dry|--live`.
- Produces: JSON `{status, reached, published, reel_url, pre_urls, post_urls, screenshots}`. Exit zero with `published=true` only when exactly one new public Reel URL is observed.

- [ ] **Step 1: Write a fake-CDP state-machine test**

```python
def test_dry_reaches_share_then_discards_without_clicking_share(fake_cdp, media):
    result = post_reel(request(media, live=False), fake_cdp)
    assert result["status"] == "dry_verified"
    assert result["published"] is False
    assert "share" not in fake_cdp.destructive_actions

def test_live_requires_noncommercial_capability_and_new_public_reel(fake_cdp, media):
    fake_cdp.pre_urls = {"https://www.instagram.com/reel/OLD123/"}
    fake_cdp.post_urls = fake_cdp.pre_urls | {"https://www.instagram.com/reel/NEW456/"}
    result = post_reel(request(media, live=True, capability="noncommercial_post"), fake_cdp)
    assert result["published"] is True
    assert result["reel_url"] == "https://www.instagram.com/reel/NEW456/"

def test_share_click_without_new_url_is_unconfirmed_failure(fake_cdp, media):
    fake_cdp.post_urls = fake_cdp.pre_urls
    assert post_reel(request(media, live=True), fake_cdp)["status"] == "share_unconfirmed"
```

Also test missing/invalid MP4, wrong handle in the active session, challenge page, commercial capability mismatch, `/p/` not accepted as a Reel, and multiple new URLs treated as ambiguous.

- [ ] **Step 2: Prove RED**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py
```

- [ ] **Step 3: Implement the adapter with an injectable ACI**

Use this concrete request/result boundary:

```python
@dataclass(frozen=True)
class PostRequest:
    video: Path
    caption: str
    handle: str
    port: int
    tid: str
    capability: str
    live: bool

@dataclass(frozen=True)
class PostResult:
    status: str
    reached: str
    published: bool
    reel_url: str | None
    pre_urls: tuple[str, ...]
    post_urls: tuple[str, ...]
    screenshots: tuple[str, ...]
```

The injected browser ACI exposes exact methods `active_handle`, `reel_urls`, `open_composer`, `upload_video`, `advance_to_caption`, `enter_caption`, `share`, and `discard`. The production implementation imports the shared raw CDP helper, captures Reel URLs before opening the composer, follows the video-specific cover/crop/caption steps, and polls the target profile after share. Normalize only fixed URL syntax; do not use keyword/regex judgment for content.

- [ ] **Step 4: Prove GREEN and dry CLI behavior**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py
python3 -m py_compile skills/earn/capafy-marketing/scripts/capafy_reel_poster.py
```

- [ ] **Step 5: Update the spec and commit**

```bash
git commit -m "feat(capafy): verify browser-published Reels"
```

---

### Task 6: Turn the Marketer into a creative candidate producer plus deterministic publisher

**Files:**

- Modify: `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`
- Modify: `skills/earn/capafy-marketing/capafy-marketing-handoff.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: lifecycle snapshot, one creative candidate, the Reel poster JSON, and P0 handoff.
- Produces: terminal `lifecycle_waiting`, `dry`, `published`, `challenge`, or `failure`; only the shell may construct `published`.

- [ ] **Step 1: Write failing controller tests**

With fake runner/poster/sender, prove:

```text
needed/replacement_requested -> creative runner not called; manager kickstarted
warmup_0_of_2 or warmup_1_of_2 -> runner/poster not called; truthful waiting terminal
noncommercial_ready -> creative runner called with marketing-agent
candidate commercial_intent=true -> live post refused
candidate missing media/listing/campaign field -> live post refused
valid candidate + dry mode -> poster --dry; no published claim
valid candidate + live mode + verified new URL -> shell writes published result
poster challenge -> account retired and manager kickstarted
same terminal envelope -> no second Telegram receipt
```

- [ ] **Step 2: Prove RED**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
```

- [ ] **Step 3: Remove provisioning and posting ownership from the creative prompt**

The prompt's terminal contract becomes:

```text
Select one verified public Capafy listing and create one 9:16 MP4 plus exact caption.
This pass is non-commercial: no offer CTA and no bio-link instruction.
Write one creative candidate JSON with schema_version, title, agent_id,
listing_url, campaign_url, caption, media_path, and commercial_intent=false.
Do not provision accounts, warm sessions, publish, verify publication, or send Telegram.
```

The shell validates candidate shape and media existence, calls `capafy_reel_poster.py`, then constructs the P0 outcome. Generate the campaign URL deterministically from the verified agent id and fixed Instagram UTM fields.

- [ ] **Step 4: Add stable handoff idempotency**

Before sending, compare `delivery_key(envelope)` to the current marketing terminal. If equal and the terminal contains a real Telegram message id, exit zero without sending. For `published`, require all three URLs and record the public Reel in the lifecycle snapshot only after the sender receipt succeeds.

- [ ] **Step 5: Prove GREEN and regress P0 truthfulness**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_outcome.py \
  skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
```

- [ ] **Step 6: Update the spec and commit**

```bash
git commit -m "feat(capafy): separate creative work from publication"
```

---

### Task 7: Install and prove the P1 schedulers and repair wiring

**Files:**

- Create: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-ig-marketing-daily.plist`
- Create or finalize: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-marketing-warmup.plist`
- Create or finalize: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-ig-account-manager.plist`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**

- Consumes: source scripts and exact GUI launchd domain.
- Produces: direct source-controlled jobs: account manager every 300 seconds, warmup at 11:20 JST, content at 16:00 JST.

- [ ] **Step 1: Write failing plist contract tests**

```python
def test_p1_jobs_call_source_controlled_scripts_directly():
    assert command("ai.anicca.capafy-ig-account-manager")[-1].endswith("capafy-ig-account-manager.sh")
    assert command("ai.anicca.capafy-marketing-warmup")[-1].endswith("warm_jitter.sh")
    assert command("ai.anicca.capafy-ig-marketing-daily")[-1].endswith("capafy-ig-marketing-daily.sh")

def test_capafy_publisher_is_not_routed_through_quarantined_scheduled_runner():
    assert "scheduled_runner.py" not in plist_text("ai.anicca.capafy-ig-marketing-daily")
```

Also assert explicit HOME/PATH, `StartInterval=300`, warmup `11:20`, content `16:00`, unique labels, and log paths.

- [ ] **Step 2: Prove RED, implement plists, prove GREEN**

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py
plutil -lint skills/earn/capafy-marketing/launchd/ai.anicca.capafy-*.plist
```

- [ ] **Step 3: Install reversibly and verify with `launchctl print`**

Resolve `uid=$(id -u)`. For each exact label, boot out the existing job if present, copy/format the source plist to `~/Library/LaunchAgents`, bootstrap it, and kickstart only the account manager first. Preserve the previous installed plist as a timestamped backup. Do not edit or delete the untracked Gate 6 scheduler sources.

Confirm:

```text
ai.anicca.capafy-ig-account-manager: interval 300, latest exit 0
ai.anicca.capafy-marketing-warmup: 11:20, loaded
ai.anicca.capafy-ig-marketing-daily: 16:00, loaded
```

- [ ] **Step 4: Seed a challenge-to-replacement fixture**

Use temporary HOME, fake launchctl, fake runner, and fake sender to prove:

```text
challenge -> retire -> replacement_requested -> manager wake
-> provisioning -> created_session_verified -> one Telegram lifecycle closure
```

- [ ] **Step 5: Run the complete offline P1/P0 regression suite**

```bash
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py \
  skills/earn/capafy-marketing/tests/test_capafy_marketing_lane.py \
  skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py \
  skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py \
  skills/earn/capafy-marketing/tests/test_capafy_outcome.py \
  skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
bash skills/earn/capafy-marketing/tests/test_capafy_ig_warmup.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
bash skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh
bash skills/self/tests/test_capafy_ig_account_state.sh
```

- [ ] **Step 6: Update the spec and commit**

```bash
git commit -m "feat(capafy): operate the P1 Instagram lifecycle"
```

---

### Task 8: Complete one real fresh lifecycle and close P1

**Files:**

- Modify only after evidence exists: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`
- Runtime evidence only: `~/.cloak/clip-accounts-capafy.json`, `~/.cloak/ig-warmup-$HANDLE.json`, `~/.openclaw/state/capafy-ig-lifecycle.json`, terminal receipts and incident files.

**Interfaces:**

- Consumes: the installed P1 jobs and real Instagram/Capafy state.
- Produces: one fresh browser-owned account, two distinct-date verified warmups, one verified public non-commercial Reel, one truthful Telegram message with all three URLs, and P1 completion evidence.

- [ ] **Step 1: Kickstart replacement provisioning and verify reality**

Run the exact account-manager LaunchAgent. Accept success only when all are true:

```text
new unique handle is appended after the three historical failed rows
status is warming and session_owner is browser
credential file exists with mode 0600
dedicated browser identity is live and resolves the same handle
Telegram contains the real new handle and says 0/2 warmups, no post
old failed handles remain terminal and are not selected
```

- [ ] **Step 2: Complete warmup success 1/2 on the first real date**

Kickstart the warmup job inside its safe hour window. Verify the warmup file contains positive `verified.reels_played`, positive `actions.scrolls`, no later abort/ban signal, and lifecycle `warmup_1_of_2`. Do not synthesize the date and do not post.

- [ ] **Step 3: Wait for the next real calendar date, then complete warmup success 2/2**

On the next JST date, run the same job and verify a second distinct evidence date. Lifecycle must become `noncommercial_ready`; calendar manipulation or duplicate-date evidence is not acceptable.

- [ ] **Step 4: Publish and verify the first non-commercial Reel**

Kickstart the 16:00 Marketer job. Verify:

```text
creative candidate has commercial_intent=false
media is a real 1080x1920 MP4
browser adapter observed exactly one new /reel/ URL
the URL opens publicly
lifecycle records first_noncommercial_post_verified/reach_observing
```

- [ ] **Step 5: Verify Telegram and idempotency**

The delivered message must contain the exact real values:

```text
Watch the Reel: lifecycle.last_public_reel_url
Open the skill: marketing_terminal.outcome.listing_url
Campaign link: marketing_terminal.outcome.campaign_url
```

Re-run the handoff and outcome monitor. Telegram message id and delivery key must remain unchanged.

- [ ] **Step 6: Final P1 acceptance and living spec update**

Re-run Task 7's complete suite, inspect all three jobs with `launchctl print`, and render the company state. Mark P1 complete only if every Section 8 acceptance item has current evidence. Record the new handle, warmup evidence dates, real Reel/skill/campaign URLs, Telegram message ids, test counts, LaunchAgent exits, and task commit hashes. Set P2 as the next single active priority.

Commit:

```bash
git commit -m "docs(capafy): record verified P1 lifecycle"
```

## Rollback and Failure Policy

- If provisioning hits phone/captcha or an explicit human-only challenge, contain the account, preserve evidence, schedule a bounded retry with a new identity, and report the actual external blocker. Do not label P1 complete.
- If a new session shows a challenge, retire it immediately and never password/private-API relogin it.
- If warmup evidence has no verified actions, it does not count even when the subprocess exits zero.
- If share is clicked but no new public Reel URL appears, classify `share_unconfirmed`, start repair, and do not send a published message.
- If Telegram delivery fails, leave the delivery key unset so the same terminal can retry safely.
- If a LaunchAgent behaves unexpectedly, boot out only its exact label, restore its timestamped prior plist, and preserve logs/state.
- If any task overlaps unrelated dirty files, stage only the P1 hunk and inspect `git diff --cached --name-only` plus `git diff --cached` before committing.
