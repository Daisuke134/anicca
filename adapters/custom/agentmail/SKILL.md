---
name: adapter-agentmail
description: AgentMail thin REST wrapper for Anicca. Wraps POST /v0/inboxes/{inbox}/messages/send so any skill can send an email without re-implementing curl headers. Use when Anicca needs to outbound an email (gig client follow-up, cold outreach, transactional notification). Inbox creation + receive + webhooks live in spec 10's anicca-inbox-keeper — this is the send side only.
metadata:
  type: custom-adapter
  spec: 12-CUSTOM-ADAPTERS.md
  parallel_safe: true
  invariants:
    rate_limit_sends_per_hour: 60
  requires:
    bins: [bash, curl, jq]
    env: [AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID]
---

# adapter-agentmail

Thin send-side wrapper for AgentMail REST. Receive / webhook subscribe / inbox provisioning are in spec 10 (anicca-inbox-keeper); this adapter only sends so cron skills can reach `agentmail.to` with one bash call.

## Scripts

| Script | Use |
|---|---|
| `scripts/send.sh <to> <subject> <text> [inbox]` | POST to `/v0/inboxes/<inbox>/messages/send`. Defaults to `$AGENTMAIL_INBOX_ID` if `inbox` arg omitted. |

## Env

| Var | Source |
|---|---|
| `AGENTMAIL_API_KEY` | `~/.openclaw/.env` (already provisioned, anicca-genesis@agentmail.to) |
| `AGENTMAIL_INBOX_ID` | `~/.openclaw/.env` (default inbox) |

## Output

Each send appends to `state/sent-log.jsonl`: `{ts, to, subject, message_id, http}`.
