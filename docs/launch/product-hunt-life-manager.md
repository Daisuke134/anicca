# Product Hunt launch — Life Manager (ready-to-submit draft)

Status: DRAFT content ready. Create the PH launch as a draft, pick the go-live day (Tue–Thu, 12:01am PT is
best for ranking), Dais reviews + hits launch. The Telegram product is live + dogfooded, so it's launchable.

## Name
Life Manager

## Tagline (≤60 chars) — pick one
1. The AI that calls you 10 min before you have to leave  (52)
2. An AI that phones you before you're late — no app  (50)
3. It calls you before you must leave, fills your travel time  (58)
→ Recommended: #1 (concrete, the core hook).

## Topics (PH categories)
Productivity · Artificial Intelligence · Calendar · Telegram Bots

## Links
- Website / try it: https://aniccaai.com/life-manager
- Telegram bot: https://t.me/LifeManagerBotbot?start=ph

## Description (≤260 chars)
Life Manager reads your Google Calendar, blocks out travel time before every event, and CALLS your phone 10 and 5 minutes before you have to leave — with a voice, not a notification. No location? It asks on Telegram. No app to open. $20/mo.

## Gallery (assets to attach — screenshots of the live /life-manager page)
1. Hero: the /life-manager page (headline + "Start in two taps" + QR + web card). [scratchpad: wb-final.png]
2. The four jobs diagram (travel block / wake call / ask location / late notice).
3. A wake-call mock: "09:30 · call, 10 min before · time to move".
4. Telegram onboarding flow (name → calendar → phone → done).
(Generate clean 1270x760 PH-spec images from the live page before submit.)

## First comment (maker's comment — post immediately on launch)
Hey Product Hunt 👋

I kept missing the moment to actually LEAVE — the calendar reminder pings at the meeting time, but by then I'm already late. So I built Life Manager: it works backward from when you have to walk out the door.

Every morning it reads your Google Calendar, adds a [Travel] block before each event, and figures out your real departure time (event − travel − a 5-min buffer). Then it CALLS your phone 10 and 5 minutes before that — a voice (not a push notification) telling you to move, sharper the second time.

If an event has no location, it asks you on Telegram (or email) and writes your answer back to the calendar — and remembers it so it never asks twice. Running late? It drafts the "I'm late" message to whoever's waiting and sends it once you say OK.

There's nothing to open. You set it up in two taps on Telegram (name, Google Calendar, phone), and it runs on calls and messages. $20/mo.

Two honest notes: (1) it's for people who oversleep / run late and don't wake to notifications — if your alerts already get you there, you don't need this. (2) it never reads your Gmail (privacy + cost): it sends from its own domain and reads only the replies you send back.

Would love feedback on the wake-call timing (10/5 min) and which other things you'd want it to handle before you leave the house.

## Maker
Daisuke Narita (built with the Anicca autonomous agent)

## Launch-day checklist
- [ ] Generate PH-spec gallery images (1270×760) from the live page.
- [ ] Create the launch as a DRAFT on producthunt.com (Google login keiodaisuke).
- [ ] Schedule for a Tue/Wed/Thu, 12:01am PT.
- [ ] Set the Telegram deep link with ?start=ph for attribution.
- [ ] Dais reviews → hit launch → post the first comment immediately.
