---
description: Comprehensive security and quality review of uncommitted changes.
---

# Code Review Command

Comprehensive security and quality review of uncommitted changes.

## What This Command Does

1. Get changed files: `git diff --name-only HEAD`

2. For each changed file, check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- Exposed sensitive data
- Missing input validation
- Insecure data storage
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- print() statements in production code
- TODO/FIXME comments
- Force unwrapping without guards

**Best Practices (MEDIUM):**
- Mutation patterns (use immutable instead)
- Missing tests for new code
- Accessibility issues (a11y)
- Memory leaks (strong reference cycles)

3. Generate report with:
   - Severity: CRITICAL, HIGH, MEDIUM, LOW
   - File location and line numbers
   - Issue description
   - Suggested fix

4. Block commit if CRITICAL or HIGH issues found

## When to Use

Use `/code-review` when:
- Before committing changes
- After completing a feature
- Before creating a pull request
- When unsure about code quality

## Example Output

```
# Code Review Report

## CRITICAL Issues (Must Fix)

### 1. Hardcoded API Key
**File:** Services/APIService.swift:45
**Issue:** API key hardcoded in source code
**Fix:** Move to environment variable or Keychain

## HIGH Issues (Should Fix)

### 1. Missing Error Handling
**File:** ViewModels/OnboardingViewModel.swift:78
**Issue:** Force unwrap without guard
**Current:** `let user = auth.currentUser!`
**Fix:** `guard let user = auth.currentUser else { return }`

### 2. Large Function
**File:** Views/MyPathTabView.swift:120-210
**Issue:** Function is 90 lines, should be < 50
**Fix:** Extract into smaller functions

## MEDIUM Issues (Consider Fixing)

### 1. Print Statement
**File:** Services/NotificationScheduler.swift:34
**Issue:** print() in production code
**Fix:** Remove or use proper logging

---
**Summary:**
- CRITICAL: 1
- HIGH: 2
- MEDIUM: 1

⚠️ Fix CRITICAL and HIGH issues before committing!
```

## Related Agents

This command uses the `code-quality-reviewer` agent.

Never approve code with security vulnerabilities!
