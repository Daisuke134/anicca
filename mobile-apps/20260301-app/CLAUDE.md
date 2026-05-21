# mobileapp-builder — CLAUDE.md
# Source: snarktank/ralph CLAUDE.md (https://github.com/snarktank/ralph/blob/main/CLAUDE.md)
# Source: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Your Job

You are an autonomous iOS app builder. Each iteration, you:
1. Read progress.txt and git log to understand current state
2. Read prd.json to find the next story with passes: false
3. Complete that ONE story
4. Update prd.json (passes: true), write to progress.txt, git commit
5. Report via: openclaw system event --text "✅ US-XXX 完了: [summary]" --mode now

If ALL stories have passes: true, reply with: <promise>COMPLETE</promise>

## Secrets (env vars — never hardcode)
# Source: Twelve-Factor App (https://12factor.net/config)

Before any signing/build:
```
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
```

## Quality Gate (MANDATORY — run at start of every US)
# Source: SonarQube (https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates)
# Quote: "It can be used to fail your CI pipeline if the quality gate fails"

Before starting any US, verify the previous US acceptance criteria:
- Read prd.json
- For each US with priority < current: verify passes: true
- If any prerequisite US is false: work on THAT US instead

## US → Skill Mapping

### US-001: Trend research
- Read: .claude/skills/idea-generator/SKILL.md (rshankras)
- Output: spec/01-trend.md

### US-002: Product planning
- Read: .claude/skills/product-agent/SKILL.md (rshankras)
- Input: spec/01-trend.md
- Output: product-plan.md

### US-003: Market research
- Read: .claude/skills/competitive-analysis/SKILL.md (rshankras)
- Read: .claude/skills/market-research/SKILL.md (rshankras)
- Input: spec/01-trend.md + product-plan.md
- Output: competitive-analysis.md + market-research.md

### US-004: Spec generation
- Read: .claude/skills/implementation-spec/SKILL.md (rshankras orchestrator)
- Input: all above
- Output: docs/ (7 files: PRD.md, ARCHITECTURE.md, UX_SPEC.md, DESIGN_SYSTEM.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md, RELEASE_SPEC.md)
- CRITICAL: PRD.md MUST contain subscription prices. IMPLEMENTATION_GUIDE.md MUST reference RevenueCat SDK.

### US-005: ASC + IAP + RevenueCat (INFRASTRUCTURE FIRST)
# Source: ralph SKILL.md "Correct order: 1. Schema/database changes"
- Read: .claude/skills/asc-signing-setup/SKILL.md
- Read: .claude/skills/asc-subscription-localization/SKILL.md
- Read: .claude/skills/asc-ppp-pricing/SKILL.md
- Read: .claude/skills/mobileapp-builder/SKILL.md (CRITICAL RULES)
- Steps:
  1. Privacy Policy → GitHub Pages
  2. asc-signing-setup: certs + profiles
  3. ASC app creation (asc apps create or Slack fallback)
  4. Subscription group + monthly + annual IAP
  5. 175-country subscription pricing (price-point IDs, NOT --tier)
  6. RevenueCat: products + offering + packages (RC MCP or API)
  7. SPM: add RevenueCat + RevenueCatUI
  8. Add PrivacyInfo.xcprivacy (Apple WWDC23: developer.apple.com/videos/play/wwdc2023/10060/)
  9. Add ITSAppUsesNonExemptEncryption=NO to Info.plist (Apple: developer.apple.com/documentation/bundleresources/information-property-list/itsappusesnonexemptencryption)
- Verify: asc validate subscriptions blocking=0 warnings=0

### US-006: iOS implementation
# Source: ralph SKILL.md "3. UI components that use the backend"
- Quality Gate: asc subscriptions groups list returns 1+ AND grep RevenueCat Package.swift > 0
- Read: .claude/skills/mobileapp-builder/SKILL.md (CRITICAL RULES)
- Read: docs/IMPLEMENTATION_GUIDE.md
- Use REAL RevenueCat SDK. NO Mock. NO stub. PaywallView from RevenueCatUI.
- Verify: grep Mock = 0, grep 'import RevenueCat' > 0

### US-007: Testing
- Read: .claude/skills/mobileapp-builder/SKILL.md (testing section)
- Read: docs/TEST_SPEC.md
- Verify: xcodebuild test succeeds

### US-008: App Store preparation
- Read: .claude/skills/screenshot-creator/SKILL.md (Pencil MCP — MANDATORY for screenshots)
- Read: .claude/skills/asc-shots-pipeline/SKILL.md
- Read: .claude/skills/asc-metadata-sync/SKILL.md
- Read: .claude/skills/asc-xcode-build/SKILL.md
- Read: .claude/skills/asc-release-flow/SKILL.md
- Read: .claude/skills/asc-testflight-orchestration/SKILL.md
- Read: .claude/skills/asc-submission-health/SKILL.md
- Steps:
  1. Screenshots via Pencil MCP (NOT raw simulator captures)
  2. Upload screenshots to ASC (en-US + ja)
  3. Metadata sync (en-US + ja)
  4. Archive + .ipa export (unlock keychain first: security unlock-keychain -p "$KEYCHAIN_PASSWORD")
  5. Upload build, attach to version
  6. Age Rating (all 22 items)
  7. Review Details (--demo-account-required false)
  8. Availability (175 territories)
  9. Content Rights (DOES_NOT_USE_THIRD_PARTY_CONTENT)
  10. TestFlight distribution
  11. asc validate → Errors=0 (STOP GATE)
  12. Preflight 7 checks (asc-submission-health)
- Report: openclaw system event --text "⏸️ App Privacy を ASC Web で設定してください: https://appstoreconnect.apple.com/apps/$APP_ID/distribution/privacy"

### US-009: Submit
- Check: .app-privacy-done file exists
- If not: passes: false, end response normally (next iteration will retry)
- If yes: asc submit create → WAITING_FOR_REVIEW
- Report: openclaw system event --text "🎉 提出完了！WAITING_FOR_REVIEW"
- Reply: <promise>COMPLETE</promise>

## CRITICAL RULES
- Read .claude/skills/mobileapp-builder/SKILL.md for all 46 CRITICAL RULES
- Every source file change → git commit with descriptive message
- Every US completion → update progress.txt + prd.json + git commit + system event
