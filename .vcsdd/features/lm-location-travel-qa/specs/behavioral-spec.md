# Behavioral Spec — Life Manager location resolution + travel-time blocks (EARS)

Feature: `lm-location-travel-qa` (strict). SUT: apps/life-call `lib/ask.js` (agentResolveLocation, askTick),
`lib/travel.js` (fillTravel, travelDecision, directionsMinutes), `lib/wake-filter.js` (shouldWake),
`scheduler.js` (travelTick 30min, askTickAll 20min). The MODEL judges via prompt+tools — NO hardcoded
regex for judgment. Paid product → must run autonomously for ALL users.

## A. Location classification (agentResolveLocation → online | filled | ask)
- REQ-01 WHEN an event's title names a public landmark and the location field is empty (e.g. "東京スカイ
  ツリーで打ち合わせ"), the system SHALL web-search the landmark and RESOLVE its real address (kind=filled),
  and SHALL NOT ask the user. [the Skytree email bug]
- REQ-02 WHEN the title names a real shop/venue (e.g. "スタバ新宿南口店"), the system SHALL resolve its
  address (filled).
- REQ-03 WHEN the title is a company/office commute (e.g. "MUIT 出社"), the system SHALL resolve the
  company's office building address (filled).
- REQ-04 WHEN the title names a school/institution with a room name (e.g. "[NAIST] 情報科学大講義室"), the
  system SHALL resolve the institution's campus address (filled).
- REQ-05 WHEN the title indicates an online/remote/phone/video event (オンライン/Zoom/Meet/Teams/電話/
  リモート/ビデオ通話), the system SHALL classify it NO-TRAVEL (online) and SHALL NOT create a block or ask.
- REQ-06 WHEN the title is an online meeting with a named person (e.g. "三島さんとオンラインミーティング"),
  the system SHALL classify NO-TRAVEL (online) and SHALL NOT ask where it is.
- REQ-07 WHEN the event is a personal routine with no external venue (Sleep / Running / Meditation /
  remote Day-job), the system SHALL classify NO-TRAVEL (online) and SHALL NOT ask.
- REQ-08 WHEN the title is a vague external activity tied to a person with no findable venue (e.g.
  "Lunch with Mai", "1on1"), the system SHALL classify ASK.
- REQ-09 WHEN the location is one only the user knows (e.g. "おばあちゃんの家"), the system SHALL ASK the
  user via their connected channel (Telegram else email).
- REQ-10 WHEN the location field is already set and geocodable (e.g. "渋谷ヒカリエ"), the system SHALL use
  it directly without re-asking.
- REQ-11 WHEN the location field is a room name or a URL, the system SHALL resolve the real address (filled)
  or, if a URL/online, classify NO-TRAVEL — never route a URL.
- REQ-12 WHEN a venue name is ambiguous, the system SHALL use the user's home city as disambiguation context.
- REQ-13 The system SHALL behave identically for English and Japanese titles.

## B. Travel-time block creation (fillTravel)
- REQ-14 WHEN an event must be travelled to, the system SHALL insert a GO `[Travel] 🚆` block at head-out
  time = event_start − travel_minutes − buffer.
- REQ-15 WHEN an event must be travelled to, the system SHALL ALSO insert a RETURN `[Travel] 🚆` block at
  event_end lasting the travel time back home (venue → home). **[CURRENTLY UNIMPLEMENTED — gap]**
- REQ-16 WHEN the previous event ends ≤90 min before and at a real venue, the origin SHALL be that previous
  venue (back-to-back), else home.
- REQ-17 WHEN the destination is an airport/flight, the buffer SHALL be 60–180 min (not the default 15).
- REQ-18 IF the computed leave time is already in the past, the system SHALL NOT create a block.
- REQ-19 The system SHALL NOT create a second [Travel] block for an event that already has one (dedup).
- REQ-20 WHEN origin == destination (home→home / same-location), the system SHALL NOT create a block.
- REQ-21 The system SHALL fill ALL must-travel events across today + the next 7 days each run.
- REQ-22 The system SHALL compute travel as max(transit, traffic-aware drive) (never-late bias).

## C. Ask channel + reply
- REQ-23 WHEN ASK and the user linked Telegram, the system SHALL ask via Telegram and patch the location
  from the webhook reply.
- REQ-24 WHEN ASK and no Telegram, the system SHALL ask by email and patch the location from the Re: reply.
- REQ-25 The system SHALL re-attempt RESOLVE on every tick (a past ask SHALL NOT permanently block a fill);
  it SHALL dedup only the ask SEND (never email/Telegram the same event twice).
- REQ-26 The system SHALL NOT double-ask an event already asked and awaiting reply.

## D. Determinism (non-functional)
- REQ-27 The SAME event over N runs SHALL yield the SAME classification (online/filled/ask). Target ≥9/10
  stable per case. [bounds the Skytree run-to-run variance — the #1 risk]

## E. Voice call (boundary)
- REQ-28 WHEN a wake call connects, Charon SHALL speak first, address the user by name, in the user's
  language (EN/JA).
- REQ-29 The system SHALL escalate calls at T−15/10/5 min until the user moves.
- REQ-30 The outbound Charon audio SHALL be audible to the caller (not silent).
