# Technical Plan: CC BP Restructuring

**Master Spec:** `.cursor/plans/claude-code-bp-restructuring-plan.md` (v3, 15 phases)
**Research:** Complete (20 sources analyzed, 7 official Anthropic docs scraped)

## Technical Context

| Item | Value |
|------|-------|
| Language | Markdown, JSON, Bash, YAML frontmatter |
| Platform | macOS (Mac Mini), Claude Code CLI |
| Dependencies | Claude Code, OpenClaw, git, SwiftLint, ESLint |
| Config format | JSON (settings.json, .mcp.json), Markdown (CLAUDE.md, rules/, skills/) |

## Implementation Strategy

**Sequential phases with independent parallelizable sub-tasks within each phase.**

**Strict Topological Order (single source of truth):**
```
Step 1: Phase 14 (/init gap analysis)
Step 2: Phase 1 (CLAUDE.md rewrite) — depends on: Phase 14
Step 3: Phase 2 (rules -> skills migration) — depends on: Phase 1
Step 4: Phase 3, 4, 5, 9 (PARALLEL) — depends on: Phase 2
Step 5: Phase 7, 10, 11, 12, 13 (PARALLEL) — depends on: Step 4 completion
Step 6: Phase 6 (CC<->OpenClaw integration) — depends on: Phase 3, 4
Step 7: Phase 15 (Git/OSS) — depends on: Phase 7 (skill audit complete)
```
**Phase 8 (.mcp.json) is an independent lane with zero dependencies — execute at any step.**

## Phase Grouping for Implementation

### Group A: Foundation (Sequential, Blocking)
1. **Phase 14** - /init gap analysis
2. **Phase 1** - CLAUDE.md slim down, @import, paths
3. **Phase 2** - rules/ -> skills/ migration

### Group B: Parallel after Group A (all start after Phase 2 completes)
4. **Phase 3** - OpenClaw separation (.openclaw/workspace/ updates)
5. **Phase 4** - agent_docs/ creation
6. **Phase 5** - Hooks setup (8 or more scripts, 3 types, incl. FR-011 compact re-injection)
7. **Phase 9** - settings.json full config

### Independent Lane (no dependencies, execute at any step)
8. **Phase 8** - .mcp.json creation (zero dependencies on any other phase)

### Group C: Depends on Group B
9. **Phase 7** - 176 skills, 10 agents, 20 commands audit
10. **Phase 10** - Boris 12 customizations
11. **Phase 11** - CLI flags documentation
12. **Phase 12** - Plugin system
13. **Phase 13** - Bundled skills and context:fork

### Group D: Integration & OSS
14. **Phase 6** - CC <-> OpenClaw integration protocol
15. **Phase 15** - Git structure & skill OSS

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| @import syntax may not work | Test with single import first, fallback to inline |
| Skill semantic matching breaks | Test each moved skill with sample prompt before deleting original |
| 176 skill audit is large | Batch audit with scripted frontmatter checker |
| settings.json breaks CC | Backup current settings, incremental additions with testing |
| OpenClaw workspace changes break Anicca | Changes go to Daisuke134/anicca repo, separate from anicca-products |
