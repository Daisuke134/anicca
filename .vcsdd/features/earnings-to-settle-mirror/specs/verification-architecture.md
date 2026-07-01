---
feature: earnings-to-settle-mirror
phase: 1b
mode: lean
generated_at: 2026-07-01
updated: cycle-2 rewrite
---

# Verification Architecture — earnings-to-settle-mirror

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/settle_mirror.py` | `parse_earnings_line(line)` | none |
| PURE — `lib/settle_mirror.py` | `is_settled_row(row)` (status in SETTLED set, jpy > 0) | none |
| PURE — `lib/settle_mirror.py` | `extract_pass_id_or_sentinel(row)` — reads row.pass_id; if absent or not matching `^p-\d+$`, returns `unmatched-requestId-<X>` | none |
| PURE — `lib/settle_mirror.py` | `build_settle_row(pass_id, requestId, jpy, status, ts, slot, earnings_ts)` — top-level pass_id + requestId + earnings_status for dedup | none |
| PURE — `lib/settle_mirror.py` | `settle_row_dedup_key(row)` — returns (requestId, earnings_status) tuple | none |
| I/O SINK — `lib/settle_mirror.py` | `mirror_earnings_to_settle(slot_dir, earnings_path, now_ts) -> dict` | reads earnings.jsonl + settle.jsonl tail (dedup); writes settle.jsonl append + state/settle-mirror-last-run.json + state/settle-mirror-offset.json |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 6 | new `elif picked.category == "settle-mirror"` branch (~10 lines) — invokes mirror in-process; skips enqueue |
| SHELL PATCH (a1) — `skills/earn/gig/gig-cli.sh` STARTUP string | additive `pass_id` inclusion + task-request-map.jsonl append + earnings.jsonl pass_id lookup | disk (write task-request-map.jsonl, write applied.jsonl / earnings.jsonl with new field) |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-R3i-pass-id-direct-read | 1 | true | REQ-R3(ii) — earnings row with `pass_id: "p-123"` → mirror uses `p-123` verbatim (no substring) |
| PROP-R3i-malformed-pass-id-fallback | 1 | true | REQ-R3(ii), EDGE-E4 — earnings row with `pass_id: "not-a-pass-id"` → sentinel |
| PROP-R3i-missing-pass-id-fallback | 1 | true | REQ-R3(ii), EDGE-E6 — pre-(a1) earnings row lacks pass_id → sentinel |
| PROP-R4-no-fabrication | 1 | true | REQ-R4 — grep source for `"p-" + str` etc. = 0 (never constructs a plausible pass_id) |
| PROP-R5-dedup-top-level | 1 | true | REQ-R5 — top-level requestId + earnings_status accessible; dedup skips duplicate |
| PROP-R6-offset-last | 1 | true | REQ-R6 (iv) — offset write LAST; monkeypatched os.replace verifies ordering |
| PROP-M2-dispatcher-invokes | 1 | true | REQ-M2 — integration test: category==settle-mirror invokes in-process, tasks/ untouched, outcome starts with "settle-mirror:new=" |
| PROP-E3-non-settled-ignored | 1 | true | EDGE-E3 — status="applied" → not appended |
| PROP-E3-non-settled-and-zero-jpy-ignored (FIND-2-002 fix — rebound) | 1 | true | EDGE-E3 covers BOTH non-settled status AND zero-jpy after cycle-2 renumbering; the prop tests both branches |
| PROP-E4-malformed-pass-id-fallback (renamed for FIND-2-002 clarity) | 1 | true | EDGE-E4 (row has pass_id but not `^p-\\d+$` → sentinel) |
| PROP-E8-offset-reset | 1 | true | EDGE-E8 |
| PROP-I1-no-tmux-kill | 1 | true | REQ-I1 grep on settle_mirror.py + the (a1) STARTUP diff |
| PROP-I2-no-gig-write | 1 | true | REQ-I2 — SHA-256 of earnings.jsonl before/after + source grep for `open(...earnings...`, `"w"`, `"a"` in settle_mirror.py = 0 write-mode hits |
| PROP-I3-no-human-touch | 1 | true | REQ-I3 grep |
| PROP-I4-no-shell-injection | 1 | true | REQ-I4 grep |
| PROP-L3-restart-deploy-safety | 1 | true | REQ-L3 — test script (or manual runbook) that runs `gig-cli.sh --restart`, waits 30s, verifies `--status` returns ALIVE within window; if not, rollback command is provided |
| PROP-L1iii-exact-jq-match-no-substring (FIND-2-001 fix) | 1 | true | REQ-L1(iii) — grep gig-cli.sh STARTUP diff for `grep '"requestId":` = 0 hits; must find `jq -c ... 'select(.requestId ==` verbatim. Fixture: task-request-map with two entries where requestId "5123" appears as a substring of another entry's ts → jq exact-match returns 1 row not 2 |
| PROP-L1ii-per-apply-not-per-tick (FIND-2-003 fix) | 1 | true | REQ-L1(ii) — inspection of the STARTUP diff shows the map append call inside the per-apply loop body of B2 (i.e., each application appends a row), NOT before/after the B2 loop |
| PROP-integration-full-loop | 1 | true | E2E: seed earnings row WITH `pass_id: "<real-gig-pass-id>"` → invoke mirror → assert settle.jsonl row created with matched pass_id → invoke reconciler → assert roi.jsonl updated with `roi_jpy_realized > 0` |
| PROP-integration-sentinel-path | 1 | true | E2E: seed earnings row WITHOUT pass_id → invoke mirror → assert settle.jsonl row with sentinel → invoke reconciler → assert `.unmatched.jsonl` gains row with `reason: "unknown-pass-id"` |

17 required:true. Tests:
- `__tests__/test_settle_mirror.py` — PURE + I/O unit tests
- `__tests__/test_settle_mirror_integration.py` — dispatcher branch + BOTH full-loop paths (matched pass_id + sentinel path)

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- vcsdd:vcsdd-adversary PASS (fresh context, 5 dims, 0 new findings)
- Live E2E on production gig:
  (1) matched path: seed synthetic earnings row with a real roi.jsonl
      pass_id → mirror + reconciler → verify roi row's realized > 0
  (2) sentinel path: seed synthetic earnings row without pass_id →
      mirror + reconciler → verify `.unmatched.jsonl` gains row
  (3) INV-4: SHA-256 of ~/gig/earnings.jsonl BYTE-IDENTICAL throughout
  (4) INV-1: gig-cli.sh --status = ALIVE (unless the (a1) restart step
      was explicitly executed, which counts as a controlled deploy exception)

## Sprint-5 handoff notes

- Real Coconala 検収 will fire (a1) → earnings.jsonl gets pass_id →
  mirror → settle.jsonl → reconciler → roi.jsonl. This is the M2 gate.
- Pre-(a1) earnings rows (23 already-in-flight applications) will
  route to `.unmatched.jsonl`. Human review determines whether to
  manually reconcile them. Sprint-5 can add a fuzzy time-based match
  or a manual pass_id-request-id map fill-in tool.
</parameter>
