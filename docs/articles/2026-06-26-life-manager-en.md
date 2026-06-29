# The scheduling AI that phones you 10 minutes before you have to leave: building and running Life Manager

## First: what this is

- **Life Manager** reads your Google Calendar, blocks out travel time before each event on its own, and calls your real phone 10 and 5 minutes before you need to leave, with a voice telling you to move. If an event has no location, it asks you over Telegram or email. There is no app to open. It runs on calls and messages.
- **What we did**: built this agent and ran it until a real call rang our own number. The voice wake-up, the automatic travel blocks, and the location fill-in all ran.
- **Result**: the pre-departure call reached a real phone (a Gemini Live voice preset named Charon speaks). The part where the AI figures out a location and writes it into the calendar ran on a real calendar. The path that asks over Telegram and takes the reply there is live. The email path: the send is confirmed with a real send, but the receive side is still only unit-tested (the live email inbound is not wired yet). Price: $20/mo.
- **Who it's for**: people who oversleep, run late, or forget to send the "I'm late" message. People who never keep an app-opening habit. People who have the events but always miss the moment to walk out the door.
- **Who it's not for**: people whose notifications already get them there on time. People who hate being pushed by a phone call. People who don't use a calendar at all.

## Not an app. A call that comes to you

The trouble with reminder apps is that the alert fires at the event time. A 10:00 meeting pings at 10:00. But what you actually need is an alert for the time you have to LEAVE. If the meeting is 30 minutes away, you have to be moving by 9:20, and most apps never compute that departure time.

Life Manager works backward. It checks the travel time to the event's location, sets the departure as "event start − travel − a 5-minute buffer," and calls 10 and 5 minutes before that. Not a notification, but a ringing call, and a voice that says "leave now." Hard to ignore.

## What the agent actually does

The job splits into four parts.

```
┌─────────────────────────────────────────────┐
│ Life Manager: the four jobs                   │
├─────────────────────────────────────────────┤
│ 1. Travel block  add a [Travel] block before   │
│                  events that lack one           │
│ 2. Wake call     call at T-10 / T-5 (voice)     │
│ 3. Ask location  no place → ask via Telegram/mail│
│ 4. Late notice   won't make it → draft a note   │
│                  to the people waiting          │
└─────────────────────────────────────────────┘
```

(1) reads your calendar each morning and adds a travel block only to events that don't have one yet, and skips events that need no travel (online ones). (2) calls when the departure time gets close. (3) decides "is this online or in-person?" and, if it's in-person with no address, asks you. (4) sees you won't make it in time, drafts the message to the attendees, and sends it after you approve.

## What's out there, and how this differs

Several tools "automate" scheduling. The difference is how much the human still has to do.

| Tool | What it does | Computes departure time | Wakes you by call |
|---|---|---|---|
| Built-in calendar alerts | pings at the event time | no | no |
| Travel-time / routing apps | show route + duration | only shows it | no |
| AI schedulers (meeting coordination) | find slots, book | no | no |
| **Life Manager** | writes travel blocks, calls before you leave | yes (event − travel − buffer) | yes (T-10/T-5, voice) |

A routing app tells you "30 minutes," but it won't call you 30 minutes ahead and tell you to move. Life Manager turns the computed departure time into the trigger for action, and uses a phone call, the hardest thing to ignore, to intervene. That's the gap it fills.

## How it works under the hood

The build is a set of external services stitched together, with the parts that need judgment handed to an AI.

**Reading and writing the calendar** goes through Composio, an integration service, to Google Calendar. The user grants access once with their own Google account; after that, adding travel blocks and writing back locations runs on its own.

**The phone call** wires together Telnyx (a telephony provider) and Google's Gemini Live (an AI that generates voice directly). When the departure time arrives, it dials the number and a Gemini Live voice preset named Charon says, "10 minutes before your next event, time to move." Ten minutes out it's gentle; five minutes out it's sharp. That escalation isn't a fixed script; the urgency level is passed in and changes the tone.

**Deciding the location** is the one piece left to the AI, not to regex or keyword lists. "Call with Fujii-san" is online; "meeting in Shibuya" is in-person and needs an address, and the AI makes that call from the event title and location field. If it's in-person with no address, it asks you. Once you answer, it remembers, and never asks again for that same recurring event.

One honest note: Life Manager doesn't guarantee "a call always fires before every event." It checks the calendar every minute and picks up events that have entered the departure window. The window is a few minutes wide, and each event it has already called is recorded so it doesn't double-dial. It's not a perfect-timing guarantee; it's a "you'll almost certainly make it" design.

## Which channel receives the questions and replies

To "ask the location," it needs a way to reach you. Life Manager asks Telegram users over Telegram and takes the reply there. Web sign-ups are asked by email.

The email side has a trick. Instead of reading your Gmail, it sends the question FROM our own domain (aniccaai.com) and sets the reply address (the Reply-To header, where a reply is delivered) to `reply+<token>@reply.aniccaai.com`. When you reply, it lands in OUR inbox, not your Gmail. So no permission to read your Gmail is needed at all.

Why this matters. The permission to "read" Gmail is tightly restricted by Google: a public app using it must pass a yearly security assessment (CASA) that costs money and weeks of time. And most integration vendors charge per user per month, so cost balloons as users grow. A design that **never reads, and receives the reply on its own domain** avoids both the assessment and the per-user fee. A token embedded in the reply identifies "whose reply, for which event," and the location is written back to that event. The token is an unguessable 128-bit random string resolved against a server-side ledger (no signature; length and randomness alone defeat guessing), so a stranger can't slip into someone else's event.

## We built it and ran it

The build went: wire the external services, hand the judgment to the AI, and run it end to end.

- With the calendar connected (Composio), we made a test event and confirmed a travel block appeared on its own.
- We dialed an event whose departure was close and confirmed a real phone rang with Charon's voice.
- The part where the AI figures out a location and writes it into the calendar's location field ran on a real calendar. The Telegram path that asks and takes the reply is live too.
- The email send was confirmed with a real send (it actually arrived from our domain). The receive side was unit-tested to resolve "whose event" from an unguessable token and to NOT write twice on a duplicate reply (the live email inbound is not wired yet).

One thing tripped us up: the reply address got too long and broke the email spec (the local part has a 64-character limit), so the send was rejected. We'd been embedding the user id and event id directly, which is long. Switching to a short random token, with the token-to-event mapping kept in our own ledger, fixed it.

## So, does it work

The honest verdict first.

**Who it's for**:
- People who oversleep or run late by habit and can't wake to a notification. A ringing call is harder to ignore.
- People who "know the event but miss the moment to leave." The departure-time math is the core value.
- People who never keep an app habit. There's nothing to open; it's all calls and messages.

**Who it's not for**:
- People whose notifications already get them there. No need to be woken by a call.
- People for whom being pushed by a call is itself stressful.
- People who don't use a calendar. With nothing to read, nothing happens.

Price: $20/mo, including the calls, the travel math, and the location memory. No app download. Message @LifeManagerBotbot on Telegram, give your name, calendar, and phone number, and it starts.

## Finally

Every week we run, for real, the tools that let an AI earn money or do work on its own, and we write down what happened. We're building an AI called Anicca, and Life Manager is one of the things that AI put together.

The product entry point: aniccaai.com/life-manager

---

Note: why it doesn't read Gmail (for the technically curious)

The permission to read Gmail (gmail.readonly and friends) is a Google "restricted scope": an app exposing it to general external users must pass a yearly third-party security assessment (CASA), thousands to tens of thousands of dollars, weeks to months. "Send" only (gmail.send) is a "sensitive scope": a lighter review, no audit. Life Manager avoids reading entirely and receives replies on its own domain, sidestepping both the assessment and the per-user vendor fee. The token embedded in the reply address is a 128-bit random value, so guessing your way into someone else's event is not feasible.
