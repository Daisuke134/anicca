# Life Manager 8d.1 PANEL-0 — personalized control center

Implement in the separate worktree `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center`, branch `feature/lm-panel-control-center`, stacked on `1f1be94de` / PR #330. Do not edit the 8d worktree. Do not merge or deploy; push the branch and open a stacked PR against `feature/lm33d-daily-preflight` only after local verification. Main session owns final review/merge/deploy order.

Canonical requirements are the root checkout spec at `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, current commit `e1ca5bd18`: §9.5, §9.9, §10 row `8d.1 PANEL-0`, §10.0, §10.1 U5, §10.2–10.3. Sync those exact requirements into the worktree spec without overwriting the branch's newer 8d evidence.

Use VCSDD in `.vcsdd/features/life-manager-panel-control-center/` as the feature truth and advance 1a→1b→1c→2a→2b→2c→3→4→5→6. Read and follow `spec-driven-development`, `tdd-bug-fix`, `frontend-design`, and `agent-browser`; project rule wins for browser order, so use existing CloakBrowser/daily-driver CDP first, camofox only if blocked. Before any browser command, load the installed browser skill's current core workflow. No nested agent/review.

## Goal

`/panel` must be a personalized dashboard, not a read-only page. Two entry paths converge on one user-scoped command layer:
1. Telegram chat intent such as “connect calendar”, “turn calls off”, or Japanese equivalents.
2. Clickable dashboard connection cards and settings toggles.

Both must read/mutate only the authenticated user's real connections, context, gates, and settings. Static labels may be shared; connection state/context/action/results may not be hardcoded or cross-user.

## Phase 1 — reproduce and specify before fixing

Use one authorized harmless production probe to reproduce the current report:
- derive the actual LM bot peer without printing tokens/secrets;
- use the existing pinned MTProto sidecar to send one fresh `/panel` to Dais's LM bot chat;
- parse the bot reply privately, never print/store the opaque URL or token, and open it in the existing authenticated browser;
- record only Telegram request/reply hashed refs, HTTP status, final path, query-token absence, and whether the link was fresh/used;
- separately prove an old/used link is 403. Do not confuse correct used-token rejection with a fresh-token bug.

Inspect actual `panel-auth.js`, `panel-api.js`, `panel-ui.js`, server routing, migrations/RPC, current provider connection helpers, and prod response. State the root cause with VERIFIED/REASONED/ASSUMED. If production probing would expose a secret, stop that probe and use a private mode-0600 evidence file.

Write VCSDD findings/spec/test contract before implementation. The implementation spec must include exact data model, API routes, CSRF/session rules, connection capabilities, chat intent grammar, UI states, rollback, and L3 steps.

## Required behavior

### Access/auth
- `/panel` sends an inline clickable WebApp/URL button where Telegram supports it; otherwise a clickable URL. Never plain unclickable text only.
- Fresh 5-minute single-use token exchanges to HttpOnly session and redirects to `/panel` with query removed. Fresh 403 is a blocker.
- Used/expired/invalid token remains rejected, but returns a human page rather than raw `forbidden`, with one clickable “Get a new dashboard link” Telegram deep-link. Implement the bot deep-link intent so it creates a new single-use link; do not weaken single-use security.
- No opaque token in logs/spec/test snapshots/browser URL after exchange.

### Personalized control center
- Resolve session to one `uid + telegram_chat_id`; every read and mutation filters that uid. Add explicit tenant isolation tests with two users for response data, mutation target, OAuth state, and chat intent.
- Render actual per-user identity/context summary and connection states from backend rows/providers. Do not hardcode Dais, connected booleans, scores, context, or fixture state.
- Connection cards cover at minimum calendar, Telegram, location, call, email, and payout/wallet with honest states: `connected`, `action_required`, `unavailable`, `error`.
- Only supported actions are clickable. Gmail must follow current U1 truth (reading unavailable unless a real authenticated free path exists); do not fake success. Location/payout may route to exact Telegram permission/setup instructions. Calendar must reuse the existing Composio connector; do not invent OAuth.
- **Alignment correction (HARD): the root spec says connect / reconnect / disconnect / turn on / turn off.** The current VCSDD draft and `user-command.js` omit every `connection.disconnect`, which is out of spec. Before continuing implementation, revise Phase 1 artifacts/test contract as a new iteration and add a typed, user-scoped `connection.disconnect` lifecycle for each genuinely supported connector. At minimum Composio Calendar must support Connect, Reconnect, and Disconnect through the existing official provider contract, from both chat grammar and panel controls, with the same command service, CSRF/idempotency, tenant isolation, failure rollback, honest ACTIVE readback, and tests. Search the installed Composio SDK/current official API before choosing the disconnect operation; do not invent provider success. If the existing connector contract truly cannot disconnect, record the primary-source limitation and expose an honest non-success path rather than silently omitting the requirement.
- Telegram is the panel's authentication anchor and must not receive a destructive disconnect action in PANEL-0. Gmail remains unavailable; location/wallet/call follow their real permission/provider capability and may use turn-off or instructions instead of a fake disconnect. Never disconnect Dais's production Calendar/account. Any L3 disconnect proof must use an isolated test connected account only; this order remains local/stacked and performs no provider disconnect.
- Settings include real per-user call enabled/policy, call language/timezone, notification/organ automation controls, and delegation where the schema/runtime supports them. If an additive persistence table/column is needed, write migration + rollback and keep it user-keyed; no destructive prod schema changes.
- Every button/toggle has loading/success/failure states, idempotency, rollback-on-failure, keyboard/accessibility semantics, and mobile/desktop layout. No dead cards or decorative fake controls.

### One command layer
- Implement a single allowlisted, typed user command service used by panel POST endpoints and Telegram intent parsing. The UI and chat must not write DB/provider state independently.
- Natural-language parser is deterministic/closed for connection and toggle intents; ambiguous intent reports the available actions without a generic open question. OAuth/permission remains the only necessary user gate.
- Panel mutation uses POST, same-site session, CSRF/origin check, JSON schema/allowlist, idempotency key, and user filter. GET remains side-effect free.
- Report result in both surfaces: panel updates immediately; chat action sends a concise success/failure report. No cross-user notification.

## TDD contract

Write and run RED first for:
- fresh token forbidden / RPC mismatch root cause;
- used/expired invalid page and new-link deep link;
- sendPanelLink contains a clickable inline button without leaking token elsewhere;
- non-clickable cards/toggles;
- user A cannot read/mutate user B, including OAuth state and chat intent;
- chat action and panel action converge to identical command/result state;
- Calendar Connect/Reconnect/Disconnect commands exist in both chat and panel, converge on one service, are user-scoped/idempotent, and provider failure keeps the prior ACTIVE/inactive state;
- unsupported connector cannot report connected;
- CSRF/origin, invalid action, duplicate idempotency, provider failure rollback;
- personalized data differs for two fixtures, with no hardcoded Dais/default connection state;
- mobile/desktop semantic assertions and every visible action has an actual handler.

Then minimal GREEN, refactor, full `npm test`, relevant eval, changed-module line/function coverage >=90%, `git diff --check`, secret/PII/raw-log scan, and browser fixture smoke.

Do not mark 8d.1 done from fixtures. Keep it `pending — local GREEN` until stacked parent is mergeable and L3 production evidence exists. Commit/push and open stacked PR; report commit, PR URL, remote equality, RED/GREEN commands, coverage, reproduced root cause, and exact remaining L3/deploy prerequisites. Do not call phone, send email, disconnect Dais's real provider, alter wallet, or perform destructive schema/provider changes.
