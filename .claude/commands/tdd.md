---
description: Enforce test-driven development workflow. Write tests FIRST, then implement minimal code to pass. Ensure 80%+ coverage.
---

# TDD Command

This command invokes the **tdd-guide** agent to enforce test-driven development methodology.

## What This Command Does

1. **Scaffold Interfaces** - Define types/protocols first
2. **Generate Tests First** - Write failing tests (RED)
3. **Implement Minimal Code** - Write just enough to pass (GREEN)
4. **Refactor** - Improve code while keeping tests green (REFACTOR)
5. **Verify Coverage** - Ensure 80%+ test coverage

## When to Use

Use `/tdd` when:
- Implementing new features
- Adding new Views/ViewModels
- Fixing bugs (write test that reproduces bug first)
- Refactoring existing code
- Building critical business logic

## How It Works

The tdd-guide agent will:

1. **Define interfaces** for inputs/outputs
2. **Write tests that will FAIL** (because code doesn't exist yet)
3. **Run tests** and verify they fail for the right reason
4. **Write minimal implementation** to make tests pass
5. **Run tests** and verify they pass
6. **Refactor** code while keeping tests green
7. **Check coverage** and add more tests if below 80%

## TDD Cycle

```
RED → GREEN → REFACTOR → REPEAT

RED:      Write a failing test
GREEN:    Write minimal code to pass
REFACTOR: Improve code, keep tests passing
REPEAT:   Next feature/scenario
```

## Example Usage

```
User: /tdd I need a function to calculate nudge frequency based on user settings

Agent (tdd-guide):
# TDD Session: Nudge Frequency Calculator

## Step 1: Define Interface (SCAFFOLD)

```swift
enum NudgeStrength {
    case gentle, moderate, aggressive
}

func calculateNudgeFrequency(
    for problems: [ProblemType],
    strength: NudgeStrength
) -> TimeInterval {
    fatalError("Not implemented")
}
```

## Step 2: Write Failing Test (RED)

```swift
func testCalculateNudgeFrequency_gentleStrength() {
    let problems: [ProblemType] = [.procrastination]

    let frequency = calculateNudgeFrequency(for: problems, strength: .gentle)

    XCTAssertEqual(frequency, 4 * 3600) // 4 hours
}

func testCalculateNudgeFrequency_aggressiveStrength() {
    let problems: [ProblemType] = [.procrastination]

    let frequency = calculateNudgeFrequency(for: problems, strength: .aggressive)

    XCTAssertEqual(frequency, 1 * 3600) // 1 hour
}
```

## Step 3: Run Tests - Verify FAIL

```bash
xcodebuild test

FAIL: testCalculateNudgeFrequency_gentleStrength
  Fatal error: Not implemented
```

✅ Tests fail as expected. Ready to implement.

## Step 4: Implement (GREEN)

```swift
func calculateNudgeFrequency(
    for problems: [ProblemType],
    strength: NudgeStrength
) -> TimeInterval {
    let baseInterval: TimeInterval = switch strength {
    case .gentle: 4 * 3600
    case .moderate: 2 * 3600
    case .aggressive: 1 * 3600
    }
    return baseInterval
}
```

## Step 5: Run Tests - Verify PASS

```bash
xcodebuild test

PASS: All tests passing
```
```

## TDD Best Practices

**DO:**
- ✅ Write the test FIRST, before any implementation
- ✅ Run tests and verify they FAIL before implementing
- ✅ Write minimal code to make tests pass
- ✅ Refactor only after tests are green
- ✅ Add edge cases and error scenarios
- ✅ Aim for 80%+ coverage

**DON'T:**
- ❌ Write implementation before tests
- ❌ Skip running tests after each change
- ❌ Write too much code at once
- ❌ Ignore failing tests
- ❌ Test implementation details (test behavior)

## Integration with Other Commands

- Use `/plan` first to understand what to build
- Use `/tdd` to implement with tests
- Use `/build-fix` if build errors occur
- Use `/code-review` to review implementation
- Use `/test-coverage` to verify coverage

## Related Agents

This command invokes the `tdd-guide` agent.
