---
feature: gig-run-shim
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — gig-run-shim

## Purity boundary

| Layer | Symbols | Side effects |
|---|---|---|
| PURE — `lib/proactive_observe.py` | `summarize_loops_dir(loops_dir, plist_path, launchctl_print_rc)` → `{installed, last_pass_ts, last_pass_step, build_log_passes}` | none — pure dict/file-stat in / dict out (file stats are read-only) |
| SHELL — `skills/earn/gig/run.sh` (modified) | calls existing gig-cli + reads ~/gig/* + invokes `python3 -m lib.proactive_observe` once, merges its JSON into status output | reads disk; ZERO writes under `~/loops/gig/` |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-S1-back-compat | 1 | true | REQ-S1 (= all existing JSON keys preserved verbatim) |
| PROP-S2-shape | 1 | true | REQ-S2 (= `proactive_loop` object has 4 named keys) |
| PROP-S3-installed-both-checks | 1 | true | REQ-S3 (= disk AND launchctl print, not OR) |
| PROP-S4-core-status-read | 1 | true | REQ-S4 (= ts/step extracted from core-status.json) |
| PROP-S5-pass-count | 1 | true | REQ-S5 (= count of `## ` headers in build_log.md) |
| PROP-I1-no-loops-writes | 1 | true | REQ-I1 (= snapshot-diff of `~/loops/gig/` mtimes before/after) |
| PROP-I2-no-tmux-kill | 1 | true | REQ-I2 (= grep run.sh for `tmux kill` / `--restart` = 0 hits) |
| PROP-I3-pre-migration-graceful | 1 | true | REQ-I3 (= no ~/loops/gig dir → all-false defaults) |
| PROP-D1-no-human-touch | 1 | true | REQ-D1, REQ-D2 (= grep shim + Python helper) |
| PROP-NFR1-time-budget | 0 | false | NFR-1 (= optional smoke test) |
| PROP-E2-malformed-json-no-crash | 1 | true | EDGE-E2 (= synthetic bad JSON → fields null, exit 0) |
| PROP-E5-disk-but-not-loaded | 1 | true | EDGE-E5 (= plist on disk, launchctl rc!=0 → installed=false) |

11 required:true PROPs (lean Tier 0/1). Test plan:
- `__tests__/test_proactive_observe.py` — PURE unit tests (cross-platform).
- `__tests__/test_gig_run_shim_darwin.py` — integration on Darwin (1 test
  exercising the real run.sh end-to-end + JSON parse + mtime snapshot).
- `__tests__/test_gig_run_shim_no_human_touch.py` — static grep.

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + my own live `bash skills/earn/gig/run.sh` against the
  real gig slot (~/gig/ has 23 in-flight applications today), JSON parses
  with `proactive_loop` object present + ~/loops/gig/ mtimes unchanged.
