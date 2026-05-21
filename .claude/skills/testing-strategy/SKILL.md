---
name: testing-strategy
description: Defines the testing pyramid, TDD cycle, Swift Testing patterns, Maestro E2E rules, and test execution commands for the Anicca iOS project. Use when writing tests, setting up TDD, choosing between unit/integration/E2E, or troubleshooting test failures.
---

# Testing Strategy & Requirements

## Test Pyramid

| Layer | Ratio | Speed | Tool |
|-------|-------|-------|------|
| Unit | 70% | ms | Swift Testing / XCTest |
| Integration | 20% | sec | XCTest + Mock |
| E2E | 10% | min | Maestro |

**Coverage target: 80%+**

## TDD Cycle (Mandatory)

RED (failing test) → GREEN (minimal code to pass) → REFACTOR (clean up) → REPEAT

## Test Best Practices

**AAA Pattern** (Arrange-Act-Assert) required for all tests. Target: **10 lines or less** per test.

**Swift Testing (Xcode 16+, recommended):**
```swift
#expect(result == expected)

@Test(arguments: ["staying_up_late", "cant_wake_up"])
func testProblemTypeContent(type: String) {
    let content = NudgeContent.forProblemType(type)
    #expect(content != nil)
}
```

**FIRST:** Fast, Isolated, Repeatable, Self-validating, Thorough

## Test Locations

| Type | Path | Convention |
|------|------|-----------|
| Unit | `aniccaios/aniccaiosTests/` | `*Tests.swift` |
| Integration | `aniccaios/aniccaiosTests/Integration/` | `*IntegrationTests.swift` |
| E2E | `maestro/` | `NN-description.yaml` |

## Test Commands

**xcodebuild 直接実行禁止。Fastlane 必須。**

```bash
cd aniccaios && fastlane test          # Unit + Integration
maestro test maestro/                   # E2E
```

## TDD vs Maestro

| TDD対象 | Maestro対象 |
|---------|------------|
| アルゴリズム、データ変換、API処理 | 画面遷移、ボタンタップ、フルユーザーフロー |
| UI変更なし → Maestro不要 | 新画面/新ボタン → Maestro必須 |

## Maestro Rules

| ルール | 詳細 |
|--------|------|
| エージェントはMCP必須 | CLI禁止（CI/CDのみ） |
| 1 Flow = 1 Scenario | YAML詰め込み禁止 |
| Accessibility ID | `#if DEBUG` ボタン禁止 |
| 日本語テキスト | View Hierarchy で実テキスト確認必須 |

```
inspect_view_hierarchy → run_flow → take_screenshot → YAML保存 → run_flow_files
```

## Device Testing

Unit + Maestro PASS後 → `fastlane build_for_device`（未接続→`build_for_simulator`）
TestFlightは最終確認用。開発中はbuild_for_device/simulator。
