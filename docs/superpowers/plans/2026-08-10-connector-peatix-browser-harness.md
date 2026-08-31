# Peatix Browser Harness Same-page Fallback Plan

> **For Luna:** Use Superpowers test-driven-development. Own only the four implementation/test files listed below. Do not edit the SSOT, launchd state, browser profile, Connector state, private profile, evidence, or any external system.

**Goal:** Route Peatix `unknown_required_field` through the existing bounded same-page Browser Harness while keeping every entered or selected answer parent-owned.

**Architecture:** Reuse the existing production Harness, proposer, page observer, action executor, private Luma form profile, and in-memory Peatix attendee profile. Add Peatix only to the existing provider registry. The model may choose one control/action, but it never receives private values and may not invent a free-text, select, checkbox, or radio answer. The parent resolver supplies name/email/Kana, an exact `form_answers` match, an explicitly approved answer value, or organizer privacy consent; otherwise the action fails safely before submit. Peatix parent readback remains the only completion authority.

**Ponytail scope:** Four files are necessary because the provider-neutral Harness contract and its production dependency composition are separate boundaries. Soft target: production <= 55 LOC changed, tests <= 90 LOC changed. No new module, store, schema, service, target, page, session, retry, or prompt field.

**Files:**

- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`
- Modify: `apps/mr-bot/lib/connector-minimal-production.js`
- Modify: `apps/mr-bot/lib/connector-minimal-production.test.js`

## Contracts

1. RED first: Peatix proposer input and Peatix `runFallback` are currently rejected; production factory does not supply `peatixWorkflow` or Peatix identity to the Harness.
2. Allow only existing providers `luma`, `connpass`, `peatix`; unknown providers remain invalid.
3. The proposer prompt names only the validated provider and sanitized controls. It receives no page object, websocket, candidate identity, private value, profile, cookie, or secret.
4. The production Harness selects the matching provider workflow and uses that workflow's `readProviderState` after every successful action.
5. Replace the Luma-only resolver boundary with a provider-neutral private resolver while keeping a backwards-compatible export only if an existing consumer requires it.
6. Parent-owned value policy:
   - exact name/email labels resolve from the in-memory Peatix attendee profile;
   - exact family/given Kana labels resolve from that profile;
   - phone and exact question labels resolve from the existing mode-0600 form profile;
   - select values resolve only from an exact `form_answers` question match;
   - checkbox/radio is permitted only for explicit organizer-privacy consent or when its visible option label exactly matches an approved `form_answers` value;
   - missing/unmatched values return null and `performAction` returns `failed` before DOM action.
7. Do not log, persist, or send values. Do not generate answers. Do not click the final Peatix confirmation in tests or production outside the existing bounded flow.
8. Preserve one claimed page, max 10 steps, no browser/session/target creation, and parent `registered|pending` completion.

## TDD execution

1. Add focused RED tests for Peatix proposer acceptance, Peatix workflow readback routing, factory dependency composition, identity/form-answer resolution, and rejection of an unapproved radio/checkbox.
2. Run the focused tests and record that they fail for the missing Peatix route/composition.
3. Implement the smallest changes satisfying the contracts.
4. Run GREEN:

```bash
node --test \
  apps/mr-bot/lib/connector-production-browser-harness.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js
```

5. Run the adjacent provider/router/native focused suite and syntax checks. Report RED evidence, GREEN counts, exact changed LOC, and any residual live limitation to Sol. Do not commit or push; Sol owns verification, SSOT, commit, and push.

## Live acceptance owned by Sol

After fresh review and push, Sol runs one official schedule-disabled foreground wake. Acceptance is either a new parent-verified Peatix `registered|pending` state or a more specific safe failure proving no unapproved answer/final confirmation occurred. Sol then audits the Peatix dashboard, external-effect counts, cleanup, Gateway positive ID, updates the Active SSOT, commits, and pushes before continuing.

## Implementation status

- [x] RED reproduced the missing Peatix proposer, fallback, resolver, and factory contracts.
- [x] Luna implemented the bounded provider route and parent-owned value policy.
- [x] Primary Sol and fresh Sol review found and closed cross-question, Kana/privacy, and cached-provider regressions.
- [x] Focused 20/20, adjacent 23/23, native 7/7, syntax, and diff checks pass.
- [ ] Sol live acceptance remains pending until the pushed official foreground wake is measured.
