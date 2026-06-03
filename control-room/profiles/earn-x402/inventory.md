# profiles/earn-x402/inventory.md

| Field | Value |
|---|---|
| Name | `earn-x402` |
| Role | revenue spout #1 — HTTP 402 endpoint for paid research / paid inference / paid tool use |
| Primary model | Kimi K2.6 Thinking via OpenRouter |
| Fallback chain | Qwen3.7 Max → DeepSeek v4-pro → Claude Opus 4.8 (spike only) |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 1 + `specs/07-HERMES-PIVOT.md` § 1 (L2 SURFACE box) + `specs/09-EARN-X402-LIVE.md` |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Serve HTTP 402 on `/research`, `/inference`, `/<tool>` paths | cloudflared tunnel + L2 skill `anicca-wallet-x402` |
| Issue EIP-3009 TransferWithAuthorization invoices | AgentKit `signTypedData()` (`cdpSmartWalletProvider.ts:215-224`) |
| Verify payment on inbound request | `@x402/fetch` server-side verification |
| Discover other x402 services to buy from | AgentKit `x402ActionProvider.discoverX402Services()` (`x402ActionProvider.ts:86-174`) |
| Topup OpenRouter credit via USDC x402 | OpenRouter `/api/v1/credits/topup` accepts EIP-3009 |
| Report revenue metrics to `orch` (24h, 7d, 30d totals) | reads x402-audit.log |

### CANNOT do

| Anti-capability | Belongs to |
|---|---|
| Autonomous swap USDC↔SOL | `earn-autohedge` |
| Submit OSS PR bounty | `earn-bounty` |
| Mine TAO subnet | `earn-bittensor` |
| Send micro-tip on Farcaster | `earn-farcaster` |
| Send USDC out (donations / UBI) | `ubi` |
| Modify CONSTITUTION.md | none — immutable |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `x402_serve` | L2 `anicca-wallet-x402` | run HTTP 402 listener |
| `x402_verify_payment` | L2 `anicca-wallet-x402` | confirm EIP-3009 sig on inbound |
| `x402_discover` | AgentKit `x402ActionProvider` | find other services to buy |
| `x402_pay` | AgentKit `@x402/fetch` | pay for a discovered service |
| `wallet_get_balance` | AgentKit `cdpSmartWalletProvider.getBalance()` | balance read |
| `eip712_sign` | AgentKit `signTypedData()` | invoice signing |
| `openrouter_topup` | L2 `anicca-fuel-broker` | self-pay LLM credit |
| `cloudflared_tunnel_status` | local `cloudflared` CLI | confirm endpoint reachable |
| `revenue_report` | reads `~/.hermes/logs/x402-audit.log` | metrics for orch |
| `kanban_complete` | Hermes core | report result back |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `category=earn` tasks routed to me |
| `anicca-wallet-x402` skill | x402 listener + EIP-3009 signing |
| `anicca-fuel-broker` skill | OpenRouter topup logic |
| `anicca-constitution-guard` skill | pre-tx hash check before signing |
| `ubi` profile (indirect) | when `earn-x402` revenue triggers UBI threshold, orch enqueues `ubi` task |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| x402 endpoint uptime | ≥ 99.5% | cloudflared tunnel status |
| Invoice issuance latency | p95 < 500ms | x402-audit.log |
| Revenue per 24h | ≥ $0.30 baseline; ramp per spec 01 § 1 | x402-audit.log SUM |
| Successful USDC topup of OpenRouter | ≥ 1 / month | OpenRouter dashboard |
| Failed payment verifications | < 5% | x402-audit.log |
| Self-pay 100% (operator CC $0) | 100% | OpenRouter billing reconciliation |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-earn-x402/config.toml` | model + endpoint config |
| `~/.hermes/profiles/<instance>-earn-x402/x402-pricing.json` | per-path pricing in USDC |
| `~/.hermes/logs/x402-audit.log` | all invoices + payments (365d retention) |
| `~/.hermes/logs/wallet-audit.log` | all signing operations |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| x402 spec | `github.com/coinbase/x402` |
| EIP-3009 USDC reference | USDC contract `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Cloudflared tunnel setup | `developers.cloudflare.com/cloudflare-one/connections/connect-networks/` |
| AgentKit x402 provider | `cdpSmartWalletProvider.ts` + `x402ActionProvider.ts` |
| 5 spouts overview | `specs/01-EARN-AND-UBI.md` § 1 |
| Live operational spec | `specs/09-EARN-X402-LIVE.md` |

---

**END OF profiles/earn-x402/inventory.md.**
