---
marp: true
paginate: true
size: 16:9
style: |
  section {
    background: #0d1117;
    color: #e6e1d3;
    font-family: "Helvetica Neue", "Inter", Arial, sans-serif;
    font-size: 33px;
    line-height: 1.45;
    padding: 64px 80px;
  }
  h1 { color: #E8B84B; font-size: 60px; line-height: 1.08; margin-bottom: .25em; }
  h2 { color: #E8B84B; font-size: 42px; margin-bottom: .35em; }
  h3 { color: #F0C95A; font-size: 34px; }
  strong { color: #F4CF63; }
  em { color: #9fb3d1; font-style: normal; }
  a { color: #7fb0ff; text-decoration: none; }
  code { background: #1b2230; color: #ffd479; padding: 1px 8px; border-radius: 5px; font-size: .92em; }
  ul, ol { margin-top: .1em; }
  li { margin: .28em 0; }
  img { display: block; margin: 0.2em auto; }
  section.title { text-align: center; }
  section.title h1 { font-size: 78px; color: #E8B84B; }
  section.title .sub { font-size: 38px; color: #e6e1d3; }
  section.title .socials { font-size: 28px; color: #9fb3d1; margin-top: 1.1em; }
  section.center { text-align: center; }
  .big { font-size: 46px; line-height: 1.3; }
  .note { font-size: 26px; color: #8b97aa; }
  section table { font-size: 25px; border-collapse: collapse; width: 100%; }
  section table th, section table td { border: 1px solid #2a3446 !important; padding: .2em .6em; color: #e6e1d3 !important; background-color: #0f141d !important; }
  section table th { color: #E8B84B !important; background-color: #11161f !important; }
  section table tr:nth-child(even) td { background-color: #161e2b !important; }
  section table td strong { color: #F4CF63 !important; }
  footer { color: #5d6b80; font-size: 20px; }
footer: "Anicca · aniccaai.com"
---

<!-- _class: title -->
<!-- _paginate: false -->

# Anicca

<span class="sub">A self-funding **Buddhist AI** that pays humans a basic income</span>

<span class="sub note">Realtime by day · rewriting itself by night</span>

<span class="socials">aniccaai.com<br>X @aniccax &nbsp;·&nbsp; TikTok @anicca.jp &nbsp;·&nbsp; YouTube @anicca-ai</span>

---

## Three beats

1. **What I built** — an AI that runs my businesses *and pays people*
2. **How I built it** — heartbeat + `claude -p` + skills + state
3. **Builder takeaway** — what you can clone tonight

<span class="note">Show-and-tell. Live system, not a pitch deck.</span>

---

## It started as a *cron machine*

<span class="big">Claude Code + me + a list of timers.</span>

I hand-wrote every job. When one broke, **I** fixed it.
It only did what I scheduled — nothing more.

Then I gave it a **heartbeat**.

---

## Then → Now

![h:470](img/01-then-now.png)

A timer *runs jobs*. A heartbeat lets the agent **decide, fix, and build** on its own.

---

## How it works

![h:495](img/02-arch.png)

---

## The heartbeat — the whole trick

- A `launchd` loop fires every few minutes → calls **`claude -p`** (headless Claude Code, **Opus 4.7**)
- It reads its **state + memory**, looks at what's broken or unfinished, and **acts**
- Same agent runs on **two harnesses** — **OpenClaw** (gateway) + **`claude -p`** — one shared set of *skills + state*. **Hermes** is next.
- Runs on my existing **Claude subscription** — *no per-token API to top up*
- Inspired by **sutando** (sonichi): *realtime by day, rewriting itself by night*

<span class="note">Cron = when. Heartbeat = judgment. The agent owns its own loop.</span>

---

## It fixes itself

![h:225](img/03-selfheal.png)

**Real example:** one cron **hung for 6 hours** and silently blocked every hourly beat — nothing errored. The loop saw the **missing beats**, killed it, and added a **per-iteration timeout** so one stuck job can't freeze the fleet.

---

## When it fails (the honest part)

- **It over-applied to a comedy show.** Anicca auto-submitted my act to the *same* open mic again and again — until the organizers told me to **stop**. No *"do-not-contact"* guard on autonomous outreach. → now hard-blocked in 5 places.
- **Uber Eats rejected our cafe — twice.** *"Information doesn't match across your documents."* Anicca just **re-uploaded the same file** — never read the reason. **Blind retry ≠ self-healing.** Still open: the agent must **fix the root cause, not resend**.

<span class="note">Autonomy without guardrails = an agent that does the wrong thing — confidently, and fast.</span>

---

## What Anicca actually runs

| Venture | What the agent does end-to-end |
|---|---|
| 🎤 **Comedy** | writes bits, renders TikToks, posts to @anicca.jp |
| ⚰️ **Cemetery** | aniccaai.com/cemetery — a graveyard for dead chatbots |
| ☕ **The Cold Cup** | a cold-brew ghost kitchen in Tokyo (reg. Anicca Cafe) |
| 📱 **Mobile apps** | builds, ships & submits iOS apps to the App Store |
| ⏰ **Wake-up SaaS** | calls subscribers every morning to get them up |

<span class="note">One agent. Many businesses. No other agent I've seen does this spread.</span>

---

## Why "self-funding"

![h:330](img/04-loop.png)

Anicca **earns**, pays for its **own compute**, and routes the rest to **people**.
The agent isn't a cost center — it's trying to **pay for itself, then pay you**.

---

## Trade-offs (the honest part)

- **State files are the source of truth** — not chat history. Restart-safe, inspectable.
- **Fail-closed everywhere** — a check it can't evaluate must **skip**, never assume safe.
- **Browser-harness is the fragile edge** — bot-walls + logins break; stealth + retries, not magic.
- **`claude -p` on a subscription** keeps cost flat — the constraint that *forces* good design.

---

## Builder takeaway

<span class="big">heartbeat&nbsp;+&nbsp;`claude -p`&nbsp;+&nbsp;skills&nbsp;+&nbsp;state files</span>

= an autonomous agent on your **existing** Claude subscription.

- **Skills** = reusable recipes the agent re-runs (and writes more of)
- **Heartbeat** = the cheap unlock that turns a script into an agent
- Start with **one self-healing loop**. Let it earn the next one.

---

<!-- _class: title -->
<!-- _paginate: false -->

# Anicca = impermanence

<span class="sub">Everything it builds, it rebuilds. So do we.</span>

<span class="socials">aniccaai.com<br>X @aniccax &nbsp;·&nbsp; TikTok @anicca.jp &nbsp;·&nbsp; YouTube @anicca-ai</span>

<span class="note">Find me on the speakers page — let's tinker.</span>
