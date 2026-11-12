# Anicca soft-paywall review and focused validation

Scope: PR #9346, base 812a828307. Specification: anicca-ops 68c17484.

Independent read-only review of 0d0452cdac found one blocking issue: purchase/restore from Settings → Themes dismissed only the navigation destination. Fixed in 5beb4064b8 by closing the owning Settings sheet through a callback; wiring regression failed first and then passed.

Review of the added CI recording lane found one blocking issue: failed/missing recording could pass when Maestro succeeded. Fixed in 3f3b9b27e3: recorder liveness/termination checks, nonempty file, duration covering the journey and real frame decoding via AVFoundation. Five harness tests exercise start failure, missing recording, recorder failure, invalid video and success. Those tool doubles are failure-gate tests only, not evidence of a real mobile journey.

Local Python suite: 31 cases, 30 passed, 1 existing platform-dependent skip. Bash syntax and git diff --check passed.

Native standalone Swift selection suite: 21/21 passed using the remote Mac's CommandLineTools swiftc, with sources copied from this dedicated checkout into a temporary build directory. This exposed a pre-existing stale test call missing the identifier closure; the test caller was brought into agreement with the production signature. No source in the remote checkout was edited.

Actual iOS build/unit tests and Maestro recording remain separately evidenced by GitHub Actions runs. None of the focused checks above establishes App Store submission or real E2E completion.

## Real-run failure and runtime correction

Run43255570230 produced an actual 238.825-second H.264 recording and failed JUnit (1 flow, 1 failure): `paywall-plan-cta` never appeared. The recorded app passed through onboarding/free feed and reached the actual Premium screen, which displayed "Could not load plans". This is not a successful experience artifact.

Observed device: iPhone16Pro / iOS18.5; Xcode16.4. The artifact also lists available iOS26.0/26.1/26.2 runtimes. [RevenueCat's known StoreKit issue FB17105187](https://www.revenuecat.com/docs/known-store-issues/storekit/ios-18-4-simulator-fails-to-load-products) identifies empty real products on18.4–18.5 and recommends Xcode26+/iOS26+. The next real run binds both Xcode and simulator to26.2. The hypothesis remains unconfirmed until that run loads real plans.

No local StoreKit catalog, mock offering or fake purchase was substituted. The existing Anicca.storekit fixture has stale prices and is not used by this `simctl`/Maestro lane; it remains outside this change. Runner-image tool paths were checked against the [official macOS15 image inventory](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md).

The negative runtime test failed on the former selector, then passed after the26.2 binding. This tests selection policy, not real StoreKit connectivity.

## Attempt2: relaunch system alert, not a broken free exit

Run43260350714 attempt2 used Xcode26.2/iPhone17Pro/iOS26.2. Real plans loaded. JUnit failed the final feed-scroll assertion (1flow/1failure), so its 213.508-second video is not accepted as a complete journey. Frames170s show the sandWave free feed after closing Premium;190s and205s show the Apple Account modal covering that feed after relaunch. This disproves the hypothesis that theme selection failed to return to the feed.

A candidate explanation involving passive syncPurchases was checked against the pinned RevenueCat5.78.0 [API contract](https://github.com/RevenueCat/purchases-ios/blob/629a56ecef190469914b8f0914bf0446363eb09f/Sources/Purchasing/Purchases/PurchasesType.swift): it explicitly does not trigger App Store login. The receipt/backend sync implementation remains unchanged. As in the existing first-launch flow, the relaunch now cancels the simulator account prompt without entering credentials; feed visibility, no onboarding/paywall and actual swipe-to-a-different-quote remain required. An existing SDK-key print was independently removed to honor the no-credential-logging boundary.

The two focused regression checks failed before the fix; Python wiring passes after it. Real Maestro completion remains pending a new run.

## Intel cancellation: official timeout, incomplete recording

Run43268640984/job131358901842 was cancelled. The official check annotation states: "The job has exceeded the maximum execution time of 40m0s". Artifact13969783630 (6,406,746 bytes) was downloaded and inspected. Metadata records the actual app build/source cf91e56ccd and recording start at2026-11-12T17:56:53.691823Z; the build/record step began17:23:20Z and was cancelled18:02:13Z. Thus the build reached recording after roughly33.5 minutes. maestro.log only says "Waiting for flows to complete..."; no result.xml, exit-code.txt or video-validation.json was produced. ffprobe rejects the MP4 with "moov atom not found". There is no decodable completed video and no passing E2E result.

The final authorized retry keeps the allocated standard free macos-15-intel runner and Xcode/iOS26.2, changing only the job limit to120 minutes. The previous ARM lane had a documented host-admission failure; switching back would introduce that independent failure mode. App source, flow assertions, real products/offering and prices remain unchanged. Per the user's final-stage instruction, dispatch exactly once; failure, cancellation or admission failure ends this retry budget, with no rerun. Record the resulting official run ID and final evidence in the existing progress file.
