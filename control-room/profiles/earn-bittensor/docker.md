# profiles/earn-bittensor/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific resource notes

| Item | Detail |
|---|---|
| Additional disk | ~300 MB for `bittensor` Python SDK + subnet template + wallet keystore |
| Additional RAM | ~100 MB for SDK + miner process (varies by subnet) |
| Additional CPU | spike during subnet inference work (depends on subnet type) |

For inference-heavy subnets (LLM mining), consider running the actual miner
in a **dedicated** Daytona sandbox via `anicca-spawn-controller`
(ephemeral, killed when subnet APY drops below threshold).

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-earn-bittensor/` | config + subnet positions |
| `/root/.hermes/profiles/<instance>-earn-bittensor/bittensor-wallet/` | TAO keystore (chmod 600) |
| `/root/.hermes/logs/bittensor-audit.log` | events |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to Bittensor finney / subtensor endpoints | yes |
| Egress to subnet validator endpoints (varies per subnet) | yes |
| Egress to TAO ↔ USDC bridge / DEX | yes |
| Inbound (if miner serves a port) | only on subnet-required port; firewall-narrow to validator IPs if possible |

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Bittensor finney endpoint | `entrypoint-finney.opentensor.ai:443` |
| Subnet routing | `docs.bittensor.com/subnets` |

---

**END OF profiles/earn-bittensor/docker.md.**
