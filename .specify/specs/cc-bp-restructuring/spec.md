# Feature: Claude Code Best Practices Restructuring

**Branch:** `feature/cc-bp-restructuring`
**Status:** Specified
**Master Spec:** `.cursor/plans/claude-code-bp-restructuring-plan.md` (v3)

## Problem Statement

Current Claude Code setup loads 2,501 lines every session (CLAUDE.md 278 lines x 2 files = 556 lines, rules/ 1,945 lines across 19 files). Measured 2026-03-05 via `wc -l`. Research shows LLM instruction compliance degrades uniformly as instruction count increases, with frontier models stable at 150-200 instructions. Current setup has >= 500 instructions = 50% compliance rate.

## User Scenarios

### P1: Context Load Reduction (Core)

**As** Claude Code, **I want** to load only essential instructions at session start, **so that** instruction compliance stays above 90%.

**Acceptance:**
- Given CLAUDE.md is 278 lines (measured 2026-03-05), When restructured, Then `wc -l CLAUDE.md` <= 150
- Given rules/ is 19 files / 1,945 lines (measured 2026-03-05), When restructured, Then `ls .claude/rules/*.md | wc -l` = 5 AND `wc -l .claude/rules/*.md | tail -1` <= 300
- Given total session load is 2,501 lines (556 CLAUDE.md, 1,945 rules; measured 2026-03-05), When restructured, Then sum <= 450 (82% reduction)

### P2: On-Demand Knowledge Loading

**As** Claude Code, **I want** specialized knowledge to load only when relevant, **so that** context window is preserved for actual work.

**Acceptance:**
- Given testing rules exist in rules/, When moved to skills/, Then they load only when test-related prompts appear
- Given deployment rules exist in rules/, When moved to skills/, Then they load only when deploy-related prompts appear
- Given 7 rule files are moved to skills, When each has proper frontmatter, Then semantic matching triggers correct skill

### P3: OpenClaw Separation

**As** the system, **I want** OpenClaw config separated from CC config, **so that** CC doesn't load OpenClaw settings and vice versa.

**Acceptance:**
- Given OpenClaw files exist in anicca-project/ rules/, When separated, Then they exist only in .openclaw/workspace/
- Given CLAUDE.md contains OpenClaw sections, When separated, Then CLAUDE.md has max 2 lines referencing OpenClaw CLI

### P4: Full Feature Utilization

**As** Claude Code, **I want** to use all available CC features, **so that** development is maximally efficient.

**Acceptance:**
- Given settings.json has 5 settings, When configured, Then it has 25 or more settings
- Given 0 hooks exist, When configured, Then 8 or more hooks covering 3 types (command/prompt/http)
- Given 0 plugins, When investigated, Then `/plugin` output documented AND 1 or more code intelligence plugins evaluated (install if score >= 3/5 on: symbol nav, speed, stability)
- Given bundled skills unused, When documented, Then /simplify, /batch, /debug each referenced in agent_docs/tool_reference.md with usage example

### P5: Quality Infrastructure

**As** Claude Code agents, **I want** full frontmatter on all skills/agents/commands, **so that** semantic matching and permissions work correctly.

**Acceptance:**
- Given 176 skills, When audited, Then all have name, description, and relevant frontmatter
- Given 10 agents, When audited, Then all have 14 frontmatter fields including Agent(type) restrictions
- Given 20 commands, When audited, Then all have 4 frontmatter fields and dynamic injection where useful

### P6: Git Structure & OSS

**As** the project, **I want** reusable skills published as individual OSS repos, **so that** the community can use them.

**Acceptance:**
- Given skills are embedded in anicca-products, When restructured, Then 3 or more factory skills have individual GitHub repos under Daisuke134/
- Given mobileapp-builder exists, When renamed, Then `gh repo view Daisuke134/mobileapp-factory` succeeds
- Given no submodule structure, When configured, Then `git submodule status` shows >= 3 entries under packages/

## Edge Cases

| Case | Handling |
|------|----------|
| Skill semantic matching fails after move | Verify description triggers with test prompts |
| @import syntax not supported in CC version | Fallback: keep referenced content inline in CLAUDE.md |
| Plugin marketplace empty/unavailable | Document findings, skip Phase 12 |
| Existing hooks conflict with new hooks | Audit existing, merge or replace |
| .openclaw/workspace/ files have merge conflicts | Manual resolution, Anicca repo is separate git |

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | CLAUDE.md must be <= 150 lines after restructuring |
| FR-002 | rules/ must have exactly 5 files totaling <= 300 lines |
| FR-003 | 7 rule files must become skills with proper frontmatter |
| FR-004 | OpenClaw config must exist only in .openclaw/workspace/ |
| FR-005 | settings.json must have >= 25 active settings |
| FR-006 | >= 8 hook scripts covering command/prompt/http types |
| FR-007 | All 176 skills must have validated frontmatter |
| FR-008 | All 10 agents must have 14-field frontmatter |
| FR-009 | All 20 commands must have 4-field frontmatter |
| FR-010 | .mcp.json with 9 MCP servers |
| FR-011 | SessionStart compact hook for context re-injection |
| FR-012 | context:fork on 4 heavy skills: codex-review, recursive-improver, competitive-ads-extractor, content-research-writer |
| FR-013 | Agent(type) restrictions on all agents |
| FR-014 | packages/ directory with git submodules for OSS skills |
| FR-015 | /init gap analysis before CLAUDE.md rewrite |

## Success Criteria

| Metric | Current (measured 2026-03-05) | Target | Verification Command |
|--------|-------------------------------|--------|---------------------|
| CLAUDE.md lines | 278 | <= 150 | `wc -l CLAUDE.md` |
| CLAUDE.md file count | 2 (root and .claude/) | 1 (root only) | `find . -name CLAUDE.md -not -path '*/node_modules/*' \| wc -l` |
| rules/ file count | 19 | 5 | `ls .claude/rules/*.md \| wc -l` |
| rules/ total lines | 1,945 | <= 300 | `wc -l .claude/rules/*.md \| tail -1` |
| Session load lines | 2,501 (556 and 1,945) | <= 450 (82% reduction) | Sum of above |
| settings.json settings | 5 | >= 25 | `jq 'paths \| length' .claude/settings.json \| wc -l` |
| Hook scripts | 0 | >= 8 | `ls .claude/hooks/scripts/*.sh \| wc -l` |
| Skill frontmatter compliance | Unknown | 100% | `.specify/scripts/audit-skills.sh` |
| Agent frontmatter fields | 3 | 14 per agent | Manual audit per agent |
| MCP servers in .mcp.json | 0 | 9 | `jq '.mcpServers \| length' .mcp.json` |
| OSS skill repos | 1 | >= 3 | `gh repo list Daisuke134 --json name \| jq '[.[] \| select(.name \| test("factory"))] \| length'` |

## Baseline Measurement Log (2026-03-05)

```
$ wc -l CLAUDE.md .claude/CLAUDE.md
     278 CLAUDE.md
     278 .claude/CLAUDE.md
     556 total
$ ls .claude/rules/*.md | wc -l
      19
$ wc -l .claude/rules/*.md | tail -1
    1945 total
$ jq 'paths | length' .claude/settings.json | wc -l
       4
$ ls .claude/hooks/scripts/*.sh 2>/dev/null | wc -l
       1
$ jq '.mcpServers | length' .mcp.json
not found (file does not exist)

Total session load: 556 (CLAUDE.md) and 1,945 (rules/) = 2,501 lines
```

## Boundaries (Out of Scope)

- iOS app code changes
- API server code changes
- OpenClaw skill creation/modification (separate repo)
- Mixpanel/RevenueCat configuration
- App Store submission
- Content creation or marketing
