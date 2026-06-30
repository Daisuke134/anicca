---
feature: gig-run-shim
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — gig-run-shim

## Declared Boundaries

| Layer | Symbols | Side effects |
|---|---|---|
| PURE — `lib/proactive_observe.py` | `summarize_loops_dir(loops_dir, plist_path, launchctl_print_rc=...)` | reads disk only (loops_dir + plist_path stat + core-status.json + build_log.md) |
| SHELL — `skills/earn/gig/run.sh` | calls existing `gig-cli.sh` (= LAYER C, unchanged), reads `~/gig/*.jsonl`, invokes `python3 -m lib.proactive_observe gig ~/loops/gig` once, emits JSON to stdout | reads disk; ZERO writes under `~/loops/gig/`; preserves all pre-shim run.sh semantics |
| CLI seam (`_cli`) | shells out `launchctl print` once for rc capture, prints JSON to stdout | OS service registry (read-only) |

## Observed Boundaries

`summarize_loops_dir` accepts `launchctl_print_rc` as an injected int — the
PURE helper itself never invokes launchctl, making it cross-platform testable.

`run.sh` exits unchanged in failure modes (`|| true` on the observer
subprocess; default empty `{}` on JSON parse failure) so existing
classifier consumers always get a valid status JSON.

## Boundary Deviations

1. `_cli(argv)` shells out to `launchctl print` for rc — semantically I/O,
   confined to the module's CLI seam; the PURE helper it delegates to
   remains side-effect-free.
2. `run.sh` already had `bash gig-cli.sh` invocations pre-shim; the shim
   adds exactly ONE new subprocess (`python3 -m lib.proactive_observe`).

## Summary

PURE layer = 1 helper + 1 module CLI entry. Adversary iter-2 confirmed no
write under ~/loops/gig/ via sentinel-seeded mtime + content invariance +
file-set XOR. INV-1 / INV-4 / INV-P1 all honored by static and dynamic checks.
