# adapters/custom/ — spec 12 (anicca-adapter-smith)

Custom adapters for surfaces Composio doesn't cover:

| Adapter | Transport | Use |
|---|---|---|
| `lancers/` | camofox saved session | JP gig DMs + inbox reads |
| `coconala/` | camofox saved session | JP gig DMs + inbox reads |
| `bland-ai/` | REST | outbound voice calls |
| `agentmail/` | REST | outbound email (send-side only; receive lives in spec 10) |

## Invoke

Each adapter is a folder with a `SKILL.md` (= Hermes / OpenClaw registry frontmatter) and bash scripts. Examples:

```bash
# Lancers — bootstrap session (one-time, idempotent thereafter)
bash adapters/custom/lancers/scripts/login.sh

# Lancers — read inbox as JSON
bash adapters/custom/lancers/scripts/read-inbox.sh

# Lancers — send DM in existing thread (rate-capped to 10/h)
bash adapters/custom/lancers/scripts/send-dm.sh "https://www.lancers.jp/mypage/inbox/<thread_id>" "ご返信ありがとうございます。..."

# Coconala — same trio
bash adapters/custom/coconala/scripts/login.sh
bash adapters/custom/coconala/scripts/read-inbox.sh
bash adapters/custom/coconala/scripts/send-dm.sh "https://coconala.com/mypage/inbox/<thread>" "ご連絡ありがとうございます。..."

# Bland.ai — outbound call (dry-run safe)
bash adapters/custom/bland-ai/scripts/outbound-call.sh "+818012345678" "Wake up call from Anicca." "maya" --dry-run

# AgentMail — send mail
bash adapters/custom/agentmail/scripts/send.sh "contact@aniccaai.com" "subject" "body"

# E2E harness — runs all 4 adapters dry-run-safe and logs verdicts
node adapters/custom/tests/e2e.ts
```

## Env

All scripts source `~/.openclaw/.env` first. Required keys:

| Adapter | Vars |
|---|---|
| Lancers / Coconala | `GOOGLE_LOGIN_EMAIL`, `GOOGLE_LOGIN_PASSWORD` |
| Bland.ai | `BLAND_API_KEY` (if absent, scripts log `missing-key` and exit 3 — round-2 signup task) |
| AgentMail | `AGENTMAIL_API_KEY`, `AGENTMAIL_INBOX_ID` |

## Invariants (per spec §5)

- ≤ 10 DM/h on Lancers + Coconala (enforced via `state/dm-log.jsonl` sleep gate)
- ≤ 20 calls/h on Bland.ai
- ≤ 60 sends/h on AgentMail
- All `state/*.json*` written chmod 600
- CAPTCHA detection in camofox snapshot → log + exit 3, no Dais escalation (HARD RULE #-1)

## State

Each adapter writes under `adapters/custom/<name>/state/`:

| File | Content |
|---|---|
| `lancers-session.json` / `coconala-session.json` | session meta (cookie dir, tabId, status) |
| `dm-log.jsonl` | every send attempt (rate cap source of truth) |
| `last-inbox.json` | last `read-inbox.sh` output |
| `call-log.jsonl` | every Bland.ai call attempt |
| `sent-log.jsonl` | every AgentMail send |
| `last-captcha-block.txt` | first 2KB of snapshot when CAPTCHA detected |

`adapters/custom/../../state/adapter-test-log.jsonl` — top-level e2e ledger.
