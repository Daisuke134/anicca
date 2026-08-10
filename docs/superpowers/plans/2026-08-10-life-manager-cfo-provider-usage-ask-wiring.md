# CFO-2a2.3c1 Ask Candidate Usage Wiring Plan

**Status:** COMPLETE — verified and closed before CFO-2a2.3c2.

> Luna owns production code/tests/commands. Sol owns planning, review, verification, closure, commit, and push.

**Goal:** Route both real Gemini calls in the ask candidate search through the verified span/store helper.

**Architecture:** `askTick` already owns `uid`, `supaUrl`, and `supaKey`. Pass one closed usage context through
`agentSearchCandidate` to the existing default `geminiRaw`. The raw function separates the network request from its
legacy catch: with usage context it calls `captureGeminiGenerateContent`; without context it preserves `{}` fallback.
Injected raw functions keep working and merely receive an ignored third argument.

## Ponytail gate

- Modify only `apps/life-call/lib/ask.js` and `lib/lm-p0.test.js`.
- Soft target: 20 production + 50 test additions; two files/70 additions.
- No new file/dependency/export/framework, scheduler/server change, other Gemini path, retry, pricing, migration,
  production request, local E2E, DB apply, or Telegram send.

## Task 1 — Wire the two ask candidate calls

1. RED uses the non-injected `agentSearchCandidate` path with a restored-after-test `global.fetch` stub. Return two
   literal Gemini responses with provider usage and two matching closed RPC receipts. Before wiring, zero RPC calls
   prove the default path does not capture usage.
2. In `ask.js`, import `captureGeminiGenerateContent`. Refactor `geminiRaw` so one inner async request performs the
   existing fetch and JSON parse. With no third argument, catch and return `{}` exactly as before. With a third
   `usage` argument, call the helper with explicit context fields and `{ storeOptions }`; do not catch its fixed error.
3. `agentSearchCandidate` passes `deps.providerUsage` as the third argument on both grounded-research and extraction
   calls. `askTick` supplies exactly:

```js
{
  owner_id: uid,
  financial_unit_id: "life_manager_saas",
  request_model: "gemini-2.5-flash",
  storeOptions: { supaUrl, supaKey },
}
```

4. GREEN assertions: the existing candidate result is unchanged; two Gemini requests produce two RPC appends with
   different non-zero trace IDs. Both Gemini request bodies exclude `owner_id`, `financial_unit_id`, `supaUrl`,
   `supaKey`, and `storeOptions`. RPC receipts echo their trace IDs. A separate compact default-path case makes the
   first RPC return non-2xx and proves exact `cfo_provider_usage_span_failed:store` propagation rather than `{}`.
   Keep one existing injected-raw assertion that both calls receive the same exact closed usage object.
5. Run `node --test lib/lm-p0.test.js`, `npm run test:cfo`, `npm test`, `node --check lib/ask.js`, and
   `git diff --check`. Confirm two files/70 additions. Do not commit/push; return RED/GREEN totals and scope to Sol.

## Completion evidence

- RED: focused suite 12/15, with the three intended missing-wiring failures.
- GREEN: focused 15/15, CFO 263/263, full suite exit 0, syntax and diff checks clean.
- Scope: only the two planned files, 70 additions and 7 deletions.
- Fresh Sol review: Critical 0, Important 0, ship.
