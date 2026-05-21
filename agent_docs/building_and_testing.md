# Building & Testing Reference

## iOS Build

| Command | Purpose |
|---------|---------|
| `cd aniccaios && fastlane test` | Unit + Integration tests |
| `cd aniccaios && fastlane build_for_device` | Device install |
| `cd aniccaios && fastlane build_for_simulator` | Simulator launch |
| `cd aniccaios && fastlane build` | App Store IPA |
| `cd aniccaios && fastlane full_release` | Build + Upload + Submit |

**xcodebuild 直接実行禁止。** 必ず Fastlane 経由。

**非インタラクティブ環境変数:**
```bash
FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1
```

## API

```bash
cd apps/api && npm test        # Jest tests
cd apps/api && npm run dev     # Local dev server
cd apps/api && railway up --environment staging  # Manual deploy
```

## E2E (Maestro)

MCP必須（CLI禁止、CI/CDのみ許可）。

```
mcp__maestro__inspect_view_hierarchy → run_flow → take_screenshot → run_flow_files
```

## Test Pyramid

| Layer | Ratio | Tool |
|-------|-------|------|
| Unit | 70% | Swift Testing / XCTest |
| Integration | 20% | XCTest + Mock |
| E2E | 10% | Maestro |

## TDD Cycle

RED → GREEN → REFACTOR → REPEAT. Coverage target: 80%+.
