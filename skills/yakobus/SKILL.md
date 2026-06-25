---
name: yakobus
description: Book the best available overnight bus (夜行バス) end-to-end with no human in the loop — search & compare, pick the best, fill passenger info, pay with the saved card, auto-clear 3-D Secure via Gmail OTP, and add it to Google Calendar. Use when the user asks to book/find an overnight or highway bus between Japanese cities.
---

# yakobus — best overnight-bus booking

Verified end-to-end on 2026-06-25 (booked カジュアルツィンクル号, なんばOCAT 21:05 → バスタ新宿 06:34,
¥5,200, reservation 1020255713, MUFG Visa Secure 3-D Secure cleared from Gmail automatically).

## When to use
User says something like "book my yakobus from <origin> to <destination>, <date>, cheap, <gender>,
ideally ≤¥<budget>". Origin may be an area ("nearest Osaka/Nara/Kyoto") — resolve to the cheapest hub.

## The judgment is YOURS (the model), not a rule
"Best" = the cheapest plan that is (a) actually AVAILABLE and (b) whose stop list INCLUDES the requested
destination, balanced against the user's soft budget and comfort hints. Do NOT hardcode regex/keyword
rules to decide — reason over the candidate list `search_buses.py` returns. When the literal request
can't be met (cheapest is sold out, or only lands one stop short e.g. 池袋 vs 新宿), surface the real
trade-off and ask ONE crisp question; otherwise just proceed.

## Supported today
The verified path is **バス比較なび → kosokubus.com** booking. `search_buses` works for any bushikaku
route; the booking-drive selectors in §gotchas (card-field IDs, levers) are **kosokubus-specific**. Other
sites (willer/busbookmark) are reachable via cloak.py but need their own selectors — detect the host first
and adapt; do not assume kosokubus DOM elsewhere.

## Tools (scripts/) — run STRICTLY SEQUENTIALLY (one CDP client at a time; never two at once)
- `python3 search_buses.py <from> <to> <YYYYMMDD>` → JSON candidates (price, stops, availability, times)
  + bookingLinks. Sorted cheapest-first. Raw data only — you pick. Exits 1 with `{"error":...}` if no
  candidates. Closes its own tab. `stops` are the real alighting place-names (works for any destination).
- `CLOAK_TARGET=<urlsubstr> CLOAK_SHOT_DIR=<dir> python3 cloak.py <cmd> [arg]` → drive the live
  daily-driver CloakBrowser (goto/eval/url/pages/shot/shotfull/clicktext/clicksel/clickxy/typeat/fill).
- `read_otp.py --merchant <name> --amount <jpy> --minutes 15 --tries 6` → newest 3-D Secure OTP from
  Gmail, RETRIED 6× (email arrives delayed), validated by merchant+amount. Exits 1 if none.
- Card + passenger profile live in `~/.openclaw/.env` (`DAIS_CARD_PAN/_EXP_MONTH/_EXP_YEAR/_CVV/_NAME`,
  `DAIS_PHONE`); email redacted@example.invalid.
  **SECRETS**: never put card values in argv (visible in `ps`/transcript). Fill them via
  `CLOAK_FILL_VALUE="$DAIS_CARD_PAN" cloak.py fill '#cardNum'` (value read from env, printed masked).
  `typeat` puts its text in argv → use it only for NON-secret fields (times, OTP), never card PAN/CVV.
- Google Calendar: gog has NO gcal CLI. Use the **Google Calendar MCP `create_event`** (the verified
  2026-06-25 mechanism) for the two events. This is an external MCP dependency BY DESIGN — not a bundled
  script (no OAuth creds shipped in-skill).

## Flow
1. `search_buses` for the route/date. Pick the best (see judgment above).
2. Open the chosen plan's bookingLink with cloak → follow to the booking site (kosokubus / willer / etc.).
3. Select boarding + alighting stops and adult count (gender). Choose ゲスト予約 (no signup) if offered.
4. Fill passenger info (name kana, sex, age, tel, email×2, prefecture).
5. Select credit card, fill card from env, decline optional insurance, agree 約款.
6. Submit to final confirm. Read the page back and verify every field.
7. Final confirm → 3-D Secure: when challenged, `read_otp.py` → enter code → 確認.
8. VERIFY (no mock): payment_complete page + reservation number + confirmation email +
   card-charge notification. Only then is it done.
9. Add to Google Calendar: (a) leave/transit event (route + leave-by time, reminders),
   (b) bus event (reservation #, stops, price, "mobile ticket required").

## CRITICAL gotchas — VERIFIED, obey these
- **ONE CDP client only.** Two playwright clients + a JS dialog crashes the browser. Don't run a
  launch_persistent_context keepalive alongside cloak.py; keep Cloak Chromium up as a standalone
  process. cloak.py always accepts dialogs. Never close the daily-driver.
- **Target the right tab.** The profile has many tabs; always set `CLOAK_TARGET` to the working URL
  substring. Never assume "last tab".
- **aggregator availability lags.** "わずか" on bushikaku may be 満席 on the booking site — verify there.
- **kosokubus card fields = id-only & async & fragile.** `#cardNum/#cardDateMonth/#cardDateYear/
  #ccSecurityCode` have NO name attr; they inject only after a REAL click on the クレジットカード lever
  (`span.lever`), load a few seconds later, and get wiped if other fields change → **fill the card LAST,
  poll until `#cardNum` exists, then don't touch other fields**.
- **counters / custom radios** = click the visible `span.lever` / `span.btn-man-up.js-count-up`, not the
  hidden input.
- **3-D Secure OTP groups in ONE Gmail thread** → use newest MESSAGE (read_otp.py does this), not the
  thread's oldest. Validate merchant + amount.
- **cheapest ≠ destination** — confirm the destination is actually in the stop list.

## Cancellation (verified)
Online self-cancel button disappears at the reservation cutoff (~booking deadline). Before departure the
fee is small (e.g. ¥660 on kosokubus → most of the fare refunds to the card); after departure 100%. If
the online 【キャンセルする】 button is gone, cancel via the operator's automated phone line (kosokubus
center 0570-048-983, 自動音声 24/7; human Mon–Fri 10–17).

## Definition of done (4-D convergence)
spec ✓ + the flow runs ✓ + payment_complete & reservation # captured ✓ + confirmation email & card
charge verified ✓. "It compiles" / "the page loaded" is NOT done.
