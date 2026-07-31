# Xcode Version Check for Factory

**Source**: Apple Developer — Upcoming Requirements (https://developer.apple.com/news/upcoming-requirements/?id=02032026a)

**核心の引用**:
> "Begins April 28, 2026. Apps uploaded to App Store Connect must be built with Xcode 26 or later using an SDK for iOS 26, iPadOS 26, tvOS 26, visionOS 26, or watchOS 26."

---

## Current Factory Configuration

- **Xcode Version**: 15.3 (as of 2026-03-28)
- **iOS SDK**: iOS 17 SDK
- **Deployment Target**: iOS 15.0

---

## Required Upgrade Timeline

| Date | Requirement |
|---|---|
| **April 28, 2026** | Xcode 26 + iOS 26 SDK becomes mandatory for all App Store submissions |
| **March 2026 (Now)** | Test Xcode 26 RC builds locally |
| **April 2026** | Upgrade production factory to Xcode 26 |

---

## Implementation in ralph.sh

**Add to ralph.sh (before build step)**:

```bash
# Check Xcode version
XCODE_VERSION=$(xcodebuild -version | head -n 1 | awk '{print $2}')
REQUIRED_MAJOR_VERSION=26

if [[ $(echo "$XCODE_VERSION" | cut -d. -f1) -lt $REQUIRED_MAJOR_VERSION ]]; then
    echo "⚠️  WARNING: Xcode $XCODE_VERSION detected. App Store Connect requires Xcode $REQUIRED_MAJOR_VERSION or later after April 28, 2026."
    echo "Current build will succeed locally but may be rejected by App Store."
    # Uncomment to enforce:
    # exit 1
fi
```

---

## Manual Check Command

```bash
xcodebuild -version
# Expected output (post-upgrade):
# Xcode 26.0
# Build version XXXXX
```

---

## SDK Check

```bash
xcodebuild -showsdks | grep -i ios
# Expected output (post-upgrade):
# iOS 26.0 -sdk iphoneos26.0
```

---

## Related Files

- **ralph.sh**: Main build script (add check before `xcodebuild` command)
- **mobileapp-factory/SKILL.md**: Document Xcode version requirement in Prerequisites section

---

**Last Updated**: 2026-03-28 by factory-bp-efficiency cron
