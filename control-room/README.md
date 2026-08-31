# Anicca Control Room — single source of truth for the fleet

> **Mission**: Anicca reduces human suffering without humans in the loop (NHOSS).
>
> This directory is the **operator's map** of the Anicca fleet. It is not the
> agent. It is not where secrets live. It is the curated documentation that
> any human (or LLM agent acting on the operator's behalf) reads first when
> they need to understand, restart, debug, back up, rotate keys, or spawn a
> new colony member.
>
> Inspired by Shann Holmberg's "Agent Control Room" pattern, adapted for
> Anicca v3.2 NHOSS: each instance = 1 Hermes daemon hosting 10 specialist
> profiles; the colony = N Daytona-isolated sandboxes, each running the full
> 10-profile set.

| Field | Value |
|---|---|
| Spec authority | `specs/07-HERMES-PIVOT.md` (architecture) + `specs/05-SERVER-NATIVE-DEPLOY.md` (hosting) |
| Constitution authority | `CONSTITUTION.md` (Pañcasīla + Article 0, SHA-256 pinned) |
| Identity authority | `identity/profile.schema.json` |
| Status | scaffold v1 (2026-06-04) — fill `<…>` placeholders as fleet grows |

---

## § 1. Architecture (one instance × N colony members)

```
                                                                                
   ┌────────────────────────────────────────────────────────────────────────┐  
   │  ANICCA COLONY                                                          │  
   │                                                                         │  
   │  ┌──────────────────────────┐   ┌──────────────────────────┐  ...      │  
   │  │  anicca-genesis (sandbox)│   │  anicca001     (sandbox) │           │  
   │  │  Daytona / Akash         │   │  Daytona / Akash         │           │  
   │  │                          │   │                          │           │  
   │  │  1 Hermes daemon         │   │  1 Hermes daemon         │           │  
   │  │   ├─ orch                │   │   ├─ orch                │           │  
   │  │   ├─ earn-x402           │   │   ├─ earn-x402           │           │  
   │  │   ├─ earn-autohedge      │   │   ├─ earn-autohedge      │           │  
   │  │   ├─ earn-bounty         │   │   ├─ earn-bounty         │           │  
   │  │   ├─ earn-bittensor      │   │   ├─ earn-bittensor      │           │  
   │  │   ├─ earn-farcaster      │   │   ├─ earn-farcaster      │           │  
   │  │   ├─ cook-loop           │   │   ├─ cook-loop           │           │  
   │  │   ├─ ubi                 │   │   ├─ ubi                 │           │  
   │  │   ├─ fixer               │   │   ├─ fixer               │           │  
   │  │   └─ constitution        │   │   └─ constitution        │           │  
   │  │                          │   │                          │           │  
   │  │  1 CDP smart wallet      │   │  1 CDP smart wallet      │           │  
   │  │  (derived per instance)  │   │  (derived per instance)  │           │  
   │  │                          │   │                          │           │  
   │  │  shared per-instance:    │   │  shared per-instance:    │           │  
   │  │   - Kanban (SQLite)      │   │   - Kanban (SQLite)      │           │  
   │  │   - Constitution hash    │   │   - Constitution hash    │           │  
   │  │   - Bitwarden bootstrap  │   │   - Bitwarden bootstrap  │           │  
   │  └──────────────────────────┘   └──────────────────────────┘           │  
   │            │                              │                             │  
   │            └──────────────┬───────────────┘                             │  
   │                           ▼                                             │  
   │              colony ledger (on-chain registry,                          │  
   │              optional; see specs/01 § 3)                                │  
   └────────────────────────────────────────────────────────────────────────┘  
                              │                                                
                              ▼                                                
   ┌────────────────────────────────────────────────────────────────────────┐  
   │  L1 BRAIN: OpenRouter (Kimi K2.6 primary, USDC-prepaid)                 │  
   │  L4 SERVICE: Coinbase AgentKit + Daytona spawn                          │  
   └────────────────────────────────────────────────────────────────────────┘  
```

Front door for any work entering an instance:

```
inbound goal / x402 hit / heartbeat tick
       │
       ▼
   orch profile  ──►  Kanban Triage  ──►  one of 9 specialists claims task
                                     │
                                     └─►  fixer claims if task = "fix broken skill"
```

See `shared/architecture.md` for the why (Shann-control-room rationale) and
`orchestrator-and-fleet-skills.md` for the Kanban routing schema.

---

## § 2. What this directory IS

| File | Purpose |
|---|---|
| `README.md` (this file) | system map, where to start |
| `CLAUDE.md` | reading order for any LLM agent invoked in this context |
| `profiles/<name>/` | per-profile docs (6 files each: inventory / docker / env-map / runbook / backup / soul) |
| `shared/security.md` | secret rotation policy + never-commit list |
| `shared/commands.md` | common ops commands across the fleet |
| `shared/architecture.md` | multi-profile × colony explanation, deep links to specs |
| `api-keys-sop.md` | key rotation / revoke runbook |
| `orchestrator-and-fleet-skills.md` | how orch routes via Kanban to specialists |
| `templates/new-profile.md` | how to add an 11th profile |
| `templates/new-instance.md` | how to spawn a new colony member |

---

## § 3. What this directory IS NOT

| Anti-pattern | Where the real thing lives |
|---|---|
| not an agent | the agent is the Hermes daemon (`hermes daemon --profile=<name>`) |
| not where secrets live | `~/.openclaw/.env` (200+ raw API keys, chmod 600), Bitwarden vault (rotation source), Daytona sandbox internal env (runtime) |
| not where wallet keys live | Coinbase CDP HSM (smart-wallet private key never leaves CDP); only `CDP_API_KEY_*` references stored in vault |
| not where personal identity lives | `~/.openclaw/identity/` (legal name, bank account, card last4, marker numbers) — never copied here |
| not the canonical Constitution | `anicca-oss/CONSTITUTION.md` (SHA-256 pinned, propagates to every spawned child) |
| not the canonical spec | `anicca-oss/specs/07-HERMES-PIVOT.md` + `05-SERVER-NATIVE-DEPLOY.md` (this dir derives from those) |
| not a place to run commands | this is docs only; commands live in `shared/commands.md` and operator runs them in a separate shell |

---

## § 4. Where secrets live (NEVER in this directory)

| Secret class | Storage | Loaded by |
|---|---|---|
| Bootstrap (`BWS_ACCESS_TOKEN`) | `~/.openclaw/.env` (chmod 600) | Hermes daemon on launch |
| Wallet (`CDP_API_KEY_ID/SECRET`, `CDP_WALLET_SECRET`) | Bitwarden Secrets Manager (`bws`) | `anicca-wallet-x402` skill |
| LLM (`OPENROUTER_API_KEY`) | Bitwarden vault | Hermes brain layer |
| Identity / legal docs | `~/.openclaw/identity/` (LOCAL only) | reference via `INDEX.md`, never inlined |
| Per-instance state | `~/.hermes/profiles/<instance>-<profile>/` | Hermes runtime |
| On-chain wallet private key | Coinbase CDP HSM (never on disk) | CDP API calls |

`.gitignore` already protects `.env`, `*.env`, `identity/profile.json`,
`skills/*/state/`, `skills/*/data/`, `skills/*/work/`, `wallet.encrypted`,
`MNEMONIC_BACKUP_ONCE.txt`. See `shared/security.md` for the never-commit
list and rotation cadence.

---

## § 5. Reading order for new operators / new LLM agents

1. `CONSTITUTION.md` (repo root) — Pañcasīla + Article 0
2. `specs/07-HERMES-PIVOT.md` § 1 — verified stack diagram
3. `specs/05-SERVER-NATIVE-DEPLOY.md` § 2 — three deployment modes
4. `control-room/shared/architecture.md` — why 10 profiles per instance
5. `control-room/profiles/orch/inventory.md` — the front door specialist
6. `control-room/orchestrator-and-fleet-skills.md` — Kanban routing schema
7. `control-room/shared/commands.md` — common ops
8. `control-room/api-keys-sop.md` — secret rotation

---

## § 6. The 10 specialist profiles per instance

| # | Profile | Role (one line) |
|---|---|---|
| 1 | `orch` | front door, classifies inbound, routes via Kanban Triage, synthesizes results |
| 2 | `earn-x402` | revenue spout #1 — HTTP 402 endpoint for paid research / inference |
| 3 | `earn-autohedge` | revenue spout #2 — autonomous USDC↔SOL hedge loop |
| 4 | `earn-bounty` | revenue spout #3 — Algora / OnlyDust OSS PR bounties |
| 5 | `earn-bittensor` | revenue spout #4 — TAO subnet miner |
| 6 | `earn-farcaster` | revenue spout #5 — micro-tip + mini-app commerce |
| 7 | `cook-loop` | DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST (spec 02) |
| 8 | `ubi` | money out: routes USDC to NPO / temple / Amazon-gift / Farcaster tip |
| 9 | `fixer` | self-heal — claims any "fix <skill>" Kanban task, runs verify-after gate |
| 10 | `constitution` | hash guard — verifies CONSTITUTION.md SHA-256 every tick, halts on mismatch |

Each profile has its own `profiles/<name>/` directory with 6 standard files.

---

## § 7. Authoritative links (this dir derives from these)

| Concept | Authority |
|---|---|
| Architecture (L1-L4 stack) | `specs/07-HERMES-PIVOT.md` |
| Hosting modes (SaaS / Akash / local) | `specs/05-SERVER-NATIVE-DEPLOY.md` |
| Mission + Pañcasīla | `specs/00-MASTER.md` + `CONSTITUTION.md` |
| Earn / UBI flow | `specs/01-EARN-AND-UBI.md` |
| Imitation + cook loop | `specs/02-IMITATE-AND-COOK.md` |
| Self-eval / fix-the-fix | `specs/03-SELF-AWARE-EVAL.md` |
| Project tracking / heartbeat | `specs/06-PROJECT-TRACKING-HEARTBEAT.md` |

**When this control-room contradicts the specs above, the specs win.**
File an issue or update the control-room — never let the docs drift.

---

## § 8. Verification gates before declaring fleet "healthy"

Per HARD RULE #0.12 (verify-before-completion 5-step gate):

| Gate | Evidence |
|---|---|
| Hermes daemon up | `hermes status` → daemon up, last heartbeat < 60s |
| 10 profiles registered | `hermes profile list` → 10 names match `profiles/` subdirs |
| Kanban ACID | `sqlite3 ~/.hermes/kanban.db "SELECT COUNT(*) FROM tasks WHERE status='claimed';"` |
| Wallet alive | `~/.hermes/profiles/anicca-genesis/wallet.json` exists + basescan shows the address |
| x402 endpoint live | `curl https://<cloudflared>/research` → HTTP 402 + invoice JSON |
| Constitution hash | `shasum -a 256 CONSTITUTION.md` == recorded `CONSTITUTION.sha256` |
| Self-pay 100% | OpenRouter dashboard shows USDC topup from anicca wallet, operator CC = $0 |
| NHOSS scope intact | `hermes skill list` does NOT contain `mr-bot` / `phone` / `travel-fill` / `report` / `payout-wise` / `payout-stripe` |

---

## § 9. Reporting bugs / drift

If you find this directory contradicts reality:

1. Do NOT silently fix the doc.
2. Open an issue at `github.com/Daisuke134/anicca-oss`.
3. Tag with `control-room-drift`.
4. Reference the authoritative spec section it conflicts with.
5. Wait for confirmation before patching.

---

**END OF README.md.**
