# CORE-a / 8d proof-provenance fresh artifact review

You are a fresh independent reviewer. Review committed head `2df9585c743aafb9083046b8b3dba6613030e474` against parent `145f18dd19b49096c4fdef46be5ce7f92df5e474` in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`.

Read only. Do not edit, commit, push, merge, deploy, call Railway/provider APIs, send Telegram/email, or dial. Do not spawn another agent. Ignore builder claims: use the committed diff, tests, spec, and historical artifact only.

Goal: independently decide whether the four blockers from the prior review are closed without creating a new false-green path. Row 8d must remain pending because production truth is still 6/9.

SSOT:
- spec row `8d CORE-a` and §10.2–10.3
- prior review log `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-postcommit-review.log`
- historical production artifact `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json`

Check the riskiest assumptions first:
1. No arbitrary runtime `--proofs`, file, JSON, command, or caller-supplied boolean can make Telegram/email green. Dependency injection is test-only; production controlled mode uses fixed in-repo collectors.
2. Telegram controlled proof comes from a real same-run round trip and bounded polls of actual `getWebhookInfo.pending_update_count`, with final sample exactly zero. Do not accept invented update IDs or Telethon message IDs as Bot API update IDs. `[1,0]` passes; `[1,1,1]` fails.
3. Email requires attempted + provider accepted + inbox received + owned recipient + provider/message references + fresh timestamp. A rejected send or missing receipt fails.
4. `controlledL3` is emitted by the same report builder from validated collector results; it cannot be manually appended after generation. Timestamp/provenance is reproducible.
5. Final serialization uses closed allowlisted schemas. It must drop/redact hostname, names, opaque URL/query/token, raw provider errors/messages, email/phone/IDs/secrets while retaining only safe enums, booleans, counts, timings, and hashed refs.
6. Direct negative tests cover stale proof, Telegram non-draining backlog and missing allowed update, Telnyx number/connection/profile/webhook/WSS/auth mismatch, Gemini Live/standard failures, email rejection/missing receipt, and location missing/stale.
7. Historical artifact remains unchanged and honestly says 6/9 with telegram/call/email failing; spec stays pending. No production side effect occurred in this commit.

Run fresh local read-only verification:
- `git diff --check 145f18dd19..2df9585c7`
- focused tests including `daily-preflight-provenance.test.js`
- full `npm test`, `npm run eval`, and changed-module coverage if practical
- inspect the exact production CLI wiring, not only injected tests
- parse/scan the historical artifact for truth and sensitive leakage

Use VERIFIED / REASONED / ASSUMED. Re-read this order before verdict.

Finish exactly:

```text
FINAL_VERDICT: PASS | FAIL
MERGE: NO
BLOCKERS: <count>
FINDINGS:
- [severity] file:line — problem — correction
VERIFICATION:
- command => exit/result
```

`MERGE` remains NO regardless of code review because production is not 9/9.
