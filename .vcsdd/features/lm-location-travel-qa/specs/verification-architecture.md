# Verification Architecture — lm-location-travel-qa

## Purity boundary
- PURE (tier-0 unit, deterministic): `travelDecision` (origin/home→home/same-location), head-out math
  (leaveMs = start − (mins+buffer)), dedup window, airport-buffer selection, departureMs/originFor.
- AGENTIC / IMPURE (tier-1, real Gemini + Places): `agentResolveLocation` classification (online/filled/ask),
  `directionsMinutes` (Routes/Directions API).
- SIDE-EFFECTING (tier-2 live E2E): gcal patch/create (Composio), Telegram/email send, Telnyx call.
- STATISTICAL (tier-3): determinism harness.

## Proof obligations (PROP per REQ) + verification tier
| REQ | PROP | what to prove | tier |
|---|---|---|---|
| 01 landmark+empty→resolve | PROP-01 | Skytree/Tower/駅 → filled, never ask | 1 (real Gemini) |
| 02 shop→resolve | PROP-02 | スタバ店名 → filled | 1 |
| 03 office commute | PROP-03 | MUIT 出社 → office addr | 1 |
| 04 school+room | PROP-04 | NAIST room → campus addr | 1 |
| 05 online keyword | PROP-05 | オンライン/Zoom → no-travel | 1 |
| 06 online w/ person | PROP-06 | 三島さんとオンライン → no-travel | 1 |
| 07 routine | PROP-07 | Sleep/Run/remote → no-travel | 1 |
| 08 vague+person | PROP-08 | Lunch with Mai → ask | 1 |
| 09 only-user place | PROP-09 | おばあちゃんの家 → ask | 1 |
| 10 field set+geocodable | PROP-10 | 渋谷ヒカリエ → use it | 0/1 |
| 11 room/URL field | PROP-11 | URL → no-travel; room → resolve | 1 |
| 12 ambiguous name | PROP-12 | uses home city | 1 |
| 13 EN+JA | PROP-13 | both classify same | 1 |
| 14 GO block head-out | PROP-14 | leaveMs = start−travel−buffer | 0 (pure) |
| **15 RETURN block** | **PROP-15** | **venue→home block at event_end — UNIMPLEMENTED** | 0+2 |
| 16 back-to-back origin | PROP-16 | prev venue when ≤90min | 0 |
| 17 airport buffer | PROP-17 | 60–180min | 0 |
| 18 past leave→skip | PROP-18 | no past block | 0 |
| 19 dedup | PROP-19 | no 2nd block | 0 |
| 20 home→home skip | PROP-20 | no block | 0 |
| 21 today+7d all | PROP-21 | every must-travel filled | 2 (live cal) |
| 22 transit vs drive | PROP-22 | max() | 0 |
| 23 TG ask+reply | PROP-23 | TG send + webhook patch | 2 |
| 24 email ask+reply | PROP-24 | mail send + Re: patch | 2 |
| 25 re-resolve/dedup-send | PROP-25 | resolves a previously-asked event | 1+2 |
| 26 no double-ask | PROP-26 | one send per event | 2 |
| **27 determinism** | **PROP-27** | **same event ×N → same kind, ≥9/10** | **3 (statistical)** |
| 28 greet first/name/lang | PROP-28 | recording has Charon by name | 2 |
| 29 escalation 15/10/5 | PROP-29 | calls fire at levels | 2 |
| 30 audio audible | PROP-30 | recording RMS/peak non-silent | 2 |

## ★ Two highest-risk items ★
1. **PROP-27 determinism (the Skytree bug)** — same event classified differently across ticks (asked vs
   resolved). Needs a STATISTICAL harness: run each classification case N=10 times, require ≥9/10 stable.
   Current state: VARIES (observed: one tick emailed the user, one tick resolved Skytree). MUST nail.
2. **PROP-15 RETURN trip — UNIMPLEMENTED.** Only the GO block exists. The return-trip block
   (venue → home, starting at event_end) is missing → user has no "head home" time. Needs implementation
   then verification.

## Gate
Tier-1 cases run against real Gemini (no mock). Tier-2 run on Dais's live calendar (plant + verify + clean
the test artifact so no fake call fires). Tier-3 (determinism) is the convergence gate: if any case is
<9/10 stable, FAIL → tighten the prompt (few-shot/right-altitude, not regex) and re-run.
