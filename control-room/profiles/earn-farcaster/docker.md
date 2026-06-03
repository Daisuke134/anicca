# profiles/earn-farcaster/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific notes

| Item | Detail |
|---|---|
| Reuses `earn-x402` cloudflared tunnel | Frame endpoint at `https://<instance>.aniccaai.com/frame/*` |
| No own tunnel | one tunnel per instance keeps cost low |
| Egress to Neynar API + Farcaster Hubs | mostly read; writes are signed casts |

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-earn-farcaster/` | config + persona + frame-config |
| `/root/.hermes/logs/farcaster-audit.log` | casts + tips + frame events |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to `api.neynar.com` | yes |
| Egress to Farcaster Hub (custom URL) | yes |
| Egress to `mainnet.base.org` | yes (USDC tx for tip-out) |
| Inbound via `earn-x402` tunnel path `/frame/*` | yes |

## § 4. Frame endpoint routing

The `earn-x402` cloudflared tunnel routes:

| Path prefix | Profile |
|---|---|
| `/research`, `/inference` | `earn-x402` |
| `/frame/*` | `earn-farcaster` |
| `/health` | shared |

Implemented via a thin reverse-proxy in the L2 skill layer (= the
`anicca-wallet-x402` server can route `/frame/*` to a local socket owned
by `anicca-earn-farcaster`).

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Frame spec | `docs.farcaster.xyz/reference/frames/spec` |
| Shared tunnel | `profiles/earn-x402/docker.md` § 5 |

---

**END OF profiles/earn-farcaster/docker.md.**
