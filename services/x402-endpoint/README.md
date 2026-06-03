# anicca-x402-endpoint (Wave 1 + 2-public)

Anicca's first sovereign revenue endpoint. Buyers pay USDC on Base; server verifies on-chain and serves content. No login, no Stripe, no JPY.

Spec: [`/specs/09-EARN-X402-LIVE.md`](../../specs/09-EARN-X402-LIVE.md)

## Live (public)

| Layer | Detail |
|---|---|
| Public URL | written to `~/.openclaw/state/anicca_x402_url.txt` on every boot (cloudflared quick tunnel — URL rotates per boot) |
| Receiver wallet | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` (Anicca, read-only here) |
| 402 response shape | Anicca custom `challenge` **+** canonical x402 v2 `accepts[]` + `extensions.bazaar` (Bazaar-discoverable) |
| Persistence | launchd: `~/Library/LaunchAgents/ai.anicca.x402-endpoint.plist` (`RunAtLoad=true`, `KeepAlive=true`) — wrapper `run.sh` boots tsx + cloudflared and writes the live URL to the state file |

## Run (local)

```bash
cd services/x402-endpoint
pnpm install   # or npm install
pnpm start     # node --loader tsx server.ts
# → [anicca-x402] listening on :8403 — receiver 0xa3CDd...
```

Port `:8403` (not `:8402`; that collides with OpenClaw gateway's built-in x402-proxy — see spec 15 § 17.4 U-86).

## Try it

```bash
# 1. Health
curl http://localhost:8403/health
# → 200 { ok:true, ... }

# 2. Unpaid call → 402 challenge
curl -i http://localhost:8403/v0/echo?text=hi
# → 402 with WWW-Authenticate header + challenge JSON

# 3. Pay 0.001 USDC on Base to 0xa3CDd... then:
curl -H "x-paid-tx-hash: 0xYOUR_TX_HASH" \
  "http://localhost:8403/v0/echo?text=hi"
# → 200 { ok:true, echoed:"hi", paid:{...} }
```

## Routes (Wave 1)

| Route | Method | Price | Status |
|---|---|---|---|
| `/health` | GET | free | live |
| `/v0/echo` | GET | 0.001 USDC | live |
| `/v0/learn` | POST | 0.01 USDC | live (stub lesson; full FTS5 in T5/T8) |
| `/v0/draft` | POST | 0.05 USDC | TBD (Wave 2) |
| `/v0/call` | POST | 0.30 USDC | TBD (Wave 2) |

## Synthetic test

```bash
pnpm start &        # in another shell or background
./node_modules/.bin/tsx test/synthetic.ts
# → 4/4 passed, exit 0
```

Cases: `/health` 200 + receiver match · `/v0/echo` no-payment 402 + nonce_sig present · `/v0/echo` bogus tx → 402 (verify fails) · `/v0/learn` no-payment 402.

## Security notes

| Layer | Mechanism |
|---|---|
| Forgery | Each challenge nonce signed with HMAC-SHA256 (`X402_HMAC_SECRET` env or per-process random) |
| Replay | On-chain tx hash uniqueness + Base block age window < 10 min (see `verify.ts`) |
| Tamper | `nonce_sig` recomputable server-side via `recomputeNonceSig()` |

## Install / reinstall the launchd job

```bash
cp services/x402-endpoint/launchd/ai.anicca.x402-endpoint.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/ai.anicca.x402-endpoint.plist
launchctl list ai.anicca.x402-endpoint        # expect LastExitStatus=0, PID present
tail -f /tmp/anicca-x402.log                  # boot trace; tunnel URL line lands ~10s after start
cat ~/.openclaw/state/anicca_x402_url.txt     # current public URL
```

## agentic.market listing

`agentic-market.json` carries this endpoint's discovery payload (per the x402 Bazaar PaymentRequiredResponse schema).

Probed 2026-06-03: **agentic.market has no public REST submission endpoint** (`/api/*` returns 404). Discovery is settlement-driven — when a payment routes through a Bazaar-compatible facilitator (e.g. `api.cdp.coinbase.com/platform/v2/x402/facilitator/*`), the resource is auto-indexed at `/platform/v2/x402/discovery/resources` and surfaces on agentic.market. The 402 challenge already emits the canonical `accepts[]` + `extensions.bazaar` envelope (see `server.ts`), so the endpoint is ready to be picked up on first settled payment.

## Deploy

Wave 1 = local + manual. Wave 2-public = launchd plist + cloudflared quick tunnel (this revision). Wave 3 adds a named Cloudflare tunnel (stable hostname) + `Dockerfile` for Akash per spec § 2 T6.
