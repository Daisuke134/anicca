---
description: Incrementally fix Swift and Xcode build errors with minimal changes.
---

# Build Fix Command

Incrementally fix Swift and Xcode build errors.

## What This Command Does

1. Run build: `xcodebuild -scheme aniccaios build`

2. Parse error output:
   - Group by file
   - Sort by severity

3. For each error:
   - Show error context (5 lines before/after)
   - Explain the issue
   - Propose minimal fix
   - Apply fix
   - Re-run build
   - Verify error resolved

4. Stop if:
   - Fix introduces new errors
   - Same error persists after 3 attempts
   - User requests pause

5. Show summary:
   - Errors fixed
   - Errors remaining
   - New errors introduced

## When to Use

Use `/build-fix` when:
- Build fails with errors
- Type errors blocking development
- Import/module resolution errors
- After merging branches with conflicts

## Example Session

```
User: /build-fix

Agent:
# Build Error Resolution

## Running build...
Found 3 errors in 2 files.

---

### Error 1 of 3
**File:** Views/NudgeCardView.swift:45
**Error:** Value of optional type 'String?' must be unwrapped

**Context:**
```swift
43: func displayMessage() {
44:     let problem = userProblem
45:     let message = problem.nudgeMessage.uppercased() // ERROR
46: }
```

**Fix:** Add optional chaining
```diff
- let message = problem.nudgeMessage.uppercased()
+ let message = problem.nudgeMessage?.uppercased() ?? ""
```

**Applying fix...**
**Re-running build...**
✅ Error 1 resolved. 2 remaining.

---

### Error 2 of 3
...

---

## Summary
- Errors fixed: 3
- Errors remaining: 0
- New errors: 0
- Build status: ✅ SUCCESS
```

## Important Rules

- **Minimal changes only** - Don't refactor, just fix the error
- **One error at a time** - Verify each fix before moving on
- **No architectural changes** - Only fix what's broken
- **Preserve functionality** - Don't change behavior

## Related Agents

This command uses the `build-error-resolver` agent.

Fix one error at a time for safety!
