# Life Manager

**Life Manager manages your body, mind, and money.** It is a personal manager that turns goals into
completed real-world actions. It acts within delegated boundaries, verifies what happened, and reports the
result in plain language with evidence in Telegram.

| Organ | What Life Manager manages |
|---|---|
| **Daily** | Calendar, event and accelerator applications, job applications, priorities, and follow-through |
| **Physical / Mental** | Routines, wellbeing, and continuity of care |
| **Financial** | Net worth, cash flow, spending, income opportunities, and risk-managed investing |

[Open Life Manager](https://aniccaai.com/lm) · [Start in Telegram](https://t.me/LifeManagerBotbot?start=lp) · [View the source](https://github.com/Daisuke134/life-manager)

Start locally and keep your data on your machine; move to the web/cloud service when you want an always-on
manager. Both surfaces use the **same core**, evidence ledger, and human-readable reporting contract. Life
Manager never guarantees wealth or investment returns, and it never reports an attempted action as completed
without a receipt.

**Life Manager is the product. Anicca is the company name only when a form explicitly asks for it.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🌐 **[日本語版 README はこちら →](README.ja.md)**

**Repository SSOT:** this repository, [`Daisuke134/life-manager`](https://github.com/Daisuke134/life-manager), is the only Life Manager code, spec, release, workflow, and deployment source. `Daisuke134/life-manager-v0` is a read-only migration source until its required-code and runtime-reference counts reach zero. The current ordered execution plan and remaining work are maintained in [`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`](docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md); repository consolidation history remains in [`docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`](docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md).

---

## Quick start

### Use it — cloud (nothing to install)

[Start in Telegram](https://t.me/LifeManagerBotbot?start=lp), or open the
[web app](https://aniccaai.com/lm). The always-on service runs the scheduler, the connectors, and the
authenticated `/panel`; you talk to it in Telegram and it reports back there with receipts.

### Run it yourself — local (your machine holds the data)

Requires Docker. The local stack is Postgres + an object store + the API, scheduler, and worker — the same core
the cloud runs.

```bash
git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
cp deploy/local/.env.example deploy/local/.env     # ports and local-only object-store credentials
docker compose -f deploy/local/compose.yaml up -d --build
docker compose -f deploy/local/compose.yaml ps     # postgres · object-store · api · scheduler · worker
```

The API listens on `http://localhost:18788` and the worker exposes health on `:18790` (both overridable in
`deploy/local/.env`). Your data stays in the local Postgres and object store — nothing is shipped anywhere by
running this.

**Secrets are referenced, never inlined.** Jobs carry `secret://…` references and resolve them from the local
keychain or a tenant vault; see [`apps/life-manager/.env.example`](apps/life-manager/.env.example) for the shape
(`TELEGRAM_BOT_TOKEN_REF`, `POSTIZ_ACCESS_TOKEN_REF`, `REVENUECAT_API_KEY_REF`, …). Connect your own Telegram bot
token this way to talk to a local instance.

### Not what you wanted?

If you came here for the **self-funded agent** — the wallet-holding loop that earns its own compute — that is a
different thing and it lives in [`docs/agent-economy.md`](docs/agent-economy.md). It shares this repository and
this core, but it is not the product described above.

---

## One product, two execution surfaces

Life Manager is one product in one repository. “Local Life Manager” and the web app are not separate products or repositories; they are two execution surfaces powered by the same core, capabilities, and state contracts.

```text
                              LIFE MANAGER
                    one product · one repository
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
     LOCAL / SELF-HOSTED                      WEB / CLOUD
     deploy/local/compose.yaml                 apps/landing
          │                                  onboarding UI
          ▼                                       │
     apps/life-manager                             ▼
     api · scheduler · worker            apps/life-manager
          │                              Telegram · voice
          ▼                              scheduler · /panel
     postgres · object store                       │
     (your machine)                                ▼
             │                              user-scoped services
             └───────────────────┬───────────────────┘
                                 │
                shared economy and infrastructure
        runtime/loop · runtime/compute-proxy · services/x402-*
```

| Path | Role | What it is not |
|---|---|---|
| `apps/life-manager/` | The product core: Telegram, scheduling, calls, authenticated `/panel`, billing, and user workflows. Runs both locally (compose) and in the cloud (Railway) | Not the whole repository |
| `deploy/local/` | The local execution surface — compose stack, ports, local-only credentials | Not a separate “local edition” product |
| `apps/landing/` | The Life Manager onboarding web subset | Not the old multi-product Anicca website |
| `runtime/loop/`, `install.sh`, `start-local.sh` | The self-funded agent loop — see [`docs/agent-economy.md`](docs/agent-economy.md) | Not how you start Life Manager |
| `runtime/compute-proxy/`, `services/` | Self-pay inference and x402 settlement/API infrastructure | Not user-facing apps |
| `skills/` | Shared capabilities used by local and cloud execution | Not independent products |
| `apps/job-search-loop/`, `control-room/`, `adapters/` | Supporting operations, fleet documentation, and integrations | Not another Life Manager codebase |
| `docs/`, `specs/` | Current SSOT, evidence, and retained architecture history | Historical files are not automatically current authority |

Some internal package names, environment variables, service labels, and older documents still use `anicca`. In this repository, **Anicca is the company/technical namespace; Life Manager is the product**. A remaining `anicca` identifier does not imply a second product or another canonical repository.

---

## What's real today (honest)

| Capability | Status |
|---|---|
| **Local stack** (`deploy/local/compose.yaml`) — postgres · object store · api · scheduler · worker | **Runs** — the five services come up healthy and stay up (observed running for days on the maintainer's machine). |
| **Cloud service** (`apps/life-manager`, `node server.js` on Railway) | **Deployed** — the scheduler and API are the same code the local stack runs. |
| **Telegram reporting with receipts** | **Live** — every report carries a message id, and a send that fails is not recorded as sent. |
| **Calendar, connectors, coverage** (`lib/calendar-*`, `lib/connector-*`) | **Implemented, coverage still moving** — per-connector state and gaps are tracked in the execution spec rather than claimed here. |
| **Financial organ** (net worth, cash flow, payouts, ledgers) | **Partial** — the ledger and payout jobs exist; their current health is tracked in the execution spec. Nothing here is an investment guarantee. |
| **The self-funded agent economy** | Separate track — status and on-chain evidence in [`docs/agent-economy.md`](docs/agent-economy.md). |

---

## North Star (immutable)

```
Reduce suffering.
No killing (Pāṇātipātā veramaṇī).
```

These two lines are SHA-256 hash-pinned and cannot be changed by any skill, self-edit loop, or PR.

---

## Links

- **Product:** <https://aniccaai.com/lm> · [Telegram](https://t.me/LifeManagerBotbot?start=lp)
- **Live dashboard (auto-updated):** <https://aniccaai.com/dashboard>
- **The agent economy underneath:** [`docs/agent-economy.md`](docs/agent-economy.md)
- **Repository (whole product):** <https://github.com/Daisuke134/life-manager>
