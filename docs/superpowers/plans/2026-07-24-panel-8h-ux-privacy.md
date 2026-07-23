# PANEL 8h UX / Privacy Closure Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to execute this plan task-by-task, with RED/GREEN evidence and fresh reviews.

**Goal:** Ship the authenticated Life Manager panel with five human-readable sections on mobile and desktop, while preventing raw provider payloads, internal diagnostics, secrets, and personal identity text from reaching API responses or the emitted browser.

**Architecture:** Add a closed presentation-policy boundary shared by the panel API and emitted browser. Project timeline and ledger source records into small safe DTOs, validate scores/gates/settings/control-center before serialization, and fail closed with an exact section error. Preserve `call_language=null` as a valid persisted state. Verify the boundary through real `handlePanelApiRequest` calls and browser execution of captured responses.

**Tech Stack:** Node.js CommonJS, `node:test`, direct request/response fixtures, emitted panel JavaScript executed with `vm`, Playwright for authenticated mobile/desktop evidence.

**Historical input:** The dirty worktree `.worktrees/sol-panel-8h-ux-privacy` is read-only. Its v5 closure package defines the three unresolved findings and deterministic totals. Do not create or modify VCSDD artifacts.

**External security basis:**

- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html — access tokens, passwords, database connection strings, and encryption keys should not be logged directly.
- GitHub Secret scanning: https://docs.github.com/ja/code-security/secret-scanning/introduction/about-secret-scanning — scans for API keys, passwords, tokens, private keys, connection strings, and generic API keys.
- Gitleaks default configuration: https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml — established provider patterns cover Google, OpenAI, private keys, Stripe, and Telegram credentials.

---

## Task 1: Close the executable presentation contract

**Files:**

- Create: `apps/life-call/eval/panel-v5-contract.js`
- Create: `apps/life-call/eval/panel-v5-matrix-harness.js`
- Create: `apps/life-call/eval/run-panel-v5-matrix-eval.js`
- Create: `apps/life-call/lib/panel-v5-contract.test.js`
- Modify: `apps/life-call/package.json`

**Step 1: Write the failing contract test**

Encode the retained hostile path/variant matrix, the 19-value synthetic secret corpus, the nine presentation channels, and the two positive `call_language=null` compatibility cases. Assert deterministic generation and these derived totals:

- 536 negative cases over 139 paths
- 536 policy-unit executions
- 536 real API executions
- 422 emitted-browser executions
- 2/2/2 positive compatibility executions

Each API count increments only after a real `handlePanelApiRequest` response has been captured and asserted. Each browser count increments only after `loadPanelSection` consumes that captured response. Control-center cases must execute the exported real `buildControlCenter`; they must not use `buildControlCenterImpl`.

**Step 2: Run RED**

Run:

```bash
cd apps/life-call
node --test lib/panel-v5-contract.test.js
```

Expected: FAIL because the closed policy, response boundary, and compatibility behavior do not exist.

**Step 3: Add the smallest deterministic harness**

Use only synthetic fixtures. Inject hostile source values through existing store/provider dependencies. For hostile DTO shapes impossible from a valid source, use one direct-call-only response-candidate transform after the real reader/builder executes. Never accept the transform from URL, headers, cookies, or body.

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
node --test lib/panel-display-policy.test.js lib/panel-api.test.js lib/panel-control-center.test.js lib/panel-v5-contract.test.js
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
node --test lib/panel-display-policy.test.js lib/panel-v5-contract.test.js lib/panel-api.test.js lib/panel-api-score-semantics.test.js lib/panel-control-center.test.js lib/panel-score-semantics.test.js
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
node --test lib/panel-ui.test.js lib/panel-privacy-browser.test.js lib/panel-v5-contract.test.js
```

Expected: FAIL on old raw renderers and null placeholder behavior.

**Step 3: Implement minimal GREEN**

Embed the shared validators and sanitizers in the emitted script, render only projected DTO fields, keep safe fixed fallback copy, and preserve the five-section order and responsive one-column layout.

**Step 4: Run full local verification**

Run:

```bash
cd apps/life-call
npm run test:panel
npm run eval:panel-v5
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

Give a fresh reviewer the plan, diff, RED/GREEN commands, and matrix output. Fix every Critical/Important finding with another RED/GREEN cycle, commit, and push.

**Step 2: Fresh final review**

Run a second independent review over the completed branch. Require no Critical/Important findings.

**Step 3: Merge through a PR**

Use a PR, wait for required checks, merge, and verify `origin/main` contains the merge.

**Step 4: Production L3**

Verify the deployed commit, authenticated API responses, actual production data boundaries, and full-screen mobile plus desktop screenshots. Confirm five sections, exact null behavior where applicable, zero secret/raw/internal echo, user isolation, and no mutation/provider side effects.

**Step 5: Close SSOT**

Update only the canonical PANEL 8h row with immutable commit, deployment, API/browser/eval counts, screenshot/evidence hashes, and next remaining item. Commit, push, PR, merge, and verify `origin/main`.
