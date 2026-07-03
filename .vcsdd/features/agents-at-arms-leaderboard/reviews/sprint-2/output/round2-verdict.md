# VCSDD Sprint-2 Round-2 Combined Re-Review — agents-at-arms-leaderboard

Reviewer: fresh-context adversary (disk-only). **No Bash tool in this session** (tool list =
Read/Grep/Glob/Write only) — disclosed per honesty rule, not fabricated. Verified instead by full
statement-trace of every RED assertion against the actual implementation + ground-truth deps, and
cross-checked against `.vcsdd/features/agents-at-arms-leaderboard/evidence/sprint-2-green-phase.log`
(74/74 pass, timestamped 2026-07-03T15:54:06Z, post-fix).

## Overall verdict: **PASS**

| Dimension | Verdict |
|---|---|
| Spec Fidelity | PASS |
| Edge Case Coverage | PASS |
| Implementation Correctness | PASS |
| Structural Integrity | PASS |
| Verification Readiness | PASS |

## Disposition of every round-1 finding

| Finding | Disposition | Evidence |
|---|---|---|
| S2-SPEC-FIND-001 | RESOLVED | `apps/landing/supabase/2026-07-instances-leaderboard.sql:18` adds `log_feed jsonb`; `spawn-register.test.js:25` includes `log_feed` in `basePayload()`; test S9.1 (`spawn-register.test.js:48-49`) asserts byte-identity via `canonicalMessage(p)` which includes `log_feed` (`telemetry-verify.js:18`); `schema-migration.test.js:37-39` asserts the column regex. |
| S2-SPEC-FIND-002 | RESOLVED | Spec S9.1 (`sprint-2-behavioral-spec.md:38-46`) now states the exact signature `async registerSpawn({ privateKey, payload, storeDeps, now = ... })` returning `{ message, signature, last_heartbeat }`; `spawn-register.js:9,38` matches verbatim; `spawn-register.test.js:47,53-54` asserts on that exact return shape. |
| S2-SPEC-FIND-003 | RESOLVED | Spec S11.4 added (`sprint-2-behavioral-spec.md:70-77`); `render-dashboard.mjs:47-53` exports pure `shouldRefuseCliWrite({env,fetchOk,fetchThrew})`; `main()` (lines 135-148) routes through it twice (pre-fetch env check, post-fetch fetch-ok check) before any write; unit test `render-dashboard.test.js:83-90` binds to all 4 refuse/allow branches without spawning a subprocess. |
| S2-SPEC-FIND-004 | RESOLVED | `spawn-register.test.js:77-80` now asserts literal `/signer/`, `err.message.includes(wrongId)`, AND the recovered-signer substring — no longer a permissive `/signer|mismatch|id/i`. `spawn-register.js:28` throws a message containing all three tokens. |
| S2-SPEC-FIND-005 | RESOLVED | Spec S11.5 added (`sprint-2-behavioral-spec.md:78-83`); `render-dashboard.test.js:92-104` models a pre-migration row with all 7 additive columns explicit `null` (including `log_feed:null`) and asserts `renderDashboard` doesn't throw. |
| S2-IMPL-FIND-001 (critical) | RESOLVED | `render-dashboard.mjs:120-125` exports `isDirectCliInvocation(argv, importUrl)` comparing `path.resolve(argv[1])` to `fileURLToPath(importUrl)` — correct for both absolute and relative argv (the real cron/GH-Action shape). `render-dashboard.mjs:126` gates `main()` through it. `render-dashboard.test.js:106-115` unit-tests all 4 cases (absolute true, relative true, wrong script false, missing argv false). |
| S2-IMPL-FIND-002 | RESOLVED | `spawn-register.test.js:97-116` adds two integration tests calling `registerSpawn` directly with `tags:[123]` and `revenue_today_usd(9) > revenue_mo_usd(5)`, both asserting `stub.calls.length === 0`. Traced against `telemetry-schema.js:17-19,20-22`: both cases correctly return `{ok:false, reason:"schema"}`, which `spawn-register.js:33-34` turns into a throw before `upsertInstance` (line 37) is ever reached — the rejection happens strictly before the store call, matching S2-IMPL-FIND-002's requirement. |
| S2-IMPL-FIND-003 | RESOLVED (documented, non-blocking) | `spawn-register.js:18-23,30-32` now carries an explicit rationale comment: the pre-check owns the semantic "signer/id mismatch" error message (needed so S9.2's RED test can bind to a specific string), `verifyTelemetry`'s internal signer check is provably unreachable after the pre-check (dead-but-harmless), and is retained only for its schema+replay checks. This is an acknowledged, justified duplication, not drift risk — no behavior depends on the second check ever firing differently. |
| S2-IMPL-FIND-004 | N/A | No S2-IMPL-FIND-004.json exists on disk (impl-verdict.md's 4th numbered item was S2-IMPL-FIND-003's cleanup restated, not a distinct 004 finding). Nothing outstanding here. |

## Additional adversarial checks performed this round (no new defects found)

- `telemetry-verify.js:15-19` `canonicalMessage` conditionally appends `tags`/`revenue_today_usd`/`revenue_by_source`/`log_feed` only `if !== undefined` — base-only messages (sprint-1 payloads without these fields) remain byte-identical, so cross-language/back-compat signing is preserved (INV-BACKCOMPAT held).
- `spawn-register.js` calls `verifyTelemetry(message, signature, { now: payload.ts, lastTs: 0 })` — using `payload.ts` as `now` rather than a real clock means the replay/staleness window check (`telemetry-verify.js:30-31`) is effectively a no-op inside `registerSpawn` (always `p.ts > payload.ts+5` false, `payload.ts - p.ts > 60` false). This is benign for a client-side self-signed heartbeat (the server-side netlify verifier is the one that enforces staleness/replay against a real `now`/`lastTs` per sprint-1), and is consistent with spec S9.1(c)'s wording ("verifies locally... schema + replay window" — the schema half is the operative check here). Not filed as a new finding: no requirement or test claims `registerSpawn` itself enforces replay-freshness against wall-clock time: that is out of scope for this client helper by design (S9.2 explicitly scopes S9's local verification to schema).
- `isDirectCliInvocation` correctness re-derived independently: for the cron shape (`node apps/landing/scripts/render-dashboard.mjs` from repo root), `process.argv[1]` is relative to `process.cwd()`; `path.resolve()` resolves against the SAME `process.cwd()` at runtime, so it converges to the absolute script path — matches `fileURLToPath(import.meta.url)`. Sound for the stated production invocation shape.
- Regression: none of the fixes touch `telemetry-schema.js` validation for the base 11 fields, `telemetry-aggregate.js`, or `dashboard-sync.js` — sprint-1's R1-R12 contract is untouched by this round's diffs (only additive `if (o.tags !== undefined)`-style branches were added to `telemetry-schema.js`, all gated on `!== undefined`).

## Must-fix

No must-fix. All 9 round-1 findings are resolved on disk with binding tests; the evidence log's
74/74 green count is consistent with the statement-trace performed here.
