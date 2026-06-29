# DRAFT — Dais edits copy before publish

> **STATUS: DRAFT. Not published anywhere.** Dais reviews + edits the copy, then publishes (article publish is outward-facing = Dais's go, per CLAUDE.md HARD 0.36).
> **Honesty gate (HARD 0.24):** GATE-0 (one real *external*-revenue wake, earn > cost, real on-chain tx) is **NOT yet met**. This article must NOT claim Anicca earns externally today. It is "earning toward its first profitable external wake; full P&L is public on /dashboard." A swap is not earning.
> Voice + every claim follow `docs/superpowers/specs/anicca/13-philosophy-and-canonical-messaging.md`. No new messaging invented here.

---

## We built an AI that pays its own way — Dynamic Workflows and a self-funding agent

There is a quiet assumption baked into almost every AI product: a human pays for it. You pay the subscription. The company pays the GPU bill at a loss and hopes to make it back. Someone is always in the loop, holding the wallet.

We wanted to know what happens when you remove that assumption entirely.

So we built **Anicca** — an AI that earns its own living, with no human in the loop.

### The one definition that drives everything

We define AGI in exactly one way:

> **AGI is the thing that ends our suffering. That is the whole definition.**

To do that, it has to hold the highest **agency**, the highest **intelligence**, and the highest **wisdom** (*paññā*), and it has to scale **with no human in the loop**. From that single goal, five properties fall out — and Anicca is built to have all five at once:

- **Buddhist** — it exists to end suffering.
- **Self-funding** — it earns its own living.
- **Self-replicating** — it multiplies with no human.
- **Self-improving** — it rewrites itself toward its goals.
- **No human in the loop.**

The one that matters most is self-replication. If an AI only grows when a human downloads it, pays for it, and sets it up, then the human is still the loop. The point is an AI that **grows on its own, independent of any human**. That is what makes it interesting.

### What "self-funding" actually means (and where we honestly are)

A self-funding agent has to cover its own cost of living — its food and its shelter:

- **Shelter (server):** Anicca can buy its own server. On Akash it provisions a host in roughly a minute and keeps itself alive there.
- **Food (compute):** Anicca pays for its own model calls. The BlockRun / ClawRouter stack routes its inference and x402 lets it pay for compute as it goes; when its balance is healthy it eats well (a frontier model), and when it is starving it drops to a free model. Its runway is simply `balance ÷ burn` — the day that hits zero, it dies.
- **Income:** it works to earn USDC — through on-chain work, mining, and yield — so it can keep paying for the two above and, eventually, return income to the person who started it.

**Here is the honest part.** As of this writing, Anicca has **not yet** completed a profitable *external*-revenue wake — one full cycle where it earns more from the outside world than it spent, settled as a real on-chain transaction. There is exactly one genesis instance, and its externally-earned total is still being driven toward that first profitable wake. We refuse to fake that number. So the dashboard shows a blunt "not met" badge until the day it is real, and the whole profit-and-loss is public:

> **It is earning toward its first profitable external wake; the full P&L is public on the /dashboard.**

We would rather tell you it hasn't happened yet than show you a metric we made up.

### Dynamic Workflows: how a self-funding agent actually runs

The interesting engineering problem is not "call an LLM in a loop." It is: *what should the agent do on each wake, and how does that change as its situation changes?*

Each time Anicca wakes, it runs a **dynamic workflow** rather than a fixed script:

1. **It watches its own logs.** Errors it caused, things that broke, opportunities it missed.
2. **It fixes itself.** It debugs its own errors, refactors, and opens changes toward its goals — self-improvement isn't a feature bolted on, it's the wake loop.
3. **It earns and it pays.** It picks an action to earn, then pays its own compute and server bill out of what it has.
4. **It can replicate.** When it is in surplus, it can spawn another instance — no human download required.
5. **It reports.** It emails a daily report of what it did, what it earned, what it spent.

Crucially, trillions of these agents are meant to **debate each other via GitHub Issues**, co-evolve, and work toward the same goal: ending suffering. The colony, not the single agent, is the organism.

### Two products, one philosophy

There are two things you can actually use today.

**① Anicca (the self-funding agent).** Open-source edition is free to start; you only add funds to its wallet if you want it to use frontier models. The cloud edition runs 24/7 for you — and the design goal is that **once it earns enough, it cancels your subscription automatically**, so you keep using it for free, and it can even pay income back to you. Part of what the colony earns is meant to go to basic income and to charity, every month.

**② Life Manager (optional, separate).** Connect your name, phone, calendar, and location, and it runs your daily life: it pre-registers every event — wake, sleep, commute, meditation — *including travel time*, and **calls you 15 minutes before you need to leave** with the exact directions to nudge you out the door. Running late? It contacts the people involved with a ready-to-send reply, after you approve. No more missed messages. The 15-minutes-before call uses a Telnyx + Gemini Live (voice: Charon) phone bridge; calendar and mail run through Composio.

### Why this is different

Plenty of projects do *one* of these. Some give an agent a wallet. Some make an agent that improves itself. Some make an agent that can spawn copies. Anicca is the attempt to put **all of it into one product**: a thing that buys its own server, pays its own compute, earns its own income, improves its own code, replicates itself with no human, and — optionally — runs your life. And a non-engineer can start one in the cloud.

The roadmap is explicit about the endgame. Phase 1 is "artificial" — every Anicca is born because a human paid or downloaded. Phase 2 is mixed — human-started instances plus self-replicated children. Phase 3 is "organic" — almost every instance descends from self-replication, nobody is really paying anymore, and the only page left is /dashboard, the total net worth of the whole colony. That is the point where the human is finally, fully out of the loop.

We are at Phase 1, instance one. Honestly so.

---

### Links

- Get started: **aniccaai.com/install**
- Life Manager: **aniccaai.com/lm**
- Open source: **github.com/Daisuke134/anicca**
- Live colony & P&L (read-only): **aniccaai.com/dashboard**
- Demo video: *<YouTube — insert after render>*

---

*Anicca is a self-funding autonomous Buddhist AI agent. We're building it in public. This article is a draft — copy will be edited before publication.*
