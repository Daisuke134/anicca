# Mr.bot iOS Native Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the native iPhone onboarding and chat-first Mr.bot experience, approve the complete English journey, then add a complete Japanese projection from the same backend semantics.

**Architecture:** An XcodeGen-created SwiftUI app uses an actor API client, Keychain session store, service protocols, and `@MainActor @Observable` view models injected through `AppEnvironment`. `RootView` renders an explicit onboarding/auth/chat state machine. The client decodes frozen backend fixtures and projects existing server decisions; it never calculates routes, schedules calls, or invents provider facts.

**Tech Stack:** iOS 17, Swift 5.9, SwiftUI, Observation, Foundation, AuthenticationServices, Security, OSLog, XCTest, XcodeGen 2.44.1, Fastlane. No third-party package is required for the first release.

## Global Constraints

- Bundle ID `ai.anicca.mr-bot`; scheme `MrBot`; iPhone-only; supported regions `en`, `ja`; source language `en`.
- Ignore generated `.xcodeproj`, DerivedData, build output, workspaces, and `*.local.xcconfig`.
- Config stores only API base URL and callback scheme; no API/provider secret ships in the app.
- Access/refresh tokens live only in Keychain. No client UID is sent.
- Accessibility IDs are attached to leaf controls/text, never large containers.
- No bottom tabs, calendar grid, editable map, general AI composer, local route engine, or local call timer.
- Paywall is soft: every cancel/failure/continue action returns to route-enabled chat.
- The active developer directory must point to a full Xcode installation before build verification; planning observed Command Line Tools only.

## File Structure

```text
apps/mr-bot-ios/
├── Gemfile
├── project.yml
├── fastlane/{Appfile,Fastfile}
├── MrBot/
│   ├── App/{MrBotApp.swift,AppEnvironment.swift,AppViewModel.swift,RootView.swift}
│   ├── Configuration/AppConfiguration.swift
│   ├── Models/{Session.swift,UserProfile.swift,AnalysisResult.swift,ChatMessage.swift,Route.swift}
│   ├── Networking/{HTTPTransport.swift,URLSessionTransport.swift,APIClient.swift,APIEndpoint.swift,APIError.swift}
│   ├── Security/{SessionStoring.swift,KeychainSessionStore.swift}
│   ├── Services/{AuthService.swift,ProfileService.swift,AnalysisService.swift,ChatService.swift,TestCallService.swift}
│   ├── Features/Onboarding/{OnboardingViewModel.swift,OnboardingContainerView.swift,CalendarConnectView.swift,ProfileConfirmationView.swift,PhoneSetupView.swift,FirstAnalysisView.swift,SoftPaywallView.swift}
│   ├── Features/Chat/{ChatViewModel.swift,ChatView.swift,ChatComposerView.swift,MessageBubbleView.swift,RouteMessageView.swift,RouteDetailSheet.swift}
│   ├── Features/Settings/{SettingsViewModel.swift,SettingsView.swift}
│   ├── DesignSystem/{Theme.swift,AccessibilityID.swift}
│   ├── Config/{Debug.xcconfig,Release.xcconfig}
│   └── Resources/{Localizable.xcstrings,PrivacyInfo.xcprivacy,Assets.xcassets}
└── MrBotTests/{Support,ModelTests,NetworkingTests,ServiceTests,ViewModelTests}
```

### Task 1: Create the Reproducible App Skeleton

**Files:**
- Create: `apps/mr-bot-ios/project.yml`
- Create: `apps/mr-bot-ios/Gemfile`
- Create: `apps/mr-bot-ios/fastlane/Fastfile`
- Create: `apps/mr-bot-ios/MrBot/Info.plist`
- Create: `apps/mr-bot-ios/MrBot/Resources/PrivacyInfo.xcprivacy`
- Create: `apps/mr-bot-ios/MrBot/Config/*.xcconfig`

- [ ] Point `xcode-select` to full Xcode and verify `xcodebuild -version`, XcodeGen 2.44.1, Ruby, Bundler, Fastlane, and an iPhone simulator runtime.
- [ ] Define app/test targets, iOS 17, Swift 5.9, en/ja regions, iPhone family, `UIRequiresFullScreen`, non-exempt encryption false, and `mrbot` callback URL scheme.
- [ ] Add `test` and `build_for_simulator` lanes now; reserve `build_for_testflight` for the integration plan when signing is known.
- [ ] Generate the project and write a smoke XCTest that launches `MrBotApp` with a test environment.
- [ ] Run `bundle exec fastlane test`; record RED before app target creation and GREEN after the smoke test passes.
- [ ] Commit/push the skeleton without generated project/build artifacts.

### Task 2: Decode Contracts, Store Sessions, and Refresh Once

**Core protocols:**

```swift
protocol HTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}
protocol SessionStoring: Sendable {
    func load() async throws -> Session?
    func save(_ session: Session) async throws
    func clear() async throws
}
```

- [ ] Reference `../mr-bot/contracts/mobile-v1` as test fixture resources in `project.yml` so Swift tests consume the backend's canonical JSON without copies.
- [ ] Add `Codable`, `Sendable`, and `Equatable` models for bootstrap, five analysis states, chat page/message/actions, localized route, question, call/device/deletion receipts, and structured errors.
- [ ] Add fixture decoding tests for every contract, including nullable platform/fare/geometry and ISO/IANA fields.
- [ ] Implement Keychain add/update/read/delete with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` and tests through an injected security adapter.
- [ ] Implement `APIClient` as an actor that adds bearer/idempotency headers, performs one single-flight refresh on 401, persists rotated tokens, and signs out after refresh-family rejection.
- [ ] Use `TestURLProtocol`/mock transport to prove concurrent 401s produce one refresh and request replay never changes idempotency keys.
- [ ] Run model/network/security tests and commit/push.

### Task 3: Implement the Native Onboarding State Machine

**State:**

```swift
enum AppRoute: Equatable {
    case restoring, welcome, calendarConnecting, profile, phone, analyzing
    case chat, softPaywall, fatal(AppErrorState)
}
```

`AppErrorState` is an `Equatable`, `Sendable` presentation value containing the backend error code, localized message key, and retry permission; raw transport errors never enter navigation state.

```swift
protocol AuthServicing: Sendable {
    func restoreSession() async throws -> Session?
    func connectCalendar() async throws -> Session
    func refresh(_ session: Session) async throws -> Session
    func signOut() async throws
}
protocol ProfileServicing: Sendable {
    func fetch() async throws -> UserProfile
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile
}
protocol AnalysisServicing: Sendable {
    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult
}
```

- [ ] Write view-model tests for welcome → Calendar OAuth → callback exchange → profile → phone add/skip → analysis → chat/paywall.
- [ ] Assert no separate login appears, phone skip sends null plus calls false, and all five terminal analysis results enter chat.
- [ ] Implement `AuthServicing`, `ProfileServicing`, and `AnalysisServicing` protocols with production services and deterministic test doubles.
- [ ] Open OAuth with `ASWebAuthenticationSession`, validate only the app callback, and let the backend own state/nonce/replay.
- [ ] Build one primary action per setup screen, real backend phase labels, visible terminal errors, and retry actions.
- [ ] Add leaf IDs: `welcome.connectCalendar`, `profile.name`, `profile.home`, `profile.continue`, `phone.add`, `phone.skip`, `analysis.phase`, `analysis.retry`.
- [ ] Run onboarding view-model and accessibility tests; commit/push.

### Task 4: Build One Durable Chat and Honest Route UI

**Services:**

```swift
protocol ChatServicing: Sendable {
    func fetch(after cursor: String?) async throws -> ChatPage
    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage
}
```

- [ ] Write `ChatViewModel` tests for initial page, pagination, stable-ID dedupe, retry, preserved scroll anchor, question-only composer, and stale reply.
- [ ] Write route rendering tests: collapsed card includes event, origin/destination, leave/arrival, duration, buffer, optional fare, and ordered leg summary.
- [ ] Assert null platform/fare/geometry produces no replacement claim, and unsupported entrance/exit/car/crowding labels never render.
- [ ] Implement chronological bubbles with backend ID identity, manual refresh, foreground hook interface, failure row, and settings sheet entry.
- [ ] Implement `RouteDetailSheet` from the already-decoded route object; it performs no network request and closing preserves chat position.
- [ ] Add leaf IDs: `chat.list`, `chat.refresh`, `chat.settings`, `chat.composer`, `chat.send`, `route.card.<messageID>`, `route.showDetails`, `route.detail.close`.
- [ ] Verify Dynamic Type through accessibility sizes and VoiceOver labels that state action, times, services, and provider honesty note.
- [ ] Run chat/route/view-model tests and commit/push.

### Task 5: Add Soft Paywall, Settings, Calls, and Deletion UI

- [ ] Write tests proving paywall appears only after first useful resolved result and `Continue free`, cancel, restore failure, and purchase failure all preserve chat/route access.
- [ ] Build a self-owned SwiftUI soft paywall with `Upgrade`, `Restore purchases`, and `Continue free`; do not add an entitlement gate.
- [ ] Write settings tests for Calendar status, name, home, product language, phone, call enablement, conditional call language, subscription/restore, logout, and deletion.
- [ ] Add phone E.164 validation feedback; enabling calls is a separate server mutation.
- [ ] Add `Call me now` confirmation and display server cooldown/daily-limit receipts; never place or schedule a call locally.
- [ ] Add destructive account confirmation and show the backend deletion receipt before clearing local session.
- [ ] Add leaf IDs for paywall actions, each settings control, call confirmation, deletion confirmation, and receipt.
- [ ] Run paywall/settings/call/deletion tests and commit/push.

### Task 6: Approve English, Then Add Complete Japanese

**Files:**
- Modify: `apps/mr-bot-ios/MrBot/Resources/Localizable.xcstrings`
- Add tests: `apps/mr-bot-ios/MrBotTests/ModelTests/LocalizationConsistencyTests.swift`

- [ ] Populate semantic English keys for onboarding, statuses, chat chrome, routes, errors, paywall, settings, notifications, accessibility, and deletion.
- [ ] Run an English screen crawl and script test that excludes user content/provider code allowlist and rejects Japanese scripts in generated UI.
- [ ] Capture and approve the complete English onboarding → route → detail → free paywall → settings journey before adding Japanese.
- [ ] Add complete Japanese values to the same keys; provider navigation values arrive already localized from backend and are not translated client-side.
- [ ] Add a Japanese crawl that rejects missing keys and untranslated English prose while allowing registered names and codes.
- [ ] Switch `product_locale`, refetch outbox, and prove historical generated messages re-project while user-authored Calendar fields remain unchanged.
- [ ] Run all Swift tests in both app languages, commit/push, and record Gate 5/6 receipts in the spec.

## Verification Commands

```bash
cd apps/mr-bot-ios
xcodegen generate
bundle install
bundle exec fastlane test
bundle exec fastlane build_for_simulator
git diff --check
```

`fastlane test` must pass every model, network, security, service, view-model, accessibility, and localization test. The simulator lane must produce a launchable `MrBot.app` from a clean checkout with no local secret.
