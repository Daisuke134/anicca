# Security Hardening Report — promote-gate-claude-bin-fix

## Feature: promote-gate-claude-bin-fix | Sprint: 2 | Date: 2026-07-10

## Scope

`skills/earn/self-improve/lib/promote_gate_run.py::_resolve_claude_bin()` (19-line
path-selection function, +17 lines vs the previous 2-line implementation) plus the new
test file `skills/earn/self-improve/tests/test_resolve_claude_bin.py`. No other file in
the repo was modified by this feature (confirmed by two independent fresh-adversary
implementation reviews — see
`.vcsdd/features/promote-gate-claude-bin-fix/reviews/implementation/iteration-2/output/verdict.json`,
`spec_fidelity` dimension: worktree file is main's 332 lines +17 = 349, delta isolated to
lines 93-111).

## Tooling

| Tool | Availability | Result |
|------|--------------|--------|
| Semgrep 1.168.0 (`--config auto`, community registry, 290 rules over python + multilang) | Available (`/opt/homebrew/bin/semgrep`) | 0 findings (0 blocking) across both changed files — raw JSON: `security-results/semgrep-promote_gate_run.json`, human summary: `security-results/semgrep-summary.txt` |
| Wycheproof (cryptographic test vectors) | N/A — not applicable | This change contains no cryptographic code (no hashing, signing, key derivation, or crypto library import). `_resolve_claude_bin()` only touches `shutil.which`, `os.path.isfile`, `os.access`, and a fixed tuple of path strings. |
| `cargo kani` / other Tier 2-3 formal tools | N/A | Not a Rust codebase; also not warranted per `specs/verification-architecture.md`'s Verification Tier Rationale (Tier 1 unit tests, no Tier 2/3 obligations for this feature). |
| `mutmut` (Python mutation testing) | Not run as a separate automated pass | Manual mutation tracing was already performed and recorded during the Phase 3 adversary review (iteration 2, `edge_case_coverage` dimension): `os.X_OK -> os.F_OK/os.R_OK`, `and -> or`, and candidate-list reversal mutations were traced by hand and confirmed caught by the 5-test suite. No automated mutmut run was additionally executed for this hardening pass; the manual trace is treated as sufficient given the function's small size (19 lines) and the Tier 1 rationale. |

## Findings

None. Semgrep returned 0 findings (0 blocking) against both the implementation file and
the test file, run with the full community Python + multilang ruleset (290 rules,
~100% parsed lines, no scan errors).

## Why the risk surface is small

- No subprocess/shell invocation inside `_resolve_claude_bin()` itself (the surrounding
  `_invoke_adversary()`'s `subprocess.run` call sites are unchanged by this feature — see
  `verification-architecture.md`'s Purity Boundary Map and `purity-audit.md` below).
- No untrusted/external input reaches this function — it reads only the process `PATH`
  env var (via `shutil.which`) and a fixed, hardcoded tuple of three candidate path
  strings (`_CLAUDE_BIN_KNOWN_GOOD_PATHS`) that are not user- or network-controlled.
- No new file writes, no new network calls, no new deserialization, no new dynamic code
  execution.
- No wallet keys, `.env`, `.solana-session`, `ledger.mjs`, or spend-cap code is touched
  (explicit out-of-scope per `specs/behavioral-spec.md`).

## Summary

Security hardening sweep: **CLEAN PASS**. Semgrep (0 findings, 290 rules, 2 files) is the
only applicable automated tool for this change; Wycheproof and formal-methods tooling are
explicitly not applicable (no cryptography, no Rust/Kani surface). No blocking or
non-blocking security findings. No follow-up required before Phase 6.
