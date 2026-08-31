# Connector Peatix Confirm Kana Fill Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Edit only the two owned Peatix browser-provider files; do not change native identity, routing, evidence, or scheduling.

**Goal:** Fill the two measured Peatix confirm-page Katakana identity controls from the private in-memory attendee profile, require Peatix's own form validation to pass, then preserve the existing one-click and exact parent-readback boundary.

**Architecture:** Extend only the private provider profile contract with validated `family_name_kana` and `given_name_kana`. After the existing exact event/button confirm check, locate the two measured controls by their actual `name` attributes, fill once, and ask the page's existing jQuery validator for a Boolean result. A false/unavailable validator stops before the final external effect. A true result permits the existing final click exactly once; success still comes only from independent same-event readback.

**Tech Stack:** Node.js CommonJS, `node:test`, Playwright-compatible supplied page API.

## Ponytail gate and measured contract

- **Reuse:** frozen private attendee profile, exact Peatix event/ticket/button gates, supplied owned page, Playwright fill, Peatix jQuery validation, and parent readback.
- **Measured live DOM:** confirm controls have `name=lastname_edit` and `name=firstname_edit`; their DOM ids are different, so guessed `#lastname_edit/#firstname_edit` is invalid. Both rules are exactly `required,kanaAlphabet`. Filling the private family/given Katakana values through exact name selectors produced intended-value equality true/true, lengths 3/4, `form.valid()=true`, and empty error list with Submit 0.
- **Do not build:** transliteration, generic name mapping, alternate selectors, direct form submit, synthetic click, retry/second click, new page/session/target, readback expansion, evidence recovery, Calendar, Telegram, schedule, or support for another candidate.
- **Plan size:** two files; target production delta under 30 LOC and focused test delta under 45 LOC.

## Global constraints

- Provider profile independently requires both fields to be 1–100 characters of full-width Katakana plus prolonged sound mark, with no trimming/coercion/inference.
- Locate exactly one visible `#confirm-form [name="lastname_edit"]` and one visible `#confirm-form [name="firstname_edit"]`; missing, duplicate, hidden, or changed controls fail before final click.
- Fill family into `lastname_edit` and given into `firstname_edit` exactly once.
- Require exact same-page Peatix jQuery `#confirm-form` validation to return true after fill. False, missing jQuery/form, or evaluation error fails before final click.
- Do not return, log, persist, hash, or serialize identity values.
- Final external click remains at most one. No retry after ambiguity.
- `registered` remains exact parent readback only; click or validation success is never registration evidence.

---

### Task 1: Fill and validate the measured confirm identity controls

**Files:**
- Modify: `apps/mr-bot/lib/peatix-browser-provider.test.js`
- Modify: `apps/mr-bot/lib/peatix-browser-provider.js`

- [x] **Step 1: Add focused failing measured-flow coverage**

Extend the synthetic attendee profile with invented Katakana family/given values. Make the fixture expose the two controls only under the exact scoped `name` selectors and record their fills. Assert the measured successful flow fills ticket/name/email/privacy, then family/given, obtains provider validation true, clicks final exactly once, and returns exact registered readback. Assert neither values nor keys appear in the outcome.

- [x] **Step 2: Add destructive-boundary regressions**

Cover missing/invalid Kana profile, missing/duplicate/hidden confirm control, selector drift to guessed ids, validation false, missing validator/form, and evaluation failure. Assert final click 0 and privacy-safe non-success for every case. Preserve the existing ambiguous post-click case as one final click and non-success.

- [x] **Step 3: Run focused RED**

```bash
node --test apps/mr-bot/lib/peatix-browser-provider.test.js
```

Expected: the new exact fill/validation assertions fail because production ignores Kana profile fields and clicks before filling them.

- [x] **Step 4: Implement the minimum profile and confirm fill**

Extend the private profile validator, fill the two exact scoped controls once, and add one privacy-safe page evaluation returning only `{ valid: Boolean }`. Keep the existing final click and readback logic unchanged except that they execute only after `valid=true`.

- [x] **Step 5: Run focused and required integration GREEN**

```bash
node --test apps/mr-bot/lib/peatix-browser-provider.test.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  skills/connector/test/native-entrypoint.test.js \
  skills/connector/test/minimal-production-contract.test.js
node --check apps/mr-bot/lib/peatix-browser-provider.js
git diff --check
```

Expected: all pass, no network or external write, no private identity in outputs or diff.

- [x] **Step 6: Report exact RED/GREEN evidence to Sol**

Do not commit or push. Sol performs fresh review, commits/pushes the approved two-file implementation, updates the SSOT, then runs one official foreground wake with scheduling still unloaded.
