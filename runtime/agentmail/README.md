# anicca-agentmail (spec 10)

Per-Anicca AgentMail inboxes + push-webhook receiver + autonomous reply loop. Round 3 final wired 2026-06-04.

## Architecture (round 3 final — Tailscale Funnel is canonical)

```
Gmail → AgentMail (Svix) → https://aniccanomac-mini-1.tail7a0ba4.ts.net/agentmail
                            ↓ Tailscale Funnel (path: /agentmail → localhost:8810/agentmail)
                            ↓
                         :8810 webhook-server.ts
                            ↓ Svix HMAC verify
                            ↓ append inbox-queue.jsonl
                            ↓
                         replier-tick.sh (launchd, every 5 min)
                            ↓ ingest.ts → agentmail.db
                            ↓ replier.ts → DeepSeek v4-pro (fallback v4-flash)
                            ↓ spec-12 adapter send.sh
                            ↓
                         Reply lands in Gmail inbox
```

The Tailscale Funnel URL is **permanent** (tied to the tailnet hostname). No trycloudflare rotation, no Netlify relay needed in the hot path.

## Files

| File | Role |
|---|---|
| `inboxes.ts` | Provisions `anicca-001-{claude,openclaw,hermes}@agentmail.to` (free-tier cap = 3/org → hermes deferred). |
| `webhook-server.ts` | Express on `:8810`, Svix HMAC verify, append-only JSONL queue, always 200. |
| `webhook-subscribe.ts` | Register webhook URL with AgentMail. Pass `WEBHOOK_PUBLIC_URL` for stable URL. |
| `ingest.ts` | Drain JSONL → SQLite (idempotent via cursor file). |
| `replier.ts` | DeepSeek v4-pro generates reply (fallback v4-flash on empty content). Uses spec-12 `send.sh`. |
| `nudge.ts` | Reply-Zero analog — re-ping after 24h of silence (capped at `NUDGE_MAX_COUNT`, default 1). |
| `replier-tick.sh` / `nudge-tick.sh` | launchd wrappers; source `~/.openclaw/.env`. |
| `launch.sh` | launchd wrapper for `webhook-server.ts`. |
| `state-schema.sql` | `inbox_threads`, `inbox_messages` (+`in_reply_to`), `awaiting_reply`. |
| `netlify-relay/` | Legacy / fallback. Stable URL alternative if Tailscale Funnel is unavailable. |
| `ai.anicca.agentmail-webhook.plist` | launchd: KeepAlive on `webhook-server.ts`. |
| `ai.anicca.agentmail-replier.plist` | launchd: `StartInterval=300` (5 min cron). |
| `ai.anicca.agentmail-nudge.plist` | launchd: `StartCalendarInterval` 09:00 daily. |
| `ai.anicca.agentmail-cloudflared.plist` | Legacy / fallback. Use only if Tailscale Funnel is unreachable. |
| `state/inboxes.json` | Cached provisioned addresses. |

## Stable public URL via Tailscale Funnel

```bash
# One-time setup (already done on this host; tailscale funnel is persistent)
tailscale funnel --bg --https=443 --set-path=/agentmail http://localhost:8810/agentmail
tailscale funnel --bg --https=443 --set-path=/agentmail/healthz http://localhost:8810/healthz
# Then subscribe AgentMail:
WEBHOOK_PUBLIC_URL=https://aniccanomac-mini-1.tail7a0ba4.ts.net \
  node webhook-subscribe.ts
```

## Env (in `~/.openclaw/.env`, chmod 600)

```
AGENTMAIL_API_KEY=…
AGENTMAIL_WEBHOOK_SECRET=whsec_…   # rotates only when webhook URL changes
DEEPSEEK_API_KEY=…
```

## E2E verified 2026-06-04 (Tailscale Funnel path)

| # | Event | Timestamp | Result |
|---|---|---|---|
| 1 | keiodaisuke@gmail.com sends via gog | 14:59:13Z | gog messageId=`19e8dfee6cb70dc4` |
| 2 | Webhook → Tailscale Funnel → :8810 → queue | 14:59:18Z (Δ=5.4s) | `status=verified`, secret=`whsec_s6jl…` |
| 3 | Replier ran | 14:59:?? (12.2s incl. LLM) | v4-pro empty → v4-flash success → adapter http=200 |
| 4 | Reply landed in gog gmail | 14:59:?? | `Re: Round 3 final — stable Tailscale URL test`, msgId `19e8dff41c562d5a` |

**Anicca's verbatim reply:** *"Confirmed: Gmail → AgentMail → Tailscale Funnel → :8810, no trycloudflare or Netlify hop. — Anicca"*

## Reply-Zero (nudge) cron — round 3 evidence

Planted synthetic awaiting_reply row with `sent_at = NOW() - 25h`:

- `eligible nudges: 1` (correct: >24h, no inbound since, nudge_count=0)
- DeepSeek v4-pro produced the nudge text on first try
- Adapter sent: subject=`Re: Round 3 final — nudge cron evidence`, http=200, msg_id captured
- DB updated: `last_nudge_at=2026-06-03T15:00:17.715Z`, `nudge_count: 0→1`
- **Idempotency proven**: re-run shows `eligible nudges: 0` (cap reached → no double-send)

## launchd active units

| Label | Schedule |
|---|---|
| `ai.anicca.agentmail-webhook` | KeepAlive (binds :8810) |
| `ai.anicca.agentmail-replier` | StartInterval=300s (5 min) |
| `ai.anicca.agentmail-nudge` | StartCalendarInterval 09:00 daily |
| `ai.anicca.agentmail-cloudflared` | **disabled** (Tailscale Funnel is canonical; load only as fallback) |

## Spec G1–G6 gate status

| Gate | Status | Evidence |
|---|---|---|
| G1 | PARTIAL | 3 inboxes live (`claude`, `openclaw`, `genesis`); `hermes` deferred — AgentMail free tier caps at 3/org |
| G2 | PASS | `curl POST :8810/agentmail` with signed body → 200; unsigned → 200 status=`rejected` (no retry storms) |
| G3 | PASS | `client.webhooks.list()` → `ep_3EdBnKdVDn9kw92o400HrwTJ3c8` at the Tailscale Funnel URL |
| G4 | PASS | Two real Gmail→Anicca→Gmail round trips today, both < 30s (12s + 26s) |
| G5 | PASS | Synthetic 25h-old row → nudge sent, `nudge_count` 0→1, idempotent on re-run |
| G6 | LIKELY | KeepAlive=true on all three launchd units; not yet exercised across a full machine reboot — first boot after reboot will prove it |

[`specs/10-AGENTMAIL-INBOXES.md`](../../specs/10-AGENTMAIL-INBOXES.md) · [`docs.agentmail.to/webhook-verification`](https://docs.agentmail.to/webhook-verification) · [`tailscale.com/kb/1247/funnel-serve-use-cases`](https://tailscale.com/kb/1247/funnel-serve-use-cases)
