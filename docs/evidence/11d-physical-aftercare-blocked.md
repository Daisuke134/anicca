# 11d physical aftercare blocked by unconfirmed booking

## Result

Atomic 11d remains pending. Its required Telegram copy says a reservation was made, its Google
Calendar event represents that reservation, and its same-day calls are tied to that confirmed
event. Atomic 11c has provider readback `booking_id=null` and
`status=honest_failure_reported`, so emitting any of those three effects would be false.

The closed gate returns:

```json
{"schema_version":1,"status":"blocked","blocker":"confirmed_booking_required","effects":{"telegram_report":0,"calendar_event":0,"same_day_call_schedule":0}}
```

## Three approaches

1. Treat the real selectable DigiKar slot as an appointment. Rejected: the slot redirects to
   patient SMS verification and has no provider confirmation or booking id.
2. Reuse real Telegram message `3394` as the §9.11 post-booking copy. Rejected: that message
   truthfully states that the booking is unconfirmed, while the canonical copy says it was booked
   and added to Calendar.
3. Create a tentative Google Calendar event and wire calls to it. Rejected: the calendar and calls
   would create a false appointment from an unconfirmed slot.

Provider switching, phone booking, SMS bypass, invented booking ids, false Telegram success,
Google Calendar writes, and call scheduling all remain zero.

## Resume boundary

Resume 11d only after the frozen provider returns a real confirmed booking id and start time.
Then the same closed gate permits exactly one Telegram report, one Google Calendar event, and one
same-day call schedule. Until then, 12b is independent and can proceed.

## Verification

- TDD: missing module RED, then focused `3/3` GREEN.
- The contract rejects tentative slots, failure reports, and unconfirmed/fabricated ids.
- No provider, Telegram, Calendar, or call mutation occurs in 11d.
- Source of truth: [11c evidence](11c-real-care-booking-boundary.md) records the real provider
  SMS boundary and `booking_id=null`.
