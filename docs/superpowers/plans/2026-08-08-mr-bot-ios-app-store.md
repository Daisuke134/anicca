# Mr.bot iOS App Store Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the verified Gate 9 TestFlight build into a bilingual, privacy-complete, signed App Store submission and retain App Store Connect receipts.

**Architecture:** Release metadata and screenshots live beside the app and are uploaded by explicit Fastlane/ASC commands. Privacy answers derive from an audited data-flow inventory rather than guesses. The same source/build that passed TestFlight is promoted; release work does not change product behavior. Submission health is checked before the irreversible review submission call.

**Tech Stack:** Fastlane, App Store Connect API/CLI, Xcode archive/export, Apple signing, en-US/ja metadata, Maestro screenshot artifacts, public privacy/support pages.

## Global Constraints

- Begin only after Gate 9's real OAuth, route, free/no-phone, call, APNs, deletion, and cost receipts are green.
- Product binary changes invalidate the release candidate and return to the affected implementation gate.
- Never store `.p8`, issuer/key IDs, provisioning profiles, archives, or passwords in Git.
- Metadata and screenshots describe implemented behavior only; no live location, automatic late message, entrance/exit, best-car, crowding, or paid-only route claim.
- Japanese metadata is complete, not machine-placeholder text. English and Japanese screenshots contain one product language per frame.

## File Structure

| File | Change |
|---|---|
| `apps/mr-bot-ios/fastlane/Fastfile` | Add metadata, screenshot, upload, health, and submit lanes |
| `apps/mr-bot-ios/fastlane/Appfile` | Bundle/app identifier configuration |
| `apps/mr-bot-ios/fastlane/metadata/en-US/*` | English name, subtitle, description, keywords, URLs, review notes |
| `apps/mr-bot-ios/fastlane/metadata/ja/*` | Japanese equivalent metadata |
| `apps/mr-bot-ios/fastlane/screenshots/en-US/*` | English iPhone screenshots |
| `apps/mr-bot-ios/fastlane/screenshots/ja/*` | Japanese iPhone screenshots |
| `apps/mr-bot-ios/release/privacy-data-map.md` | Audited collection/linking/tracking inventory |
| `apps/mr-bot-ios/release/submission-checklist.md` | Build/metadata/privacy/signing receipt checklist |
| `apps/landing/app/mr-bot/privacy/page.tsx` | Create only if the public privacy route is absent |
| `apps/landing/app/mr-bot/support/page.tsx` | Create only if the public support route is absent |

### Task 1: Audit Privacy and Compliance Against the Binary

- [ ] Enumerate every app/backend datum: identity, name, home, phone, Calendar content, route, chat/question, device token, subscription, call records, provider cost, diagnostics, and deletion receipt.
- [ ] For each datum record purpose, server system, retention, deletion behavior, user linkage, tracking status, and third-party processors.
- [ ] Inspect the final archive for SDKs, required-reason APIs, entitlements, permissions, domains, URL schemes, and privacy manifests.
- [ ] Assert no ATT prompt/advertising identifier/analytics SDK exists and answer App Privacy based on measured code and traffic.
- [ ] Verify `ITSAppUsesNonExemptEncryption=NO`, iPhone-only support, production APNs entitlement, and Calendar/OAuth disclosures.
- [ ] Commit the data map and checklist; push.

### Task 2: Publish Privacy and Support Surfaces

- [ ] Request `https://aniccaai.com/life-manager/privacy` and `https://aniccaai.com/life-manager/support` and record status/body/language.
- [ ] If either is absent or inaccurate, create/update the corresponding landing source with bilingual content, contact route, account deletion instructions, provider list, and effective privacy language matching the data map.
- [ ] Deploy the landing change and verify both public URLs return 200 from an external request.
- [ ] Exercise the support contact route and account-deletion instructions without deleting the release account.
- [ ] Commit/push any landing change and record deployment evidence.

### Task 3: Create Complete en-US and ja Metadata

- [ ] Write localized app name, subtitle, description, keywords, promotional text, support URL, privacy URL, marketing URL, copyright, and release notes.
- [ ] Keep the promise concrete: connected Calendar, calculated leave time, chat route, optional confirmed calls, English/Japanese.
- [ ] Add review notes explaining Google OAuth, phone skip, soft paywall free path, notification behavior, account deletion, and a stable reviewer account/setup sequence.
- [ ] Validate field lengths and prohibited claims through Fastlane/ASC metadata validation.
- [ ] Have one native-quality language pass check Japanese meaning against the implemented English semantics.
- [ ] Commit/push metadata.

### Task 4: Capture and Validate Bilingual Screenshots

- [ ] Use the verified staging tenant and controlled non-sensitive Calendar event; do not use Dais's private Calendar content.
- [ ] Capture the same five scenes in English and Japanese: promise/Calendar connect, direct analysis result, collapsed route card, route detail, and settings/language or soft paywall free path.
- [ ] Produce required iPhone dimensions from the release simulator/device matrix without stretching.
- [ ] Inspect every frame for mixed script, personal data, debug banners, unofficial precision, stale route/provider facts, clipped Dynamic Type, and inconsistent time/locale.
- [ ] Copy only final lossless screenshots to Fastlane locale folders and run screenshot count/dimension validation.
- [ ] Commit/push final screenshots.

### Task 5: Configure the App Record, Signing, and Release Candidate

- [ ] Resolve or create the App Store Connect app for bundle `ai.anicca.mr-bot`, primary language English, SKU `mr-bot-ios`, and exact app name availability.
- [ ] Resolve distribution certificate, App Store provisioning profile, APNs capability, app ID, agreement status, tax/banking state relevant to the soft paywall, and team access.
- [ ] Set semantic version/build number once, regenerate project, run all backend/Swift/Maestro gates, and archive the unchanged release candidate.
- [ ] Validate archive signing, entitlements, privacy manifest, symbols, launch behavior, API production URL, and absence of local secrets.
- [ ] Upload the candidate and wait for `VALID`; if processing wait times out after VALID, continue with the standalone health/submit flow rather than rebuilding.
- [ ] Record app ID, version ID, build ID, upload timestamp, and processing state.

### Task 6: Upload Metadata and Run Submission Health

- [ ] Upload both locale metadata and both screenshot sets explicitly; do not use a lane that skips either.
- [ ] Set build attachment, App Privacy answers, age rating, content rights, encryption/export compliance, availability, pricing/free status, and phased-release choice.
- [ ] Resolve every App Store Connect warning/error and re-fetch the version/build state.
- [ ] Verify the review account/setup works from a clean device and the review notes match current UI.
- [ ] Run `asc`/Fastlane help for the installed versions, then execute the current supported list/view commands and save their structured receipts.
- [ ] Mark submission checklist entries only from returned App Store Connect state.

### Task 7: Submit and Record the Receipt

- [ ] Reconfirm the selected build is the Gate 9 binary and all localized metadata/screenshots are attached.
- [ ] Submit the version for review with the explicit confirmation flag.
- [ ] Read back version state, review submission ID, submitted timestamp, and build association.
- [ ] Commit/push the completed release checklist and App Store receipt with secrets removed.
- [ ] Update Gate 10 and Definition of Done in the approved iOS spec with the App Store Connect evidence.
- [ ] Send the user the version/build, TestFlight link, submission state, known external review dependency, and cost state.

## Verification Commands

```bash
cd apps/mr-bot-ios
bundle exec fastlane test
bundle exec fastlane build_for_testflight
bundle exec fastlane upload_metadata
bundle exec fastlane upload_screenshots
bundle exec fastlane submission_health
asc --version
asc apps list --bundle-id ai.anicca.mr-bot --output json
asc builds list --app ai.anicca.mr-bot --output json
git diff --check
```

These commands are valid for the currently installed ASC CLI 2.5.0; the executor rechecks `asc --help` if the installed version changes. `submit_review` is intentionally absent from this verification block; it runs once in Task 7 only after health checks return green.
