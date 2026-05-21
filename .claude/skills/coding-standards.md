---
name: coding-standards
description: Universal coding standards, best practices, and patterns for Swift, SwiftUI, and general development.
---

# Coding Standards & Best Practices

Universal coding standards applicable across all projects.

## Code Quality Principles

### 1. Readability First
- Code is read more than written
- Clear variable and function names
- Self-documenting code preferred over comments
- Consistent formatting

### 2. KISS (Keep It Simple, Stupid)
- Simplest solution that works
- Avoid over-engineering
- No premature optimization
- Easy to understand > clever code

### 3. DRY (Don't Repeat Yourself)
- Extract common logic into functions
- Create reusable components
- Share utilities across modules
- Avoid copy-paste programming

### 4. YAGNI (You Aren't Gonna Need It)
- Don't build features before they're needed
- Avoid speculative generality
- Add complexity only when required
- Start simple, refactor when needed

## Swift/SwiftUI Standards

### Variable Naming

```swift
// GOOD: Descriptive names
let userSelectedProblems: [ProblemType] = []
let isNotificationEnabled = true
let totalSessionCount = 10

// BAD: Unclear names
let probs = []
let flag = true
let x = 10
```

### Function Naming

```swift
// GOOD: Verb-noun pattern
func fetchUserData(for userId: String) async { }
func calculateSimilarity(between a: [Float], and b: [Float]) -> Float { }
func isValidEmail(_ email: String) -> Bool { }

// BAD: Unclear or noun-only
func user(id: String) { }
func similarity(a: [Float], b: [Float]) { }
func email(_ e: String) { }
```

### Immutability Pattern (CRITICAL)

```swift
// ALWAYS prefer let over var
let problems = user.selectedProblems

// Use structs for value types
struct UserSettings {
    let notificationsEnabled: Bool
    let nudgeStrength: NudgeStrength
}

// Return new values instead of mutating
func updateSettings(_ settings: UserSettings, notifications: Bool) -> UserSettings {
    return UserSettings(
        notificationsEnabled: notifications,
        nudgeStrength: settings.nudgeStrength
    )
}
```

### Error Handling

```swift
// GOOD: Comprehensive error handling
func fetchData() async throws -> Data {
    do {
        let response = try await URLSession.shared.data(from: url)
        return response.0
    } catch {
        print("Fetch failed: \(error)")
        throw AppError.networkError(error)
    }
}

// Use Result type for synchronous errors
func parseJSON(_ data: Data) -> Result<User, ParseError> {
    // Implementation
}
```

### Optional Handling

```swift
// GOOD: Safe unwrapping
if let userName = user.name {
    displayName(userName)
}

// Guard for early exit
guard let userId = auth.currentUserId else {
    return
}

// Nil coalescing for defaults
let displayName = user.name ?? "Anonymous"

// Optional chaining
let uppercased = user.name?.uppercased()

// AVOID: Force unwrapping (unless certain)
let name = user.name! // Dangerous
```

## SwiftUI Best Practices

### View Structure

```swift
// GOOD: Small, focused views
struct ProblemCardView: View {
    let problem: ProblemType
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack {
                Image(systemName: problem.icon)
                Text(problem.displayName)
            }
        }
        .background(isSelected ? Color.blue : Color.gray)
    }
}

// BAD: Massive view with everything
struct MegaView: View {
    // 500 lines of code...
}
```

### State Management

```swift
// Use appropriate property wrappers
@State private var isLoading = false        // Local UI state
@Binding var selectedProblem: ProblemType   // Parent-owned state
@ObservedObject var viewModel: ViewModel    // External observable
@EnvironmentObject var settings: Settings   // Injected dependency

// Functional updates for state based on previous state
@State private var count = 0

Button("Increment") {
    count += 1 // Simple case is OK
}
```

### Async/Await

```swift
// GOOD: Proper async handling
func loadData() async {
    isLoading = true
    defer { isLoading = false }

    do {
        let data = try await api.fetchData()
        self.data = data
    } catch {
        self.error = error
    }
}

// Use Task for launching async work from sync context
Button("Load") {
    Task {
        await loadData()
    }
}
```

## File Organization

### Project Structure

```
aniccaios/
├── App/                    # App entry point
├── Models/                 # Data models
├── Views/                  # SwiftUI views
│   ├── Onboarding/        # Feature-based grouping
│   ├── MyPath/
│   └── Components/        # Reusable UI components
├── ViewModels/            # View models
├── Services/              # API, notifications, etc.
├── Utilities/             # Helpers and extensions
└── Resources/             # Assets, localization
```

### File Size Guidelines
- 200-400 lines typical
- 800 lines maximum
- Extract components when files grow large

## Comments & Documentation

### When to Comment

```swift
// GOOD: Explain WHY, not WHAT
// Use exponential backoff to avoid overwhelming the API during outages
let delay = min(1000 * pow(2.0, Double(retryCount)), 30000)

// Deliberately using force unwrap - value is guaranteed by storyboard
let label = view.viewWithTag(1) as! UILabel

// BAD: Stating the obvious
// Increment counter by 1
count += 1

// Set name to user's name
name = user.name
```

### Documentation Comments

```swift
/// Schedules notifications for the user's selected problems.
///
/// - Parameters:
///   - problems: Array of problem types to schedule notifications for
///   - strength: How aggressive the notification frequency should be
/// - Returns: Number of notifications scheduled
/// - Throws: `NotificationError` if permissions not granted
///
/// - Note: Call this after user completes onboarding
func scheduleNotifications(
    for problems: [ProblemType],
    strength: NudgeStrength
) throws -> Int {
    // Implementation
}
```

## Code Smell Detection

Watch for these anti-patterns:

### 1. Long Functions
```swift
// BAD: Function > 50 lines
func processEverything() {
    // 100 lines of code
}

// GOOD: Split into smaller functions
func processData() {
    let validated = validateData()
    let transformed = transformData(validated)
    saveData(transformed)
}
```

### 2. Deep Nesting
```swift
// BAD: 5+ levels of nesting
if user != nil {
    if user.isAdmin {
        if market != nil {
            if market.isActive {
                if hasPermission {
                    // Do something
                }
            }
        }
    }
}

// GOOD: Early returns
guard let user = user else { return }
guard user.isAdmin else { return }
guard let market = market else { return }
guard market.isActive else { return }
guard hasPermission else { return }

// Do something
```

### 3. Magic Numbers
```swift
// BAD: Unexplained numbers
if retryCount > 3 { }
DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { }

// GOOD: Named constants
private let maxRetries = 3
private let debounceDelay: TimeInterval = 0.5

if retryCount > maxRetries { }
DispatchQueue.main.asyncAfter(deadline: .now() + debounceDelay) { }
```

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No print statements in production code
- [ ] No hardcoded values
- [ ] Follows existing patterns in codebase

**Remember**: Code quality is not negotiable. Clear, maintainable code enables rapid development and confident refactoring.
