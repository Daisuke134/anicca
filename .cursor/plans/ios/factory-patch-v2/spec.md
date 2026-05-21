# Factory Patch v2 — US-008 Screenshot & Release Pipeline Overhaul

**Date:** 2026-03-08
**Status:** DRAFT — Dais review → CC review → apply
**Root cause:** FrostDip US-008a failed 5x (32M tokens wasted) due to Gate 3 circular dependency + 2-simulator overhead

---

## Problem Summary

FrostDip (20260307-223953-app) stopped at 14/20 US, $7.68 spent. US-008a consumed 37.5% of total tokens (32M) across 4 failed attempts. Root causes:

1. **Gate 3 circular dependency**: validate.sh checks MISSING_METADATA (requires Review Screenshots) but gates on `US-005b` instead of `US-008a`. CC uploads screenshots → validate resets passes:true → false → infinite loop.
2. **2-simulator overhead**: 6.1" + 6.5" = 16 screenshots. Apple only requires 6.9" (others auto-scale).
3. **UserDefaults key mismatch**: Recipe says `hasCompletedOnboarding`, app uses `has_completed_onboarding`. CC wastes iterations guessing.
4. **axe describe-ui empty tree**: SwiftUI a11y tree delayed on boot. No fallback documented.
5. **Path errors**: `find build/` misses nested paths, `$HOME` empty in CC env, `defaults delete` error misinterpreted.

---

## Tested ASC CLI Commands (v0.37.2)

| Command | Status | Evidence |
|---------|--------|----------|
| `asc screenshots upload --device-type IPHONE_69` | ✅ Works | 1320x2868 accepted. Same dims as IPHONE_67. |
| `asc release run --dry-run` | ✅ Works | 5-step pipeline: ensure_version → apply_metadata → attach_build → validate → submit. Returns structured JSON with per-step status. |
| `asc localizations upload --path ./dir/` | ✅ Works | `.strings` format. Both `--type version` and `--type app-info`. `--dry-run` supported. |
| `asc metadata pull --app APP --version VER --dir ./meta/` | ✅ Works | Outputs `app-info/{locale}.json`. Used by `asc release run --metadata-dir`. |
| `asc screenshots run --plan` | ❌ Skip | Experimental. AXe dependency (empty tree problem unsolved). |
| `asc workflow` | ❌ Skip | Not stable enough per Dais. |

---

## Patch List

### A. validate.sh — Gate 3 condition fix ✅ ALREADY APPLIED (commit aacd8c9e)

**File:** `.claude/skills/mobileapp-builder/validate.sh`

```diff
- if [ "$(us_passes US-005b)" = "true" ] && [ -n "$APP_ID" ]; then
+ if [ "$(us_passes US-008a)" = "true" ] && [ -n "$APP_ID" ]; then
```

**Why:** Gate 3 checks MISSING_METADATA which requires Review Screenshots (uploaded in US-008a Step 1h). Running before US-008a guarantees failure.

---

### B. us-008-release.md — Device table: 6.9" only

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** "使用デバイス（固定）" table (~line 116-127)

```diff
- | iPhone 17 Pro | 1206x2622 | IPHONE_61 | 常に必須（ベース） |
- | iPhone 14 Plus | 1284x2778 | IPHONE_65 | 6.9" 未提供時に必須（= 常に必須） |
+ | iPhone 16 Pro Max | 1320x2868 | IPHONE_69 | 常に必須（6.9" 提出で全サイズ自動スケール） |
```

**Source:** Apple ASC Help — Screenshot specifications
https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
- 「6.5" Display — Required if screenshots for 6.9" display aren't provided」
- 「If screenshots with the accepted sizes aren't provided, scaled screenshots for 6.9" displays are used」

**Verified:** `asc screenshots upload --device-type IPHONE_69` accepts 1320x2868 (tested 2026-03-08).

---

### C. us-008-release.md — Step 1a: Single 6.9" simulator

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Step 1a (~line 139-175)

Replace UDID_61 + UDID_65 setup with:

```bash
# 6.9" シミュレータのみ使用（Apple が 6.5"/6.3"/6.1" を自動スケール）
UDID_69=$(xcrun simctl list devices available | grep "iPhone16ProMax-69\|iPhone 16 Pro Max\|iPhone 17 Pro Max" | head -1 | grep -oE '[A-F0-9-]{36}')
if [ -z "$UDID_69" ]; then
  RUNTIME=$(xcrun simctl list runtimes | grep "iOS" | tail -1 | grep -oE 'com.apple[^ ]+')
  UDID_69=$(xcrun simctl create "iPhone16ProMax-69" "com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro-Max" "$RUNTIME")
fi
xcrun simctl boot $UDID_69 2>/dev/null || true
```

Replace build + install:
```bash
APP_PATH=$(find . -path "*/Debug-iphonesimulator/*.app" -not -path "*/DerivedData/SourcePackages/*" | head -1)
[ -n "$APP_PATH" ] || { echo "FAIL: .app not found after build"; exit 1; }
xcrun simctl install $UDID_69 "$APP_PATH"
```

**Pre-created simulator:** `iPhone16ProMax-69` (UDID: `1D9F5D85-7C93-447F-A62E-1DA07A490E93`, 1320x2868 verified).

---

### D. us-008-release.md — UserDefaults key detection

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** All `defaults write ... hasCompletedOnboarding` instances (~line 226, and in 1c, 1h)

Replace hardcoded key with grep-based detection:

```bash
# ⚠️ MANDATORY: UserDefaults キー名はアプリのコードから確認する
# hasCompletedOnboarding / has_completed_onboarding / isOnboardingComplete 等はアプリごとに異なる
ONBOARDING_KEY=$(grep -rh "completedOnboarding\|isOnboarding\|onboardingDone\|hasCompleted" \
  --include="*.swift" . 2>/dev/null | head -1 | grep -oE '"[^"]*[Oo]nboard[^"]*"' | tr -d '"' | head -1)
[ -z "$ONBOARDING_KEY" ] && ONBOARDING_KEY="hasCompletedOnboarding"  # fallback
xcrun simctl spawn "$UDID_69" defaults write "$BUNDLE_ID" "$ONBOARDING_KEY" -bool true
```

**Why:** FrostDip used `has_completed_onboarding` (snake_case) but recipe assumed `hasCompletedOnboarding` (camelCase). CC wasted 3 iterations guessing.

---

### E. us-008-release.md — Maestro absolute path

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Add near top of Step 1b

```bash
# Maestro パス（$HOME が空になる場合があるため絶対パス指定）
MAESTRO="/Users/anicca/.maestro/bin/maestro"
[ -x "$MAESTRO" ] || MAESTRO=$(which maestro 2>/dev/null || echo "maestro")
```

---

### F. us-008-release.md — defaults delete error clarification

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** All `defaults delete` instances

Add comment above each:
```bash
# ⚠️ "Domain (...) not found" / "Invalid device" は正常（キーが存在しない = 期待通り）
# エラーではない。リトライ不要。
xcrun simctl spawn "$UDID_69" defaults delete "$BUNDLE_ID" 2>/dev/null || true
```

---

### G. us-008-release.md — find path fix

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Step 1a app path resolution (~line 172)

```diff
- APP_PATH=$(find build/ -name "*.app" -path "*/Debug-iphonesimulator/*" | head -1)
+ APP_PATH=$(find . -path "*/Debug-iphonesimulator/*.app" -not -path "*/DerivedData/SourcePackages/*" | head -1)
+ [ -n "$APP_PATH" ] || { echo "FAIL: .app not found after build"; exit 1; }
```

**Why:** xcodebuild with `-derivedDataPath build/` puts .app at `build/Build/Products/Debug-iphonesimulator/`. The old `find build/` works but is fragile.

---

### H. us-008-release.md — Upload: IPHONE_69 only

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Step 1f2 upload section (~line 568-598)

Replace 4 upload commands (IPHONE_61 + IPHONE_65 × 2 locales) with 2:

```bash
# 6.9" のみアップロード（Apple が 6.5"/6.3"/6.1" を自動スケール）
asc screenshots upload \
  --version-localization "$EN_LOC_ID" \
  --path "./screenshots/raw-69/en-US" \
  --device-type "IPHONE_69"

asc screenshots upload \
  --version-localization "$JA_LOC_ID" \
  --path "./screenshots/raw-69/ja" \
  --device-type "IPHONE_69"
```

**Verified:** `asc screenshots upload --device-type IPHONE_69` accepts 1320x2868 (tested 2026-03-08).

---

### I. us-008-release.md — Delete sections 1b2, 1c2, 1b3, 1c3

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`

Delete entirely:
- **1b2**: en-US 6.5" capture (~50 lines)
- **1c2**: ja 6.5" capture (~30 lines)
- **1b3**: en-US iPad capture (~40 lines)
- **1c3**: ja iPad capture (~40 lines)

**Total: ~160 lines removed.**

iPad is unnecessary (`TARGETED_DEVICE_FAMILY: "1"` = iPhone only). 6.5" is unnecessary (6.9" auto-scales).

Screenshot directories change:
```diff
- screenshots/raw/en-US/      (6.1")
- screenshots/raw/ja/         (6.1")
- screenshots/raw-65/en-US/   (6.5")
- screenshots/raw-65/ja/      (6.5")
+ screenshots/raw-69/en-US/   (6.9")
+ screenshots/raw-69/ja/      (6.9")
```

---

### J. us-008-release.md — Step 2 Metadata: use asc localizations upload

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Step 2 (~line 700-720)

Replace 4× `asc localizations update` calls with:

```bash
# .strings ファイル生成（CC が PRD から内容を生成）
mkdir -p metadata/version metadata/app-info

cat > metadata/app-info/en-US.strings << 'STREOF'
"name" = "<APP_NAME>";
"subtitle" = "<SUBTITLE>";
"privacyPolicyUrl" = "https://aniccafactory.com/privacy";
STREOF

cat > metadata/app-info/ja.strings << 'STREOF'
"name" = "<APP_NAME_JA>";
"subtitle" = "<SUBTITLE_JA>";
"privacyPolicyUrl" = "https://aniccafactory.com/privacy";
STREOF

cat > metadata/version/en-US.strings << 'STREOF'
"description" = "<DESCRIPTION>";
"keywords" = "<KEYWORDS>";
"supportUrl" = "https://aniccafactory.com/support";
"whatsNew" = "Initial release";
STREOF

cat > metadata/version/ja.strings << 'STREOF'
"description" = "<DESCRIPTION_JA>";
"keywords" = "<KEYWORDS_JA>";
"supportUrl" = "https://aniccafactory.com/support";
"whatsNew" = "初回リリース";
STREOF

# 一括アップロード（2コマンドで全ロケール完了）
asc localizations upload --app "$APP_ID" --type app-info --path metadata/app-info/
asc localizations upload --version "$VERSION_ID" --path metadata/version/
```

**Verified:** `asc localizations upload --dry-run` works for both types (tested 2026-03-08).

---

### K. us-008-release.md — Step 8+9: asc release run

**File:** `.claude/skills/mobileapp-builder/references/us-008-release.md`
**Location:** Step 8-9 (~line 840-890)

Add `asc release run` as the submit step (after all prerequisite fields are set):

```bash
# Prerequisites (must be done BEFORE asc release run):
# - Copyright: asc versions update --version-id $VER --copyright "2026 Daisuke Kobayashi"
# - Age Rating: asc age-rating set ...
# - Review Details: asc review details-create --app $APP_ID --version-id $VER --demo-account-required false
# - Category: asc categories set --app-info $APP_INFO_ID --primary HEALTH_AND_FITNESS
# - Availability: asc availability set --app $APP_ID --territories ALL
# - Encryption: asc encryption set ... --uses-non-exempt-encryption false

# metadata-dir for asc release run (JSON format, NOT .strings)
asc metadata pull --app "$APP_ID" --version "1.0" --dir metadata/release/

# Release pipeline (version + metadata + attach build + validate + submit)
asc release run \
  --app "$APP_ID" \
  --version "1.0" \
  --build "$BUILD_ID" \
  --metadata-dir "metadata/release/" \
  --confirm

# If --confirm fails, check with --dry-run first:
# asc release run --app "$APP_ID" --version "1.0" --build "$BUILD_ID" --metadata-dir "metadata/release/" --dry-run --pretty
```

**Verified:** `asc release run --dry-run` returns structured JSON with step-level status (tested 2026-03-08).

**Note:** `asc release run` does NOT handle: copyright, age rating, review details, category, availability, pricing, encryption. These must be set before calling `asc release run`.

---

### L. prd.json — No change (deferred)

US-008b/c/d/e consolidation depends on `asc release run` covering enough steps. Keep existing 20+1 US structure. Revisit after first successful build with patches.

---

### M. CLAUDE.md — Add ASC skill references

**File:** `.claude/skills/mobileapp-builder/CLAUDE.md`

Add to references section:
```markdown
- US-008a screenshots: read `.agents/skills/asc-shots-pipeline/SKILL.md` for pipeline patterns
- US-008b metadata: read `.agents/skills/asc-metadata-sync/SKILL.md` for sync patterns
- US-008e release: read `.agents/skills/asc-release-flow/SKILL.md` for release flow
- CLI usage: read `.agents/skills/asc-cli-usage/SKILL.md` for flags/output/auth guidance
```

---

### N. us-007-testing.md — Maestro rules ✅ ALREADY APPLIED (commit aacd8c9e)

No change needed.

---

## Screenshot Flow: Before vs After

### Before (FrostDip — 32M tokens, 4 failures)

```
boot 6.1" + 6.5" simulators
build + install on BOTH
en-US: 4 screens on 6.1" → raw/en-US       ← 4 captures
en-US: 4 screens on 6.5" → raw-65/en-US     ← 4 captures
ja:    4 screens on 6.1" → raw/ja            ← 4 captures
ja:    4 screens on 6.5" → raw-65/ja         ← 4 captures
upload: IPHONE_61 en + ja                    ← 2 uploads
upload: IPHONE_65 en + ja                    ← 2 uploads
paywall review screenshot                    ← 1 capture
= 17 captures + 4 uploads
= validate.sh Gate 3 resets → repeat 4x
```

### After (next app — target ~4M tokens, 1 pass)

```
boot 6.9" simulator (create if needed)
build + install on ONE
grep Swift code for onboarding key name
en-US: 4 screens on 6.9" → raw-69/en-US     ← 4 captures
ja:    4 screens on 6.9" → raw-69/ja         ← 4 captures
upload: IPHONE_69 en + ja                    ← 2 uploads
paywall review screenshot                    ← 1 capture
= 9 captures + 2 uploads
= validate.sh Gate 3 only runs after US-008a ✅
```

## Metadata Flow: Before vs After

### Before
```
asc localizations update --type app-info --locale en-US ...
asc localizations update --type app-info --locale ja ...
asc localizations update --version $VER --locale en-US ...
asc localizations update --version $VER --locale ja ...
= 4 separate API calls
```

### After
```
CC generates .strings files (en-US.strings + ja.strings)
asc localizations upload --app $APP_ID --type app-info --path metadata/app-info/
asc localizations upload --version $VERSION_ID --path metadata/version/
= 2 commands (batch all locales)
```

## Release Flow: Before vs After

### Before (US-008e)
```
asc versions attach-build --version-id $VER --build $BUILD_ID
asc submit create --app $APP_ID --version "1.0" --build $BUILD_ID --confirm
= Manual multi-step, no validation
```

### After (US-008e)
```
asc release run --app $APP_ID --version "1.0" --build $BUILD_ID --metadata-dir ./metadata/release/ --confirm
= 1 command: version check → metadata apply → attach → validate → submit
= --dry-run for preview, --checkpoint-file for resume
```

---

## Cost Projection

| Phase | Before (FrostDip) | After (projected) | Savings |
|-------|-------------------|-------------------|---------|
| US-007 E2E | 10.2M ($0.91) | ~5M ($0.45) | -50% |
| US-008a Screenshots | 32.2M ($2.88) | ~4M ($0.36) | -88% |
| US-008b-e Release | ~10M ($0.89) | ~3M ($0.27) | -70% |
| **Total build** | **86M ($7.68)** | **~50M ($4.46)** | **-42%** |
| Weekly capacity | 15.4% per app | ~9% per app | +70% more apps |

---

## Execution Plan

1. Dais reviews this spec ← NOW
2. CC reviews this spec (MacBook)
3. Apply patches B-M to recipe files (A, N already done)
4. `git add + commit + push` to dev
5. Test: `asc release run --dry-run` on FrostDip (already tested above)
6. Test: `asc localizations upload --dry-run` on FrostDip (already tested above)
7. Run factory: new app with patched recipes
8. Monitor US-008a — should complete in 1 iteration (~4M tokens)

---

## Files Changed

| File | Patches | Lines changed (est.) |
|------|---------|---------------------|
| `references/us-008-release.md` | B, C, D, E, F, G, H, I, J, K | -200, +80 (net -120) |
| `CLAUDE.md` | M | +4 |
| `validate.sh` | A (done) | 0 (already applied) |
| `us-007-testing.md` | N (done) | 0 (already applied) |
| `prd.json` | L (deferred) | 0 |

Total: **~120 lines net reduction** in us-008-release.md (948 → ~828 lines).
