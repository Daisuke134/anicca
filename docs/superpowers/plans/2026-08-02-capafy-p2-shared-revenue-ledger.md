# Capafy P2 Shared Revenue Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and production-verify one idempotent Capafy revenue event ledger whose projection drives both Telegram and the public company dashboard.

**Architecture:** Existing Builder, Marketer, account, money, metric, and incident artifacts remain source evidence. Standard-library Python adapters translate only verified source artifacts into a locked append-only public-safe JSONL ledger plus private evidence sidecars; one deterministic fold produces a projection identifier consumed by Telegram and `/company/`.

**Tech Stack:** Python 3 standard library, Bash controllers, JSON/JSONL, pytest, shell integration tests, Netlify static deploy, existing Capafy LaunchAgents and Telegram sender.

## Global Constraints

- Preserve the parent living spec and update it after every verified task.
- No routine human approval, account warmup, or elapsed-day gate.
- No hardcoded product, pricing, niche, hook, or creative judgment; deterministic code is limited to schema, identity, evidence, arithmetic, state, and delivery.
- Existing source ledgers and dirty user files remain untouched unless named by a task.
- Public projections contain no secrets, credential values, local absolute paths, or private technical diagnostics.
- Money dimensions remain separate: gross, pending, realized, MRR, cost, and contribution.
- A duplicate business observable is a no-op; a conflicting claim under the same `event_id` fails closed.
- Telegram and dashboard completion requires one identical `projection_id` derived from the same ledger revision.

---

### Task 1: Canonical event model and durable store

**Files:**
- Create: `skills/earn/capafy-marketing/schemas/capafy-revenue-event.schema.json`
- Create: `skills/earn/capafy-marketing/scripts/capafy_event_store.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_event_store.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Produces: `validate_event(event: dict) -> list[str]`
- Produces: `canonical_event_bytes(event: dict) -> bytes`
- Produces: `semantic_event_bytes(event: dict) -> bytes` (excludes store-owned `recorded_at`)
- Produces: `append_event(ledger: Path, event: dict, evidence: dict | None, evidence_dir: Path) -> AppendResult`
- Produces: `read_events(ledger: Path) -> list[dict]`
- Produces CLI: `capafy_event_store.py validate|append|read --ledger PATH [--evidence-dir PATH]`
- `AppendResult` fields: `event_id: str`, `appended: bool`, `ledger_count: int`, `evidence_path: str | None`

- [ ] **Step 1: Write failing schema-validation tests**

Add fixtures that use exact public evidence and all six decimal money fields:

```python
VALID = {
    "schema_version": 1,
    "event_id": "capafy:content.published:instagram:DbgsvEbo5kd",
    "event_type": "content.published",
    "occurred_at": "2026-08-01T20:32:53Z",
    "recorded_at": "2026-08-01T20:32:54Z",
    "loop": "marketer",
    "entity": {"type": "content", "id": "instagram:DbgsvEbo5kd"},
    "correlation_id": "capafy-marketer-20260801T164641Z-4e195cd6",
    "summary": "Published and owner-verified an Instagram Reel.",
    "status": {"before": "publish_probe_ready", "after": "reach_observing"},
    "money": {name: "0.00" for name in (
        "gross_delta", "pending_delta", "realized_delta", "mrr_delta",
        "cost_delta", "contribution_delta"
    )} | {"currency": "USD"},
    "metrics": {},
    "public_evidence": {
        "urls": ["https://www.instagram.com/reel/DbgsvEbo5kd/"],
        "labels": ["post-write owner session verified"],
    },
    "technical_evidence_ref": "capafy:content.published:instagram:DbgsvEbo5kd",
    "source": {
        "producer": "capafy-marketing-handoff",
        "source_id": "marketing-published:DbgsvEbo5kd",
        "source_digest": "sha256:" + "a" * 64,
    },
    "next": {"owner": "marketer", "retry_at": None},
}
```

Assert rejection of a missing `event_id`, unsupported event type, HTTP URL, absolute local path anywhere in the public event, a money value `"9.9"`, negative metrics, and an invalid timestamp.

- [ ] **Step 2: Run the validation tests and verify RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_event_store.py -k validation
```

Expected: collection fails because `capafy_event_store` does not exist.

- [ ] **Step 3: Implement the event model and validator**

Use a fixed set of machine event types from the design, `Decimal` quantization for two-digit money, `datetime.fromisoformat` for timestamps, `urlparse` for HTTPS evidence, recursive string-value inspection to reject values beginning with `/Users/`, `/private/`, `~`, or `file:`, and recursive key inspection to reject credential-bearing keys such as `password`, `token`, `secret`, `cookie`, and `authorization`. This is fixed-format safety validation, not business judgment.

The JSON Schema mirrors the Python contract and sets `additionalProperties: false` at every fixed object boundary while allowing event-specific `metrics` keys from:

```json
["impressions", "views", "clicks", "likes", "comments", "orders"]
```

- [ ] **Step 4: Write failing append/idempotency/durability tests**

Cover:

```python
def test_identical_retry_is_a_noop(tmp_path): ...
def test_same_id_with_different_payload_is_a_conflict(tmp_path): ...
def test_concurrent_writers_append_one_line(tmp_path): ...
def test_truncated_tail_refuses_new_append(tmp_path): ...
def test_private_sidecar_is_mode_0600_and_not_embedded(tmp_path): ...
```

Use `multiprocessing` for the concurrency test and verify exactly one compact JSON line exists.

- [ ] **Step 5: Run append tests and verify RED**

Run the full Task 1 test file. Expected: validator tests pass and append tests fail because storage behavior is missing.

- [ ] **Step 6: Implement locked append and CLI**

Use `fcntl.flock(LOCK_EX)` on `ledger.with_suffix(".lock")`, parse and validate every existing non-empty line while locked, and compare semantic event bytes with store-owned `recorded_at` excluded. Adapters omit `recorded_at`; the store stamps it once for a new event, while a retry carrying a different `recorded_at` remains identical when every semantic field matches. Append through `os.open(..., O_APPEND|O_CREAT|O_WRONLY, 0o600)`, then flush and `os.fsync`. Write sidecars through temporary-file plus `os.replace`, followed by `chmod(0o600)`.

CLI `append` reads one event object from stdin and optionally one technical-evidence object from `CAPAFY_EVENT_EVIDENCE_JSON`; it prints only the serialized `AppendResult`.

- [ ] **Step 7: Run Task 1 and P0/P1 regression tests**

```bash
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_event_store.py \
  skills/earn/capafy-marketing/tests/test_capafy_outcome.py \
  skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py
git diff --check
```

Expected: all pass with no diff errors.

- [ ] **Step 8: Update the living spec and commit**

Record RED/GREEN counts and the event-store contract under a new P2 execution log, then commit:

```bash
git add skills/earn/capafy-marketing/schemas/capafy-revenue-event.schema.json \
  skills/earn/capafy-marketing/scripts/capafy_event_store.py \
  skills/earn/capafy-marketing/tests/test_capafy_event_store.py \
  docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md
git commit -m "feat(capafy): add canonical revenue event store"
```

---

### Task 2: Verified outcome and lifecycle adapters

**Files:**
- Create: `skills/earn/capafy-marketing/scripts/capafy_event_adapters.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_event_adapters.py`
- Modify: `skills/self/capafy-loop/capafy-builder-handoff.sh`
- Modify: `skills/earn/capafy-marketing/capafy-marketing-handoff.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Consumes: Task 1 `append_event`
- Produces: `events_from_outcome(outcome: dict, correlation_id: str | None) -> list[dict]`
- Produces: `events_from_lifecycle(before: dict, after: dict) -> list[dict]`
- Produces CLI: `capafy_event_adapters.py append-outcome|append-lifecycle --ledger PATH`

- [ ] **Step 1: Write failing adapter tests**

Fixtures and expected event identifiers:

```text
builder_submitted -> capafy:listing.submitted:9480246345:status-1
marketing_published -> capafy:content.published:instagram:DbgsvEbo5kd
marketing_published owner proof -> capafy:account.post_verified:capafy.skills8m4q2z:DbgsvEbo5kd
account_created -> capafy:account.created:capafy.skills8m4q2z
account_created session -> capafy:account.session_ready:capafy.skills8m4q2z
account_created capability -> capafy:account.publish_probe_ready:capafy.skills8m4q2z
```

Assert that `marketing_dry`, `builder_noop`, a missing owner proof, or a non-HTTPS URL never emits a success event.

- [ ] **Step 2: Run adapter tests and verify RED**

Expected: import failure for `capafy_event_adapters`.

- [ ] **Step 3: Implement pure adapters and append CLI**

Build event identifiers from verified immutable fields. Source digests are SHA-256 of canonical source envelopes. Technical evidence contains the full source envelope and evidence directory; the public event contains only safe URLs and labels.

- [ ] **Step 4: Write failing handoff integration tests**

Extend fake outcomes so each successful Builder/Marketer/account envelope writes the expected event before Telegram. Assert:

- sender retry does not add a second event;
- event append failure sends no success Telegram and returns nonzero;
- a recovered terminal can deliver Telegram from the already-appended event;
- a Marketer failure or challenge emits no `content.published` event.

- [ ] **Step 5: Run handoff tests and verify RED**

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
```

Expected: new ledger assertions fail.

- [ ] **Step 6: Wire Builder and Marketer handoffs**

Add environment seams:

```bash
EVENT_ADAPTER="${CAPAFY_EVENT_ADAPTER:-$HERE/scripts/capafy_event_adapters.py}"
EVENT_LEDGER="${CAPAFY_EVENT_LEDGER:-$STATE/capafy-revenue-events.jsonl}"
EVENT_EVIDENCE_DIR="${CAPAFY_EVENT_EVIDENCE_DIR:-$STATE/capafy-revenue-evidence}"
```

Builder resolves the Marketer script path through `../../earn/capafy-marketing/scripts`. Append the verified envelope before `send_with_receipt`/`send_receipt`; duplicate append is success. Account-created envelopes emit all three lifecycle events in one adapter call.

- [ ] **Step 7: Run adapter/handoff/full P1 regressions**

Run adapter pytest, Builder handoff tests, Marketer outcome/controller tests, account manager tests, and `bash -n` on modified scripts.

- [ ] **Step 8: Update spec and commit**

```bash
git commit -m "feat(capafy): emit verified outcome events"
```

---

### Task 3: Sales, payout, cost, attribution, and metric writers

**Files:**
- Create: `skills/earn/capafy-marketing/scripts/capafy_event_sync.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_event_sync.py`
- Modify: `skills/self/capafy-loop/capafy_earn_reconcile.py`
- Modify: `skills/earn/capafy-marketing/scripts/pull_attribution.py`
- Modify: `skills/earn/capafy-marketing/scripts/ig_metrics.py`
- Modify: `skills/self/capafy-loop/loop.sh`
- Create: `skills/self/capafy-loop/tests/test_capafy_earn_reconcile.py`
- Create: `skills/earn/capafy-marketing/tests/test_ig_metrics.py`
- Modify: `skills/earn/capafy-marketing/tests/test_pull_attribution.py`
- Modify: `skills/earn/capafy-marketing/tests/test_build_landing.py`
- Modify: `skills/self/capafy-loop/test-loop.sh`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Consumes: Task 1 store and Task 2 event builders
- Produces: `events_from_sales_rows(rows: list[dict]) -> list[dict]`
- Produces: `events_from_payout_rows(rows: list[dict]) -> list[dict]`
- Produces: `events_from_cost_rows(rows: list[dict]) -> list[dict]`
- Produces: `events_from_attribution_rows(rows: list[dict], verification_clicks: dict[str, int]) -> list[dict]`
- Produces: `events_from_ig_metrics(rows: list[dict]) -> list[dict]`
- Produces CLI: `capafy_event_sync.py sync-money|sync-attribution|sync-metrics|sync-all`

- [ ] **Step 1: Write failing money adapter tests**

Verify the production fixture maps to:

```text
order.received: gross_delta=9.99, orders=1, contribution_delta=0.00
balance.reconciled: pending_delta=8.00, contribution_delta=0.00
payout.received: only a positive total_payout delta; realized_delta equals contribution_delta
cost.measured: cost_delta=4.78 and contribution_delta=-4.78 across immutable usage deltas; the private sidecar retains the exact source value `4.776955221`, while public parity compares the specified two-decimal projection
```

Assert repeated mutable cumulative totals do not double-count and an older snapshot cannot move money backwards without a refund/correction source event.

- [ ] **Step 2: Write failing metric adapter tests**

For agent `4866150011`, subtract the two recorded deployment-verification clicks before emitting organic clicks. Assert negative organic counts clamp to zero with a public label that verification traffic was excluded, and subsequent metric snapshots replace rather than add cumulative values.

- [ ] **Step 3: Run sync tests and verify RED**

Expected: import failure for the sync module.

- [ ] **Step 4: Implement source readers and event builders**

Source record identities use canonical source digests and stable dates/shortcodes. The sync CLI accepts explicit fixture paths for tests and defaults to the production files only when paths are omitted. It prints counts for `observed`, `appended`, `duplicates`, and `conflicts` by source.

- [ ] **Step 5: Add direct producer hooks**

- `capafy_earn_reconcile.py` invokes `sync-money` after its atomic source-ledger write.
- `pull_attribution.py` invokes `sync-attribution` after its dated row append.
- `ig_metrics.py` invokes `sync-metrics` after its snapshot append.
- `loop.sh` invokes `sync-money` after cost/sales reconciliation so cost events do not wait for the daily report.

Each producer has `CAPAFY_EVENT_SYNC` and `CAPAFY_EVENT_LEDGER` test seams. A sync failure makes the producer terminal nonzero but does not rewrite or delete source evidence.

- [ ] **Step 6: Run producer, sync, and legacy ledger tests**

Run `test_capafy_event_sync.py`, `test_capafy_earn_reconcile.py`, `test_ig_metrics.py`, `test_pull_attribution.py`, the direct-hook assertions in `test_build_landing.py`, and `skills/self/capafy-loop/test-loop.sh`.

- [ ] **Step 7: Update spec and commit**

```bash
git commit -m "feat(capafy): join money and marketing metrics"
```

---

### Task 4: Incident phase events and verified repair closure

**Files:**
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_event_adapters.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh`
- Modify: `skills/self/tests/test_capafy_builder_outcome.sh`
- Modify: `skills/self/tests/test_verify_loops_audit_capafy_cap_full.sh`
- Modify: `skills/self/tests/test_verify_loops_audit_capafy_label_mismatch.sh`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Produces: `event_from_incident(record: dict) -> dict`
- `transition_incident(update: dict, event_writer: Callable | None = None) -> dict` writes the incident record first, then the idempotent canonical phase event.

- [ ] **Step 1: Write failing phase-mapping tests**

For incident `capafy-marketer-20260801T201313Z-6b646dbe`, assert exact identifiers:

```text
capafy:incident.detected:capafy-marketer-20260801T201313Z-6b646dbe
capafy:incident.repair_started:capafy-marketer-20260801T201313Z-6b646dbe
capafy:incident.repaired:capafy-marketer-20260801T201313Z-6b646dbe
capafy:incident.verified:capafy-marketer-20260801T201313Z-6b646dbe
```

`unresolved` maps similarly and includes next owner/retry. `verified` requires a concrete `verification` object.

- [ ] **Step 2: Run tests and verify RED**

Expected: incident event mapping is absent.

- [ ] **Step 3: Implement transition event emission**

Keep `capafy_outcome.py` outcome validation/render functions pure. Inject the writer into `transition_incident`; the CLI supplies the production writer unless `CAPAFY_EVENT_WRITE_DISABLED=1`. If state write succeeds and event append fails, return nonzero; retrying the same phase is legal and completes the missing event without moving state backwards.

- [ ] **Step 4: Add failure/closure integration tests**

Seed a failed event append, retry the incident phase, then verify the canonical event exists exactly once and Telegram closure is sent exactly once only after `incident.verified` evidence.

- [ ] **Step 5: Run incident and P0 self-heal regressions**

Run outcome pytest, outcome monitor shell, Builder outcome shell, both Capafy verify-loop audit shells, goal monitor tests, and syntax checks.

- [ ] **Step 6: Update spec and commit**

```bash
git commit -m "feat(capafy): trace repair phases in revenue ledger"
```

---

### Task 5: Deterministic company projection and Telegram parity

**Files:**
- Create: `skills/earn/capafy-marketing/scripts/capafy_event_projection.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_event_projection.py`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/capafy-goal-monitor.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Produces: `project_company(events: list[dict]) -> dict`
- Produces: `projection_id(events: list[dict], projection: dict) -> str`
- Produces CLI: `capafy_event_projection.py project --ledger PATH`
- Projection fields: `schema_version`, `kind`, `as_of`, `last_event_id`, `projection_id`, `inventory`, all six money totals, `orders`, `account`, `marketing`, `metrics`, `incident`, `listing_url`, `dashboard_url`.

- [ ] **Step 1: Write failing projection tests**

Cover ordered folding, duplicate protection, daily aggregate orders, gross/pending/realized/cost/contribution separation, latest entity metric replacement, current account/Reel state, active versus verified incidents, deterministic projection identifiers, and different identifier after one new event.

- [ ] **Step 2: Run projection tests and verify RED**

Expected: import failure.

- [ ] **Step 3: Implement the projection**

Fold only validated events in ledger order. Inventory is the latest event per listing entity. Metrics are the latest `content.measured` snapshot per content entity. Money is summed with `Decimal` and serialized to two digits. The projection identifier is a SHA-256 of ordered event identifiers plus the public projection before adding the identifier.

- [ ] **Step 4: Write failing Telegram parity tests**

Render a fixture projection through `capafy_outcome.py render` and assert every money value, public URL, account state, active incident, and short projection identifier appears exactly as represented by the projection. Seed a contradictory legacy terminal and assert it is ignored after the parity gate switches to ledger mode.

- [ ] **Step 5: Migrate the goal monitor behind a parity gate**

Add:

```bash
EVENT_LEDGER="${CAPAFY_EVENT_LEDGER:-$HOME/.openclaw/state/capafy-revenue-events.jsonl}"
PROJECTION="${CAPAFY_EVENT_PROJECTION:-$SCRIPT_DIR/scripts/capafy_event_projection.py}"
```

The monitor runs `sync-all`, projects the ledger, compares it with independently read money/account/content/incident values, and refuses Telegram/dashboard publication on mismatch. After parity passes, the projected object becomes the only Telegram input.

- [ ] **Step 6: Run projection, renderer, and goal-monitor suites**

Expected: all pass; seeded mismatch exits nonzero and creates an incident rather than sending a contradictory report.

- [ ] **Step 7: Update spec and commit**

```bash
git commit -m "feat(capafy): render Telegram from event projection"
```

---

### Task 6: Public company dashboard from the same projection

**Files:**
- Create: `skills/earn/capafy-marketing/scripts/build_company_dashboard.py`
- Create: `skills/earn/capafy-marketing/tests/test_build_company_dashboard.py`
- Generate at runtime, do not hand-edit: `skills/earn/capafy-marketing/site/company/index.html`
- Generate at runtime, do not hand-edit: `skills/earn/capafy-marketing/site/company/state.json`
- Modify: `skills/earn/capafy-marketing/netlify.toml`
- Modify: `skills/earn/capafy-marketing/capafy-goal-monitor.sh`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Consumes: Task 5 projection JSON on stdin or `--projection PATH`
- Produces CLI: `build_company_dashboard.py --projection PATH --output-dir PATH`
- Produces public `index.html` and byte-stable `state.json` with the same `projection_id`.

- [ ] **Step 1: Write failing dashboard tests**

Assert deterministic output, escaped titles, real clickable Reel/listing URLs, separate money labels, lifecycle/incident visibility, projection identifier parity, no absolute paths, no credential keys, no technical evidence, and unchanged root landing output.

- [ ] **Step 2: Run dashboard tests and verify RED**

Expected: generator import failure.

- [ ] **Step 3: Implement dependency-free dashboard generation**

Use `html.escape`, embedded CSS, semantic HTML, and no client-side dependencies. `state.json` is the exact public projection. Dashboard generation writes a temporary directory and atomically replaces only the two files inside `site/company`; it never rewrites `site/index.html` or `allowed-agents.json`.

- [ ] **Step 4: Wire generation after projection**

Goal monitor generates the dashboard before Telegram and records the local dashboard projection identifier. A generation failure starts/resumes an incident and leaves the previous dashboard visibly stale.

- [ ] **Step 5: Run all dashboard/parity tests and Netlify build**

```bash
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_build_company_dashboard.py \
  skills/earn/capafy-marketing/tests/test_capafy_event_projection.py \
  skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
cd skills/earn/capafy-marketing && npm ci && netlify build --site 41c8e52e-b163-442a-84ff-fd866269bf6c
```

- [ ] **Step 6: Update spec and commit**

```bash
git commit -m "feat(capafy): publish event-backed company dashboard"
```

---

### Task 7: Production backfill, deployment, self-heal proof, and P2 closure

**Files:**
- Modify: `skills/earn/capafy-marketing/scripts/capafy_event_sync.py`
- Create: `skills/earn/capafy-marketing/tests/test_capafy_p2_production_contract.py`
- Modify: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`
- Modify: `docs/superpowers/plans/2026-08-02-capafy-p2-shared-revenue-ledger.md` checkbox status while executing

**Interfaces:**
- Consumes all P2 components and production source paths.
- Produces production ledger, private sidecars, public dashboard, Telegram projection, and verification artifact `~/.openclaw/state/capafy-p2-verification.json`.

- [ ] **Step 1: Write the production-contract test**

The test accepts explicit fixture paths and proves:

- one clean backfill creates expected Builder, Marketer, account, order, balance, cost, metric, and incident events;
- a second backfill appends zero events;
- projection matches the known one order / $9.99 gross / $8.00 pending / $0 realized / current recorded cost / real Reel / no active Marketer incident state;
- dashboard and Telegram render the same identifier;
- private evidence is absent from public output.

- [ ] **Step 2: Run the complete offline P0-P2 suite**

```bash
python3 -m pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_event_store.py \
  skills/earn/capafy-marketing/tests/test_capafy_event_adapters.py \
  skills/earn/capafy-marketing/tests/test_capafy_event_sync.py \
  skills/earn/capafy-marketing/tests/test_capafy_event_projection.py \
  skills/earn/capafy-marketing/tests/test_build_company_dashboard.py \
  skills/earn/capafy-marketing/tests/test_capafy_p2_production_contract.py \
  skills/earn/capafy-marketing/tests/test_capafy_outcome.py \
  skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py \
  skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
bash skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh
bash skills/self/tests/test_capafy_ig_account_state.sh
git diff --check
```

- [ ] **Step 3: Backfill production twice**

Run `sync-all` against the real sources with an initially absent canonical ledger. Capture first-run counts and SHA-256, rerun, and require `appended=0` with unchanged ledger SHA-256 on the second pass.

- [ ] **Step 4: Verify local projection parity before switching**

Compare every inventory, order, gross, pending, realized, MRR, cost, contribution, account, Reel, and incident field with independent source reads. Stop and repair on any mismatch.

- [ ] **Step 5: Kickstart goal monitor and verify exactly-once Telegram**

Record the Telegram message identifier and body. It must contain natural language, the real Reel/listing/dashboard URLs, all separated money values, no local path, and the same short projection identifier as the local projection.

- [ ] **Step 6: Deploy the existing Capafy Netlify site explicitly**

```bash
cd skills/earn/capafy-marketing
npm ci
netlify deploy --prod \
  --site 41c8e52e-b163-442a-84ff-fd866269bf6c \
  --skip-functions-cache \
  --message "Publish Capafy event-backed company dashboard" \
  --json
```

Do not use the repository root's unrelated linked Netlify project.

- [ ] **Step 7: Verify public dashboard parity**

Require HTTP 200 from `/company/` and `/company/state.json`; compare remote `projection_id` and every business value with the local projection. Recheck `/go/4866150011` UTM preservation and the existing Reel/listing HTTP status.

- [ ] **Step 8: Seed and close one writer incident**

Using isolated fixture state and the normal outcome monitor, force one canonical append failure, verify `incident.detected` and `incident.repair_started`, repair the tail, retry the original append, and require `incident.repaired` then `incident.verified`. No production Reel, listing, sale, or Telegram success is repeated.

- [ ] **Step 9: Update living spec and commit P2 closure**

Change the parent spec status to `P0-P2 verified; P3 active`, add exact test counts, event counts, ledger digest, production projection identifier, Telegram ID, Netlify deploy ID, URLs, and seeded self-heal incident chain.

```bash
git commit -m "docs(capafy): verify shared revenue ledger in production"
```

- [ ] **Step 10: Run verification-before-completion audit**

Re-run the full commands from Step 2 and all runtime checks from Steps 3-8. P2 is complete only if every item in the P2 design's ten-point verification strategy has direct current evidence.
