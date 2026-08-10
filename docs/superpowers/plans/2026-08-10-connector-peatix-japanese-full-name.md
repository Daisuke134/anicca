# Connector Peatix Parent-owned Japanese Full-name Plan

> **For Luna:** Use Superpowers test-driven-development. Own only the four production/test files below. Do not edit docs/spec, commit/push, browser/state/private profile, or external systems.

**Goal:** Resolve the live Peatix fields `お名前（漢字）` and `お名前（ひらがな）` from the existing mode-0600 identity SSOT without exposing private values to the model or inventing questionnaire answers.

**Measured live boundary:** Official wake `wake-57b1fcec2b743b251614c7a6` crossed the optional/method defect but candidate 3 stopped on exact required controls `お名前（漢字）` and `お名前（ひらがな）`; phone was already parent-resolvable. A no-submit dedicated diagnostic reproduced those two unresolved booleans. Candidate 2 instead requires subjective Shibuya/motivation/source/privacy answers, so it remains fail-closed.

**Architecture:** Extend the existing private identity loader to read validated `candidate.name_ja` beside the already validated Katakana family/given names. Derive a Hiragana full name deterministically from those exact Katakana parts in the parent process. Add both values to the in-memory Peatix attendee profile, and map only the two measured exact labels in the parent resolver. The agent continues to receive sanitized label/required/completed fields only.

**Ponytail scope:** Four files; production <= 35 added LOC, tests <= 45 added LOC. Reuse the current private SSOT, attendee profile, resolver, and tests. No new file/store/schema/service/profile write/model prompt/browser action/retry/provider/questionnaire default.

**Files:**

- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`
- Modify: `apps/life-manager/lib/connector-production-browser-harness.js`
- Modify: `apps/life-manager/lib/connector-production-browser-harness.test.js`

## Contracts

1. RED first: the native attendee profile lacks Japanese and Hiragana full-name values, and the resolver returns null for the two measured exact labels.
2. Read `candidate.name_ja` only from the existing mode-0600 job-search profile. Require a trimmed non-empty string <=200 with no control characters; any missing/invalid value fails the existing production config closed.
3. Convert each already validated Katakana family/given part to Hiragana with a deterministic Unicode Katakana→Hiragana mapping, preserving the long-vowel mark, and join the two parts with one ASCII space. Do not call a model or transliteration service.
4. The frozen in-memory `peatixAttendeeProfile` adds only `name_kanji` and `name_hiragana`. Neither may enter wake input, action history, evidence, Telegram, logs, error text, or durable state.
5. The parent resolver maps exact normalized labels `お名前（漢字）` to `name_kanji` and `お名前（ひらがな）` to `name_hiragana`. Do not broaden generic `氏名`, `フリガナ`, organization, motivation, affiliation, discovery-source, consent, or arbitrary question matching.
6. Preserve all current exact name/email/Kana/privacy/form-answer behavior and fail-closed behavior for subjective candidate-2 questions.

## TDD and verification

1. Add focused RED for valid profile derivation, invalid/missing Japanese name rejection, exact two-label resolution, near-label rejection, and no-private-value boundary.
2. Record RED before production edits; implement the smallest GREEN.
3. Run native entrypoint, Harness/factory/runner adjacent, syntax, and diff checks.
4. Return RED/GREEN evidence and LOC. Sol owns fresh review, SSOT, commit/push, and exactly one next official foreground wake.
