# 10i personalized action E2E evidence

## Result

Atomic 10i is done with one real current-context action. The production paid user has an active
calendar connection, and the connected calendar returns five upcoming event candidates for the
privacy-safe `イベント` query. The selected real source event is
`2ft16f53672kdfmoqs6dn4ch24`; its title, location, account address, user ID, and chat ID are never
written to repository evidence or command output.

The user's explicit atomic instruction is represented as an `explicit_goal` and `delegation`
entry with `user_message` provenance. The existing `opportunity-engine.js` returns:

`act / delegated-reversible-low-risk:delegation-10i`

The single chosen action is an email preparation brief for the upcoming event. It is reversible,
cost-low, risk-low, and asks no approval question.

## Real provider receipt

| Step | Readback |
|---|---|
| Gmail send | provider id `19f9380e8cbc40f9` |
| RFC Message-ID | `<CAFe2jSZ67NfG8FML7qkRPpkKxzO9XAJim8i1Hc8GN=6-9dO-BQ@mail.gmail.com>` |
| Gmail readback | exact provider id; labels include `SENT` and `INBOX` |
| Calendar post-report | event `fd7rvh2u2sbqa0e4q4vl6vo0rs`, `status=confirmed` |
| Calendar idempotency marker | private property `life_manager_action=10i` |
| Telegram post-report | real message id `3392` |
| Approval questions | `0` |

The Telegram message is one-way and contains one leading emoji:
`📨 次の予定に向けた準備メモをメールで送り、カレンダーにも確認枠を入れておきました。`

The first production attempt stops before providers because the production profile intentionally
has no email value. Corrective TDD adds a fail-closed fallback to the single locally managed
Gmail+Calendar account: RED `3/4`, GREEN `8/8` with the existing opportunity tests. The second
attempt completes. A further provider read proves both Gmail and Calendar receipts. A separate
provider-side marker guard is RED `4/5` → GREEN `9/9`; a real rerun returns
`personalized_action_already_completed` and performs zero duplicate sends/events/reports.

## Verification

- Focused personalized/opportunity tests: `9/9`.
- Full `npm test`: exit `0`.
- Evals: calendar `21/21`, late `12/12`, context `12/12`, score `27/27`, intent `18/18`,
  mental `15/15`, physical `12/12`.
- Panel privacy: `api=177`, `browser=63`, `recipes=19`, `channels=9`.
- Changed-path gitleaks and added-line secret/PII scans: zero.

## Best-practice sources

- Google Calendar, [Extended properties](https://developers.google.com/workspace/calendar/api/guides/extended-properties):
  “Extended properties make it easy to store application-specific data for an event.” The private
  `life_manager_action=10i` marker is the provider-side duplicate guard.
- Gmail API, [Sending email](https://developers.google.com/workspace/gmail/api/guides/sending):
  “You can send it directly using the messages.send method.” The result is not accepted until the
  sent message is read back with its RFC Message-ID.
- Google Calendar API, [Events: insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert):
  “Creates an event.” The confirmed event ID, rather than a local success boolean, is the
  post-action calendar evidence.
