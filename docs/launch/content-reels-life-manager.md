# Life Manager — short-form content scripts (TikTok / YouTube Shorts / Reels)

Three ready-to-shoot vertical (9:16) scripts. Each is ~20-30s, hook in the first 2s, one idea, CTA to the
Telegram bot. Record on phone or generate with the reel pipeline; post to TikTok/YT/IG (accounts on the
daily-driver). Caption ends with the @LifeManagerBotbot link.

## Reel 1 — "The reminder fires too late" (the core insight)
- HOOK (0-2s, on-screen text big): "Your reminder app is lying to you."
- 2-8s: "It says '10am meeting' at 10am. But the meeting is 30 minutes away. You're already late."
- 8-18s (show a phone ringing): "Life Manager calls you at 9:25 — the minute you actually have to LEAVE. Then again at 9:30, sharper."
- 18-25s: "It reads your calendar, blocks the travel time, and phones you before you walk out the door."
- CTA: "It's a Telegram bot. Link in bio." (caption: t.me/LifeManagerBotbot)

## Reel 2 — "A voice, not a notification" (the hook is the call)
- HOOK: "An AI just called my phone to yell at me." (text + a real incoming-call screen)
- 3-10s (play the call audio): "10 minutes before your next event. Time to move." → 5 min later, sharper: "Leave now or you're late."
- 10-20s: "No app. No notification you can swipe away. A real call, every time, before you have to leave."
- CTA: "Set it up in two taps on Telegram."

## Reel 3 — "It asks where, then never asks again" (the smart part)
- HOOK: "My calendar said 'Dentist 3pm' with no address. So the AI asked me."
- 3-12s (show a Telegram message): "📍 Where is 'Dentist'? — I reply 'Shibuya 1-1' — it writes it into my calendar."
- 12-22s: "Next time it's the same dentist, it already knows. It never asks twice."
- CTA: "Life Manager on Telegram. Link in bio."

## Caption template (all three)
Stop being late. Life Manager reads your Google Calendar, blocks your travel time, and CALLS you 10 and 5 minutes before you have to leave — with a voice, not a notification. No app. $20/mo.
Try it 👉 t.me/LifeManagerBotbot
#productivity #ai #calendar #latebird #adhd

## Production notes
- Generate the talking-head or screen-recording; overlay the on-screen hook text (big, first 2s).
- Reel 2's call audio = a real Charon wake-call recording (Telnyx + Gemini Live).
- Idempotent posting: 1 reel/day, record (reel × platform × date) so re-runs skip. (Existing reelclaw infra.)
- These are the funnel: the simple hook + the bot link; the full value (departure-time math) is in the article.
