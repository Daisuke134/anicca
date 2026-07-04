# Security Hardening Report — profitable-article-writer, Sprint 1 + Sprint 2 + Sprint 3 (2.5)

Mode: strict. Phase 5. Sprint 1 = orchestration skeleton (no network). Sprint 2 = REAL network I/O landed
(note.com auth via stored cookies, browser automation). Sprint 3 = a real IRREVERSIBLE publish action — this
report covers all three.

## Sprint-3 hardening: exception safety on a real side-effecting action

The highest-severity finding across this whole feature's adversary reviews (Phase-3-contract-review round 1
FIND-004) was here: `note-publish-live.py`'s browser-session lifecycle had no exception handling, so a realistic
browser failure (navigation error, DOM change, cookie expiry) would (a) leak an open browser context and (b)
leak a raw Python traceback to the caller instead of the tool's own documented clean-refusal contract. For a
tool whose entire purpose is a one-off irreversible publish action, an unhandled exception mid-click is exactly
the failure mode that could leave the system in an ambiguous state (did it publish or not?).

Fix: the full lifecycle (browser launch → cookie load → navigate → confirm state → click) now runs inside
try/except/finally. Any exception is caught, converted to the tool's normal clean-refusal report (never a raw
traceback), and the browser context is closed exactly once in `finally` (traced by both the builder and the
Phase-3 adversary independently — no leak path, no double-close). Verified with a REAL injected failure (not
simulated): the fix was `git stash`'d, the test reran against the OLD code and genuinely failed (8/9 assertions,
raw traceback present, context leaked), then restored and reran green (9/9, clean refusal, context closed).

## Tooling (cumulative)

- `bash -n` / `python3 -m py_compile` on every script — clean.
- Static literal scan for provider/model/API-key literals — 0 matches.
- Secret redaction (Sprint 2 FIND-005) — unchanged, still enforced.
- Structural reachability scan (Sprint 3): a whole-tree grep+regex proves `note-publish-live.py` is invoked
  by NOTHING except itself and its own tests — no accidental daily-wake reachability.

## Summary

The one real-world irreversible action this feature performs (making a note.com draft public) is now
exception-safe: a failure mid-action reports cleanly and never leaks a browser session. Combined with the
structural unreachability proof, the trigger requirements (explicit env var + explicit draft key, no defaults),
and the independent post-publish verifier (never trusting the publish tool's own claim), this is as hardened as
a manually-invoked, one-off, high-stakes action reasonably needs to be before the main agent exercises it for
real on the flagship draft.

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
