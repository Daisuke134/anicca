# Task 1 report — Freeze Recipient Resolution

STATUS: DONE

## Files changed

- `apps/mr-bot/lib/late-recipient-resolver.js`
- `apps/mr-bot/lib/late-recipient-resolver.test.js`

The resolver is the only production path in this slice. The test uses injected evidence providers and
does not invoke any mail transport.

## RED

Command:

```text
cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js
```

Expected failure: Node exited before collecting tests because the production module did not exist:

```text
Error: Cannot find module './late-recipient-resolver.js'
Require stack:
- .../apps/mr-bot/lib/late-recipient-resolver.test.js
```

This was the intended missing-module RED, not a test syntax or assertion failure.

Review regression RED (before the review fixes):

```text
cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js
```

The new suite reported **13 tests, 9 pass, 4 fail**. The exact failures were the expected
`resolved`/`ambiguous` results for a generic unapproved Contacts candidate and for Gmail, Contacts,
and public-Web candidates whose email had no concrete evidence reference.

## GREEN

- `cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js` — **13 tests, 13 pass, 0 fail**.
- `cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-notice.test.js` — **39 tests, 39 pass, 0 fail**.
- `git diff --check` — pass.
- `node --check apps/mr-bot/lib/late-recipient-resolver.js` — pass.
- `node --check apps/mr-bot/lib/late-recipient-resolver.test.js` — pass.

## Mutation reasoning

- Removing organizer inclusion or the self/resource/declined filters fails the Calendar exclusion test.
- Removing verified-email normalization or evidence merging fails the Calendar+Gmail merge test.
- Removing the Contacts stage fails the approved Contacts test.
- Treating public-web-only evidence as resolved fails the public-web confirmation test.
- Omitting or repeating the confirmation stage fails the ordered-call and single-request test.
- Accepting a conflicting email as resolved or synthesizing an event-derived address fails the ambiguity/no-fabrication test.
- Adding a `send` result/action fails the explicit no-send assertions.
- Letting a generic Contacts provider resolve without `approved === true` fails the approval regression.
- Reintroducing event/index evidence fallbacks fails each Gmail, Contacts, and Web no-evidence regression.
- Dropping confirmation refs while selecting a new or existing candidate fails the top-level evidence assertions.

## Commit and push

- Implementation commit: `4d14b0a01` (`feat(mr-bot): freeze late recipient resolution`).
- Review-fix commit: `b5b21de84` (`fix(mr-bot): require recipient evidence and approval`).
- Push: **PASS** — both implementation and review-fix commits are pushed to `canonical` on `feat/lm-daily-late-approval` (`https://github.com/Daisuke134/life-manager.git`).

## Self-review

- Candidate output is limited to `{display_name,email,source,evidence_refs,confidence,event_role}`.
- Calendar organizer is included; actor/self, resource-room, and declined/cancelled attendees are excluded.
- Connected Gmail, approved Contacts, and public-web providers are injected and called in order; duplicate identities merge only by normalized explicit email and retain sorted evidence references.
- Only the explicitly approved Contacts provider contract can auto-resolve without a per-candidate approval flag; generic Contacts candidates require `approved === true`.
- Gmail, Contacts, and public-Web candidates are discarded without a concrete provider evidence reference; only Calendar and user-confirmation references may use event-bound fallback refs.
- Public-web-only and conflicting candidates remain non-sendable (`ambiguous`); no email is inferred from a name or event title.
- User confirmation is invoked at most once after the evidence stages fail to produce an unambiguous trusted recipient, and its evidence refs are included in both the candidate and top-level result.
- The resolver has no mail, Telegram, or send dependency and returns no send action.

## Concerns

- Full `npm test` was not rerun because this slice is isolated; the focused resolver suite and directly relevant existing late-notice suite are green.
- `late-notice.js` still performs its pre-existing direct-send behavior; removing that side effect is explicitly deferred to the later Gate 0 task and was not changed here.
- `git diff --check cdd1ad9500a622cfd560d86cbb7eef9be890aedb..HEAD` — **PASS (zero exit)** after the report commit; this confirms the earlier report EOF blank-line finding is fixed across the full base range.
