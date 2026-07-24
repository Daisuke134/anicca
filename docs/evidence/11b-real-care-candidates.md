# 11b real care candidates and booking-route evidence

## Result

Atomic 11b is done with three public providers discovered from the current user's production home
context. The private home value is used only as the browser search input and is absent from logs,
source, receipts, and this evidence.

The two historical clinic labels do not establish one repeated usual provider: one has no public
match and the other is ambiguous. The selector therefore marks `usual_provider=false` for all
three instead of inventing a favorite, then uses public proximity order and non-phone booking
availability.

| Rank | Provider | Official readback | Reservation judgment |
|---:|---|---|---|
| 1 | [小滝橋そら内科クリニック](https://otakibashi-sora.clinic/) | official site exposes `Web（ネット）で予約`; logged-out DigiKar page reaches outpatient → first/revisit selection | `web` |
| 4 | [新宿なないろクリニック](https://sjk-nanairo.tokyo/) | official site exposes a public web reservation endpoint; general care is also advertised as reservation-free | `web` |
| 5 | [ヒロオカクリニック](https://www.h-cl.org/) | official site exposes `予約・お問い合わせ` and a public `reserve.ne.jp` flow | `web` |

The closed selector chooses provider id `otakibashi-sora`. Its exact booking route is
`https://qr.digikar-smart.jp/bf904ea8-19e9-4853-8b02-e9c01866ce16/reserve`.
That provider is frozen for 11c; a failed booking may not silently switch to another provider.

## Verification

- Real browser: Google Maps public place pages return all three official site URLs.
- Real logged-out browser: selected provider redirects to DigiKar and displays outpatient,
  online, vaccination, and self-pay menus; outpatient reaches required first/revisit selection.
- Real official-site fetch receipt: three candidates, three `web` judgments, selected provider
  `otakibashi-sora`.
- TDD: missing selector RED `0/1`; GREEN `3/3`.
- Phone-only and unverifiable routes remain visible judgments but cannot be selected.
- Exactly anything other than three candidates fails closed.
- Full `npm test`: exit `0`; all deterministic evals and panel privacy pass.
- Changed-path gitleaks and added-line secret/PII scans: zero.
- Provider mutation, booking, email, calendar event, call, and Telegram send: zero in 11b.

## Sources

- 小滝橋そら内科クリニック official site:
  “Web（ネット）で予約.” This directly supports the selected web route.
- 新宿なないろクリニック official site:
  “予約不要で すぐ診察.” This prevents falsely claiming that general care requires booking.
- ヒロオカクリニック official site:
  “Web予約・お問合せ.” This supports a non-phone alternative while preserving the exact provider
  route for later execution.
