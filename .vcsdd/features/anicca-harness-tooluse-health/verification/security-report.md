# Security Hardening Report

## Feature: anicca-harness-tooluse-health | Sprint: 1 | Date: 2026-07-10

## Scope
Files scanned (the 4 production files this feature introduces + the existing file it modifies):
- `~/anicca/runtime/loop/harness-health.mjs` (pure aggregator, R1-R5)
- `~/anicca/runtime/loop/harness-health-snapshot.mjs` (impure CLI, R7)
- `~/anicca/skills/self/self-improve/lib/harness_health.py` (Python mirror, R8)
- `~/anicca/skills/self/self-improve/harness_health_report.py` (Python CLI, R8)
- `~/anicca/runtime/loop/index.mjs` (existing file — the 2 new `appendHarnessFailure` call-sites + the
  `redactPrivateKeyPatterns(err.message)` call site this feature adds)

## Tooling

| Tool | Availability | Notes |
|---|---|---|
| Semgrep | ✅ available (v1.168.0, `/opt/homebrew/bin/semgrep`) | Ran two scans (see below) |
| Wycheproof (crypto test vectors) | N/A — not applicable | This feature contains zero cryptographic primitives, key generation, signing, or encryption logic. It REUSES (never re-implements) the existing `env-filter.mjs::redactPrivateKeyPatterns` regex-based redaction function for one new call site (`brain_transport`'s `err.message`) — a pattern-match/string-redaction utility, not a cryptographic operation. Wycheproof vectors test crypto primitive correctness (e.g. AES, ECDSA, RSA edge cases) and have no surface here. |
| bandit (Python security linter) | ❌ NOT INSTALLED (`pip3 show bandit` empty) | Not installed on this machine. Semgrep's `p/security-audit` ruleset (77 Python rules run in this scan) substantially overlaps bandit's rule coverage (injection, subprocess/shell, hardcoded secrets, unsafe deserialization) and was used as the available substitute. Suggested install if a dedicated pass is later desired: `pip3 install bandit && bandit -r skills/self/self-improve/lib/harness_health.py skills/self/self-improve/harness_health_report.py`. |

## Raw Results

- `verification/security-results/semgrep-auto.json` — `semgrep --config auto` (`--json`) over all 5
  scoped files. 442 rules run (1074 candidate community rules, auto-filtered per matched language:
  47 multilang + 153 JS + 243 Python rule packs narrowed to files actually present). **0 findings, 0
  errors.**
- `verification/security-results/semgrep-secrets-security-audit.json` — `semgrep --config p/secrets
  --config p/security-audit` (`--json`) over the same 5 files, specifically targeting secret-leak and
  general security-audit rule packs (most relevant given this feature's redaction/append-only-log
  surface). 138 rules run (272 candidate rules narrowed by language). **0 findings, 0 errors.**

## Manual security review (beyond automated scan coverage)

Since this feature's most security-relevant behavior — "does the new `redactPrivateKeyPatterns(err.message)`
call site actually redact before any truncation/logging happens" — is a data-flow property Semgrep's
generic rule packs are not tuned to catch (it has no project-specific rule for this codebase's own
redaction function), this was independently verified by:
1. **Source trace** (this session): `index.mjs`'s `brain_transport` branch (~line 370-377) calls
   `redactPrivateKeyPatterns(err.message || '')` and passes the RESULT as `rawDetail` into
   `appendHarnessFailure`, which then applies `capFailureDetail` (whitespace-collapse + 4000-char slice)
   — redaction happens strictly BEFORE truncation in the source, so a key positioned beyond char 4000 of
   the raw message cannot leak un-redacted (redaction operates on the full string, truncation is the
   last step).
2. **Live redaction test** (re-confirmed this session): `harness-health-failure-detail.test.mjs`'s 64-hex
   private-key fixture test spawns a REAL loop with a mocked HTTP 500 body containing a raw
   `0x`+64-hex-char pattern, and asserts the persisted `harness-failures.jsonl` line shows `[REDACTED]`,
   never the raw hex — PASS in this session's fresh run.
3. **Append-only / no traversal check**: `appendHarnessFailure` (index.mjs:616-632) writes to a single
   fixed path (`$ANICCA_HOME/state/harness-failures.jsonl`, computed once at module scope from
   `ANICCA_HOME`, never from any field of the untrusted `record`/`err`/`skillResult` — no path
   concatenation from user/model-controlled input anywhere in the new code), via the pre-existing
   `appendLedgerLine` (`O_APPEND`) primitive — no new file-path-injection or directory-traversal surface
   was introduced.
4. **No money/wallet/spend path touched**: grepped `harness-health.mjs`, `harness-health-snapshot.mjs`,
   `harness_health.py`, `harness_health_report.py` for `wallet`, `privateKey`, `PRIVATE_KEY`, `spend`,
   `transfer`, `sign(` — zero matches (the ONLY private-key-pattern-related code is the REUSE of the
   existing `redactPrivateKeyPatterns` REDACTION function, i.e. code that removes key-shaped substrings
   from a string, not code that generates, reads, or moves a key/funds).

## Findings
None. Both automated Semgrep scans (general `auto` ruleset + targeted `p/secrets` + `p/security-audit`)
returned 0 findings across all 5 scoped files. Manual review of the one genuinely new security-relevant
data-flow (brain_transport redaction ordering) confirms it is correctly implemented and independently
tested end-to-end.

## Summary
- Tools attempted: Semgrep (available, ran 2 scans, 0 findings), bandit (not installed, Semgrep
  `p/security-audit` used as substitute), Wycheproof (not applicable — no cryptographic code in scope).
- Raw results captured: `verification/security-results/semgrep-auto.json`,
  `verification/security-results/semgrep-secrets-security-audit.json`.
- Clean pass: 0 findings across both scans; manual redaction-ordering review independently confirms the
  one new security-relevant call site is correct.
- No money/wallet/spend surface exists in this feature's scope (confirmed by grep).
