---
description: Safely identify and remove dead code with test verification.
---

# Refactor Clean Command

Safely identify and remove dead code with test verification.

## What This Command Does

1. Run dead code analysis:
   - Find unused files (no imports)
   - Find unused functions (no references)
   - Find unused imports
   - Find commented-out code

2. Generate comprehensive report

3. Categorize findings by severity:
   - SAFE: Unused private functions, unused imports
   - CAUTION: Unused Views, unused public functions
   - DANGER: Core models, entry points

4. Propose safe deletions only

5. Before each deletion:
   - Build project
   - Verify build passes
   - Apply change
   - Re-build
   - Rollback if build fails

6. Show summary of cleaned items

## When to Use

Use `/refactor-clean` when:
- Codebase has accumulated dead code
- After removing a feature
- Before major refactoring
- Periodic maintenance

## Example Session

```
User: /refactor-clean

Agent:
# Dead Code Analysis

## Scanning codebase...

### SAFE to Remove (6 items)

1. **Unused Import**
   File: Views/ProfileView.swift:3
   `import Combine` - not used in file

2. **Unused Private Function**
   File: ViewModels/OnboardingViewModel.swift:145
   `private func oldValidation()` - no references

3. **Commented Code Block**
   File: Services/NotificationScheduler.swift:78-92
   15 lines of commented-out code

4. **Unused File**
   File: Views/Legacy/OldHabitView.swift
   No imports found anywhere

### CAUTION (2 items)

5. **Unused Public Function**
   File: Utilities/DateHelpers.swift:34
   `func formatLegacyDate()` - verify not used dynamically

6. **Unused View**
   File: Views/Components/OldButtonStyle.swift
   May be used in SwiftUI previews

### DANGER (0 items)
None found.

---

## Proposed Actions

Remove SAFE items? (yes/no/select)

User: yes

## Removing...

✅ Removed unused import from ProfileView.swift
✅ Removed oldValidation() from OnboardingViewModel.swift
✅ Removed commented code from NotificationScheduler.swift
✅ Deleted OldHabitView.swift

Build status: ✅ SUCCESS

## Summary
- Files deleted: 1
- Functions removed: 1
- Imports cleaned: 1
- Comments removed: 15 lines
- Build: Passing
```

## Important Rules

- **Build after each deletion** - Verify nothing breaks
- **Start with SAFE items** - Leave CAUTION for manual review
- **Never touch DANGER** - These need explicit approval
- **Git commit frequently** - Easy rollback if needed

## Related Agents

This command uses the `refactor-cleaner` agent.

Never delete code without verifying build passes first!
