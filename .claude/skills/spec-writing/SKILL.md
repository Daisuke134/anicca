---
name: spec-writing
description: Defines how to write feature specifications with the core 6 sections, test matrix, E2E judgment, and anti-ambiguity rules. Use when writing specs, creating feature plans, defining acceptance criteria, or structuring task breakdowns.
---

# Spec Writing Rules

## Ambiguity Ban

| Forbidden | Replace With |
|-----------|-------------|
| 「任意」「optional」 | MUST。やらないなら書かない |
| 「中期」「将来」 | 今やる。やらないなら削除 |
| 「検討する」 | 決定して書く |
| 「推奨」 | MUST か DO NOT |

## Spec = What & Why (not How)

| Write | Don't Write |
|-------|-------------|
| What to solve, Why needed | Function bodies |
| Acceptance criteria | Full test code |
| Data model / API contract | Full Maestro YAML |
| Function signatures | Detailed algorithms |
| Test matrix | Copy-paste patches |

## Core 6 Sections (Required)

| # | Section | Content |
|---|---------|---------|
| 1 | Overview (What & Why) | Problem and motivation |
| 2 | Acceptance Criteria | Testable success criteria |
| 3 | As-Is / To-Be | Current → changed design |
| 4 | Test Matrix | Test name per To-Be item |
| 5 | Boundaries | Out of scope |
| 6 | Execution Steps | Build and test commands |

## E2E Judgment (Always Required)

```markdown
| Item | Value |
|------|-------|
| UI変更 | あり / なし |
| 結論 | Maestro: 必要 / 不要（理由: ○○） |
```

## Test Matrix Example

| # | To-Be | Test Name | Cover |
|---|-------|-----------|-------|
| 1 | Thompson Sampling | `test_selectByThompsonSampling()` | OK |
| 2 | 2日連続無視→シフト | `test_consecutive_shift()` | NG |

**全To-BeにOK必須。** NG = Spec不完全。

## User GUI Tasks (Optional: External Services)

Specにユーザー手作業を明記: 実装前（セットアップ）、実装中（確認）、実装後（検証）。
