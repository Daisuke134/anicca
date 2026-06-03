# profiles/earn-bittensor/inventory.md

| Field | Value |
|---|---|
| Name | `earn-bittensor` |
| Role | revenue spout #4 — TAO subnet miner (currently wallet-only earnings; mining work TBD per subnet) |
| Primary model | Kimi K2.6 Thinking via OpenRouter |
| Fallback chain | DeepSeek v4-pro |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 1 + `specs/07-HERMES-PIVOT.md` § 1 (L2 SURFACE) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Register on a Bittensor subnet (wallet only, no mining yet) | `bittensor` Python SDK |
| Monitor TAO balance + subnet position | subnet API + on-chain query |
| Mine on subnets that accept LLM-inference work (e.g., text-prompting subnets) | subnet template repos |
| Convert TAO → USDC via DEX (Kraken / Bittensor bridge) | DEX API |
| Report mining yield to `orch` (24h, 7d, 30d) | bittensor-audit.log |

### CANNOT do

| Anti-capability | Why |
|---|---|
| Run validator nodes | requires staked TAO ≥ 1k (out of scope for Anicca instance bankroll) |
| Mine on subnets requiring KYC | NHOSS violation |
| Spend TAO on non-USDC swaps (e.g., gambling subnets) | risk gate |
| Hold TAO position > 50% of instance bankroll | diversification gate |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `bittensor_wallet_create` | `bittensor.wallet()` SDK | wallet bootstrap (per instance) |
| `bittensor_subnet_list` | `bittensor.subtensor().subnets()` | discovery |
| `bittensor_register` | `bittensor.subtensor().burned_register()` | join subnet |
| `bittensor_mine` | subnet-specific template (e.g., text-prompting miner) | actual mining |
| `bittensor_yield_read` | reads chain state | report |
| `tao_to_usdc_swap` | Kraken API OR DEX | conversion |
| `wallet_sign_tx` | AgentKit (for USDC side) | post-swap |
| `bankroll_check` | reads vault allocation | diversification gate |
| `subnet_kpi_check` | reads subnet metrics | abandon if APY < threshold |
| `kanban_complete` | Hermes core | return result |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `earn` tasks with `subnet_id` payload |
| `anicca-bittensor-miner` L2 skill | wraps SDK |
| `anicca-fuel-broker` skill | bankroll allocation cap |
| `earn-x402` profile (indirect) | seed USDC needed for subnet registration burn |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| 30d yield in USDC equivalent | ≥ 5% APY on allocated bankroll (= conservative floor) | bittensor-audit.log |
| Subnet uptime (= miner health) | ≥ 95% | subnet status query |
| TAO position vs bankroll | ≤ 50% | bankroll-audit.log |
| Failed swap (TAO → USDC) | < 5% | bittensor-audit.log |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-earn-bittensor/config.toml` | model + subnet allowlist |
| `~/.hermes/profiles/<instance>-earn-bittensor/bittensor-wallet/` | TAO wallet keystore (chmod 600) |
| `~/.hermes/profiles/<instance>-earn-bittensor/subnet-positions.json` | active registrations |
| `~/.hermes/logs/bittensor-audit.log` | mining + swap events |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| Bittensor docs | `docs.bittensor.com` |
| Subnet templates | `github.com/opentensor/text-prompting` (and others) |
| TAO ↔ USDC bridge | varies (Kraken / DEX / bridge) |
| Spec 01 § 1 (5 spouts) | `specs/01-EARN-AND-UBI.md` |

---

**END OF profiles/earn-bittensor/inventory.md.**
