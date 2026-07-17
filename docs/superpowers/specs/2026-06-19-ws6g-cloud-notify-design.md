# WS6g — Cloud late-notice (notify a stakeholder when the user is running late)

Date: 2026-06-19 | worktree `../anicca-lm-notify` / `feature/lm-ws6g-notify`

## Constraint that shapes the design
The legacy LOCAL notify used the phone's **motion/location** to auto-detect lateness. The cloud
service has NO location signal, so it must NOT auto-guess "you're late" (a false notice to a real
attendee is worse than none). Instead WS6g is **user-initiated + agentic**: the user tells the bot
they're running late, and the agent does the rest.

## Flow
```
user (Telegram, already onboarded): "tell Mai I'm 10 min late to our 3pm"  (any phrasing)
  → webhook (done stage) → Gemini classifies the message:
        is this a "running late" notice? → {isLate, etaMinutes, freeText}
  → if late: list the user's events now→+6h that have EXTERNAL attendees;
        Gemini picks the event the user means + the attendee to notify;
        draft a short, polite "running ~N min late" email;
        send it from the user's OWN Gmail (Unipile) to that attendee;
        reply to the user: "✅ Let <attendee> know you're ~N min late."
  → if NOT late: fall through to the existing location-reply path (resolveTelegramReply).
```
No auto-send without the user saying it. The agent finds the attendee + drafts — the user triggered it.

## Modules
- `lib/notify.js`
  - `classifyLate(text, geminiKey)` → `{ isLate, etaMinutes|null }` (pure-ish, one Gemini JSON call).
  - `sendLateNotice(uid, text, { composioKey, geminiKey, unipileToken, unipileDsn, accountId, userEmail, nowMs })`
    → lists events now→+6h with external attendees; Gemini picks event+attendee+eta; sends the email
    via Unipile; returns `{ sent, to, event, etaMinutes }` (or `{sent:false}` if nothing matched).
- `server.js` /telegram done-stage: classifyLate FIRST; if late → sendLateNotice; else → location reply.

## Retire legacy
Disable OpenClaw crons `anicca-life-notify-scan` + `anicca-life-notify-poll` (old local motion path).
The cloud is now the single Life Manager. (jobs.json runtime edit, hot-reload.)

## Verify (no-mock)
1. Unit: classifyLate("I'm 10 min late to my 3pm") → {isLate:true, etaMinutes:10}; "where is it?" → isLate:false.
2. E2E: seed a near-future event with an external attendee on a test calendar; send a late message to
   the deployed /telegram; confirm an email is sent to the attendee (Unipile 2xx) + the user gets the ✅.
3. Legacy crons show disabled / not in active list.
