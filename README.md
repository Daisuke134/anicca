<!-- startup-context-version: 2026-10-20.1 -->
<!-- startup-context-digest: a2a6f2be251c15beb045c04db613e32bab010a2cd9f138be3cceb1625b0906f8 -->
# Anicca

This repository is the public flagship of **Anicca**, an open company working to end suffering through behavior intervention. Everything we can open lives here — product code, research, and evaluations. Credentials, raw operations records, and customer data are never published in this repository; they stay in a separate private operations repository.

- **Company**: Anicca
- **Model**: **Manager** — a model that learns how people respond to a stimulus (a notification, a message, a deliverable) and chooses the input most likely to produce the response people actually want.
- **Eval**: **ManagerBench** — one benchmark: can AI make something people want? Every case is *situation → what the AI made (stimulus) → the person's measured response*.
- **Product**: **Anicca** — the affirmation and nudge app people touch (iOS code under `apps/`). **Life Manager**, the no-human-in-the-loop work system, is documented in full below.

**Start here**: [START-HERE.md](START-HERE.md) · Research: [aniccaai.com/blog](https://aniccaai.com/blog) · Live company numbers: [aniccaai.com/open](https://aniccaai.com/open) · License: MIT ([LICENSE](LICENSE))

---

## Life Manager

**No Human in the Loop. No Human Credentials.**

Life Manager Cloud is being built to choose income-generating work, register its own work accounts, publish, distribute, and reconcile results without daily prompts, approval chats, or the user's private service credentials. Open it on your phone and see what your manager did and what it earned.

**The economic acceptance criterion: verified earnings exceed the subscription fee and all operating costs.** This is a requirement, not a promise of profit. Cloud signup-to-income and positive net returns are not verified end to end yet.

The stack reuses existing runtimes, browsers, schedulers, inboxes, credential stores, and ledgers. Missing capabilities are a reason to find a supported component, not write another harness. One product is designed for compatible local and cloud hosts; deployment and autonomy must be verified on each host.

[日本語](README.ja.md) · [Local setup guide](docs/getting-started.md) · [Agent catalog](docs/agents.md)

## Life Manager Cloud

[Life Manager Cloud](https://aniccaai.com/lm) is the phone-first hosted mode of this project.
The local installer below runs on your Mac; Cloud is being connected to a dedicated cloud
computer so work can continue when your phone is closed.

The current design reuses Maritime's official OpenClaw runtime, a persistent agent browser,
an agent-owned inbox, scoped credentials, scheduled wake-ups, and the existing work and
accounting ledgers. Naïve/Vetta is an additional managed execution platform; Tenki supplies
its underlying computers. These are execution environments for one product, not separate
Life Manager products. Keiki is an optional messaging interface, not another required loop.

The hosted earning workflow is **not verified end to end yet**. The first target is Capafy,
using a permitted publisher/team identity. Agent-owned service accounts are the design target;
marketplaces that require the user's own credentials or mandatory personal verification do
not qualify for that autonomous path. A listing, a sale, settlement, and profit are separate
outcomes. Local setup requirements below do not describe phone-only Cloud onboarding.

See the [runtime comparison and reusable source](docs/research/2026-11-05-cloud-runtime-lego.md),
the [Cloud specification and current tasks](docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md),
and the [public company dashboard](https://aniccaai.com/open/). The dashboard contains observed
company records with incomplete source coverage; company revenue is not Cloud-worker revenue.

## Businesses

| Business | Revenue model |
|---|---|
| Contract work | Paid projects on Coconala, Lancers, CrowdWorks, and Mercor. |
| Mobile apps | App sales and subscriptions. |
| Affiliate & CPA | Referral commissions and campaigns paid per customer action. |
| Writing | Paid articles, newsletters, and commissioned writing. |
| Digital products | Prompts, eBooks, and LINE stickers. |
| AI services | Paid AI skills, subscriptions, and APIs. |
| Investing | Configured stock-trading strategies. |

## Local edition requirements

- **ChatGPT Plus or higher.** Sign in with ChatGPT; no separate OpenAI API key is required.
- **A Mac that stays awake**, internet access, and at least 12 GiB of free disk space. A Mac mini works well for always-on use.

Each business needs its service accounts; some services may cost extra.

## Install the local edition

Run this in Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Daisuke134/life-manager/main/scripts/bootstrap.sh)" life-manager local
```

Sign in with your ChatGPT account through the official Codex login flow. Then follow the setup guide to connect accounts for the businesses you choose. Docker is not required.

See the [setup guide](docs/getting-started.md) for installation, keeping your Mac awake, and checking agent status.

- [Report an issue](https://github.com/Daisuke134/life-manager/issues)
- **License:** [MIT](LICENSE)
