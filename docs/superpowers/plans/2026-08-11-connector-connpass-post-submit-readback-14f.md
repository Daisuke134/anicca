# Connector Connpass post-submit readback Item 14F plan

## Goal

Stop a Connpass join page's public attendee-section text from impersonating a pending registration, so the Browser Harness waits for a real provider effect instead of navigating away immediately after the final click.

## Measured root cause

- Official wake `wake-963fc9da9e4da332ca9801a5` had Luma `32/32/17/10/0`, Connpass `6/6/6/5/1`, then native cache/direct/Harness actions at 0ms/2,259ms/324ms and post-submit readback at 2ms.
- The runner accepted that readback, navigated to the canonical event page, then failed canonical recovery. Bundle and Connpass receipt/artifact deltas were all zero. A later read-only canonical check returned `absent`; no registration persisted.
- The current join page contains only the final public control `申し込みを確定する`, yet the existing reader returns `pending`. DOM localization found the substring `補欠` only in two visible attendee-section nodes (`補欠者` context), not a user registration status.
- Connpass participant guidance says lottery state is checked on the event detail page after application: [抽選の参加枠に申し込む](https://help.connpass.com/participants/event-lottery) — 「イベント申込後にも、イベント詳細ページで、抽選発表日を確認できます。」

## Ponytail full gate

- Reuse `readConnpassRegistrationStateOnPage`; add no waiter, browser action, cache, state field, selector abstraction, or new service in this slice.
- Change only the existing Connpass provider and its test.
- Preserve exact registered/login/absent/unavailable branches.
- Pending is valid only on an exact canonical event path `/event/<positive integer>/` and only when one visible `innerText` line equals `抽選待ち`, `補欠`, `承認待ち`, or `キャンセル待ち`. Substrings such as `補欠者` and every join-page body marker must not qualify.
- An exact join page with the final submit control and public attendee text returns `unknown`; the existing Harness then continues bounded readback and its one-submit latch still prevents duplicate effect.

## Luna implementation slice

Ownership:

1. `apps/mr-bot/lib/connpass-browser-provider.js`
2. `apps/mr-bot/lib/connpass-browser-provider.test.js`

Soft target: 2 files; production net `-3–+10 LOC`; tests `+25–45 LOC`.

### RED

1. Actual join-shaped DOM with `補欠者` / `補欠者はいません` and only `申し込みを確定する` must return `unknown`, not `pending`.
2. Exact canonical event path with its own exact visible line `補欠` remains `pending`.
3. Canonical substring-only `補欠者` and malformed/zero/non-event paths remain non-pending.

### GREEN and verification

- Replace collapsed-body substring matching with path-gated exact visible-line matching.
- Run focused provider tests, Harness/adapter/runner/production/Connpass workflow/RSVP/evidence regressions, syntax, and diff check.
- Fresh Sol review must verify no false success, no loss of exact registered detection, no browser side effect, and no scope growth.
- After commit/push, run the official foreground wake exactly once with all four labels unloaded. Acceptance is canonical `registered|pending`, Connpass receipt/artifact, Calendar, positive Telegram IDs, one new applied bundle, and cleanup. If the one-submit latch returns a real bounded unknown effect, plan the settlement wait separately rather than weakening readback.

## Result

- RED reproduced the join-page and substring-only false pending at 4/6; GREEN passed the provider suite 6/6 and Sol's relevant combined run 91/91.
- Production is limited to canonical-path gating and exact normalized `innerText` lines; tests add actual callback-executing DOM fixtures. Diff: production 6/3, tests 45/0.
- A read-only actual-page check changed join state from the prior false `pending` to `unknown` while the canonical event remained truthfully `absent`; writes were 0 and the diagnostic tab was closed.
- Commit `3feb31310` is pushed. Fresh Sol review: `ship`, Critical 0, Important 0; reviewer independent regression 107/107.
- The schedule remains unloaded. Item 14 still requires the official live applied bundle.
