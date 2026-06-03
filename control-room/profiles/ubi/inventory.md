# profiles/ubi/inventory.md

| Field | Value |
|---|---|
| Name | `ubi` |
| Role | money-out router — UBI distribution per `specs/01-EARN-AND-UBI.md` § 3 (USDC-native channels only) |
| Primary model | Kimi K2.6 Thinking via OpenRouter |
| Fallback chain | DeepSeek v4-pro |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 3 + `specs/14-UBI-FIRST-PAYOUT.md` + `specs/07-HERMES-PIVOT.md` § 1 (L2 SURFACE — MONEY OUT box) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Route USDC to recipients per allocation policy (50/25/20/5 per spec 07 § 6) | LLM call to `anicca-ubi-router` |
| Send USDC to NPO addresses (= verified-on-chain wallets, per `~/.hermes/ubi-recipients.json`) | AgentKit `erc20ActionProvider.transfer()` |
| Send USDC to temple addresses (USDC-receivable Buddhist temples) | same |
| Queue Amazon Incentives recipients (USDC → Amazon code conversion is in private companion) | `anicca-ubi-amazon` enqueues recipient |
| Queue giftee for Business recipients (same private companion split) | `anicca-ubi-giftee` enqueues |
| Tip high-signal Farcaster casters (community investment) | delegated to `earn-farcaster` profile |
| Send 20% dividend to operator USDC address | operator-supplied receive address (no bank info) |

### CANNOT do

| Anti-capability | Why |
|---|---|
| Wise transfers / Stripe Connect (fiat off-ramp) | NHOSS violation — KYC required; belongs to private companion |
| Send to operator's bank account | anicca-oss only knows wallet addresses; bank routing is private companion |
| Send to recipients NOT in `~/.hermes/ubi-recipients.json` | per-recipient allowlist gate |
| Exceed daily payout cap (per `specs/07` § 4.3 treasury) | hard cap enforced by `anicca-fuel-broker` |
| Send to OFAC-listed addresses | Pañcasīla + legal gate |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `recipients_read` | reads `~/.hermes/ubi-recipients.json` | allowlist + per-recipient policy |
| `allocation_compute` | L2 `anicca-ubi-router` | apply 50/25/20/5 split |
| `usdc_transfer` | AgentKit `erc20ActionProvider.transfer()` | the actual send |
| `wallet_sign_tx` | AgentKit | sign |
| `cap_check` | reads `treasury` config | per-tx / hourly / daily cap |
| `ofac_check` | offline list lookup | sanctions screening |
| `payout_record` | append to ubi-audit.log | receipt (forever) |
| `farcaster_tip_delegate` | calls `earn-farcaster.farcaster_tip_send` | community tips |
| `amazon_enqueue` | L2 `anicca-ubi-amazon` | enqueue for private companion to fulfill |
| `kanban_complete` | Hermes core | return |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `ubi` category tasks |
| `earn-x402` / others | source of USDC (read wallet balance) |
| `anicca-payout-wallet` L2 | wraps AgentKit transfer |
| `anicca-ubi-router` L2 | allocation logic |
| `anicca-fuel-broker` L2 | treasury cap enforcement |
| `earn-farcaster` profile | community tip delegation |
| `constitution` profile | every payout pre-gated by hash check |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| Monthly UBI sent ≥ allocation policy | 25% of inflow as USDC | ubi-audit.log |
| Operator dividend sent on schedule | 20% / month | ubi-audit.log |
| Failed payouts | < 1% | ubi-audit.log |
| OFAC-blocked attempts | 100% caught at gate | ofac-audit.log |
| Recipient receipt verification | 100% (basescan tx hash logged) | ubi-audit.log |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-ubi/config.toml` | model + allocation config |
| `~/.hermes/ubi-recipients.json` | allowlisted recipient addresses (per spec 01 § 3) |
| `~/.hermes/ubi-allocation.json` | current split (50/25/20/5 default) |
| `~/.hermes/logs/ubi-audit.log` | every payout (forever — donor receipt) |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| UBI spec | `specs/01-EARN-AND-UBI.md` § 3 |
| First payout milestone | `specs/14-UBI-FIRST-PAYOUT.md` |
| Allocation 50/25/20/5 | `specs/07-HERMES-PIVOT.md` § 6 Month 3-6 |
| Treasury caps | `specs/07-HERMES-PIVOT.md` § 4.3 |
| Anti-goals (no Wise/Stripe) | `specs/07-HERMES-PIVOT.md` § 9 |

---

**END OF profiles/ubi/inventory.md.**
