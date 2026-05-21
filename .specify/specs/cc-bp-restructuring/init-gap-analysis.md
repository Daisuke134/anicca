# /init Gap Analysis — CC BP Restructuring

**Date:** 2026-03-05
**Sources:** Claude Code Official Docs (memory, best-practices, settings, skills, hooks, sub-agents)

## Current State vs Official Best Practices

### CLAUDE.md

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Target under 200 lines per CLAUDE.md | 278 lines x 2 files = 556 lines | Over 2x recommended size, duplicate file | Phase 1: Slim to <= 150, delete .claude/CLAUDE.md |
| Use @import for shared content | No imports used | Missing feature | Phase 1: Add @import for README, package.json refs |
| CLAUDE.local.md for personal prefs | Does not exist | Missing file | Phase 1: Create template, add to .gitignore |
| Concise, verifiable instructions only | Contains tutorials, explanations, long tables | Bloated with non-actionable content | Phase 1: Strip to commands and rules only |
| "Would removing this cause mistakes?" test | Many lines are redundant with rules/ | Duplication between CLAUDE.md and rules/ | Phase 1: Remove duplicated content |

### .claude/rules/

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Rules for always-loaded instructions | 19 files, 1,945 lines | 14 files should be skills (on-demand) | Phase 2: Migrate 7 to skills, delete 7 redundant |
| `paths:` frontmatter for file-specific rules | 0 rules have paths | Missing feature | Phase 1: Add to api-compatibility.md |
| Modular, one-topic-per-file | Some files cover multiple topics | Minor overlap | Phase 2: Consolidate during migration |

### Skills

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Skills for on-demand knowledge | 176 skills exist, but 7 rule files should be skills | Rules loaded every session that should be on-demand | Phase 2: testing-strategy, tool-usage, deployment, spec-writing, subagent-guide, skill-authoring, persona |
| Proper frontmatter (name, description with "Use when") | Unknown compliance rate | No audit done | Phase 7: Audit all 176 skills |
| context:fork for heavy skills | 0 skills use context:fork | Missing feature | Phase 13: Add to 4 heavy skills |

### Hooks

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| 3 hook types: command, prompt, http | 1 hook script exists | Severely under-utilized | Phase 5: Create 8 hook scripts |
| SessionStart for session init | No SessionStart hook | Missing | Phase 5: T5.1 |
| PreToolUse for linting | No PreToolUse hook | Missing | Phase 5: T5.2 |
| PostToolUse for notifications | No PostToolUse hook | Missing | Phase 5: T5.3 |
| Compact re-injection | No compact hook | Missing (FR-011) | Phase 5: T5.9-T5.11 |

### settings.json

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Full configuration (permissions, env, model, etc.) | 4 settings | 21 settings missing | Phase 9: Write full settings.json (>= 25) |
| settings.local.json for personal overrides | Does not exist | Missing file | Phase 9: Create template |
| Pre-approved permissions for trusted tools | Minimal permissions | Under-configured | Phase 9: Add allowed tools |

### .mcp.json

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Project-level MCP config in .mcp.json | File does not exist | Missing entirely | Phase 8: Create with 9 MCP servers |

### Agents

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| Agent(type) restrictions | 10 agents, no type restrictions | Missing feature | Phase 7: T7.5-T7.7a |
| 14-field frontmatter | 3 fields average | 11 fields missing per agent | Phase 7: T7.7-T7.9 |
| skills: preloading | No preloading configured | Missing feature | Phase 7: T7.7b |

### Commands

| Official BP | Current State | Gap | Action |
|------------|---------------|-----|--------|
| 4-field frontmatter | Unknown compliance | No audit done | Phase 7: T7.10-T7.12 |
| Dynamic injection | Not configured | Missing feature | Phase 13: T13.5 |

## Summary

| Category | Gaps Found | Severity |
|----------|-----------|----------|
| CLAUDE.md size and duplication | 3 | HIGH |
| Rules-to-skills migration | 2 | HIGH |
| Hooks under-utilization | 5 | HIGH |
| settings.json under-configuration | 2 | MEDIUM |
| .mcp.json missing | 1 | MEDIUM |
| Skill frontmatter compliance | 1 | MEDIUM |
| Agent/command frontmatter | 2 | MEDIUM |
| context:fork missing | 1 | LOW |

**Total: 17 gaps identified. All addressed in Phase 1-15 task plan.**

## Phase 1 Adjustments Based on Analysis

No adjustments needed. The task plan already covers all identified gaps. The official docs confirm:
1. 200-line target for CLAUDE.md (our 150-line target is stricter = good)
2. @import syntax is supported and recommended
3. `paths:` frontmatter works for file-specific rules
4. Skills are the correct destination for on-demand knowledge
5. `/init` would generate a basic CLAUDE.md — our plan goes far beyond what /init produces
