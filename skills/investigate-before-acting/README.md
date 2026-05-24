# 🔍 investigate-before-acting

Stop fabricating. Start citing. Every decision backed by a source.

## What This Does

Forces AI agents to search for best practices before every action. Every decision must include:
- **Source name** — where it came from
- **URL** — link to the source
- **Direct quote** — exact text from the source

No citation = decision gets deleted.

Based on [Anthropic's official hallucination reduction techniques](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations).

## Install

### OpenClaw
```bash
clawhub install investigate-before-acting
```

### Claude Code
Copy the contents of `references/claude-patch.md` into your `.claude/CLAUDE.md`.

### Manual (any agent)
Copy the contents of `references/soul-patch.md` into your agent's system prompt or configuration file.

## How It Works

1. **One-time setup**: Patches your config files (SOUL.md, CLAUDE.md, AGENTS.md) with the protocol
2. **Every session after**: Your agent bootstraps with the protocol already loaded
3. **Failsafe**: The skill stays `always: true` so the description is always visible as a reminder

## The Protocol

| Step | Action |
|------|--------|
| 1. Search | 3+ independent queries, English + user's language |
| 2. Cite | Every decision gets: Source name + URL + direct quote |
| 3. Execute | Follow best practice 100%. Zero original input. |

## Rules

- **No questions** — search engines know more than your user
- **No options** — sufficient research = one answer
- **No originals** — copy the success formula
- **No "BP doesn't exist"** — it always does, search harder

## License

MIT
