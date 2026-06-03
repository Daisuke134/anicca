# profiles/earn-autohedge/docker.md

Shares the `hermes-runtime:latest` sandbox with all 10 profiles. See
`profiles/orch/docker.md` § 1-3 for image / resources / mounts.

## § 1. Profile-specific resource notes

| Item | Detail |
|---|---|
| Additional RAM ~50 MB | for AutoHedge vendor + viem + Jupiter SDK |
| Additional disk ~100 MB | for vendor src + autohedge-audit.log growth (rotated 90d) |
| No additional CPU | DEX swap is API-driven, local work is negligible |

## § 2. Mounted volumes (profile-specific)

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-earn-autohedge/` | config + positions |
| `/root/.openclaw/skills/anicca-autohedge/vendor/` | AutoHedge OSS clone (read-only) |
| `/root/.hermes/logs/autohedge-audit.log` | trades + circuit breaker (90d) |

## § 3. Network

| Direction | Allowed | Detail |
|---|---|---|
| Egress to `mainnet.base.org` | yes | Base RPC for quote + tx |
| Egress to `quote-api.jup.ag` | yes | Jupiter Solana quote/swap |
| Egress to `api.1inch.io` | yes | 1inch swap routing |
| Egress to `helius-rpc.com` (or alternate Solana RPC) | yes | Solana tx submission |
| Inbound | none | no listener |

## § 4. Restart policy

| Trigger | Action |
|---|---|
| Profile crash mid-trade | resume from `positions.json`; reconcile any in-flight tx via on-chain status check |
| Circuit breaker tripped (drawdown > 10% in 24h) | profile auto-halts; operator must `/goal "resume autohedge"` to restart |
| Allocation cap exceeded | reject task; orch reroutes if possible |

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox details | `profiles/orch/docker.md` |
| Bankroll allocation enforcement | `anicca-oss/skills/anicca-fuel-broker/SKILL.md` |
| AutoHedge vendor location | `~/.openclaw/skills/anicca-autohedge/vendor/` |

---

**END OF profiles/earn-autohedge/docker.md.**
