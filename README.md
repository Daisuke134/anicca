<!-- startup-context-version: 2026-10-20.1 -->
<!-- startup-context-digest: 7c2a72ae0b66f083c12cafde115cc5079f2e9722807b42e2288aef3f370b170f -->
# Local Life Manager

**An open-source, no-human-in-the-loop money printer: AI agents build businesses from scratch and run them on your Mac.**

Connect the accounts your chosen businesses need. Life Manager's agents are designed to find opportunities, build businesses, sell products and services, and handle day-to-day operations toward revenue without ongoing human input.

> **Early development:** Autonomous operation and verified profit are goals, not proven results yet. See the [agent catalog](docs/agents.md) for current capabilities.

[日本語](README.ja.md) · [Setup guide](docs/getting-started.md) · [Agent catalog](docs/agents.md)

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

## Core requirements

- **ChatGPT Plus or higher.** Sign in with ChatGPT; no separate OpenAI API key is required.
- **A Mac that stays awake**, internet access, and at least 12 GiB of free disk space. A Mac mini works well for always-on use.

Each business needs its service accounts; some services may cost extra.

## Install

Run this in Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Daisuke134/life-manager/main/scripts/bootstrap.sh)" life-manager local
```

Sign in with your ChatGPT account through the official Codex login flow. Then follow the setup guide to connect accounts for the businesses you choose. Docker is not required.

See the [setup guide](docs/getting-started.md) for installation, keeping your Mac awake, and checking agent status.

- [Report an issue](https://github.com/Daisuke134/life-manager/issues)
- **License:** [MIT](LICENSE)
