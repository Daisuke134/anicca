# CORE-a / 8d corrective build 3 — real fixed collectors, no production run

You are the implementation Sol for PR #330 in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, current head `2df9585c743aafb9083046b8b3dba6613030e474`.

Implement only the two blockers in the fresh review. Do not merge, deploy, dial, send Telegram/email, call Railway/provider APIs, or rerun production smoke in this turn. Do not spawn another agent. Keep row 8d pending and preserve the historical 6/9 artifact unchanged.

Read first:
- spec §9.5, §10 row 8d, §10.2–10.3
- `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-proof-rereview.log`
- exact diff `145f18dd19..2df9585c7`
- actual existing Telegram, Resend, Gmail/Composio/Unipile integrations and package dependencies

Before designing, search the repo for reusable integrations and consult only primary provider docs needed for the exact APIs. Record source URL + one decisive sentence in the spec/order result. Do not invent a proof transport.

Verified reusable local paths (do not repeat a broad home-directory search):
- MTProto sidecar: `/Users/anicca/anicca/skills/tools/telegram-user/tg_user.py`
- fixed interpreter: `/Users/anicca/.cache/telegram-user-venv/bin/python`
- protected StringSession config: `/Users/anicca/.cloak/telegram-user.json` (mode 0600; never read/print/serialize its contents)
- Gmail receiver: `/opt/homebrew/bin/gog` through `apps/life-call/lib/transport/mail-gog.js`; `GOG_ACCOUNT` selects the already-authenticated account
- Resend sender: `apps/life-call/lib/mail-resend.js`; extend a controlled-only result shape if an accepted provider ID is needed, rather than treating its current boolean as receipt
- primary docs: `https://core.telegram.org/bots/api#getwebhookinfo`, `https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.messages.MessageMethods.send_message`, `https://resend.com/docs/api-reference/emails/send-email`, and Gmail CLI/provider docs actually used

For Telegram, derive the Life Manager bot username from Bot API `getMe`; do not add a caller-selected peer. Invoke only the pinned interpreter + pinned sidecar with an argv array (no shell), send one fixed harmless command with an internally generated nonce where the bot contract permits it, and poll/read that exact derived bot dialog for a newer inbound bot reply. Hash message IDs; discard message text and any opaque panel URL immediately. For email, the authenticated `GOG_ACCOUNT` is both the controlled recipient and the receive identity; a matching received nonce proves ownership. Do not add a free-form recipient argument.

Alignment correction: the Telegram probe command must be exactly `/panel core8d_<internal nonce>`, which the existing `isPanelCommand` accepts. Do not use `/start`; it can alter onboarding state. The `/panel` reply's opaque URL/token must never leave the MTProto adapter: retain only inbound direction, timestamp, and numeric message ID long enough to hash the ID.

TDD is mandatory: add failing tests, show RED, implement minimal GREEN, refactor, then full verification.

Required production contract:

1. Remove `collectors` injection from the exported/production `scripts/daily-preflight.js main()` completely. The executable production path must not accept arbitrary collectors, proof JSON/file, commands, booleans, refs, timestamps, or post-generation mutation.
2. If unit tests need DI, isolate it behind a non-exported factory or an explicitly test-only module that the production entrypoint cannot import/activate from argv/env. Add a direct test proving `main({ collectors: forged })` cannot turn the production path green.
3. Replace `CONTROLLED_COLLECTOR_REGISTRY` unavailable stubs with fixed in-repo production collectors that derive proof from operations they themselves perform:
   - Telegram: a real harmless same-run user-to-Life-Manager-bot command and bot reply using the already-authorized MTProto/Telethon user-session path, then bounded real Bot API `getWebhookInfo` polls until `pending_update_count === 0`. IDs from MTProto may only be hashed references; never compare them with Bot API `update_id`. Exact webhook host/path, allowed updates, provider error/backlog are fetched directly. Do not log or serialize `/panel` opaque URL/token. Reuse an existing authorized session/tool; if no reusable fixed path exists, fail closed and report that concrete prerequisite rather than substituting bot-to-user `sendMessage` or a simulated webhook.
   - Email: generate a cryptographic nonce internally, send one harmless controlled message through the existing Resend path to an allowlisted Dais-owned test recipient, poll the existing authenticated Gmail/Composio/Unipile receive path for that exact nonce, and derive provider/message hashed refs from actual provider responses. Recipient ownership comes from a fixed allowlist/config, never a caller boolean. Never expose address, subject nonce, raw Message-ID, provider error, or body in artifact/stdout. If an authenticated receive path is absent, fail closed and report the exact prerequisite; do not accept send acceptance as receipt.
4. Controlled side effects remain structurally gated: `--mode controlled-l3` only; default read-only sends nothing. Add a one-run budget of exactly one harmless Telegram command and one controlled email, with bounded poll/timeouts and no retries that can duplicate sends.
5. Collectors themselves derive success fields; validators must not trust `verified`, `recipientOwned`, `providerAccepted`, or `inboxReceived` supplied by a caller. Prefer returning raw provider observations into a pure validator/builder.
6. Same `buildPreflightReport()` call emits the validated `controlledL3`; no manual artifact append.
7. Closed allowlist serialization and all prior negative tests remain green.

Required direct tests:
- production CLI ignores/rejects forged `collectors` and has no `--proofs`/proof file path;
- read-only mode invokes zero controlled sends;
- controlled mode invokes each fixed collector exactly once;
- Telegram real-adapter contract: round trip missing/rejected, reply timeout, exact URL mismatch, missing allowed update, provider error, `[1,0]` pass, `[1,1,1]` fail;
- email real-adapter contract: recipient outside allowlist, send reject, receive timeout, nonce mismatch, stale receipt fail; exact nonce receipt pass;
- errors/timeouts exit nonzero and sanitized output contains no secret/PII/raw provider error;
- production registry contains real adapters, not unconditional unavailable stubs.

Verification:
- focused RED/GREEN commands with real exits
- `npm test`
- `npm run eval`
- changed-module line/function coverage >=90%
- `git diff --check`
- scan source and CLI help for forbidden `--proofs`, production collector DI, artifact mutation

Update worktree spec row 8d with local evidence and remaining production truth, still `pending`. Commit and push the same PR branch. Report commit, remote equality, tests, coverage, and any prerequisite that blocks the later controlled production run. No nested review.
