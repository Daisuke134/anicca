# profiles/fixer/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM for debug + fix (Opus 4.8 primary) |
| `GH_TOKEN` | conditional | Bitwarden vault | only if fix requires reading/searching upstream repo |
| `FIXER_MAX_RETRY_ROUNDS` | optional | env override | default `3` |
| `FIXER_ESCALATE_AFTER_RETRY_MIN` | optional | env override | default `60` (= 60 min total, then escalate) |
| `FIXER_LEARNED_SKILLS_DIR` | optional | env override | default `~/.hermes/skills/learned/` |

## § 2. Identity

No PII. Fixer operates on Anicca's own skills + own logs only.

## § 3. Escalation protocol

When a fix fails after `FIXER_MAX_RETRY_ROUNDS` AND
`FIXER_ESCALATE_AFTER_RETRY_MIN` elapsed:

```
1. emit Kanban task: category=ops, priority=high,
   payload={ "issue": "<original heal task>", "attempted_fixes": [...], "logs": "..." }
2. cast on Farcaster (if earn-farcaster healthy): "instance <name> needs operator review on <skill>"
3. log to ~/.hermes/logs/escalation-audit.log
4. continue claiming other heal tasks (do not block on this one)
```

Operator picks up via inbox responder loop (per `specs/08-INBOX-RESPONDER-LOOP.md`).

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Inbox responder | `specs/08-INBOX-RESPONDER-LOOP.md` |
| Self-eval doctrine | `specs/03-SELF-AWARE-EVAL.md` |

---

**END OF profiles/fixer/env-map.md.**
