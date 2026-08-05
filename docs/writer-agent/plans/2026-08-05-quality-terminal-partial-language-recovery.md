# Partial-language quality terminal recovery

## Goal

`done="a current-hash terminal block in either one or both languages is classified as a bounded same-day quality replacement instead of same-jst-day-unclassified-run"`

## Measured defect

Live run `daily-2026-08-05` has JA editorial FAIL, EN full PASS, `block_freeze`, no publication state, and a successful generation receipt. `terminal_quality_finished_at` nevertheless requires `ready=false` plus an editorial/reader failure for both languages, so the valid EN PASS makes the run unclassifiable and poisons the daily slot.

## TDD contract

- RED reproduces JA FAIL plus EN PASS and expects `new-quality-replacement` with feedback only from JA.
- Failed languages require current evaluation, current identity, `ready=false`, and an editorial or reader failure.
- Non-failed languages require current evaluation, current identity, and `ready=true`; an ambiguous or stale PASS remains fail closed.
- Existing both-language failure, destination-side-effect refusal, daily replacement limit, and exact completion tests remain unchanged.
- After promotion, re-evaluate the actual live run read-only before triggering its existing owner.
