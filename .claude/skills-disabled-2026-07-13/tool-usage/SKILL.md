---
name: tool-usage
description: Defines MCP tool priorities, skill search order, Firecrawl/Serena/Maestro usage rules, Fastlane lanes, and the Layer 2 skill-auto-apply mapping for Anicca development. Use when choosing tools, running builds, executing tests, or looking up which skill/MCP to use.
---

# Tool & MCP Usage Rules

## Skill Search Priority

| Order | Tool | Command |
|-------|------|---------|
| 1st | `find-skills` | `npx skills find "<query>"` |
| 2nd | `clawhub` | `clawhub search "<query>"` (fallback only) |

## Priority Tools

| Task | Use | Forbidden |
|------|-----|-----------|
| Web/URL | Firecrawl: `/opt/homebrew/bin/firecrawl scrape <url> markdown` | WebSearch, WebFetch |
| Code search/edit | Serena MCP: `mcp__serena__*` | Grep/Read (when Serena works) |

## MCP Priority Table

| Task | MCP |
|------|-----|
| Docs search | `mcp__context7__query-docs` |
| Apple docs | `mcp__apple-docs__*` |
| iOS E2E | `mcp__maestro__*` (CLI禁止) |
| RevenueCat | `mcp__revenuecat__*` |
| App Store Connect | `mcp__app-store-connect__*` |

## Maestro MCP (Absolute)

MCP必須。CLI禁止（CI/CDのみ）。違反→やり直し。

```
mcp__maestro__list_devices / inspect_view_hierarchy / run_flow / take_screenshot / run_flow_files
```

## Serena MCP

| Task | Tool |
|------|------|
| File search | `mcp__serena__find_file` |
| Pattern search | `mcp__serena__search_for_pattern` |
| Symbol search | `mcp__serena__find_symbol` |
| Symbol edit | `mcp__serena__replace_symbol_body` |
| Memory | `mcp__serena__read_memory` / `write_memory` |

## Skill Auto-Apply (Layer 2)

| Category | Skill | Trigger |
|----------|-------|---------|
| Dev | `tdd-workflow` | テスト作成 |
| Dev | `codex-review` | Spec更新後、5+ファイル実装後、コミット前 |
| Dev | `decisive-agent` | 技術判断 |
| Dev | `ralph-autonomous-dev` | 「終わるまでやれ」 |
| Dev | `maestro-ui-testing` | E2Eテスト |
| UI | `ui-skills` | SwiftUI/Web UI |
| UI | `canvas-design` | ビジュアルアセット |
| Marketing | `recursive-improver` | コピー改善 |
| Marketing | `aso-growth` | ASO/ASA |
| Content | `content-creator` | SNS投稿 |
| Content | `build-in-public` | X投稿 |

## Commands

`/plan` `/tdd` `/code-review` `/build-fix` `/refactor-clean` `/test-coverage` `/codex-review`

## Fastlane (Absolute: xcodebuild禁止)

| Lane | Purpose |
|------|---------|
| `test` | Unit/Integration |
| `build_for_device` | 実機 |
| `build_for_simulator` | シミュレータ |
| `build` | App Store IPA |
| `full_release` | build + upload + 審査提出 |
| `set_version version:X.Y.Z` | バージョン更新 |

**非インタラクティブ環境変数必須:**
```bash
FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane <lane>
```
