# Tasks: CC BP Restructuring

**Execution Order:** Phase 14 -> 1 -> 2 -> {3,4,5,9} parallel -> {7,10,11,12,13} -> 6 -> 15
**Phase 8 is an independent lane (zero dependencies, execute at any step).**

## Phase 14: /init Gap Analysis (RUN FIRST)

- [ ] T14.1 [FR-015] RED: Verify no /init gap analysis exists (expect fail after analysis)
- [ ] T14.2 [FR-015] Run `/init` in a temp directory, capture output
- [ ] T14.3 [FR-015] Compare /init output structure with our planned CLAUDE.md
- [ ] T14.4 [FR-015] GREEN: Document gaps and verify gap analysis is complete

## Phase 1: Foundation Setup (BLOCKING)

- [ ] T1.1 [FR-001] RED: Verify `wc -l CLAUDE.md` = 278 (current baseline, expect fail after rewrite)
- [ ] T1.2 [FR-001] Backup current CLAUDE.md and .claude/CLAUDE.md
- [ ] T1.3 [FR-001] Delete `.claude/CLAUDE.md` duplicate (`git rm .claude/CLAUDE.md`)
- [ ] T1.4 [FR-001] Rewrite `CLAUDE.md` to <= 150 lines with @import syntax
- [ ] T1.5 [FR-001] GREEN: Verify `wc -l CLAUDE.md` <= 150
- [ ] T1.6 Create `CLAUDE.local.md` template and add to .gitignore
- [ ] T1.7 [FR-002] RED: Verify `ls .claude/rules/*.md | wc -l` = 19 AND `wc -l .claude/rules/*.md | tail -1` > 300 (current baseline, expect fail after compression)
- [ ] T1.7a [FR-002] Add `paths: ["apps/api/**"]` frontmatter to `api-compatibility.md`
- [ ] T1.8 [FR-002] Compress `git-workflow.md` 125 -> <= 50 lines
- [ ] T1.9 [FR-002] Compress `dev-workflow.md` 78 -> <= 40 lines
- [ ] T1.10 [FR-002] Compress `worktree.md` 141 -> <= 60 lines
- [ ] T1.11 [FR-002] GREEN: Verify `ls .claude/rules/*.md | wc -l` = 5 AND total <= 300 lines

## Phase 2: Rules to Skills Migration (BLOCKING)

- [ ] T2.1 [FR-003] RED: Run audit-skills.sh on 7 new skills (expect fail: skills don't exist yet)
- [ ] T2.2 [FR-003] Create `.claude/skills/testing-strategy/SKILL.md` with frontmatter
- [ ] T2.3 [FR-003] Create `.claude/skills/tool-usage/SKILL.md` with frontmatter
- [ ] T2.4 [FR-003] Create `.claude/skills/deployment/SKILL.md` (with `disable-model-invocation: true`)
- [ ] T2.5 [FR-003] Create `.claude/skills/spec-writing/SKILL.md` with frontmatter
- [ ] T2.6 [FR-003] Create `.claude/skills/subagent-guide/SKILL.md` with frontmatter
- [ ] T2.7 [FR-003] Create `.claude/skills/skill-authoring-guide/SKILL.md` with frontmatter
- [ ] T2.8 [FR-003] Create `.claude/skills/persona/SKILL.md` with frontmatter
- [ ] T2.9 [FR-003] GREEN: Run audit-skills.sh on 7 new skills (expect pass)
- [ ] T2.10 Delete migrated rule files (7) and redundant files (7)
- [ ] T2.11 [FR-002] GREEN: Verify rules/ = exactly 5 files

## Phase 3: OpenClaw Separation

- [ ] T3.0 [FR-004] RED: Verify CLAUDE.md has > 2 lines referencing OpenClaw (expect fail after separation)
- [ ] T3.1 [FR-004] || Update `/Users/anicca/.openclaw/workspace/IDENTITY.md` (remove VPS, fix repo URL)
- [ ] T3.2 [FR-004] || Update `/Users/anicca/.openclaw/workspace/AGENTS.md` (Mac Mini rules, MCP IDs, Cron)
- [ ] T3.3 [FR-004] || Update `/Users/anicca/.openclaw/workspace/SOUL.md` (add IBA protocol, originality ban)
- [ ] T3.4 [FR-004] GREEN: Verify CLAUDE.md has max 2 lines for OpenClaw and grep confirms no OpenClaw config in rules/

## Phase 4: agent_docs/ Creation

- [ ] T4.1 || Create `agent_docs/building_and_testing.md`
- [ ] T4.2 || Create `agent_docs/code_conventions.md`
- [ ] T4.3 || Create `agent_docs/service_architecture.md`
- [ ] T4.4 || Create `agent_docs/openclaw_integration.md`
- [ ] T4.5 || Create `agent_docs/tool_reference.md`

## Phase 5: Hooks Setup

- [ ] T5.0 [FR-006] RED: Verify `ls .claude/hooks/scripts/*.sh 2>/dev/null | wc -l` = 0 (expect fail after hook setup)
- [ ] T5.1 [FR-006] Create `.claude/hooks/scripts/session-start.sh` (SessionStart, once:true)
- [ ] T5.2 [FR-006] Create `.claude/hooks/scripts/pre-tool-lint.sh` (PreToolUse, Edit|Write matcher)
- [ ] T5.3 [FR-006] Create `.claude/hooks/scripts/post-tool-sound.sh` (PostToolUse, Bash matcher)
- [ ] T5.4 [FR-006] Create `.claude/hooks/scripts/notification-sound.sh` (Notification)
- [ ] T5.5 [FR-006] Create `.claude/hooks/scripts/stop-continue.sh` (Stop, type:prompt)
- [ ] T5.6 [FR-006] Create `.claude/hooks/scripts/pre-compact-backup.sh` (PreCompact)
- [ ] T5.7 [FR-006] Create `.claude/hooks/scripts/subagent-stop-validate.sh` (SubagentStop)
- [ ] T5.8 [FR-006] Create `.claude/hooks/scripts/user-prompt-context.sh` (UserPromptSubmit)
- [ ] T5.9 [FR-011] RED: Verify `.claude/context/post-compact-essentials.md` does not exist (expect fail after creation)
- [ ] T5.9a [FR-011] Create `.claude/context/post-compact-essentials.md` (compact re-injection content)
- [ ] T5.10 [FR-011] Add SessionStart hook with `compact` matcher to settings.json (re-inject post-compact-essentials.md)
- [ ] T5.11 [FR-011] GREEN: Verify compact re-injection by simulating compaction and checking hook fires
- [ ] T5.12 [FR-006] Add all hooks config to settings.json (3 types: command, prompt, http)
- [ ] T5.13 [FR-006] GREEN: Verify `ls .claude/hooks/scripts/*.sh | wc -l` >= 8

## Phase 6: CC <-> OpenClaw Integration Protocol

- [ ] T6.1 Define sentinel strings in `agent_docs/openclaw_integration.md`
- [ ] T6.2 Create STATUS.md / PLAN.md templates for worktrees

## Phase 7: Skills, Agents, Commands Audit

- [ ] T7.1 [FR-007] Write audit script (`.specify/scripts/audit-skills.sh`)
- [ ] T7.2 [FR-007] RED: Run audit on all 176 skills (expect failures)
- [ ] T7.3 [FR-007] Fix missing frontmatter on failing skills
- [ ] T7.4 [FR-007] GREEN: Run audit on all skills (expect 100% pass)
- [ ] T7.5 [FR-013] RED: Verify 10 agents lack `Agent(type)` restrictions (expect fail)
- [ ] T7.6 [FR-013] Add `Agent(type)` restrictions to all 10 agents
- [ ] T7.7a [FR-013] GREEN: Verify all 10 agents have `Agent(type)` restrictions
- [ ] T7.7b Add `skills:` preloading to relevant agents (tdd-guide, deploy-checker, security-auditor, code-quality-reviewer)
- [ ] T7.7 [FR-008] RED: Audit 10 agents for 14 fields (expect failures)
- [ ] T7.8 [FR-008] Add full 14-field frontmatter to all 10 agents
- [ ] T7.9 [FR-008] GREEN: Re-audit 10 agents (expect 100% pass)
- [ ] T7.10 [FR-009] RED: Audit 20 commands for 4-field frontmatter (expect failures)
- [ ] T7.11 [FR-009] Add 4-field frontmatter and dynamic injection to all 20 commands
- [ ] T7.12 [FR-009] GREEN: Re-audit 20 commands (expect 100% pass)
- [ ] T7.13 Identify and delete unused skills

## Phase 8: .mcp.json Creation (INDEPENDENT)

- [ ] T8.1 [FR-010] RED: Verify `.mcp.json` does not exist or has fewer than 9 servers (expect fail)
- [ ] T8.2 [FR-010] Create `.mcp.json` with 9 MCP servers (existing 5, recommended 4)
- [ ] T8.3 [FR-010] GREEN: Verify `jq '.mcpServers | length' .mcp.json` = 9

## Phase 9: settings.json Full Config

- [ ] T9.0 [FR-005] RED: Verify `jq 'paths | length' .claude/settings.json | wc -l` < 25 (expect fail after full config)
- [ ] T9.1 [FR-005] Backup current `.claude/settings.json`
- [ ] T9.2 [FR-005] Write full settings.json (25 or more settings)
- [ ] T9.3 Create `.claude/settings.local.json` template and add to .gitignore
- [ ] T9.4 [FR-005] GREEN: Test CC startup with new settings (verify no breakage)
- [ ] T9.5 [FR-005] GREEN: Count settings >= 25

## Phase 10: Boris 12 Customizations

- [ ] T10.1 Terminal setup (shift+enter)
- [ ] T10.2 || Verify effort level = high (in settings.json env)
- [ ] T10.3 || Run `/plugin` to survey marketplace
- [ ] T10.4 || Verify custom agents (Phase 7)
- [ ] T10.5 || Verify permissions pre-approved (Phase 9)
- [ ] T10.6 || Verify sandbox (Phase 9)
- [ ] T10.7 || Verify status line (Phase 9)
- [ ] T10.8 Keybindings customization
- [ ] T10.9 || Verify hooks (Phase 5)
- [ ] T10.10 || Verify spinner verbs (Phase 9)
- [ ] T10.11 Output style configuration
- [ ] T10.12 || Verify settings.json committed to git (Phase 9)

## Phase 11: CLI Flags Documentation

- [ ] T11.1 Document frequently used CLI flags in agent_docs/tool_reference.md
- [ ] T11.2 Verify env vars in settings.json env key

## Phase 12: Plugin System

- [ ] T12.1 Run `/plugin` and document available plugins
- [ ] T12.2 Evaluate code intelligence plugin (score >= 3/5 on: symbol nav, speed, stability)

## Phase 13: Bundled Skills and context:fork

- [ ] T13.1 [FR-012] RED: Verify 4 skills lack `context: fork` in frontmatter (expect fail)
- [ ] T13.2 [FR-012] Add `context: fork` to codex-review, recursive-improver, competitive-ads-extractor, content-research-writer SKILL.md frontmatter
- [ ] T13.3 [FR-012] GREEN: Verify all 4 skills have `context: fork` in frontmatter
- [ ] T13.4 Document /simplify, /batch, /debug usage in agent_docs/tool_reference.md
- [ ] T13.5 || Add dynamic injection to deploy, code-review, tdd commands

## Phase 15: Git Structure & OSS

- [ ] T15.1 [FR-014] RED: Verify `git submodule status` shows 0 entries (expect fail after setup)
- [ ] T15.2a [FR-014] Identify 3 or more OSS-worthy factory skills from 176 CC skills
- [ ] T15.2 [FR-014] Create packages/ directory
- [ ] T15.3 [FR-014] Rename mobileapp-builder -> mobileapp-factory on GitHub
- [ ] T15.4 [FR-014] Set up git submodules in packages/
- [ ] T15.5 [FR-014] GREEN: Verify `git submodule status` shows >= 3 entries

## FR Traceability Matrix

| FR | Tasks | Coverage |
|----|-------|----------|
| FR-001 | T1.1(RED), T1.2-T1.4, T1.5(GREEN) | Full |
| FR-002 | T1.7(RED), T1.7a-T1.10, T1.11(GREEN), T2.11(GREEN) | Full |
| FR-003 | T2.1(RED), T2.2-T2.8, T2.9(GREEN) | Full |
| FR-004 | T3.0(RED), T3.1-T3.3, T3.4(GREEN) | Full |
| FR-005 | T9.0(RED), T9.1-T9.3, T9.4(GREEN), T9.5(GREEN) | Full |
| FR-006 | T5.0(RED), T5.1-T5.8, T5.12, T5.13(GREEN) | Full |
| FR-007 | T7.1, T7.2(RED), T7.3, T7.4(GREEN) | Full |
| FR-008 | T7.7(RED), T7.8, T7.9(GREEN) | Full |
| FR-009 | T7.10(RED), T7.11, T7.12(GREEN) | Full |
| FR-010 | T8.1(RED), T8.2, T8.3(GREEN) | Full |
| FR-011 | T5.9(RED), T5.9a, T5.10, T5.11(GREEN) | Full |
| FR-012 | T13.1(RED), T13.2, T13.3(GREEN) | Full |
| FR-013 | T7.5(RED), T7.6, T7.7a(GREEN) | Full |
| FR-014 | T15.1(RED), T15.2a-T15.4, T15.5(GREEN) | Full |
| FR-015 | T14.1(RED), T14.2-T14.3, T14.4(GREEN) | Full |

## Completion Checklist

- [ ] CLAUDE.md <= 150 lines (`wc -l`)
- [ ] rules/ = 5 files, <= 300 lines (`wc -l`)
- [ ] Session load <= 450 lines (82% reduction from 2,501)
- [ ] 7 rule files migrated to skills with frontmatter
- [ ] OpenClaw config only in .openclaw/workspace/
- [ ] settings.json >= 25 settings
- [ ] >= 8 hook scripts (3 types: command, prompt, http)
- [ ] FR-011: compact re-injection hook verified
- [ ] All skills have validated frontmatter (audit-skills.sh 100%)
- [ ] All 10 agents have 14-field frontmatter
- [ ] All 20 commands have 4-field frontmatter
- [ ] .mcp.json with 9 MCP servers
- [ ] >= 3 OSS factory skill repos with submodules
- [ ] codex-review passes on all changes
