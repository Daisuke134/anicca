# 10 — anicca-inbox-keeper  (= each Anicca own AgentMail inbox + push webhook)

| Field | Value |
|---|---|
| Spec ID | 10 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-inbox-keeper** |
| Worktree | `.worktrees/agentmail/` |
| Branch | `feature/agentmail-inboxes` |
| Wave | 1 (parallel with 11, 12, 15) |
| Authoritative for | AgentMail inbox per Anicca instance, push webhook → heartbeat trigger, Reply Zero analog |

---

## § 0. Why

Each Anicca instance must be a sovereign email identity (= matching the sovereign wallet model). Per AgentMail's agent-native flow (= verified 2026-06-03 with 0 human in loop), `client.inboxes.create()` provisions a fresh inbox in <1s. Push webhook → heartbeat receiver removes the 2h heartbeat latency for high-priority mail.

The previous spec (08 v1) proposed forking Inbox Zero. That is **abandoned**. AgentMail solves inbox + webhook + Reply Zero analog natively without the Postgres dependency or AGPL license question.

## § 1. File boundary

**TOUCHES**

| Path | Purpose |
|---|---|
| `runtime/agentmail/inboxes.ts` | provisioning script (= 3 custom-address inboxes) |
| `runtime/agentmail/webhook-server.ts` | Express server listening on `:8810` for AgentMail POST |
| `runtime/agentmail/webhook-subscribe.ts` | one-shot script: SDK `client.webhooks.create(...)` |
| `runtime/agentmail/handler.ts` | webhook payload → POST to peer-api `/event` (= existing daemon) |
| `runtime/agentmail/state-schema.sql` | `inbox_threads` + `inbox_messages` + `awaiting_reply` tables (= Reply Zero analog) |
| `runtime/agentmail/README.md` | setup + cost notes |
| `~/Library/LaunchAgents/ai.anicca.agentmail-webhook.plist` | launchd plist (= 24/7 process) |

**NEVER**

- `services/x402-endpoint/**` (= Agent-1)
- `runtime/memu/**` (= Agent-3)
- `adapters/**` (= Agent-4)
- `_shared/heartbeat-*.sh` (= Agent-3 + Agent-7)
- `~/.openclaw/skills/anicca-friction-fixer/**` (= Agent-7)
- existing `~/.openclaw/skills/anicca-agentmail/**` (= legacy, will deprecate after this lands)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 10.T1 | Provision 3 custom-address inboxes via SDK (= confirm `CreateInboxRequest` schema first, then `client.inboxes.create(request=...)`) | `client.inboxes.list()` returns 4 inboxes (= 3 + existing anicca-genesis) |
| 10.T2 | Webhook receiver Express server scaffolded with HMAC signature verification | `curl POST :8810/agentmail` with valid sig → 200 |
| 10.T3 | SDK `client.webhooks.create(url=..., events=[message.received])` | webhooks.list() includes our URL |
| 10.T4 | Public URL via Netlify Function or cloudflared tunnel for the webhook | reachable from agentmail.to side |
| 10.T5 | handler.ts: webhook → enqueue event in `~/.openclaw/state/inbox-queue.jsonl` + POST to localhost:peer-api/event | event arrives in queue + peer-api log line |
| 10.T6 | SQLite schema migration: `inbox_threads`, `inbox_messages`, `awaiting_reply(thread_id, sent_at, last_nudge_at)` | sqlite3 `.schema` shows tables |
| 10.T7 | launchd plist registered + loaded (`launchctl load`) | `launchctl list ai.anicca.agentmail-webhook` shows running |
| 10.T8 | E2E: external mail → anicca-001-claude@agentmail.to → heartbeat fires within 60s → Anicca posts reply confirmation to Slack #metrics | timestamps in Slack thread |
| 10.T9 | Reply Zero analog: if `awaiting_reply.sent_at + 24h < NOW` and no inbound → friction-fixer detects → re-ping sent | 1 synthetic timeout + 1 actual nudge confirmed |

## § 3. Dependencies

- `AGENTMAIL_API_KEY` (= 既 in `~/.openclaw/.env`, signed 2026-06-03)
- Python `agentmail==0.5.2` (= 既 installed in `~/.anicca-genesis/memU-test/.venv/`)
- Public URL for webhook (Netlify Function + secret HMAC env)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `client.inboxes.list()` returns ≥ 4 inboxes including the 3 custom |
| G2 | Webhook server responds 200 to valid signed payload |
| G3 | Webhook subscription visible via `client.webhooks.list()` |
| G4 | External test mail → Anicca reply within 60s, logged in Slack #metrics |
| G5 | 24h timeout → re-ping fires automatically (= synthetic test) |
| G6 | launchd plist alive across machine restart |

## § 5. Anti-goals

- Not forking Inbox Zero (= abandoned)
- Not Postgres (= SQLite via Conway state.db)
- Not Gmail polling (= AgentMail push only for these custom addresses; legacy Gmail polling kept for Dais's redacted@example.invalid)

## § 6. Cost (= verified)

- AgentMail free tier: shared `*.agentmail.to` subdomain, unlimited inboxes for now
- Custom domain (`anicca-001-claude@aniccaai.com`) = paid plan, defer to later spec

## § 7. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Born from spec 08 v1 abandonment; AgentMail proven 0-human-in-loop signup same day. |
