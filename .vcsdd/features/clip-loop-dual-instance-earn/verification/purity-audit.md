# Purity Boundary Audit — clip-loop-dual-instance-earn (Phase 5)

## Declared Boundaries
Per `specs/verification-architecture.md`: `_instance_paths.sh` is declared PURE (deterministic function of
`ANICCA_INSTANCE`/`EARN_LEDGER`/`HOME`, no I/O, no side effects). All I/O (queue/posted file operations,
CDP/network calls, wallet keygen) lives downstream in `producer.sh`/`run.sh`/`monitor.sh`, which CONSUME
the resolved paths but never re-derive them independently.

## Observed Boundaries
Read `_instance_paths.sh` in full (17 lines): it performs exactly 3 variable assignments
(`ANICCA_INSTANCE="${ANICCA_INSTANCE:-}"`, `_SFX=` conditional string build, 4x `CLIP_*=` string
interpolation) and zero commands, zero file reads/writes, zero network calls, zero subprocess invocation.
The purity claim HOLDS exactly as declared.

Cross-checked all 3 consumer files for the "never re-derive independently" invariant:
- `run.sh:20-23` — sources once, assigns `QUEUE`/`POSTED`/`ACCTS`/`LEDGER` directly from the `CLIP_*` vars.
- `producer.sh:18-19` — sources once, assigns `QUEUE` directly, then `mkdir -p "$QUEUE"` (the first I/O,
  correctly downstream of the pure boundary).
- `monitor.sh:8-10` — sources once, assigns `LEDGER`/`ACCTS` directly.
None of the three files independently reconstruct a path string from `HOME`/`ANICCA_INSTANCE` outside the
sourced file — the single seam holds.

## Summary
Purity boundary as declared in Phase 1b is upheld by the actual implementation with no deviation. No
scope/boundary drift found between spec and code.
