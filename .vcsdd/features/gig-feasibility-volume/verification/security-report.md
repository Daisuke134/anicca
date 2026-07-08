# Security Hardening Report

## Feature: gig-feasibility-volume | Phase 5 (lean) | Date: 2026-07-08

## Tooling

| Tool | Status | Notes |
|---|---|---|
| `shellcheck` (0.11.0) | available, used | `-S warning` against `gig-cli.sh`, `run.sh`, `monitor.sh`, `gig-healthcheck.sh`, `auditor.sh`, `cadence-deadline-check.sh` — 0 findings, exit 0 |
| `bash -n` | available, used | syntax check on `gig-cli.sh` |
| `semgrep` | not checked/not installed in this environment; degraded to manual grep + shellcheck + hand-written adversarial python/bash probes (lean mode, no new installs per task constraint) |
| Wycheproof | **not applicable** — this feature has zero cryptographic primitives (no signing, hashing-for-security, key derivation, or crypto-adjacent code in the scope-locked file set) |
| pip/npm SAST | not installed, not added (task forbids new installs) |

All raw probe commands + their real stdout/stderr are captured under
`verification/security-results/gig-security-probe-2026-07-08-verifier-session2.txt` (this session) and
the pre-existing `verification/security-results/gig-security-probe.txt` (an earlier, lighter pass —
retained, superseded in depth by this session's file).

## (a) Shell injection / STARTUP prompt safety

`gig-cli.sh`'s `STARTUP` variable is a single-quoted bash string (14,324 chars) passed as ONE argv
element to the `claude` CLI via `tmux new-session ... "$CLAUDE" ... -- "$STARTUP"`. Verified directly
this session (not merely inspected) by extracting the exact assignment line and reproducing the
tmux/claude argv construction in an isolated bash subshell: the resulting `test_argv` call reports
`ARGC=10`, with the final argument (`$STARTUP`) arriving as a single 14,324-character argv element —
proving no word-splitting and no premature quote-termination occurs, i.e. the giant prose body
(containing embedded double-quotes, backticks-as-prose, `$(...)`-looking text, etc., all as inert
prose describing what the AGENT should later type) never breaks out of its single-quoted shell
boundary. `shellcheck -S warning` independently confirms zero findings against the whole file.
`bash -n` confirms syntax validity.

The prompt text itself instructs the agent to use `jq --arg` binding (not string-interpolated jq
filters) for `requestId` lookups (`jq -c --arg x "$(printf %s "$requestId")" "select(.requestId ==
\$x)"`) — the injection-safe jq idiom — and to always write `requestId` as a quoted JSON string via
`printf %s`, never raw numeric. `requestId` itself is Coconala-platform-assigned (not directly
attacker-free-text), lowering this surface's realistic risk further.

## (b) Path handling / traversal

- `cadence-evidence.py`'s gig-specific paths are resolved exclusively via env-seam functions
  (`_gig_applied_path()`/`_gig_listings_path()`) using `os.environ.get(...) or os.path.expanduser(...)`
  — no string concatenation of untrusted input into a path.
- `funnel_report.py`'s `--applied-path`/`--listings-path`/`--out-path` are local CLI args supplied
  only by the trusted STARTUP prompt (a fixed, hardcoded absolute path,
  `~/gig/listings.jsonl`) — there is no network-facing or otherwise untrusted caller of this script,
  so classic path-traversal (attacker-supplied `../../`) is not a realistic threat model for this
  local, single-operator tool. Probed anyway (session evidence, item 5): a `../../`-laden `--out-path`
  simply resolves as ordinary relative-path navigation (expected `os.makedirs` behavior for a local
  CLI, not a vulnerability). A `category` field containing shell-metacharacters and path-traversal-
  looking text (`"../../etc/passwd; rm -rf ~"`) was fed through the real `funnel_report.run()` code
  path and confirmed to flow through purely as an inert JSON dict key — no shell execution, no path
  interpretation, no crash.
- Broken-path references (`~/anicca/skills/human-funded/gig/`, non-existent on disk) are fully
  corrected: 0 occurrences remain in `gig-cli.sh`, both replacement paths present (PROP-033, confirmed
  by grep this session).
- Minor non-attacker-reachable robustness gap found: `funnel_report.py --out-path <bare-filename>`
  (no directory component) raises an uncaught `FileNotFoundError`. See verification-report.md's minor
  robustness note. Not exploitable (no untrusted caller supplies this arg).

## (c) Secrets

`grep -rn "API_KEY|SECRET|TOKEN|PASSWORD"` across every scope-locked `.py`/`.sh`/`.json` file returns
exactly one hit: the STARTUP prompt referencing `AGENTMAIL_API_KEY` **by name only**, as an
env-var-presence precondition ("no-ops silently if AGENTMAIL_API_KEY is not set") — never a literal
key value. No hardcoded credentials, tokens, or passwords found anywhere in the diff. `passprep.py`'s
one error-path `print(f"passprep.py ERROR: {exc}", file=sys.stderr)` was checked for secret-bearing
exception messages — the only exceptions this code path can raise are JSON/file/type errors on
non-sensitive ledger data, never a credential.

## (d) Additional adversarial finding (see verification-report.md GAP-1 for full detail)

A non-dict (but syntactically valid JSON) row anywhere in `~/gig/applied.jsonl`/`~/gig/listings.jsonl`
crashes `cadence-evidence.py status gig` with an uncaught `AttributeError`, which
`cadence-deadline-check.sh`'s fallback (`|| echo False`) silently converts into a false-negative
`met:false` — a resilience/availability-adjacent gap (denial of an honest health signal, not a
confidentiality/integrity breach), flagged as **BLOCKING-severity** (recommended pre-Phase-6-adjacent
fix) in verification-report.md because it reproduces exactly the false-negative failure class this
feature's own iteration-2 spec rewrite was designed to close. Not currently triggerable against the
real production ledger (verified 270/270 real rows are dict-shaped).

## Summary

- No shell-injection surface found in `gig-cli.sh` or any scope-locked script (shellcheck clean,
  argv-integrity independently proven, jq `--arg` binding pattern confirmed in the prompt text).
- No path-traversal vulnerability found (no untrusted external path input surface exists in this
  feature's file set; one non-attacker-reachable robustness gap noted).
- No secrets found in code or documented error paths.
- Wycheproof/cryptographic checks: **not applicable** (feature has no cryptographic primitives).
- **1 BLOCKING-severity resilience gap found** (GAP-1, cross-referenced from verification-report.md) —
  a malformed-ledger-row crash in `cadence-evidence.py`'s gig branch silently degrades to a false
  "cadence not met" signal. Recommended fix before this hardening pass is considered fully closed,
  though it does not fail any literal `required:true` PROP acceptance criterion as written.
- 1 low-severity, non-blocking gap (GAP-2, `listing_weekly_target:0` falsy-zero coalescing).
