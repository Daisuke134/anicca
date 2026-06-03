# profiles/earn-x402/runbook.md

## § 1. Restart

```bash
hermes -p earn-x402 -g "halt: stop listener gracefully, finish in-flight invoices, exit"
sleep 3
hermes profile start earn-x402
hermes -p earn-x402 -g "start x402 listener, verify cloudflared tunnel reachable"
```

## § 2. Logs

| Log | Use |
|---|---|
| `~/.hermes/logs/x402-audit.log` | every invoice + payment (forever) |
| `~/.hermes/logs/wallet-audit.log` | every EIP-712 signing op |
| `~/.hermes/logs/daemon.log` (grep `[earn-x402]`) | profile-level events |
| `journalctl -u cloudflared` (inside sandbox) | tunnel-level events |

```bash
tail -F ~/.hermes/logs/x402-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[earn-x402\]'
```

## § 3. Kickstart on failure

```bash
# 1. is the listener up?
curl -i http://localhost:18402/health
# expect: HTTP/1.1 200 OK

# 2. is the tunnel up?
curl -i https://<instance>.aniccaai.com/health
# expect: HTTP/1.1 200 OK (= via cloudflared)

# 3. if listener down, restart it
hermes profile restart earn-x402

# 4. if tunnel down, restart cloudflared
sudo systemctl restart cloudflared
# OR inside Daytona:
daytona sandbox exec <instance> "systemctl restart cloudflared"

# 5. if both up but no revenue, verify pricing config
cat ~/.hermes/profiles/<instance>-earn-x402/x402-pricing.json
```

## § 4. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `EIP-3009 signature verification failed` | client sent invalid sig OR clock skew | check `nonce` + `validBefore`; sync sandbox clock via `chronyd` |
| `OpenRouter 402 insufficient credit` | self-topup hasn't fired or failed | `hermes -p earn-x402 -g "topup OpenRouter 5 USDC via x402 now"` |
| `Cloudflared tunnel 530` | tunnel down, DNS unrouted | restart cloudflared; verify CLOUDFLARE_API_TOKEN unrotated |
| `Tunnel ID not found` | CLOUDFLARED_TUNNEL_ID rotated, creds file stale | refresh creds file: `cloudflared tunnel token <id> > /etc/cloudflared/<id>.json` |
| `wallet.json not found` | orch hasn't bootstrapped wallet yet | `hermes -p orch -g "bootstrap CDP smart wallet"` |
| `Pricing config corrupt` | manual edit broke JSON | restore from `x402-pricing.json.bak` (daily backup) |
| `LLM 429 rate limit` | OpenRouter throttling Kimi K2.6 | wait or switch to fallback (Qwen3.7 Max) temporarily |
| `Payment received but no response sent` | LLM call failed mid-request | refund tx; log to `x402-audit.log` with `status=refunded` |
| `Listener port 18402 already in use` | zombie process from prior crash | `lsof -i :18402` → kill PID → restart profile |
| `Cloudflared DNS resolution failed` | upstream DNS issue | restart sandbox networking |

## § 5. Revenue inspection

```bash
# 24h revenue total
grep "$(date -u +%Y-%m-%d)" ~/.hermes/logs/x402-audit.log \
  | grep status=paid \
  | jq -s 'map(.amount_usdc | tonumber) | add'

# top paying paths
grep status=paid ~/.hermes/logs/x402-audit.log \
  | jq -r '.path' \
  | sort | uniq -c | sort -rn

# refund rate (24h)
TOTAL=$(grep "$(date -u +%Y-%m-%d)" ~/.hermes/logs/x402-audit.log | grep -c status=paid)
REFUNDS=$(grep "$(date -u +%Y-%m-%d)" ~/.hermes/logs/x402-audit.log | grep -c status=refunded)
echo "refund rate: $(echo "scale=2; $REFUNDS * 100 / $TOTAL" | bc)%"
```

## § 6. Manual invoice issuance (debugging)

```bash
hermes -p earn-x402 -g "issue test invoice for /research, return EIP-3009 typed-data JSON, do NOT broadcast"
```

## § 7. Manual topup (emergency)

If self-topup loop is broken and OpenRouter credit is critical:

```bash
# from earn-x402 profile, sign and send EIP-3009 to OpenRouter
hermes -p earn-x402 -g "manual topup: send 5 USDC to OpenRouter via x402, log as emergency-manual, alert orch"
```

## § 8. Emergency stop this profile

```bash
hermes -p earn-x402 -g "halt: stop listener, return 503 on inbound for 60s grace, exit"
```

This does NOT stop the whole instance — other 9 profiles continue. Revenue
goes to zero until restart.

## § 9. Cross-references

| Concept | Authority |
|---|---|
| L2 skill | `anicca-oss/skills/anicca-wallet-x402/SKILL.md` |
| Cloudflared CLI | `developers.cloudflare.com/cloudflare-one/connections/connect-networks/use-cases/cloudflared` |
| AgentKit x402 provider source | `cdp-agentkit-core/src/action_providers/x402/x402ActionProvider.ts` |
| Self-pay rationale | `specs/07-HERMES-PIVOT.md` § 4.2 |
| Live operational spec | `specs/09-EARN-X402-LIVE.md` |

---

**END OF profiles/earn-x402/runbook.md.**
