# CORE-a / 8d correction build order

## Role and outcome

You are the fresh builder Sol for only `8d CORE-a`. Correct PR #330's eight reviewed blockers with strict TDD, execute fresh verification, update the canonical spec with truthful evidence, commit only scoped files, and push the existing PR branch. Do not merge the PR and do not start 8e.

Done means: every required DAILY dependency has a production-aligned success/failure/timeout contract, L1/L2 are green, the corrected fresh production verification is truthfully green with controlled L3 evidence where a read-only proxy cannot prove capability, evidence is PII/secret-free, row 8d is updated to done only if all requirements pass, and the pushed remote head is reported.

Working method (non-negotiable):
1. Restate the goal in one sentence + a "done means" criterion before acting.
2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
3. Name your riskiest assumption and check it first, while it is cheap.
4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.

## Workspace and SSOT

- Worktree: `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`
- Existing branch: `feature/lm33d-daily-preflight`
- Expected starting head: `a22b6bd26d9403c70bc717538bdf420c1d04b56c`
- PR: `https://github.com/Daisuke134/anicca-products/pull/330`, base `dev`
- Spec: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, §10 row `8d CORE-a`, §10.2–10.3
- Existing evidence: `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T055121Z.json`
- Review log, read only and never commit: `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-review.log`

Start by verifying the worktree is clean and at the expected head. Use CodeGraph before broad search, but verify the current worktree files directly because the root index may not contain this PR's new files. Use official primary docs through `crwl`, Context7, or `gh`; do not use WebSearch/WebFetch.

## Fresh review verdict to correct

`FINAL_VERDICT: FAIL`, `MERGE: NO`, 8 blockers:

1. `daily-preflight.js:236`: Resend `GET /domains` does not prove a send-only credential can use production `POST /emails`; 401 can be the correct restricted-key response.
2. `daily-preflight.js:294`: preflight requires Routes and legacy Directions together while production runtime accepts an available valid route result.
3. `daily-preflight.js:115`: Telegram `getWebhookInfo` cannot return the registered secret; env presence is not proof of provider/server secret alignment, and URL host/path is not exact-checked.
4. `daily-preflight.js:176`: call check omits production `PUBLIC_WSS` and `LM_CALL_SECRET` readiness.
5. `daily-preflight.js:216`: absent or expired location can pass.
6. `daily-preflight.js:279`: only Gemini Live is checked; DAILY ask's standard `gemini-2.5-flash:generateContent` capability is omitted.
7. `daily-preflight.js:50`: generic strings can retain URL query tokens, domestic phone numbers, chat IDs, and equivalent PII.
8. `daily-preflight.js:98`: calendar chooses a different cohort from the scheduler's phone+paid+supported-provider users.

## Required implementation protocol

### 1. RED first

Add focused negative tests for all eight blockers before changing implementation. Run them and preserve a compact RED record with failing test names/count. Tests must include:

- restricted Resend key behavior is not incorrectly green;
- Maps accepts the same provider/result combinations as the production runtime and reports degraded providers separately;
- Telegram exact webhook URL plus an active auth/round-trip proof contract; mere env presence is not green;
- valid `wss://` production bridge URL/path and non-placeholder/nonempty call secret;
- required user's location missing/stale is non-pass;
- both Gemini Live bidi and standard DAILY generateContent capabilities;
- value-level redaction for query strings, domestic/international phone, email, chat/user IDs, bearer/provider keys, and nested provider messages;
- calendar selection reuses the scheduler's actual supported cohort/selector.

### 2. Minimal GREEN and shared runtime contracts

Do not duplicate production semantics. Extract or reuse shared pure predicates/selectors where necessary so runtime and preflight cannot drift. Avoid a second implementation of maps acceptance or scheduler cohort logic.

For each dependency emit useful redacted evidence, including degraded-but-operational provider state where applicable. Every required failure and timeout must remain nonzero. Abort active fetches on timeout.

### 3. Fresh production verification

Run normal tests and eval before any production action. Then execute one corrected production verification pass.

- Read-only checks remain read-only wherever they genuinely prove the runtime capability.
- Resend: first verify from official docs whether any read-only endpoint proves the same credential's `POST /emails` send scope. Do not treat `/domains` 401 as success. If no such proof exists, send exactly one controlled verification email to the existing user-owned LM verification inbox/plus-alias, never to a new external recipient. Verify provider response plus actual inbox receipt/Message-ID. Store only redacted recipient facts and Message-ID.
- Telegram: prove the real provider-to-production webhook path with one harmless user-to-bot round trip using the already-authorized Telethon user session. Prefer a command that creates no durable business action; if `/panel` is the only safe reply path, do not log its opaque URL/token and record only request/reply message IDs. Verify webhook URL host/path exactly and `pending_updates`/`last_error`.
- Call: do not dial a phone in 8d. Validate the exact Telnyx connection/number/profile plus production WSS URL/path, bridge reachability, and call secret configuration without printing values. A safe WSS handshake may be used and closed immediately; record any provider cost truthfully.
- Calendar: authenticated read for the exact scheduler cohort user, no create/patch/delete.
- Location: the required target user must have a present fresh row. If not, fail honestly; do not fabricate or update location in this atomic.
- Gemini: verify both the Live bidi model and the standard DAILY model/method with the same credential without storing prompts/responses containing PII.
- Maps: one real non-PII route query; success follows the shared runtime acceptance contract and records unavailable providers as degraded, not hidden.
- Discovery and health: no write/send.

No call dialing, calendar write, location write, discovery send, broadcast, credential rotation, schema change, billing-path change, or unrelated deployment is authorized. Controlled email and TG round trip above are the only allowed external side effects.

### 4. Verification gate

Run and report exact exits/counts:

- targeted tests for the preflight and extracted shared contracts;
- full `npm test` for `apps/life-call`;
- `npm run eval`;
- coverage for changed production modules, target >=90% lines/functions or explain a real project-enforced stricter threshold;
- syntax/lint/build commands present in this package;
- secret/PII scan of diff and new evidence;
- `git diff --check` and clean scoped status after commit.

Do not reuse the old 7/9 artifact as fresh proof. Create a new timestamped evidence artifact. The artifact must contain no recipient address, phone, location/address, chat/user ID, auth value, token, query-bearing URL, raw provider response, or opaque panel URL.

### 5. Spec and git

- If and only if all dependencies are green and controlled L3 evidence is verified, update row 8d to `done` with exact test counts, smoke summary, evidence path, redacted Message-ID/TG IDs, and commit/PR facts.
- Otherwise keep 8d `pending`, record exact remaining failure and the rejected hypothesis, then stop without moving to 8e.
- `git fetch`, stage explicit scoped paths only, commit, push `feature/lm33d-daily-preflight`.
- Never stage unrelated root/worktree changes. Never merge PR #330.

## Final stdout

Return a compact report containing starting/ending head, changed files, RED, GREEN, full tests, eval, coverage, production result, side effects, evidence path/hash, PII/secret scan, spec state, commit, push, PR URL, and any remaining blocker. Label each claim VERIFIED / REASONED / ASSUMED.
