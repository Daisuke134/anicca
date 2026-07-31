---
name: subagent-guide
description: Defines when and how to delegate tasks to sub-agents, parallel execution patterns, context management rules, and anti-patterns for multi-agent coordination. Use when delegating to sub-agents, planning parallel execution, managing context budget, or coordinating agent teams.
---

# Sub-agent & Skill Usage Guide

## When to Delegate

| Condition | Delegate To |
|-----------|------------|
| 100+ line output expected | `Explore` |
| 3+ independent tasks | Parallel sub-agents |
| Specialized knowledge needed | Matching sub-agent |
| Research/investigation | `Explore` or `tech-spec-researcher` |
| Code review | `code-quality-reviewer` |

## When NOT to Delegate

| Condition | Reason |
|-----------|--------|
| Frequent interaction needed | High latency |
| ≤5 lines change | Overhead too high |
| Implementation coding | Main has richer context |
| Interdependent phases | Needs shared context |

## Task Size Guide

| Size | Approach |
|------|---------|
| ≤5 lines | Vanilla CC (no skill) |
| 5-50 lines | 1 matching skill |
| 50+ lines / multi-file | Sub-agent delegation |

## Context Management

| Rule | Value |
|------|-------|
| Main context target | 40-60% |
| Delegation threshold | 60%+ → delegate aggressively |
| Sub-agent results | Summary only (no full dump) |
| `/compact` timing | Natural milestones |
| Parallel optimal | 3-5 agents (max 7) |

## Parallel Research Pattern

```
Sub-agent 1: Web search (BP) ← parallel
Sub-agent 2: Codebase explore ← parallel
Sub-agent 3: Review           ← parallel
    ↓
Main receives summary → decides → implements
```

## Sub-agent Handoff (Required Context)

| Include | Why |
|---------|-----|
| Task purpose | What to investigate |
| Project context | Files, tech stack |
| Files to read | Skip search overhead |
| Output format | PASS/FAIL, table, summary |
| Constraints | "Read only", "Research only" |

## Anti-patterns (Forbidden)

| Anti-pattern | Fix |
|-------------|-----|
| Parallel writes to same file | Read-only parallel, writes serial |
| Delegating tiny tasks | Direct execution for ≤5 lines |
| Dumping full output to main | Summary only |

## Agent Teams (Last Resort)

**Only when main + sub-agents fail.** Cost = 5x+. User approval required.

Use for: complex bugs (parallel hypotheses), large refactors (independent modules), multi-angle reviews.
