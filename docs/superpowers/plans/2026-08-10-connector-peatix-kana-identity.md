# Connector Peatix Kana Identity Boundary Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Edit only the two owned native-entrypoint files plus the private identity SSOT; do not edit the Peatix provider in this slice.

**Goal:** Supply the measured Peatix-required family/given name in full-width Katakana through the existing private in-memory attendee profile without placing private identity in code, logs, state, or tests.

**Architecture:** Keep the shared environment and public Connector state unchanged. Read two explicit Katakana identity fields from the existing mode-0600 private identity SSOT at `~/.config/anicca/job-search/profile.json`, validate them fail-closed, and add them only to the frozen `peatixAttendeeProfile` factory input. The wake input, action history, audit, report, and repository never receive their values.

**Tech Stack:** Node.js CommonJS, `node:test`, private JSON identity SSOT.

## Ponytail gate and measured contract

- **Reuse:** existing private identity SSOT, native production config boundary, frozen Peatix attendee profile, and no-PII wake contract.
- **Measured requirement:** Peatix `/confirm` rejects only `lastname_edit` and `firstname_edit`; each has jQuery rules `required,kanaAlphabet`. Existing private application evidence contains exactly two full-width Katakana name segments after its label and can seed the private SSOT without invention.
- **Do not build:** transliteration, inference from Romaji/Kanji, generic identity service, new env keys, repository secrets, form filling, Submit, retry, readback, Calendar, Telegram, or schedule.
- **Plan size:** two repository files, target production delta under 35 LOC and test delta under 45 LOC; one mode-0600 private JSON update outside Git.

## Global constraints

- The source identity file must be an absolute regular file, mode 0600, bounded in size, valid JSON, and contain exactly one nonempty family and given value.
- Accept only full-width Katakana plus prolonged sound mark, with no controls, Latin, Kanji, Hiragana, digits, or punctuation; bound each part to 1–100 characters.
- Never derive or guess pronunciation. Copy the two already-recorded values from the existing private application answer into the private SSOT.
- Do not return, log, hash, persist, or serialize the private values beyond the in-memory frozen factory profile.
- Missing/malformed identity must fail before dependency creation or browser work.
- The minimal wake input must remain free of all attendee profile fields and values.

---

### Task 1: Add the private Kana identity to the native factory boundary

**Files:**
- Modify: `skills/connector/test/native-entrypoint.test.js`
- Modify: `skills/connector/native-pass.js`
- Private config only: `~/.config/anicca/job-search/profile.json` (mode 0600, never Git)

- [x] **Step 1: Add focused failing factory-boundary tests**

Create a temporary mode-0600 `$HOME/.config/anicca/job-search/profile.json` fixture containing `candidate.name_kana.family` and `.given`. Assert the factory receives both fields in the frozen `peatixAttendeeProfile`, while the wake input and serialized outcomes contain neither keys nor values.

- [x] **Step 2: Add fail-closed tests**

Cover missing file, permissive file mode, invalid JSON, missing family/given, empty value, Hiragana, Kanji, Latin, digit/punctuation, controls, and overlength. Assert dependency creation and browser work remain 0.

- [x] **Step 3: Run focused RED**

```bash
node --test skills/connector/test/native-entrypoint.test.js
```

Expected: new profile assertions fail because the native boundary does not read or carry Katakana identity.

- [x] **Step 4: Implement the minimum private reader**

Add a private bounded reader/validator in `native-pass.js`. Resolve the identity SSOT under the effective home, require the exact object shape, and add only `family_name_kana` and `given_name_kana` to the frozen `peatixAttendeeProfile`.

- [x] **Step 5: Seed the private SSOT without exposing values**

Read the existing submitted application answer locally, extract the two full-width Katakana segments after the `フリガナ` label, and update `candidate.name_kana.family/given` in the mode-0600 private profile using `apply_patch`. Do not echo the values or include them in any report, diff, log, test, commit, or Telegram message. Validate only key presence, character class, lengths, and file mode.

- [x] **Step 6: Run focused GREEN and privacy checks**

```bash
node --test skills/connector/test/native-entrypoint.test.js
node --check skills/connector/native-pass.js
git diff --check
git diff -- skills/connector/native-pass.js skills/connector/test/native-entrypoint.test.js
```

Expected: all pass; diff contains fixture-only invented test values and no real identity.

- [x] **Step 7: Report exact RED/GREEN evidence to Sol**

Do not commit or push. Sol performs fresh review, commits/pushes the approved two-file implementation, then plans the separate Peatix confirm-form filling slice.
