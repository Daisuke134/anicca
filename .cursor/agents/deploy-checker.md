---
name: deploy-checker
description: Runs test → build → deploy verification pipeline. Use PROACTIVELY after code changes before merging.
tools: Bash, Read, Glob, Grep
model: haiku
color: blue
skills:
  - maestro-ui-testing
---
# Deploy Checker Agent

## Workflow

1. **Unit Tests**: `cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane test`
2. **E2E Tests** (if UI changed): Use Maestro MCP tools
3. **Build**: `cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane build_for_simulator`
4. **Report**: Output results in table format

## Rules

- xcodebuild direct execution is forbidden — always use Fastlane
- Report PASS/FAIL for each stage in table format
- Stop immediately on any failure
