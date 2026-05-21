# MindSnap — Test Specification

---

## Test Strategy

| Layer | Tool | Coverage Target |
|-------|------|----------------|
| Unit Tests | Swift Testing | Models + Services |
| UI Tests | XCTest / Maestro | Key flows |

---

## Unit Tests

### CheckIn Model Tests
| Test | What it verifies |
|------|-----------------|
| `test_checkIn_defaultsId` | UUID is generated on init |
| `test_checkIn_dateIsNow` | Date is approximately now |
| `test_checkIn_moodRange` | Mood 1-10 stored correctly |
| `test_checkIn_emptyNote` | Empty note valid |
| `test_checkIn_codable` | Encode/decode round-trip |

### CheckInService Tests
| Test | What it verifies |
|------|-----------------|
| `test_save_and_loadAll` | Save one, load one back |
| `test_multiple_saves_ordered` | Multiple saves, newest first |
| `test_delete_removes_entry` | Delete by id, not found after |
| `test_loadAll_empty` | Empty file returns [] |

### PurchaseService Tests
| Test | What it verifies |
|------|-----------------|
| `test_isPremium_false_default` | Default isPremium = false |
| `test_checkPremiumStatus_updates` | After configure, status checked |

---

## Build Verification (CI)

```bash
xcodebuild -scheme MindSnap \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -configuration Debug \
  test
```

---

## CRITICAL Checks

```bash
# No Mock (production code)
grep -r 'Mock' --include='*.swift' . | grep -v 'Tests/' | grep -v '.build/' | wc -l
# Expected: 0

# RevenueCat imported
grep -r 'import RevenueCat' --include='*.swift' . | wc -l
# Expected: > 0
```
