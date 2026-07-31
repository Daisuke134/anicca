# PANEL-0 alignment correction and resume

Fresh Sol continuation in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center`, branch `feature/lm-panel-control-center`. Read the full original order `.claude/sol-orders/order-panel-control-center.md`, especially its new HARD disconnect correction, root canonical spec at current root HEAD, and the existing dirty VCSDD/artifacts/code. Preserve and audit the interrupted Sol's work; do not discard it.

Do not spawn another agent. Do not merge/deploy, call phone, send email, alter wallet, disconnect any Dais production provider, or run another production `/panel` probe. The single production probe is already captured privately at `/tmp/lm-panel-control-center-production-probe.json`; use only its safe facts. Continue local/fixture work and open a stacked PR only after verification.

## Mandatory correction before more GREEN work

The interrupted implementation diverged from the canonical requirement:

- VCSDD `behavioral-spec.md`/`implementation-spec.md` omitted every connector disconnect and explicitly excluded it.
- `user-command.js`, tests, and UI currently expose Calendar connect/reconnect but no `connection.disconnect`.
- Root §9.9 requires supported `Connect / Reconnect / Disconnect / Turn on / Turn off` actions, and the user explicitly wants a connection dashboard rather than a page.

Revise VCSDD Phase 1 artifacts as iteration 2 and amend the sprint contract before proceeding. At minimum, the real supported Composio Calendar lifecycle must expose typed `connection.start` and `connection.disconnect` through both chat and panel, using the same user-scoped command service. Search the installed/current official Composio SDK/API for the exact connected-account disable/delete operation and cite it in the artifact. Do not invent success. Implement tenant isolation, POST+CSRF/origin, idempotency, ACTIVE/inactive provider readback, and rollback/fail-closed tests. Add deterministic EN/JA chat grammar and native panel controls for Disconnect/Reconnect.

Telegram remains the auth anchor and has no destructive disconnect in PANEL-0. Gmail remains honestly unavailable. Location/wallet/call may expose their real turn-off/instruction action rather than a fake provider disconnect. Any future L3 Calendar disconnect uses only an isolated test connected account; this turn performs no external provider disconnect.

## Resume contract

1. Inspect current diff and VCSDD state. Record why the prior Phase 1 contract was incomplete.
2. Add RED tests for Calendar disconnect across service/chat/panel, tenant isolation, duplicate idempotency, provider failure rollback, and connected→inactive honest readback. Prove RED while old regression remains GREEN.
3. Implement minimal GREEN, then finish every requirement in the original order: auth renewal page, inline button, personalized backend, real connection cards/toggles, one command layer, migrations/rollback, mobile/desktop semantics, fixture browser smoke, coverage >=90%, full tests/eval, secret/PII scan.
4. Keep root §10 row 8d.1 `pending — local GREEN`; no production L3/deploy claim.
5. Before opening the stacked PR, update/rebase the branch onto the current remote `feature/lm33d-daily-preflight` head (currently expected `904e158c8...`) without overwriting its newer row-8d evidence. Resolve only owned conflicts, rerun verification, commit/push, and open/update the PR against that parent branch.

Final response must give RED/GREEN proof, full tests/eval, coverage, current VCSDD phase, exact disconnect provider contract, commit, remote equality, stacked PR URL, and remaining L3/deploy prerequisites. Self-review is builder evidence only; main will launch a separate fresh artifact-only reviewer.
