# Lancers G2 Truthful Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Implement this single task in the existing isolated worktree. The primary owns spec/plan, production deployment, and final verification.

**Goal:** Replace the misleading mutable 5-minute Lancers reporter with one canonical, deduplicated owner report that truthfully separates acquisition funnel stages, pending/verified receipts, storefront lifecycle states, timestamps, blockers, and unknown actual cost.

**Architecture:** Keep the existing `ai.anicca.lancers-revenue-telegram-report` launchd topology and existing `telegram.sqlite3`. Build one bounded read-only report tick in the exact-main release. It reads the canonical application output/state/ledger plus official storefront counts under the existing account lock, renders one deterministic Japanese snapshot, enqueues by JST day plus semantic-state hash, and uses the existing at-most-once outbox contract. The legacy mutable reporter remains disabled until exact-SHA deployment passes.

**Tech Stack:** Python stdlib, existing Playwright/CDP boundary, SQLite outbox, launchd, unittest.

---

## Global constraints

- Ponytail full: no new DB, service, schema, crawler, envelope framework, agent call, or report abstraction.
- Root does not write production/test code. Luna owns implementation. One fresh Sol adversarial review maximum.
- TDD RED must be observed before production edits.
- Do not modify application state, marketplace ledger, listing state, browser session, or secrets.
- Do not enable the reporter during implementation. Primary alone deploys and enables after review.
- Preserve the acquisition scheduler enabled at 30 minutes and at most one application per tick.
- Do not replay or retry the 34 existing `delivery_uncertain` rows.

## File map and size budget

| File | Responsibility | Budget |
|---|---|---:|
| `skills/earn/lancers/scripts/telegram_report.py` | bounded snapshot, render, daily/state-change key, official storefront reader under account lock, enqueue/deliver, CLI | <=320 handwritten production LOC |
| `skills/_shared/marketplace-core/scripts/telegram_outbox.py` | copy the currently deployed byte-compatible durable outbox; no redesign | existing 312 LOC snapshot |
| `apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-telegram-report.plist` | existing label, 300s interval, exact release arguments, no `RunAtLoad` | <=25 LOC |
| `apps/lancers-revenue/scripts/install-local.sh` | include reporter/outbox and atomically render both plists from exact SHA | <=30 changed LOC |
| `apps/lancers-revenue/tests/test_telegram_report.py` | one focused RED/GREEN behavioral suite | <=170 LOC |
| `apps/lancers-revenue/tests/test_install_local.py` | reporter exact-release/manifest/plist regression | <=30 changed LOC |

If the reporter exceeds 320 LOC or needs another production file, stop and return `NEEDS_CONTEXT`; do not hide expansion in helpers. The original 180 LOC estimate was superseded after RED measured 265 LOC before the required official storefront reader/account lock existed. This revised ceiling is still 72% smaller than importing the 1,161-line legacy reporter/observability pair.

## Task 1: Canonical truthful report tick and exact-SHA deployment

**Files owned by implementer:** all six files in the table above and no others. The implementer must not edit the spec or this plan.

### Step 1: Write focused failing tests

Create `test_telegram_report.py` with direct imports and injected boundaries. Prove these behaviors:

1. Acquisition input `{observed_count:13, eligible_count:1, submitted:false, verified_count:0, error:"submission_uncertain"}`, pending 1, cumulative verified 14 renders observed 13 / qualified 1 / submitted 0 / newly verified 0 / pending 1 / cumulative verified 14 / blocker `submission_uncertain`.
2. Normal `{observed_count:13, eligible_count:0, submitted:false, verified_count:0, reason:"no_eligible_project"}`, pending 0 renders blocker none. It must not infer revenue from 14 receipts.
3. Storefront counts remain four separate fields. A mismatch produces `⚠️`, contains受付中/受付休止中/非表示/下書き, and never contains `未処理` or `✅`.
4. `source_observed_at`, `official_readback_observed_at`, and provider event time unknown are separately labeled. Reporter slot/file mtime is never called an official timestamp.
5. Actual AI cost is `unknown (meter未接続)` and no projected qualification cost is rendered as actual.
6. Two identical semantic snapshots on the same JST day enqueue once; a changed pending/blocker snapshot enqueues once more; the same unchanged snapshot on the next JST day enqueues once.
7. Delivery marks success only with a positive provider message ID. A possibly-started send without ID becomes `delivery_uncertain` and is not reclaimed.
8. Malformed/missing source produces `⚠️` with unknown fields and never a success icon or fabricated zero.

Extend installer RED to require both canonical reporter files in the 15-file manifest and require the reporter plist to point inside `releases/<SHA>`, use `--json`, `StartInterval=300`, omit `RunAtLoad`, and preserve the application plist behavior.

Run the focused tests and record the expected missing-file/old-installer failures.

### Step 2: Implement the minimum GREEN

- Copy deployed `telegram_outbox.py` byte-for-byte into canonical shared source; do not refactor it.
- Implement one `telegram_report.py`. Reuse `application_tick` only for CDP/account-lock/browser primitives and `ledger.py` for event reads. Read the last valid JSON object from the application stdout log; ignore malformed trailing lines and fail unknown if no valid object exists.
- Parse `application.json` strictly enough to count pending without changing it. Count cumulative verified applications from ledger and use the latest application receipt observation timestamp as `official_readback_observed_at`.
- Under the account lock, parse exactly the four official `/myplan` lifecycle anchor counts. Read the last valid storefront stdout JSON only for its latest `error`; do not total lifecycle states as work or backlog.
- Render a single Japanese owner snapshot. Use `✅` only when required sources are readable and no blocker/mismatch exists; otherwise `⚠️`.
- Compute semantic hash without observation timestamps. Enqueue key `lancers:g2:<JST date>:<sha256>` in the existing database. Repeated exact key/message is a no-op.
- Reuse the deployed outbox state machine. Notifier calls the existing `openclaw message send` contract and accepts only a nonempty provider message ID. No provider ID after attempted send is quarantined; no blind retry.
- CLI emits one JSON result containing only booleans/counts/error codes, never report text, credential, buyer text, or token.
- Extend installer archive/manifest and atomically render the existing reporter label to the exact release. Installer must never enable/bootstrap/kick either job.

### Step 3: Verify and commit

Run:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py apps/lancers-revenue/tests/test_lancers_status.py apps/lancers-revenue/tests/test_install_local.py apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test*.py'
python3 -m py_compile skills/earn/lancers/scripts/telegram_report.py skills/_shared/marketplace-core/scripts/telegram_outbox.py
git diff --check
```

Also assert live application/state/ledger/listing hashes and both launchd enable states are unchanged during tests. Commit and push only `origin/feat/lancers-g2-reporting`. Write a report with RED evidence, GREEN totals, SHA, diffstat, and any concern.

## Primary acceptance after implementation

1. Dispatch exactly one fresh Sol adversarial verifier. It must try to falsify source truth, dedupe, success icon, timestamp labeling, delivery quarantine, exact-SHA deployment, and secret safety. No second reviewer.
2. If FIX_FIRST, return only concrete findings to the same Luna once, then mechanically reverify without another review.
3. Merge/push clean canonical main, install exact SHA while reporter remains disabled, verify manifest and both plist paths.
4. Run report tick once with notifier interception to inspect the real snapshot without sending; require current values: application receipts 14, pending 0, separate storefront states, mismatch warning, actual cost unknown.
5. Announce the external report, enable/bootstrap/kick the existing reporter owner once, require a positive Telegram message ID, then leave it enabled at 300 seconds. Repeated unchanged kick must enqueue/send zero.
6. Verify application scheduler remains enabled, state/ledger/listing hashes unchanged, update SSOT, commit/push, and remove the G2 worktree only after deployment verification.

## Completion record

- Primary-owned spec/plan and Luna-owned production/test boundary held. Luna did not edit this plan or the design spec.
- Fresh Sol adversarial review: 1/1. Three HIGH findings were returned once to the same Luna; no second review ran.
- Canonical main and deployed exact release: `d63dfd1ad38458e0e5cb076cd9563df5b374bd72`.
- Primary verification: focused reporter 12, combined Lancers 30, agent-runner 15, compile and diff check pass; reporter is exactly 320 LOC.
- Real intercepted snapshot: observed 13, qualified 0, submitted 0, newly verified 0, pending 0, cumulative verified 14, storefront 6/0/0/0, warning `listing_readback_mismatch`, revenue and actual AI cost unknown.
- Live delivery: one event delivered with Telegram provider message ID `15922`; immediate unchanged kick produced `enqueued=0`, `attempted=0`, `delivered=0`.
- Final scheduler state: reporter enabled at 300 seconds and application enabled at 1800 seconds; both point to the same exact release. Existing 34 `delivery_uncertain` rows were not retried.
