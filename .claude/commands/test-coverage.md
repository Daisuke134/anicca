---
description: Analyze test coverage and generate missing tests to reach 80%+ coverage.
---

# Test Coverage Command

Analyze test coverage and generate missing tests.

## What This Command Does

1. Run tests with coverage:
   ```bash
   xcodebuild test -scheme aniccaios -enableCodeCoverage YES
   ```

2. Analyze coverage report

3. Identify files below 80% coverage threshold

4. For each under-covered file:
   - Analyze untested code paths
   - Generate unit tests for functions
   - Generate integration tests for services
   - Generate UI tests for critical flows

5. Verify new tests pass

6. Show before/after coverage metrics

7. Ensure project reaches 80%+ overall coverage

## When to Use

Use `/test-coverage` when:
- Before releasing to App Store
- After completing a feature
- Coverage has dropped below 80%
- Adding tests to legacy code

## Example Session

```
User: /test-coverage

Agent:
# Test Coverage Analysis

## Running tests with coverage...

### Current Coverage: 65%

### Files Below 80% Threshold

| File | Coverage | Gap |
|------|----------|-----|
| OnboardingViewModel.swift | 45% | -35% |
| ProblemNotificationScheduler.swift | 60% | -20% |
| NudgeCardView.swift | 70% | -10% |

---

## Generating Missing Tests

### OnboardingViewModel.swift (45% → 85%)

**Untested paths:**
- selectProblem() when problem already selected
- completeOnboarding() when no problems selected
- requestNotificationPermission() denied case

**Generated tests:**

```swift
func testSelectProblem_togglesWhenAlreadySelected() {
    let vm = OnboardingViewModel()
    vm.selectProblem(.anxiety)

    vm.selectProblem(.anxiety)

    XCTAssertFalse(vm.selectedProblems.contains(.anxiety))
}

func testCompleteOnboarding_failsWithNoProblems() {
    let vm = OnboardingViewModel()

    let result = vm.completeOnboarding()

    XCTAssertFalse(result)
}
```

**Running new tests...**
✅ All tests pass

---

### Summary

| Metric | Before | After |
|--------|--------|-------|
| Overall | 65% | 82% |
| OnboardingViewModel | 45% | 85% |
| ProblemNotificationScheduler | 60% | 88% |
| NudgeCardView | 70% | 80% |

✅ Coverage target (80%) achieved!
```

## Focus Areas

Tests should cover:
- Happy path scenarios
- Error handling
- Edge cases (nil, empty, max values)
- Boundary conditions
- Async operations

## Related Skills

This command uses the `tdd-workflow` skill for test patterns.

Ensure 80%+ coverage before App Store submission!
