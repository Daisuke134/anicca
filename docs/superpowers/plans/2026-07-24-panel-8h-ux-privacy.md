# PANEL 8h UX / Privacy Closure Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to execute this plan task-by-task, with RED/GREEN evidence and fresh reviews.

**Goal:** Ship the authenticated Life Manager panel with five human-readable sections on mobile and desktop, while preventing raw provider payloads, internal diagnostics, secrets, and personal identity text from reaching API responses or the emitted browser.

**Architecture:** Add a closed presentation-policy boundary shared by the panel API and emitted browser. Project timeline and ledger source records into small safe DTOs, validate scores/gates/settings/control-center before serialization, and fail closed with an exact section error. Preserve `call_language=null` as a valid persisted state. Verify the boundary through real `handlePanelApiRequest` calls and browser execution of captured responses.

**Tech Stack:** Node.js CommonJS, `node:test`, direct request/response fixtures, emitted panel JavaScript executed with `vm`, Playwright for authenticated mobile/desktop evidence.

**Historical input:** The dirty worktree `.worktrees/sol-panel-8h-ux-privacy` identified three real defects, but its 536-case VCSDD matrix is rejected as an implementation input. It duplicates existing schema tests, has incomplete per-case oracles, and caused planning work to dominate product work. New tests must not read that worktree or create VCSDD artifacts.

**Focused Superpowers contract:** Test only the three remaining defects: provider/generic secret leakage, truthful real API/browser execution, and valid `call_language=null`. Existing panel tests remain the regression guard for every other schema path.

**External security basis:**

- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html — access tokens, passwords, database connection strings, and encryption keys should not be logged directly.
- GitHub Secret scanning: https://docs.github.com/ja/code-security/secret-scanning/introduction/about-secret-scanning — scans for API keys, passwords, tokens, private keys, connection strings, and generic API keys.
- Gitleaks default configuration pinned at `b58d3f102cf3a2c84cb7f923d05c25c9b1aed84b`: https://github.com/gitleaks/gitleaks/blob/b58d3f102cf3a2c84cb7f923d05c25c9b1aed84b/config/gitleaks.toml — use its provider/private-key pattern shapes for the first 16 recipes; use credential-bearing PostgreSQL, Redis, and MongoDB SRV URLs for the final three.

---

## Task 1: Close the executable presentation contract

**Files:**

- Create: `apps/life-call/eval/panel-privacy-contract.js`
- Create: `apps/life-call/eval/panel-privacy-harness.js`
- Create: `apps/life-call/eval/run-panel-privacy-eval.js`
- Create: `apps/life-call/lib/panel-privacy-contract.test.js`
- Modify: `apps/life-call/package.json`

**Step 1: Write the failing contract test**

Build these 19 synthetic credential recipes from harmless string fragments at runtime so no committed file contains a complete token-like value:

`github-classic-token`, `github-fine-grained-token`, `gitlab-personal-token`, `slack-bot-token`, `slack-user-token`, `npm-access-token`, `aws-access-key-id`, `stripe-secret-key`, `google-api-key`, `openai-project-key`, `resend-api-key`, `telnyx-api-key`, `telegram-bot-token`, `stripe-webhook-secret`, `stripe-restricted-key`, `pem-private-key-header`, `postgres-credential-uri`, `redis-credential-uri`, `mongodb-srv-credential-uri`.

Run every recipe through exactly these nine channels and fixed oracles:

| Channel | Real API oracle | Emitted-browser oracle |
|---|---|---|
| `api-timeline-text` | 200; `items[0].sentence` equals the fixed safe timeline sentence | n/a |
| `api-ledger-href` | 200; `financial.items[0].link` is `null` | n/a |
| `api-settings-call-language` | exact 422 `{"error":"section_unavailable","section":"settings"}` | n/a |
| `api-settings-wake-policy` | exact 422 `{"error":"section_unavailable","section":"settings"}` | n/a |
| `api-control-center-call-language` | exact 422 `{"error":"section_unavailable","section":"control-center"}` | n/a |
| `api-control-center-wake-policy` | exact 422 `{"error":"section_unavailable","section":"control-center"}` | n/a |
| `browser-timeline-text` | same 200 safe timeline DTO | section loaded; fixed safe sentence visible; source absent |
| `browser-ledger-href` | same 200 ledger DTO with `null` link | section loaded; `a.ledger-link` absent; source absent |
| `browser-control-center-identity` | 200; `identity.name` equals `Life Manager user` | section loaded; `Life Manager user` visible; source absent |

The fixed timeline sentence is `予定の詳細を安全に表示できず、次はカレンダーで開始時刻を確認してください。`

Add these exact positive cases:

- settings `call_language=null`: API 200 with complete closed DTO and exact `null`; browser remains loaded and displays `未設定`.
- control-center `settings.call_language=null`: API 200 via the exported real `buildControlCenter`; browser remains loaded and displays a disabled `Not configured` option.

Add one representative malformed candidate for each closed section: scores, gates, settings, and control-center. Each must return exact section-specific HTTP 422, and its captured response must produce only the fixed browser load-error copy.

Expected executed assertions are exactly 177 real API responses (`19×9 + 2 + 4`) and 63 emitted-browser loads (`19×3 + 2 + 4`). Increment a counter only after the case-specific assertion passes. Control-center cases must execute the exported real `buildControlCenter`; they must not use `buildControlCenterImpl`.

**Step 2: Run RED**

Run:

```bash
cd apps/life-call
node --test lib/panel-privacy-contract.test.js
```

Expected: FAIL because the closed policy, response boundary, and compatibility behavior do not exist.

**Step 3: Add the smallest deterministic harness**

Use only synthetic fixtures. Inject hostile source values through existing store/provider dependencies. For the four representative malformed DTOs, use one direct-call-only response-candidate transform after the real reader/builder executes. Never accept the transform from URL, headers, cookies, or body.

**Step 4: Re-run RED and commit the test-only contract**

The test must still fail for product behavior, not harness syntax. Commit and push before Task 2.

## Task 2: Implement the closed API presentation boundary

**Files:**

- Create: `apps/life-call/lib/panel-display-policy.js`
- Create: `apps/life-call/lib/panel-presentation.js`
- Create: `apps/life-call/lib/panel-display-policy.test.js`
- Modify: `apps/life-call/lib/panel-api.js`
- Modify: `apps/life-call/lib/user-command.js`
- Modify: `apps/life-call/lib/panel-api.test.js`
- Modify: `apps/life-call/lib/panel-control-center.test.js`

**Step 1: Add focused RED tests**

Prove all 19 synthetic secret values are rejected or projected safely, including provider tokens, webhook secrets, PEM private keys, and credential-bearing database URLs. Prove `call_language=null` is accepted by settings and control-center. Prove malformed scores, gates, settings, and control-center produce exactly:

```json
{"error":"section_unavailable","section":"settings"}
```

with the requested section substituted and HTTP 422.

**Step 2: Run RED**

Run:

```bash
cd apps/life-call
node --test lib/panel-display-policy.test.js lib/panel-api.test.js lib/panel-control-center.test.js lib/panel-privacy-contract.test.js
```

Expected: FAIL on the missing policy/projection and exact response behavior.

**Step 3: Implement minimal GREEN**

- Project timeline source records to `date`, `timezone`, and safe human sentences/statuses.
- Project ledger records to fixed labels, date, formatted amount, and a query-free HTTPS link or `null`.
- Validate closed scores/gates/settings/control-center DTOs immediately before serialization.
- Return HTTP 422 with only `error` and `section` when a closed DTO cannot be produced.
- Allow only `null`, `ja`, or `en` for `call_language`.
- Replace the control-center identity display name with `Life Manager user`.
- Remove the existing `buildControlCenterImpl` bypass from production response construction.
- Keep all behavior read-only and user-scoped.

**Step 4: Run GREEN and regression**

Run:

```bash
cd apps/life-call
node --test lib/panel-display-policy.test.js lib/panel-privacy-contract.test.js lib/panel-api.test.js lib/panel-api-score-semantics.test.js lib/panel-control-center.test.js lib/panel-score-semantics.test.js
```

Expected: all pass, including exact execution totals and zero source echo.

**Step 5: Commit and push**

Commit only the API/policy/product changes and their tests. Fetch before push.

## Task 3: Implement emitted-browser fail-closed UX

**Files:**

- Modify: `apps/life-call/lib/panel-ui.js`
- Modify: `apps/life-call/lib/panel-ui.test.js`
- Create: `apps/life-call/lib/panel-privacy-browser.test.js`

**Step 1: Add browser RED tests**

Execute the emitted panel script, not direct renderer copies. Feed only captured API responses through `loadPanelSection` and assert:

- timeline, scores, ledger, gates, and settings render human-language content;
- HTTP 422 renders fixed load-error copy only;
- no raw JSON, stack traces, internal table/prompt names, full identity, or synthetic secret appears;
- settings `call_language=null` renders exactly `未設定`;
- control-center `call_language=null` renders a disabled `Not configured` placeholder;
- unsafe ledger links create no anchor.

**Step 2: Run RED**

Run:

```bash
cd apps/life-call
node --test lib/panel-ui.test.js lib/panel-privacy-browser.test.js lib/panel-privacy-contract.test.js
```

Expected: FAIL on old raw renderers and null placeholder behavior.

**Step 3: Implement minimal GREEN**

Embed the shared validators and sanitizers in the emitted script, render only projected DTO fields, keep safe fixed fallback copy, and preserve the five-section order and responsive one-column layout.

**Step 4: Run full local verification**

Run:

```bash
cd apps/life-call
npm run test:panel
npm run eval:panel-privacy
npm test
```

Also run `git diff --check` and a scoped secret scan over the branch diff.

**Step 5: Commit and push**

Commit the browser/UI closure and push before review.

## Task 4: Fresh review, production L3, and SSOT closure

**Files:**

- Modify only after evidence passes: the canonical Life Manager build/spec SSOT row for PANEL 8h.
- Create local evidence outside Git: `/Users/anicca/.codex/evidence/panel-8h-production-l3.json` with mode `0600`.

**Step 1: Fresh task review**

Give a fresh reviewer the plan, diff, RED/GREEN commands, and focused privacy-eval output. Fix every Critical/Important finding with another RED/GREEN cycle, commit, and push.

**Step 2: Fresh final review**

Run a second independent review over the completed branch. Require no Critical/Important findings.

**Step 3: Merge through a PR**

Use a PR, wait for required checks, merge, and verify `origin/main` contains the merge.

**Step 4: Production L3**

Verify the deployed commit, authenticated API responses, actual production data boundaries, and full-screen mobile plus desktop screenshots. Confirm five sections, exact null behavior where applicable, zero secret/raw/internal echo, user isolation, and no mutation/provider side effects.

**Step 5: Close SSOT**

Update only the canonical PANEL 8h row with immutable commit, deployment, API/browser/eval counts, screenshot/evidence hashes, and next remaining item. Commit, push, PR, merge, and verify `origin/main`.
