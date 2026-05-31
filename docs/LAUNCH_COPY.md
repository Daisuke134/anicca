# LAUNCH_COPY — paste-ready announcements for the OSS reveal

Stored separately from README so the maintainer can copy without
scrolling. Sequence the posts however you want; the Twitter thread can
go first, Show HN later (US morning = JST 22:00-25:00), Slack any time.

---

## 🐦 X / Twitter — hero post

```
🧘 anicca-oss — an autonomous AI life-leader you install on your laptop.

It runs your life — without you in the loop.

✓ Calls your phone every morning until you wake up
✓ Watches your live location, calls when it's time to leave for the next event
✓ Reads your gmail, drafts apology mails when you're running late
✓ Fills your Google Calendar with wake / sleep / meals / commute / deep work
✓ Applies to events / jobs / LT slots in your name, autonomously
✓ Earns USDC for you via x402 / Bittensor / Gitcoin / Akash
✓ Pays YOU 10% of net earnings — into your actual bank account / wallet
✓ When her wallet > 3 months runway, tells you to cancel your ChatGPT/Claude sub

setup 5 min. needs your API key (or USDC) until she self-funds — then she's free.
MIT, runs locally, data never leaves your machine.

github.com/Daisuke134/anicca-oss
```

## 🐦 X — reply thread #1 (= "she sends me money?")

```
Yes — Anicca actually sends money to your bank account.

She earns USDC autonomously (x402 / Bittensor / Gitcoin bounties).
Every month she sends you 10% (configurable). Lands in your bank via
Stripe Connect Express or Wise, or directly to a wallet you paste in.

First payout email arrives ~Day 30. The wow moment is real.
```

## 🐦 X — reply thread #2 (= "no terminal?")

```
You can install it without touching the terminal.

Copy the prompt in the README. Paste it into Claude Code / Codex /
Cursor / Aider — any local AI agent. It installs Anicca for you, asks
one question at a time, hands off to Telegram for the rest.

Lazy-path. 5 minutes.
```

## 🐦 X — reply thread #3 (= existing harness users)

```
Already running OpenClaw / Hermes / Claude-P?

You don't need the whole distro. Install just the skills you want:

  openclaw skill install anicca-life-manager
  openclaw skill install anicca-payout-wallet

Skill marketplace pattern. Your CONSTITUTION stays yours.
See docs/SKILL_CATALOG.md.
```

---

## 💬 Slack — internal share (= lab / friends)

```
hey — pushed something I've been building for the last 6 weeks:

github.com/Daisuke134/anicca-oss

it's an autonomous AI agent that lives on your laptop and runs your
life — wakes you up by phone, drives your calendar, applies to events
for you, earns USDC autonomously, eventually pays you 10% into your
bank account.

MIT, runs locally, your data never leaves your machine.

would love a star + brutal feedback. happy to walk anyone through
install on a screen-share.
```

---

## 📰 Show HN

Title:
```
Show HN: Anicca – autonomous AI life-leader that calls you on the phone
```

Body:
```
Hi HN — I've spent the last 6 weeks building anicca-oss, an autonomous
AI agent that runs on your laptop and runs your life. The repo is at
github.com/Daisuke134/anicca-oss (MIT).

The 30-second version: it reads your Google Calendar + your Telegram
Live Location, and when it's time to leave for your next event it
actually phones you (Twilio + Pipecat + Gemini Live native S2S, ~500ms
latency). If you don't move, it calls again, and again. Once you're
moving, it stops.

The angle I think is novel:

1. No-LLM in the critical path. The lateness decision is pure Python
   reading gcal + a Telegram-bot location file. The LLM is only for the
   actual phone conversation. So the 5-min cron costs near zero and
   keeps firing even if your inference quota's empty.

2. Event-type-aware persuasion. Routine events (sleep / wake / meditation
   / running) get verbs like "起き上がって" or "瞑想スペースへ" instead
   of the generic "leave home now" that other prototypes default to.

3. Auto-fill cron stack. Three sibling crons heal the calendar so the
   call logic always has clean data — they PATCH empty location fields,
   INSERT 🚆 移動 blocks between location-changing events, and fill empty
   days from a default template.

4. The self-funding loop. Once Anicca's wallet covers 3 months of her
   own compute, she emails you "cancel your sub if you want — I can fund
   myself now". The fuel-broker skill monitors this hourly. Then she
   starts sending YOU 10% of earnings.

Install path is either bash (manual) or paste-this-prompt-into-your-AI
(Claude Code / Codex / Cursor / Aider). Docs in /docs.

What I would love feedback on:
- the lateness-call prompt structure (= the wording matters a lot)
- the OSS dev pattern (= I'm using the Aider-style single-clone +
  editable runtime model)
- whether the "AI pays you 10%" framing reads as legitimate or weird

Happy to answer anything.
```

---

## 📧 Email (= if writing to specific people)

Subject: `Built an autonomous AI life-leader — anicca-oss is live`

```
Hi <name>,

I shipped anicca-oss tonight:
github.com/Daisuke134/anicca-oss

Autonomous AI life-leader. Calls you in the morning. Watches your live
location. Writes your calendar. Earns USDC. Pays YOU 10% of net
earnings into your bank. MIT, runs locally.

If you want to try: clone + paste the README Quick-Start prompt into
your local AI (Claude Code / Codex / Cursor). 5 min to set up.

I'd love to hear what you think — especially what feels off.

Dais
```
