# Task 3 report — Remove Tick-Time External Delivery

STATUS: DONE

## Scope

Task 3 changed only:

- `apps/life-manager/lib/late-notice.js`
- `apps/life-manager/lib/late-notice.test.js`
- this append-only report

Task 2's uncommitted `late-approval.js`, `late-approval.test.js`, and migration were read for
their current interface and were not edited, reverted, or staged.

## RED

The required tests were added before changing the tick implementation.  After supplying only the
pre-existing `claimEvent` test dependency so execution reached the old send boundary, the focused
command was:

```text
cd apps/life-manager && node --test lib/late-notice.test.js
```

Result against the old direct-send implementation: **30 tests, 26 pass, 4 fail**.

The new tests failed because the old path called `deps.sendLateNotice()` and returned no durable
`draft`/card row; the missing/ambiguous cases also called the old Telegram failure notification.
The first unadjusted run additionally stopped at the expected old `deps.claimEvent` dependency
(`TypeError: deps.claimEvent is not a function`), so the test fixture was then made explicit to
measure the requested direct-send RED rather than a fixture error.

## GREEN

The late tick now performs recipient resolution, immutable snapshot construction, durable draft
creation, and one approval-card enqueue only:

- `sendLateNotice` is not imported or called by `processLocationLateNotice()`.
- The old `claimEvent` send gate is not used; `(uid,eventKey)` idempotency belongs to
  `createLateDraft()`.
- Resolver output is normalized to `resolved`, `recipient_missing`, or `recipient_ambiguous`.
- Body and ETA evidence are stored in the Task 2 snapshot fields before any Telegram call.
- A resolved first draft gets exactly two callback buttons (`late:send:<draftId>` and
  `late:do_not_send:<draftId>`); a duplicate draft does not enqueue a second card.
- Missing/ambiguous rows are terminal and perform no mail or Telegram operation.
- `sendMessage` is only used as the Telegram card transport fallback; tests may inject
  `enqueueLateApprovalCard` (or the compatible approval-card enqueue aliases).

Focused verification:

```text
cd apps/life-manager && node --test lib/late-notice.test.js
```

Result: **28 tests, 28 pass, 0 fail**.

```text
cd apps/life-manager && node --test lib/late-notice.test.js lib/late-approval.test.js lib/late-recipient-resolver.test.js
```

Result: **50 tests, 50 pass, 0 fail**.

Additional checks:

```text
cd apps/life-manager && node --check lib/late-notice.js
git diff --check
```

Both exited 0.  A broader `test/daily-journey-contract.test.js` probe could not collect because
the worktree baseline lacks the unrelated `canonicalize` dependency; no dependency or unrelated
file was changed to hide that environment failure.

## Mutation reasoning

- Reintroducing the `sendLateNotice` call makes the throwing dependency test fail immediately.
- Enqueuing when `createLateDraft()` returns `duplicate: true` makes the repeated-tick test record
  two cards instead of one.
- Giving `recipient_missing` or `recipient_ambiguous` a keyboard, or falling through to
  `sendMessage`, violates the no-button/no-external-operation tests.
- Omitting the body or ETA snapshot fields breaks the card/body and route/event ETA assertions.
- Restoring the old `claimEvent` early-return would prevent the durable draft row from being
  returned on the second tick.

## Commit/push

Not yet committed or pushed.  The parent session must stage these exact Task 3 paths alongside any
concurrent Task 2 state-machine commit after fetching the canonical branch; no broad `git add -A`
was used.

## Self-review / concerns

- The card callback prefix is intentionally stable and compact so Task 4 can route signed,
  tenant-owned callbacks without changing the stored snapshot.
- Task 3 does not claim delivery or record a provider receipt; those side effects remain behind the
  authenticated callback/claim boundary owned by Task 4.
- Telegram card transport failure is reported as `queued: false` and never changes the draft into a
  sent state.  The durable draft remains the retry/idempotency anchor.
- The focused suites are green; production Supabase and Telegram were not touched by this slice.

## Post-implementation receipt

- Implementation/test commit: `13ae0044e` — `feat(life-manager): gate late notices behind approval`.
- Push: **PASS** — `canonical/feat/lm-daily-late-approval` advanced from `11f6cbc8d` to
  `13ae0044e`.
- The report itself is intentionally staged separately with `git add -f` because the repository's
  `.superpowers/sdd/.gitignore` ignores generated task reports.  No broad staging was used.
