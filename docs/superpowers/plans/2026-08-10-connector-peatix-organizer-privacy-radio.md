# Connector Peatix organizer privacy radio plan

## Goal

Peatixが親`dl.field.required`で表現する一択の主催者privacy policy同意を、既存private profileの
`accept_organizer_privacy: true`だけを根拠に検出・選択し、confirm stepへ進める。

## Measured failure

- candidate: `5075819 / 6536845`; dashboard registration count 0
- name/email: filled exactly, HTML validity valid
- form submit stays on `/form` with public error「必須項目にすべて入力してください。」
- one visible error radio, one option「確認し同意する。」; input itself has no `required`
- nearest container: `dl.field.required`
- public prompt: organizer privacy policy read/confirmed; no link、marketing、Peatix terms、data-sharing text
- provider reason: `confirm_navigation_failed`; final confirm click 0

## Ponytail scope

- files: provider + focused test, 2 files
- production LOC soft target: 8
- test LOC soft target: 18
- reuse: existing profile consent、form field classifier、`control().check()`、CSS escaping
- defer: generic radio questions、Peatix Browser Harness、safe reason persistence、other candidates/providers

## TDD

1. RED: a visible one-option radio whose closest `dl.field.required > dt` is an organizer privacy-policy confirmation is detected as privacy and checked before form submit.
2. GREEN: extend form observation only for this measured structural/semantic contract. Do not classify generic single radios or marketing/terms/event questions as privacy.
3. Fail closed for zero/multiple options, ambiguous prompts, more than one privacy group, false/missing profile consent, unknown required questions.
4. Preserve special-ID escaping, name/email validation, cross-event confirm, ambiguous readback and final-effect safety.
5. Run focused and Peatix workflow/native/minimal production/runner regressions, syntax, diff check; push and fresh review.
6. Only after review ship, rerun official foreground wake with schedule unloaded and dashboard count 0.

## Live acceptance

Provider parent readback becomes `registered`; provider receipt, Calendar independent readback, full-page PNG/SHA,
Telegram message/photo positive IDs, and exactly one immutable applied bundle share the official wake lineage.
