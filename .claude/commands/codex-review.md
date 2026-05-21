---
description: Automated spec and code review using OpenAI Codex. Use after creating spec files or completing code changes.
---

# Codex Review Command

Automated spec and code review using OpenAI Codex CLI. Iterates review-fix-review cycles until clean.

## What This Command Does

1. **Detect Change Type:**
   - Spec file (`*-spec.md`) → Spec review mode
   - Code changes → Code review mode

2. **Run Codex Review:**

   For specs:
   ```bash
   codex exec --sandbox read-only \
     --output-schema .claude/skills/codex-review/review-schema.json \
     "Review this spec file for completeness..."
   ```

   For code:
   ```bash
   codex review --uncommitted
   ```

3. **Parse Results:**
   - `ok: true` → Review passed, continue
   - `blocking` issues → Must fix before proceeding
   - `advisory` issues → Show as warnings

4. **Iterate Until Clean:**
   - Max 5 iterations
   - Fix blocking issues each round
   - Stop when `ok: true` or only advisory issues remain

## Arguments

- No arguments: Review all uncommitted changes
- `<file-path>`: Review specific file
- `--spec`: Force spec review mode
- `--code`: Force code review mode

## Usage Examples

```bash
# Review uncommitted changes
/codex-review

# Review specific spec file
/codex-review .cursor/plans/ios/phase5/feature-spec.md

# Review all changes against main branch
/codex-review --base main
```

## When to Use

This skill is **automatically triggered** when:
- A spec file (`*-spec.md`) is created or modified
- Code implementation is completed before commit
- Before creating a pull request

## Manual Invocation

Use `/codex-review` when:
- You want explicit Codex review
- After finishing a feature implementation
- Before merging to main branch

## Review Types

### Spec Review Checks
- As-Is / To-Be completeness
- Test matrix coverage
- Localization (JP/EN)
- Edge case handling
- Backward compatibility

### Code Review Checks
- Security (OWASP Top 10)
- Logic errors
- Swift/SwiftUI best practices
- Test coverage gaps
- Performance issues

## Output Format

```json
{
  "ok": false,
  "blocking": [
    {
      "file": "path/to/file.swift",
      "line": 42,
      "severity": "critical",
      "issue": "Description of problem",
      "suggestion": "How to fix it"
    }
  ],
  "advisory": [...],
  "summary": "Found 1 blocking issue"
}
```

## Success Criteria

Review is complete when:
- `ok: true` in Codex response
- No blocking issues remain
- Or max iterations (5) reached

## Related Files

- Skill: `.claude/skills/codex-review/SKILL.md`
- Schema: `.claude/skills/codex-review/review-schema.json`

## Workflow Integration

This command integrates with the standard development flow:

```
1. Create spec file
   ↓
2. /codex-review (auto-triggered)
   ↓
3. Fix any issues
   ↓
4. Implement code (/tdd)
   ↓
5. /codex-review (auto-triggered)
   ↓
6. Fix any issues
   ↓
7. Commit & push
```
