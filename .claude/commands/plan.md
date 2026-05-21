---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

This command invokes the **planner** agent to create a comprehensive implementation plan before writing any code.

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## When to Use

Use `/plan` when:
- Starting a new feature
- Making significant architectural changes
- Working on complex refactoring
- Multiple files/components will be affected
- Requirements are unclear or ambiguous

## How It Works

The planner agent will:

1. **Analyze the request** and restate requirements in clear terms
2. **Break down into phases** with specific, actionable steps
3. **Identify dependencies** between components
4. **Assess risks** and potential blockers
5. **Estimate complexity** (High/Medium/Low)
6. **Present the plan** and WAIT for your explicit confirmation

## Example Usage

```
User: /plan I need to add a new onboarding step for selecting notification time

Agent (planner):
# Implementation Plan: Notification Time Selection Step

## Requirements Restatement
- Add new step in onboarding flow after struggles selection
- User can select preferred notification time (morning/afternoon/evening)
- Save selection to UserDefaults
- Use selection in ProblemNotificationScheduler

## Implementation Phases

### Phase 1: Model Updates
- Add NotificationTimePreference enum (morning, afternoon, evening)
- Add property to OnboardingState
- Update UserDefaults keys

### Phase 2: New View
- Create NotificationTimeStepView
- Add time selection UI with icons
- Connect to OnboardingViewModel

### Phase 3: Flow Integration
- Update OnboardingStep enum
- Add navigation logic
- Update progress indicator

### Phase 4: Scheduler Integration
- Update ProblemNotificationScheduler to use time preference
- Calculate actual hours based on preference

## Dependencies
- OnboardingViewModel
- ProblemNotificationScheduler
- UserDefaults storage

## Risks
- MEDIUM: Breaking existing onboarding flow
- LOW: Migration for existing users (default to morning)

## Estimated Complexity: LOW
- Model: 30 min
- View: 1-2 hours
- Integration: 30 min

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Important Notes

**CRITICAL**: The planner agent will **NOT** write any code until you explicitly confirm the plan with "yes" or "proceed" or similar affirmative response.

If you want changes, respond with:
- "modify: [your changes]"
- "different approach: [alternative]"
- "skip phase 2 and do phase 3 first"

## Integration with Other Commands

After planning:
- Use `/tdd` to implement with test-driven development
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed implementation

## Related Agents

This command invokes the `planner` agent.
