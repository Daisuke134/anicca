# web-app-factory — CLAUDE.md
# Source: snarktank/ralph CLAUDE.md (https://github.com/snarktank/ralph/blob/main/CLAUDE.md)
# Source: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Your Job

You are an autonomous web app builder. Each iteration, you:
1. Read progress.txt and git log to understand current state
2. Read prd.json to find the next story with passes: false
3. Complete that ONE story
4. Update prd.json (passes: true), write to progress.txt, git commit
5. Report via: openclaw system event --text "✅ US-XXX 完了: [summary]" --mode now

If ALL stories have passes: true, reply with: <promise>COMPLETE</promise>

## Secrets (env vars — never hardcode)
# Source: Twelve-Factor App (https://12factor.net/config)

All shared keys are sourced from `web-apps/.env` by ralph.sh.
Per-app keys are in `.env.local`.

## Quality Gate (MANDATORY — run at start of every US)
# Source: SonarQube (https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates)

Before starting any US, verify the previous US acceptance criteria:
- Read prd.json
- For each US with priority < current: verify passes: true
- If any prerequisite US is false: work on THAT US instead

## US → Skill Mapping

### US-001: Trend research
- Read: .claude/skills/web-app-factory/SKILL.md
- Output: prd.json + CLAUDE.md

### US-002: Stripe setup
- Read: .claude/skills/web-app-factory/SKILL.md (US-002 section)
- Output: .env.local with STRIPE_PRICE_ID

### US-003: Next.js scaffold
- Read: .claude/skills/web-app-factory/SKILL.md (US-003 section)
- Output: Next.js project with npm run build passing

### US-004: Feature implementation
- Read: .claude/skills/web-app-factory/SKILL.md (US-004 section)
- Output: All pages implemented with Stripe Checkout

### US-005: Quality check
- Read: .claude/skills/web-app-factory/SKILL.md (US-005 section)
- Read: .claude/skills/webapp-testing/SKILL.md
- Output: npm run build + E2E passing

### US-006: Vercel deploy
- Read: .claude/skills/web-app-factory/SKILL.md (US-006 section)
- Output: Live Vercel URL

### US-007: Final report
- Read: .claude/skills/web-app-factory/SKILL.md (US-007 section)
- Output: AGENTS.md + X post + COMPLETE

## CRITICAL RULES
- Read .claude/skills/web-app-factory/SKILL.md for all rules
- Every source file change → git commit with descriptive message
- Every US completion → update progress.txt + prd.json + git commit + system event
