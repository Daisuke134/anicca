---
name: skill-authoring-guide
description: Defines how to create and manage Claude Code skills with proper frontmatter, description format, invocation settings, and the 3-layer defense system. Use when creating new skills, writing SKILL.md files, or auditing skill frontmatter.
---

# Skill Authoring Rules

## How Skills Auto-Trigger

Startup → all `name` + `description` injected → Claude matches user input to description → SKILL.md loaded

**description is everything.** Bad description = never used.

## Description Format (Absolute)

```
description: [What it does (3rd person)]. Use when [trigger condition + keywords].
```

| Rule | Why |
|------|-----|
| 3rd person | Injected into system prompt |
| Include trigger keywords | Match accuracy |
| "Use when..." required | Explicit trigger condition |
| ≤1024 chars | Context budget |

### Forbidden Expressions (Process Explosion Prevention)

| Forbidden | Safe Alternative |
|-----------|-----------------|
| 「プロアクティブに使用」 | 「明示的指示があった場合のみ」 |
| 「自動的に使用」 | 「Use when [specific condition]」 |
| 「コード変更後に実行」 | 「コミット前/PR前に実行」 |

## SKILL.md Structure

| Rule | Value |
|------|-------|
| Max lines | 500 |
| Reference depth | 1 level only |
| 100+ line references | TOC at top required |
| Style | Imperative, no 2nd person |

## Invocation Settings

| Type | Frontmatter |
|------|------------|
| Auto + manual (default) | None |
| Manual only | `disable-model-invocation: true` |
| Auto only | `user-invocable: false` |

## 3-Layer Defense

| Layer | Location | Role |
|-------|----------|------|
| L1 | SKILL.md description | Primary auto-trigger (90%) |
| L2 | tool-usage skill mapping | Edge case fallback |
| L3 | CLAUDE.md reference index | Indirect reinforcement |
