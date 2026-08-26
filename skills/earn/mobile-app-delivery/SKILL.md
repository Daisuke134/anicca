---
name: mobile-app-delivery
description: Build, repair, test, and package bounded iOS apps and mobile features using Swift, SwiftUI, existing web/API backends, and documented AI APIs; suited to contract work with an existing repository or a small acceptance-defined app, not unsupported Android-native or specialized SDK experience.
metadata:
  version: 1.0.0
  risk: medium
---

# Mobile App Delivery

Deliver a contract-bound iOS application or bounded feature from an existing repository, supplied
design, documented backend or explicit acceptance flow. This Skill does not search marketplaces,
write proposals, accept contracts, publish with unapproved credentials, or claim prior client work.

## Supported work

- Swift and SwiftUI implementation, debugging and maintenance.
- REST/JSON and documented OpenAI or other AI API integration.
- Authentication, local persistence, document/file flows and ordinary native UI.
- Converting an acceptance-defined web workflow into an iOS client when the backend and required
  native behavior are explicit.
- Xcode build, simulator tests, archive preparation and App Store metadata/build preparation.

Do not claim Android-native delivery, production experience with a named specialized SDK, an
unbounded cross-platform rebuild, or store publication without the required account authorization.

## Contract inputs

Require the source/repository and hash, supported iOS/Xcode target, acceptance flows, API contracts,
design/assets, secret-injection boundary, test devices or simulator targets, delivery artifact and
deadline. Convert missing implementation details into buyer questions before freezing scope.

## Delivery

Work only in the private contract project. Preserve the existing architecture unless the acceptance
criteria require a change. Keep credentials out of source and logs, bound network retries and spend,
and make failure/loading/accessibility behavior visible. Produce source changes, setup notes, tests,
build evidence and a versioned archive or package only when contracted.

Use a separate `gig-delivery-verifier` context to build and run the target, execute every acceptance
flow, inspect the visible UI and verify the exact artifact hash. Only its PASS may authorize the
marketplace delivery effect.
