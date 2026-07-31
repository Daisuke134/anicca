# CORE-a / 8d method 2 alignment correction and resume

Fresh Sol continuation in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`. Preserve/audit the interrupted uncommitted TDD changes from `order-core-8d-receipt-precision-fix.md`. Expected committed base remains `f6129abb5...`; no provider/network/Telegram/email/phone/Railway/gog-inbox calls. No deploy/merge or production artifact. No nested agent.

## Mandatory logic correction

The interrupted implementation accepted a minute-precision receipt only when its bucket contained `sentAtMs`. That is still wrong: a legitimate controlled email can be sent at `17:59:59.500` and received as gog `18:00`, whose minute interval starts after the send. Exact random same-run nonce + accepted provider ID + bounded poll proves correlation; the receipt interval only needs to be **not wholly before the send**, within the freshness window, and not wholly in the future.

Before continuing GREEN, add RED cases and correct both parser consumer and validator:

- accept same-minute bucket containing the send;
- accept next-minute/later bucket whose lower bound is after send but not after `now`, within 15 minutes;
- reject a bucket whose upper bound is before send;
- reject a bucket whose lower bound is after `now`, malformed/unknown precision, old sentAt/receipt, nonce mismatch, missing provider/message ID;
- exact second/TZ timestamp remains strict: exact instant must be >= send and <= now;
- caller cannot supply raw date or precision to production; parser alone derives bounds.

The truthful interval invariant should be equivalent to: finite ordered bounds, `sentAtMs` itself fresh, `lowerMs <= nowMs`, `upperMs >= sentAtMs`, and `upperMs >= nowMs - MAX_AGE_MS`, plus existing ownership/provider acceptance/exact nonce/message ID. A minute bucket may have `upperMs > nowMs` because its precision interval includes the remainder of the current minute; do not mistake that for a future receipt when its lower bound is not future.

Update the prior RED evidence/count to include this newly caught case. Then complete the original local-only contract: focused GREEN, full tests/eval, >=90% coverage, closed-production scans, historical SHA/mode unchanged, spec pending update, commit/push/PR-head equality. Do not claim production 9/9. Main will run fresh review before any second controlled attempt.
