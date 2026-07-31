# CORE-a / 8d final local blocker — production collectors must be closed

Implement in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, head `1f1be94de617a3b88857486daa983897d2dc087d`, PR #330.

Read exact fresh verdict `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-runtime-rereview.log`. Fix only blocker 1. No production/provider/Railway calls, no Telegram/email send, no dial/deploy/merge. Do not spawn another agent. Preserve historical artifact and row 8d pending.

TDD:
1. Add structural/behavior RED proving production modules export no injectable factory and expose no transport injection (`botCall`, `mtprotoSend`, `mtprotoRead`, `execFileImpl`, `send`, `findReceipt`, `mailFactory`, custom env/fetch/now/randomNonce/sleep/maxPolls).
2. RED must prove controlled production CLI cannot accept caller-provided collectors/transports and that tests cannot accidentally fall through to real sidecar/fetch/Resend/gog.
3. Move every injectable constructor/factory to `daily-preflight.test-support.js` (or another filename ending `.test-support.js`) and make production never import test-support.
4. Production collector wiring must be fixed/closed: pinned interpreter+sidecar, `process.env`, global fetch, real Resend/gog, internal crypto/time/sleep/bounds. It may expose one no-argument controlled collection function needed by `daily-preflight.js`; no parameter can replace observations or transport. Pure validation functions may remain exported.
5. `collectControlledL3` and production CLI must not pass env/fetch/now into controlled collectors. Default read-only behavior and read-only test injection for the nine non-side-effect checks may remain, but controlled mode ignores any caller-supplied env/fetch/collector and uses only the closed runtime environment.
6. Keep `/panel core8d_<nonce>` only; never `/start`. Keep one-send budgets, exact nonce receipt, allowlist, sanitation, bounded polls, report binding.
7. Rework tests to exercise algorithms through test-support mirrors/pure validators and structural source assertions. Any production transport test must install fakes before invocation or be removed; never allow fallback to the real sidecar.

Quality correction: do not game source scans by splitting identifiers or dynamic property access (`mail["find" + "Receipt"]`, string concatenation, aliases chosen only to evade regex). Keep normal readable calls such as `mail.findReceipt(...)`. Structural tests must inspect exported keys and function signatures/parameters for injectable surfaces; they must not ban legitimate fixed transport method invocations or command literals appearing inside closed production code.

Verify focused suite, full `npm test`, eval, changed-module line/function coverage >=90%, diff check, production import/export/forbidden-name scan, artifact hash unchanged. Update worktree spec with this review/fix and the prior unintended fixture attempt, still pending 6/9. Commit/push, prove remote equality. No nested review.
