# profiles/earn-x402/docker.md

> `earn-x402` is the **only** profile in the instance that opens an inbound
> network listener. The cloudflared tunnel originates here. All other 9
> profiles are egress-only.

## § 1. Daytona sandbox image

Shared with all 10 profiles in this instance — `hermes-runtime:latest`
(see `profiles/orch/docker.md` § 1 for image definition).

## § 2. Sandbox resources (shared)

| Resource | Value |
|---|---|
| vCPU | 0.5 (shared with all 10 profiles) |
| RAM | 512 MB (shared) |
| Disk | 5 GB (shared) |

`earn-x402` adds **negligible** local CPU/RAM cost because the actual LLM
inference (e.g., for a paid `/research` request) is delegated to OpenRouter.
The local work is: receive request → verify EIP-3009 sig → call LLM →
return response → log to audit.

## § 3. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-earn-x402/` | profile state (config.toml, x402-pricing.json) |
| `/root/.hermes/logs/x402-audit.log` | invoices + payments (365d retention) |
| `/root/.hermes/logs/wallet-audit.log` | EIP-712 signing operations |
| `/etc/cloudflared/` | tunnel config (mounted from Daytona secret) |

## § 4. Network — INBOUND (the special case)

| Direction | Allowed | Detail |
|---|---|---|
| Inbound HTTPS via cloudflared tunnel | yes | only this profile opens it |
| Inbound paths | `/research`, `/inference`, `/health` (public 200), `/<future-tools>` | path-prefix routing |
| Inbound IP filter | none (x402 is its own gate via 402 + sig verify) | reject is at app layer |
| Inbound rate limit | 100 req/min/IP default | configurable in `x402-pricing.json` |

## § 5. Cloudflared tunnel

| Property | Value |
|---|---|
| Tunnel name | `anicca-<instance>-x402` |
| Tunnel ID | from `cloudflared tunnel create` output (stored in vault as `CLOUDFLARED_TUNNEL_ID`) |
| Hostname | `<instance>.aniccaai.com` (= e.g., `genesis.aniccaai.com`) |
| Auth | Cloudflare API token (`CLOUDFLARE_API_TOKEN`) for tunnel management; tunnel itself uses token-based DNS routing |
| TLS | Cloudflare-terminated (origin is plain HTTP inside tunnel) |
| Origin | `http://localhost:18402` (the L2 skill's listener port) |

Config snippet `/etc/cloudflared/config.yml`:

```yaml
tunnel: <CLOUDFLARED_TUNNEL_ID>
credentials-file: /etc/cloudflared/<CLOUDFLARED_TUNNEL_ID>.json
ingress:
  - hostname: <instance>.aniccaai.com
    service: http://localhost:18402
  - service: http_status:404
```

## § 6. Egress (in addition to shared egress in `profiles/orch/docker.md`)

| Direction | Purpose |
|---|---|
| Egress to `openrouter.ai` | LLM call for `/inference` and `/research` endpoints |
| Egress to other x402 services | when buying research from peer Anicca instances |
| Egress to `basescan.org` | optional, for invoice receipt linking |

## § 7. Health probe

| Probe | Endpoint | Frequency |
|---|---|---|
| Liveness | `http://localhost:18402/health` | every 30s by Daytona |
| Tunnel reachable | external `curl -i https://<instance>.aniccaai.com/health` | every 60s by `fixer` profile |
| Endpoint earning | `revenue_report` tool, called per heartbeat | every 60s by `orch` |

If tunnel goes down: `fixer` profile auto-claims a heal task, restarts
cloudflared via `systemctl restart cloudflared` (or equivalent in
Daytona's init system).

## § 8. Restart policy

| Trigger | Action |
|---|---|
| Cloudflared crash | systemd / Daytona init restarts in < 5s |
| HTTP listener (L2 skill) crash | `KeepAlive=true` on its launchd-equivalent |
| Tunnel auth failure | `fixer` rotates token, restarts |
| Pricing config corrupt | revert to `x402-pricing.json.bak` (kept by daily backup) |

## § 9. Cross-references

| Concept | Authority |
|---|---|
| Cloudflared docs | `developers.cloudflare.com/cloudflare-one/connections/connect-networks/` |
| x402 server pattern | `github.com/coinbase/x402` server examples |
| Tunnel config | this file § 5 |
| Pricing config schema | `anicca-oss/skills/anicca-wallet-x402/pricing.schema.json` |
| Shared sandbox details | `profiles/orch/docker.md` § 1-3 |

---

**END OF profiles/earn-x402/docker.md.**
