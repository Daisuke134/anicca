# Connector Peatix Parent-owned Japanese Full-name Plan

**Status:** GREEN、fresh re-review `ship`。live acceptanceはSSOT進捗268以降で継続する。

> **For Luna:** Use Superpowers test-driven-development. Own only the six production/test files below. Do not edit docs/spec, commit/push, browser/state/private profile, or external systems.

**Goal:** Resolve the live Peatix fields `お名前（漢字）` and `お名前（ひらがな）` from the existing mode-0600 identity SSOT without exposing private values to the model or inventing questionnaire answers.

**Measured live boundary:** Official wake `wake-57b1fcec2b743b251614c7a6` crossed the optional/method defect but candidate 3 stopped on exact required controls `お名前（漢字）` and `お名前（ひらがな）`; phone was already parent-resolvable. A no-submit dedicated diagnostic reproduced those two unresolved booleans. Candidate 2 instead requires subjective Shibuya/motivation/source/privacy answers, so it remains fail-closed.

**Architecture:** Extend the existing private identity loader to read validated `candidate.name_ja` beside the already validated Katakana family/given names. Derive a Hiragana full name deterministically from only the exact Katakana range with a defined Hiragana counterpart. Add both values to the in-memory Peatix attendee profile, and map only the two measured exact labels in the parent resolver. The agent continues to receive sanitized label/required/completed fields only. After registered readback and before evidence capture, replace the live DOM with a fixed local privacy-safe receipt containing only validated provider/status/event reference; screenshot, durable artifact, and Telegram photo consume only that receipt.

**Ponytail scope:** Six files; production <= 70 added LOC, tests <= 90 added LOC. Reuse the current private SSOT, attendee profile, resolver, evidence chain, and tests. No new file/store/schema/service/profile write/model prompt/retry/provider/questionnaire default or image-processing dependency.

**Files:**

- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.js`
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.test.js`

## Contracts

1. RED first: the native attendee profile lacks Japanese and Hiragana full-name values, and the resolver returns null for the two measured exact labels.
2. Read `candidate.name_ja` only from the existing mode-0600 job-search profile. Require the raw value itself to be trimmed, non-empty, <=200, and free of C0, DEL, and C1 control characters; any missing/invalid value fails the existing production config closed.
3. Accept Katakana family/given parts only from `U+30A1..U+30F6` plus `U+30FC`. Convert `U+30A1..U+30F6` by the defined `-0x60` mapping, preserve the long-vowel mark, and join the two parts with one ASCII space. Reject `ヷ..ヺ` and every other character rather than emit undefined/non-equivalent Hiragana. Do not call a model or transliteration service.
4. The frozen in-memory `peatixAttendeeProfile` adds only `name_kanji` and `name_hiragana`. Neither may enter wake input, action history, logs, error text, or durable JSON state.
5. The parent resolver maps exact normalized labels `お名前（漢字）` to `name_kanji` and `お名前（ひらがな）` to `name_hiragana`. Do not broaden generic `氏名`, `フリガナ`, organization, motivation, affiliation, discovery-source, consent, or arbitrary question matching.
6. `completeEvidence` requires `page.setContent` and, after registered readback but before screenshot, replaces the page DOM with a self-contained fixed receipt. It contains only the validated provider, provider status, and event reference; no candidate title, URL, form value, profile value, original DOM text, external resource, script, or interpolation via raw HTML. The existing `{type:"png", fullPage:true}` screenshot, evidence store, SHA, and Telegram photo use only the replaced receipt. If replacement fails, screenshot/Calendar/Telegram/bundle writes are zero.
7. Preserve all current exact name/email/Kana/privacy/form-answer behavior, Calendar/evidence/Telegram ordering after a valid privacy-safe PNG, and fail-closed behavior for subjective candidate-2 questions.

## TDD and verification

1. Add focused RED for valid profile derivation, invalid/missing/C1 Japanese name rejection, unmappable Katakana rejection, exact two-label resolution, near-label rejection, and no-private-value boundary.
2. Add evidence RED proving DOM replacement happens before screenshot, the replacement payload contains only the three safe fields, screenshot follows replacement, and replacement failure causes no screenshot/store/Calendar/Telegram/bundle effect.
3. Record RED before production edits; implement the smallest GREEN.
4. Run native entrypoint, Harness/factory/runner/evidence adjacent, syntax, and diff checks.
5. Return RED/GREEN evidence and LOC. Sol owns fresh re-review, SSOT, commit/push, and exactly one next official foreground wake.
