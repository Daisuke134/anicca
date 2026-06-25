# Spec: Best Overnight-Bus (夜行バス) Booking Skill — Life Manager

Date: 2026-06-25
Status: DESIGN (verified end-to-end manually on 2026-06-25 — this spec generalizes that real run)
Owner: Life Manager (#1 Anicca-OpenClaw / #2 Hermes), model-driven
Repo: `~/anicca` (mother) → `skills/life/yakobus/`

## 1. Goal

Given a user request like *"book my yakobus from NAIST (or nearest Osaka/Nara/Kyoto) to Shinjuku BASTA,
tonight, cheap, male, ideally ≤¥5000"*, the agent books the **best available** overnight bus
**end-to-end with no human in the loop**: search → compare → pick best → fill passenger info →
pay with the saved card → auto-clear 3-D Secure via Gmail OTP → verify → add to Google Calendar.

"Best" is a **judgment the MODEL makes** (per `~/.claude/rules/building-effective-ai-agents.md`): cheapest
seat that is (a) actually available and (b) serves the requested destination, balanced against the user's
soft budget and comfort hints. **No hardcoded regex/if-else decides which bus is best** — the agent reasons
over the structured candidate list. Deterministic code only does: scraping, form-filling, OTP parsing,
gcal writes, arithmetic.

## 2. Verified reference run (2026-06-25, the ground truth)

Booked: カジュアルツィンクル号1便, なんばOCAT 21:05 → バスタ新宿 06:34, ¥5,200, 予約番号 1020255713,
paid via 三菱UFJ-VISAデビット, 3-D Secure cleared with Gmail OTP automatically, 2 gcal events created.

## 3. Inputs (agent collects/infers from the request + profile)

| field | source |
|---|---|
| origin area (+ acceptable stations/stops) | user msg; resolve nearest terminals (Osaka/Kyoto/Nara hubs) |
| destination (e.g. バスタ新宿) | user msg |
| date (tonight / specific) | user msg + current date |
| gender (male/female) | user msg / profile |
| budget (soft target) | user msg |
| passenger profile | `~/.openclaw/.env` (DAIS_* ) + known identity: name kana, age, email, prefecture, `DAIS_PHONE` |
| card | `~/.openclaw/.env` `DAIS_CARD_PAN / _EXP_MONTH / _EXP_YEAR / _CVV / _NAME` |

## 4. Flow (agent loop + deterministic tools)

1. **Search & compare** — scrape バス比較なび (`bushikaku.net/search/<from>_<to>/<YYYYMMDD>/`), parse every
   plan: price, depart/arrive stops, seat type, **availability**, booking site, external-link.
2. **Agent picks best** — the model selects the cheapest plan that is available AND serves the destination,
   honoring budget/comfort. It surfaces the genuine trade-off (e.g. ¥3,500→池袋 vs ¥5,200→新宿直行) and,
   only when the literal request can't be met (cheap option sold out / lands off-target), asks ONE crisp
   confirmation. Otherwise proceeds.
3. **Drive booking site** (CloakBrowser daily-driver) — follow external-link → booking site (kosokubus /
   willer / busbookmark / etc.). Select boarding/alighting stops + adult count (gender).
4. **Guest checkout** — choose ゲスト予約 (no signup) where available.
5. **Fill passenger info** — name kana, sex, age, tel (`DAIS_PHONE`), email ×2, prefecture.
6. **Pay** — select credit card, fill card from env, agree terms (約款), decline optional insurance.
7. **3-D Secure** — on challenge, read the OTP from Gmail and submit (see §6).
8. **Verify (no-mock E2E)** — confirm `payment_complete` + reservation number + confirmation email +
   card-charge notification. Never claim done without these.
9. **Google Calendar** — create (a) transit/leave event (with route + leave-by time) and (b) the bus event
   (reservation #, stops, price, "mobile ticket required"), with reminders.

## 5. CRITICAL gotchas (encode as skill rules — learned the hard way 2026-06-25)

| gotcha | rule |
|---|---|
| **Dual CDP client + JS dialog = browser crash** | Exactly ONE playwright client on daily-driver. Launch the Cloak Chromium standalone (binary + `--remote-debugging-port`) OR one persistent driver; ALWAYS register `page.on("dialog", accept)`. Never `browser.close()` a CDP-attached daily-driver. |
| **バス比較なび availability is cached/laggy** | "残席わずか" on the aggregator may be **満席** on the booking site. Trust the booking site, not the aggregator. |
| **kosokubus card fields = id-only, async, fragile** | `#cardNum/#cardDateMonth/#cardDateYear/#ccSecurityCode` have NO `name`. They inject only after a REAL click on the クレジットカード lever (`span.lever`), load async (poll up to ~15s), and get wiped if other fields change → **fill card LAST, poll for appearance, don't touch other fields after**. |
| **+/- counters & custom radios** | passenger count = click `span.btn-man-up.js-count-up`; payment/insurance radios are custom (hidden input + visible `span.lever`) → click the lever, not the input. |
| **3-D Secure OTP email groups in ONE Gmail thread** | `gog gmail get <thread>` returns the **OLDEST** (dead) code. Use message-level `gog gmail messages search "認証コード newer_than:15m"` → newest message id → get THAT; verify merchant+amount match before using. |
| **Multiple tabs on daily-driver** | the profile has many tabs (other sessions). Target the working page by URL substring, never "last tab". |
| **cheapest ≠ requested destination** | agent must check the destination actually appears in the alighting list. |

## 6. Tools (deterministic, well-documented — the ACI)

- `search_buses(from, to, yyyymmdd)` → structured candidate list (bushikaku scrape).
- `cloak_drive` — CDP driver against daily-driver (goto/eval/click/fill/screenshot, dialog auto-accept, URL-target).
- `read_3ds_otp(merchant, max_age)` — newest message-level Gmail 認証コード, validated by merchant/amount.
- `gcal_add(event)` — via Google Calendar MCP.
- card/profile loader from `~/.openclaw/.env` (never echo values).

## 7. Verification (definition of done)

`payment_complete` page reached + reservation number captured + confirmation email received + card-charge
notification received + both gcal events created. Anything less = not done.

## 8. Out of scope (companion features, link don't build here)

- **Departure-reminder CALL** (user wants Life Manager to *call* 10/5 min before leaving). Today this does
  not exist (notify cron only alerts third parties on lateness). Track separately as a Life Manager
  "departure call" feature (gcal-watch → Telnyx dialout N min before). 

## 9. Tasklist → see TaskCreate (registered same turn per HARD RULE 0.29)
