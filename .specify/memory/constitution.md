# Constitution v1.0.0 — CC BP Restructuring

## Governance

| Principle | Description |
|-----------|-------------|
| **BP-First** | Every decision must cite a best practice source. No original solutions. |
| **Search-Before-Act** | Minimum 3 independent searches before any action. No guessing. |
| **Single Answer** | No options. No "maybe". One answer per question. |
| **Spec = Executable** | Specifications directly generate implementations. |
| **Test-First** | Tests precede implementation (TDD: RED -> GREEN -> REFACTOR). |
| **Simplicity** | Minimum complexity for current task. No premature abstraction. |
| **Context Economy** | Minimize token consumption. On-demand loading over static. |
| **Immutability** | Never mutate. Create new objects. |
| **Push Immediately** | Every edit = immediate commit & push. No confirmation needed. |

## Quality Gates

| Gate | Criteria | Blocker |
|------|----------|---------|
| Spec Review | codex-review ok: true | Yes |
| Implementation | All tests GREEN | Yes |
| Code Review | codex-review ok: true | Yes |
| User Confirmation | Manual OK on device/simulator | Yes |

## Versioning

- MAJOR: Breaking changes to project structure (CLAUDE.md format, rules/ removal)
- MINOR: New phases, settings additions, hook additions
- PATCH: Wording fixes, path corrections, typo fixes

## Constraints

- CLAUDE.md <= 150 lines
- rules/ <= 5 files, <= 300 lines total
- Session context load <= 450 lines (82% reduction from current 2,501)
- All skills must have proper frontmatter (name, description with "Use when...")
- All agents must have full 14-field frontmatter
- Hooks must cover 3 types: command, prompt, http
- settings.json must have >= 25 active settings

## Sources of Truth

| Artifact | Location |
|----------|----------|
| Master Spec | .cursor/plans/claude-code-bp-restructuring-plan.md |
| Constitution | .specify/memory/constitution.md |
| Feature Spec | .specify/specs/cc-bp-restructuring/spec.md |
| Tasks | .specify/specs/cc-bp-restructuring/tasks.md |
| Anicca Config | /Users/anicca/.openclaw/workspace/ |
| CC Config | /Users/anicca/anicca-project/.claude/ |
