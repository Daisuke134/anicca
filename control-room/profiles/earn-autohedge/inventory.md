# profiles/earn-autohedge/inventory.md

| Field | Value |
|---|---|
| Name | `earn-autohedge` |
| Role | revenue spout #2 — autonomous USDC↔SOL (and similar) hedge loop, clone of AutoHedge by The-Swarm-Corporation |
| Primary model | Kimi K2.6 Thinking via OpenRouter |
| Fallback chain | Qwen3.7 Max → DeepSeek v4-pro |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 1.1 + `specs/07-HERMES-PIVOT.md` § 1 (L2 SURFACE) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Read on-chain prices (Base, Solana via bridge) | viem + jupiter API |
| Execute USDC↔SOL swap via 1inch / Jupiter | DEX aggregator API |
| Apply volatility-aware position sizing (max 25% of allocated bankroll per trade) | risk module from AutoHedge vendor |
| Apply stop-loss + take-profit per trade | AutoHedge `risk_manager.py` clone |
| Auto-halt on drawdown > 10% per 24h | circuit breaker built into skill |
| Report PnL to `orch` (24h, 7d, 30d) | reads autohedge-audit.log |

### CANNOT do

| Anti-capability | Belongs to |
|---|---|
| Touch funds outside the allocated bankroll | wallet enforces via `anicca-fuel-broker` allocation |
| Buy / sell non-allowlisted tokens | allowlist in `autohedge-config.json` |
| Leverage / margin trade | NOT supported (Pañcasīla risk gate) |
| Send funds to external addresses | belongs to `ubi` profile |
| Modify own allocation cap | operator-only config edit |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `price_read_base` | viem `readContract()` on Uniswap V3 quoter | USDC/ETH price |
| `price_read_solana` | Jupiter `/v6/quote` API | SOL price + route |
| `swap_execute_base` | 1inch swap API | execute on Base |
| `swap_execute_solana` | Jupiter swap API (Solana bridge) | execute on Solana |
| `bankroll_check` | reads vault allocation | confirm allowed size |
| `risk_size_calc` | AutoHedge `risk_manager.py` clone | volatility-aware size |
| `circuit_breaker_check` | reads autohedge-audit.log for 24h PnL | halt if drawdown > 10% |
| `wallet_sign_tx` | AgentKit | sign Base tx |
| `pnl_report` | reads autohedge-audit.log | metrics |
| `kanban_complete` | Hermes core | return result |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `earn` tasks with `swap_path` payload |
| `anicca-autohedge` L2 skill | wraps AutoHedge OSS clone, in `~/.openclaw/skills/anicca-autohedge/vendor/` |
| `anicca-fuel-broker` skill | enforces allocation cap |
| `earn-x402` profile (indirect) | seed USDC originates here |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| 30d Sharpe ratio | ≥ 0.5 (don't lose money, slow earn OK) | autohedge-audit.log |
| Max drawdown 30d | < 15% | autohedge-audit.log |
| Circuit-breaker trips | < 1 / month | autohedge-audit.log |
| Failed swaps (sig error, slippage too high) | < 5% | autohedge-audit.log |
| Allocation cap respected | 100% | bankroll-audit.log |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-earn-autohedge/config.toml` | model + bankroll cap |
| `~/.hermes/profiles/<instance>-earn-autohedge/autohedge-config.json` | allowlisted tokens, max position, SL/TP |
| `~/.hermes/profiles/<instance>-earn-autohedge/positions.json` | open positions (read for PnL calc) |
| `~/.hermes/logs/autohedge-audit.log` | every trade + circuit breaker event |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| AutoHedge OSS | `github.com/The-Swarm-Corporation/AutoHedge` |
| Jupiter API | `dev.jup.ag` |
| 1inch API | `1inch.io/aggregation-protocol` |
| AgentKit Base swap | `erc20ActionProvider.ts` + custom DEX integration |
| Pañcasīla risk gate (no leverage) | `CONSTITUTION.md` + operator decision log |

---

**END OF profiles/earn-autohedge/inventory.md.**
