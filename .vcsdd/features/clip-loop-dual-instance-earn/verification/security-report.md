# Security Hardening Report — clip-loop-dual-instance-earn (Phase 5)

## Tooling
- `shellcheck -S warning` (v0.x, `/opt/homebrew/bin/shellcheck`) run against the 4 WORKER files:
  `_instance_paths.sh`, `run.sh`, `producer.sh`, `monitor.sh`. Raw output captured at
  `verification/security-results/shellcheck-worker-layer.txt`.
- No proof obligations in this feature are marked `required:true` at the Tier-3 (formal/crypto) level —
  REQ-006 (wallet-distinctness, the one requirement with real security weight) is explicitly deferred to
  the follow-on `clip-loop-clawrouter-provision` feature (see behavioral-spec.md "Out of scope"). This
  feature's own attack surface is limited to filesystem path construction from an operator-set env var.

## Findings
- **SC2034 ("appears unused") x4** on `_instance_paths.sh:14-17` (`CLIP_QUEUE`/`CLIP_POSTED`/`CLIP_ACCTS`/
  `CLIP_LEDGER`) — FALSE POSITIVE. shellcheck analyzes one file at a time and cannot see that `run.sh`/
  `producer.sh`/`monitor.sh` `source` this file and consume these exact variable names. Verified by
  re-reading all 3 consumer files: each does `QUEUE="$CLIP_QUEUE"` (or equivalent) immediately after
  `source`. No action needed.
- **SC2010 ("don't use ls | grep")** on `producer.sh:47` — pre-existing code, NOT touched by this feature's
  changes (this feature only edited producer.sh's path-resolution lines 15-19). Style-only, no exploit
  path (the grep pattern is a fixed literal `-v raw`, not attacker-influenced). Out of scope for this
  feature; noted for a future cleanup pass, not blocking.
- **ANICCA_INSTANCE path-injection consideration**: `_instance_paths.sh` builds `_SFX="-${ANICCA_INSTANCE}"`
  and interpolates it directly into filesystem paths. If `ANICCA_INSTANCE` contained `/` or `..`, it could
  in principle escape the intended directory (e.g. `ANICCA_INSTANCE="../../etc"`). Risk assessment: this
  env var is ALWAYS set by a launcher script to a fixed literal instance name (e.g. `clip-cli.sh` sets
  none; a future ClawRouter launcher would hardcode a literal like `clawrouter`), never derived from
  external/user input — it is an internal deployment constant, not a system boundary per this project's
  coding-style convention ("only validate at system boundaries"). No validation added; documented here as
  an explicit, accepted risk-acceptance rather than a silent gap.

## Summary
No blocking security findings. Two shellcheck warnings triaged (one false positive from single-file
analysis, one pre-existing out-of-scope style note). The one theoretical path-injection vector
(`ANICCA_INSTANCE` containing `/`/`..`) is accepted as low-risk because the variable is always
launcher-set to an internal literal, never external input — consistent with this codebase's
validate-at-boundaries convention.
