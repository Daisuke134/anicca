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

## Install / reinstall the launchd jobs

Three plists work together; server and tunnel are decoupled so picking up new code never rotates the public URL.

```bash
cp services/x402-endpoint/launchd/ai.anicca.x402-endpoint.plist ~/Library/LaunchAgents/
cp services/x402-endpoint/launchd/ai.anicca.x402-tunnel.plist   ~/Library/LaunchAgents/
cp services/x402-endpoint/launchd/ai.anicca.x402-monitor.plist  ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/ai.anicca.x402-endpoint.plist
launchctl load -w ~/Library/LaunchAgents/ai.anicca.x402-tunnel.plist
launchctl load -w ~/Library/LaunchAgents/ai.anicca.x402-monitor.plist
launchctl list ai.anicca.x402-endpoint        # server  — PID + LastExitStatus=0
launchctl list ai.anicca.x402-tunnel          # tunnel  — PID + LastExitStatus=0
launchctl list ai.anicca.x402-monitor         # monitor — PID + LastExitStatus=0
cat ~/.openclaw/state/anicca_x402_url.txt     # current public URL (stable across server restarts)
```

| Plist | Wrapper | Role |
|---|---|---|
| `ai.anicca.x402-endpoint` | `run.sh` | Hono server on :8403; exec's tsx |
| `ai.anicca.x402-tunnel`   | `tunnel.sh` | cloudflared quick tunnel; persists URL to state file |
| `ai.anicca.x402-monitor`  | `monitor.sh` | tails `/tmp/anicca-x402.log` for REVENUE lines → Slack #metrics |

## Public URL state

`tunnel.sh` writes the current cloudflared URL to **both**:

| Path | Why |
|---|---|
| `~/.openclaw/state/anicca_x402_url.txt` | Canonical store (cron consumers, listing bumper) |
| `services/x402-endpoint/state/public-url.txt` | Repo-relative mirror (review / CI / inline tests) |

Each write is atomic (`mv` from a `.tmp.<pid>` sibling) so readers never see a half-written value.

## Named tunnel — blocker (round 4 attempt)

| Option | State | Why blocked |
|---|---|---|
| `cloudflared tunnel create anicca-x402 + tunnel route dns x402.aniccaai.com` | Blocked | `aniccaai.com` is on **NS1** (`dns1.p06.nsone.net`), not Cloudflare. The `tunnel route dns` command requires the zone to be on Cloudflare. No CF API token / no NS1 API token in `~/.openclaw/.env` to scriptthe migration. |
| `cloudflared tunnel login` + named tunnel on `<uuid>.cfargotunnel.com` | Possible but not autonomous in <15 min | Requires browser OAuth on dash.cloudflare.com against a CF account. The agent can drive camofox through it (~30 min), but the resulting `cfargotunnel.com` URL is no more memorable than the trycloudflare one — and it still rotates if the tunnel is deleted. |
| Quick tunnel (current) | Live | Decoupled from server lifecycle (separate launchd job) + hourly self-heal cron means the URL rotates only on `ai.anicca.x402-tunnel` restart, not on every server respawn. |

Round-5 candidate: pair `aniccaai.com` to Cloudflare DNS (one-time NS1 → CF nameserver swap; ~30-60 min including propagation) → then named tunnel comes for free.

## Uptime self-heal (hourly cron)

```bash
python3 services/x402-endpoint/scripts/register-cron.py
# → idempotently registers `anicca-x402-uptime-check` in ~/.openclaw/cron/jobs.json
```

`scripts/uptime-check.sh` runs at minute 0 of every hour (Asia/Tokyo). If `localhost:8403/health` or `<public_url>/health` doesn't return 200, it `launchctl kickstart`s the relevant plist and appends a JSONL line to `~/.openclaw/state/anicca_x402_uptime.jsonl`. Output is delivered to Slack #metrics via the openclaw gateway's announce mode.

## agentic.market listing

`agentic-market.json` carries this endpoint's discovery payload (per the x402 Bazaar PaymentRequiredResponse schema).

### Submission flow (probed 2026-06-03)

| Step | Mechanism |
|---|---|
| Direct REST submission | **Does not exist** — `/api/v1/services` returns 404 for POST, `/api/v1/validate` likewise. |
| `POST https://api.agentic.market/v1/validate/run` | Returns a 19-check preflight + simulate. With our server.ts payload, both `/v0/echo` and `/v0/learn` return **19/19 PASS, valid=true, simulate.outcome="processing"** with a `workflowIdHint: discover-http-<method>-<resource>`. This queues the endpoint with the Coinbase x402 facilitator for indexing. |
| Surfacing on agentic.market | Settlement-driven: per the wizard's "First Request" step, "Your endpoint needs at least one successful transaction through the CDP facilitator before it appears in the Bazaar." Until a payment routes through the facilitator, the endpoint stays in the indexing queue (`/v1/validate/check` returns `found:false`). |

### Revenue monitor

`monitor.sh` (installed as `~/Library/LaunchAgents/ai.anicca.x402-monitor.plist`, source kept at `launchd/ai.anicca.x402-monitor.plist`) tails `/tmp/anicca-x402.log` for the `REVENUE` marker that server.ts emits on every paying 200, mirrors the line into `~/.openclaw/state/anicca_x402_revenue.jsonl`, and forwards it to Slack channel #metrics via `chat.postMessage` (`SLACK_BOT_TOKEN` from `~/.openclaw/.env`).

## Deploy

| Stage | Path |
|---|---|
| Local | `pnpm install && pnpm start` (port `:8403`) |
| LaunchAgent on the Mac Mini | three plists from `launchd/` — server + tunnel + monitor (this revision, round-4) |
| Container | `docker build -t anicca-x402:0.1 .` (multi-stage Alpine, runs as non-root `anicca:anicca`, HEALTHCHECK on `/health`). The Dockerfile is intentionally minimal — copies only `server.ts`, `challenge.ts`, `verify.ts`, `pricing.json` + production `node_modules`; tsx executes TS at runtime. Built image expects port-mapping `-p 8403:8403`. |
| Akash | drop the container into the spec-13 SDL once Agent-5 lands. The lifeline of this directory ends at the container; Akash deploy is owned by `deploy/akash/**` (NOT this file boundary). |

## CFO hook

`cfo-hook.sh` is invoked by `monitor.sh` on every paying 200 (spec 09 § 2 T9). It:

1. Parses the `REVENUE` log line emitted by `server.ts`.
2. Appends a structured event to `~/.openclaw/state/cfo_x402_events.jsonl` (schema `anicca-x402/cfo-event/v1`).
3. Atomically updates `~/.openclaw/state/x402_revenue_summary.json` (schema `anicca-x402/cfo-hook/v1`) — rolling totals + per-route + last-tx + wallet pointer.

Schema of the summary blob (the file `cfo-core` reads to bump `dashboard.lineage[*].x402_revenue` on its next pass):

```json
{
  "schema": "anicca-x402/cfo-hook/v1",
  "wallet": "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21",
  "x402_revenue_usdc_total": 0.011,
  "x402_revenue_count": 2,
  "x402_revenue_by_route": { "echo": 0.001, "learn": 0.01 },
  "last_event_at": "2026-06-03T15:31:00Z",
  "last_tx_hash":  "0x..."
}
```

The wallet pointer matches the lineage entry `id=anicca-001-claude` (or any entry whose `wallet` field equals the receiver). Writing is atomic (`mv` from `.tmp.<pid>`).
