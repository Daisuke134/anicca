# Security Hardening Report — profitable-article-writer, Sprint 1 + Sprint 2

Mode: strict. Phase 5. Sprint 1 = orchestration skeleton (no network). Sprint 2 = REAL network I/O landed
(note.com auth via stored cookies, browser automation) — this report covers both.

## Tooling

- `bash -n` / `python3 -m py_compile` syntax check on every script — clean.
- Static literal scan (grep) for provider/model/API-key literals across the skill tree — 0 matches (PROP-1).
- JSONL-injection review: `json_escape()` (python3 `json.dumps` primary, sed fallback) applied at both
  `failures.jsonl` write sites; hostile-topic (quote/newline/backslash) proven to round-trip as valid single-line
  JSON (test-prop15, test-json-escape-fallback). Both escape branches exercised.
- **Secret-redaction review (Sprint 2, FIND-005):** `lib/note_publish.sh`'s error paths capture each Python
  sub-step's combined stdout+stderr and previously re-emitted it verbatim on failure — a real leak risk, since
  those sub-steps authenticate via `NOTE_COOKIES_FILE`. `_note_redact_secrets()` now applies TWO independent
  passes before any error output is emitted: (1) every literal cookie VALUE read from `NOTE_COOKIES_FILE` is
  substituted with `[REDACTED]` wherever it appears in the captured text; (2) a generic case-insensitive
  cookie/session/token/auth key=value pattern is also redacted, covering values this process never saw the exact
  bytes of. Fail-safe: if the cookies file is unreadable, pattern-2 scrubbing still runs. Tested (test-find005):
  a synthetic secret-shaped string is proven absent from final error output; a non-secret diagnostic string is
  proven NOT over-redacted (still useful for debugging).
- Semgrep / SAST: no injectable shell sink found (no `eval`, no unescaped variable in a command position); the
  browser-automation scripts use Playwright's API (parameterized), not string-built JS/shell injected into the page.

## Summary

Sprint 1 had no security attack surface. Sprint 2 introduced real ones — note.com authentication via stored
session cookies, browser automation, and (in error paths) subprocess output capture that could have leaked those
cookies. The one identified leak path (FIND-005) is closed and tested with both a positive and negative-control
assertion. Deferred to Sprint 3+: credential-at-rest encryption for NOTE_SESSION_COOKIE, rate-limit/abuse handling
on the live judge_v05 model call once wired, and Stripe/on-chain key custody once those rails' V4 earn lands.
