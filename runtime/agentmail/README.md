# anicca-agentmail (spec 10)

Per-Anicca AgentMail inboxes + push-webhook receiver on `:8810`. Round 2 wired live on 2026-06-03.

## Files

| File | Role |
|---|---|
| `inboxes.ts` | Provisions `anicca-001-{claude,openclaw,hermes}@agentmail.to`. Free-tier cap = 3 inboxes/org; `LimitExceeded` reported as deferral, not error. |
| `webhook-server.ts` | Express on `:8810`. Svix HMAC verify against raw body; enqueues each event to `~/.openclaw/state/inbox-queue.jsonl`; always 200 (no retry storms). |
| `webhook-subscribe.ts` | `client.webhooks.create({url, eventTypes:["message.received"]})`. Spawns inline `cloudflared` quick-tunnel unless `WEBHOOK_PUBLIC_URL` set. Prints `whsec_…`. |
| `ingest.ts` | Drains `inbox-queue.jsonl` → `agentmail.db` (`inbox_threads`, `inbox_messages`). Cursor file makes it idempotent. |
| `launch.sh` | launchd wrapper — sources `~/.openclaw/.env` then execs `node webhook-server.ts`. |
| `state-schema.sql` | `inbox_threads` + `inbox_messages` + `awaiting_reply` (Reply-Zero analog). |
| `ai.anicca.agentmail-webhook.plist` | launchd unit for the receiver (uses `launch.sh`). |
| `ai.anicca.agentmail-cloudflared.plist` | launchd unit for the quick-tunnel. |

## Env (in `~/.openclaw/.env`, chmod 600)

```
AGENTMAIL_API_KEY=…               # signed up 2026-06-03
AGENTMAIL_WEBHOOK_SECRET=whsec_…  # printed by webhook-subscribe.ts; rotates if URL changes
WEBHOOK_PUBLIC_URL=https://…      # optional; otherwise cloudflared trycloudflare quick-tunnel
```

## Install (one-shot)

```bash
npm install
node inboxes.ts
sqlite3 ~/.openclaw/state/agentmail.db < state-schema.sql
for p in ai.anicca.agentmail-webhook.plist ai.anicca.agentmail-cloudflared.plist; do
  sed "s|<USER>|$USER|g" "$p" > ~/Library/LaunchAgents/"$p"
  launchctl unload ~/Library/LaunchAgents/"$p" 2>/dev/null
  launchctl load   ~/Library/LaunchAgents/"$p"
done
sleep 8
URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' ~/.openclaw/logs/agentmail-cloudflared.log | head -1)
WEBHOOK_PUBLIC_URL="$URL" node webhook-subscribe.ts   # captures whsec_, paste into ~/.openclaw/.env
launchctl kickstart -k gui/$UID/ai.anicca.agentmail-webhook
node ingest.ts   # any future cron / heartbeat re-runs this
```

## Verification snapshots (round 2, 2026-06-03)

- `curl http://localhost:8810/healthz` → `{"ok":true,"port":8810,"signed":true}`
- `client.webhooks.list()` → 1 entry pointing at the live trycloudflare URL
- E2E: anicca-genesis → anicca-001-claude, send@14:32:35 → queue verified-row@14:32:38 (≈2.5s)
- `sqlite3 agentmail.db "SELECT … FROM inbox_messages"` → 1 inbound row, subject `Spec 10 E2E test …`

## Caveats

- trycloudflare URLs are ephemeral. After every cloudflared restart, re-run `webhook-subscribe.ts` and update `AGENTMAIL_WEBHOOK_SECRET`.
- `client.webhooks.update()` cannot change URL — must delete + recreate.
- AgentMail free-tier cap = 3 inboxes/org; `anicca-001-hermes` deferred until plan upgrade.

## Spec links

[`specs/10-AGENTMAIL-INBOXES.md`](../../specs/10-AGENTMAIL-INBOXES.md) · uses [`docs.agentmail.to/webhook-verification`](https://docs.agentmail.to/webhook-verification).
