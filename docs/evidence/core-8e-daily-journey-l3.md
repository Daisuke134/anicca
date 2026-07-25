# CORE-8e — DAILY user journey, production L3

Run date: 2026-07-25 (JST). Production service `life-call`, Railway environment `production`.

## What was unproven before

The journey could show that Resend *accepted* a late notice, never that one *arrived*. Resend answers a
send with its own queue id (`lib/mail-resend.js`), so the spec's "real email Message-ID" was unreachable.
Three earlier attempts all died on the same boundary: the notice recipient was a mailbox we could not read.

## What unblocked it

An externally controlled `@agentmail.to` inbox exists and is readable over an API, so it can be a genuine
external calendar attendee. Verified before use: HTTP 200, and 20 of 20 real messages carry an RFC-shaped
`message_id` (0 of 20 in `smtp_id` — the first implementation had the two fields swapped and was corrected
from the live data).

## Real-world evidence

| Leg | Measured |
|---|---|
| Real calendar event | Created via the real provider; readback showed `external=1, self=false, organizer=false`, attendee domain `agentmail.to` — the exact condition that failed in the earlier attempt |
| Travel autofill | Production travel loop logged `[travel] uid=lm_784ad279- inserted=2 checked=13`; an outbound block `[Travel] 新宿区南元町15-27→渋谷ヒカリエ` and its return block were both created |
| Real call, T-10 | `lm_wake_log`: `called_at=2026-07-25T02:55:07Z`, `answered_at=2026-07-25T02:55:18Z` (answered 11s later), level `10`, `event_key=lm_784ad279-…\|2026-07-25T12:49:04+09:00\|10` |
| Call recording + transcript | `2026-07-25T02-55-31-42932e3a-de8e-4aa6-a48c-7d310cb343e9.mp3`, whisper: "Yes?" / "Hi, Dyson." / "Time to leave now for your next event. Do you need directions?" / "It's okay." — real two-way call in English |
| Location gate, late | `lm_late_notice_log` claim `2026-07-25T01:57:51Z`, decided from the live Telegram location row (`source=telegram_live_location`, non-expired) |
| Real email Message-ID (1) | `<0106019f96fe3ec1-f96214c9-4ba0-43f8-bdbb-46b47481dd62-000000@ap-northeast-1.amazonses.com>` |
| Real email Message-ID (2) | `<0106019f9739595a-f134ea99-e1cc-4a21-b34d-6d1f2b71a8d6-000000@ap-northeast-1.amazonses.com>`, claim `2026-07-25T03:02:24Z` |
| Real Telegram id | Production log `[late] uid=lm_784ad279- decision=late sent=true tg_message_id=245` |
| Not-late case | For the on-time event no claim row was written and a strict receipt lookup returned `null` — no notice was sent, which is the correct behaviour |

Both email receipts were re-verified under `fromIncludes="aniccaai.com"` and `subjectIncludes="Running late:"`,
so neither is a calendar invitation (see the trap below).

## Two real defects this run exposed

1. **A claimed meeting silenced the rest of the day.** The finder took only the FIRST located event and a
   failed claim returned immediately. On 2026-07-25 an all-day located event (`kucv75fkku06j65uomu96v8a9c`)
   was claimed at `00:31:51Z` and ran until evening, so every later event was unreachable. Candidates are now
   walked; a run where every candidate is claimed stays deduplicated and silent. The fix is what let the
   production claim at `01:57:51Z` happen at all.
2. **A calendar invitation could be mistaken for delivery proof.** Putting the receipt inbox on an event makes
   Google send it an invitation carrying the same nonce. `findReceipt` now takes `fromIncludes` /
   `subjectIncludes` so a caller pins which message counts.

Also fixed: the Telegram leg discarded the provider's response, so the delivered message could not be named.
The id is now carried on the result and logged.

## Verification at the merged commit

`npm test` 737 pass / 0 fail · `npm run eval` 7 suites at 100% · `npm run eval:panel-privacy` PASS.

Canonical main and Railway production both at `5c855632` (deployment status SUCCESS).

## Cleanup

Every event created for this run, and the travel blocks generated from them, were deleted. A readback of the
calendar afterwards showed only the user's own real events. No third party was ever emailed: the only external
attendee was the controlled receipt inbox, and the user's real meeting that day carried zero attendees.
