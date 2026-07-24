# 11c real care booking boundary and honest report

## Result

Atomic 11c is done through the specification's honest-failure branch. The provider selected and
frozen by 11b remains `otakibashi-sora`; no fallback provider is tried.

The public DigiKar flow reaches a real selectable initial-visit slot. Selecting one opens the
patient verification page, which requires the patient's mobile number, acceptance of the
provider terms, and an SMS verification code before the reservation can continue. Life Manager
does not have the patient's SMS receive channel, so it does not submit a phone number, invent a
code, bypass verification, or claim a booking.

The exact outcome receipt is:

```json
{"schema_version":1,"status":"honest_failure_reported","provider_id":"otakibashi-sora","channel":"web","booking_id":null,"blocker":"patient_sms_verification_required","telegram_message_id":3394}
```

Real Telegram message `3394` reports that an available slot was reached, SMS verification is
required, the provider remains unchanged, and the booking is not confirmed. It is a one-way
status report with no question.

## Verification

- Provider selection is unchanged: `otakibashi-sora` before and after the attempt.
- Real public flow: outpatient → initial visit → real available slot → patient verification.
- Provider readback says `ご本人の電話番号を入力してください` and `認証コードを送信`.
- Booking id: `null`; provider mutation: `0`; phone call: `0`; email: `0`.
- CAPTCHA/OAuth/SMS bypass: `0`; local recurring-runtime dependency: `0`.
- Provider-directed message: `0`, so no undisclosed impersonation occurs.
- Real Telegram delivery: message id `3394`.
- TDD: missing module RED, then focused contract `4/4` GREEN.

## Sources

- [小滝橋そら内科クリニック official site](https://otakibashi-sora.clinic/):
  “Web（ネット）で予約.” This is the frozen provider's published non-phone route.
- [DigiKar public reservation entry](https://qr.digikar-smart.jp/bf904ea8-19e9-4853-8b02-e9c01866ce16/reserve):
  “クリニック外来での対面診察.” The logged-out provider flow exposes the route used in the
  attempt.
- DigiKar patient verification readback after selecting a real slot:
  “ご本人の電話番号を入力してください” and “認証コードを送信.” This is the measured stop
  boundary; it is not inferred from a fixture.
