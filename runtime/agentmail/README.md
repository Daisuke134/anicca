# anicca-agentmail (spec 10)

Per-Anicca AgentMail inboxes + push-webhook receiver on `:8810`.

## Files

| File | Role |
|---|---|
| `inboxes.ts` | Provisions `anicca-001-{claude,openclaw,hermes}@agentmail.to` (idempotent via `clientId`). |
| `webhook-server.ts` | Express on `:8810`. Verifies Svix HMAC, enqueues to `~/.openclaw/state/inbox-queue.jsonl`. Returns 200 on bad sig (no retry storms). |
| `webhook-subscribe.ts` | Calls `client.webhooks.create({url, eventTypes:["message.received"]})`. Spawns `cloudflared` quick-tunnel unless `WEBHOOK_PUBLIC_URL` is set. Prints `whsec_…`. |
| `state-schema.sql` | `inbox_threads`, `inbox_messages`, `awaiting_reply` (Reply-Zero analog). |
| `ai.anicca.agentmail-webhook.plist` | launchd template; replace `<USER>` and load into `~/Library/LaunchAgents/`. |

## Env (in `~/.openclaw/.env`)

```
AGENTMAIL_API_KEY=…               # already set
AGENTMAIL_WEBHOOK_SECRET=whsec_…  # printed by webhook-subscribe.ts
WEBHOOK_PUBLIC_URL=https://…      # optional; otherwise cloudflared quick-tunnel
```

## Run

```bash
npm install
node inboxes.ts                                     # T1 — provision inboxes
sqlite3 ~/.openclaw/state/inbox.db < state-schema.sql  # T6 — apply schema
node webhook-server.ts &                            # T2 — local receiver
node webhook-subscribe.ts                           # T3/T4 — register w/ AgentMail
```

## Verification

- `npm install` → exit 0
- `curl -sS -X POST http://localhost:8810/agentmail -H 'Content-Type: application/json' -d '{"type":"message.received"}'` → server logs + `inbox-queue.jsonl` appended (status `unverified` until `AGENTMAIL_WEBHOOK_SECRET` is set, `verified`/`rejected` after).
- `sqlite3 :memory: < state-schema.sql` → exit 0.

## Spec links

[`specs/10-AGENTMAIL-INBOXES.md`](../../specs/10-AGENTMAIL-INBOXES.md) · uses [`docs.agentmail.to/webhook-verification`](https://docs.agentmail.to/webhook-verification).
