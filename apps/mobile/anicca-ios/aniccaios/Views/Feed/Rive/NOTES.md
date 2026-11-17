# Living home Rive asset

`living_home.riv` is a real, self-contained **4,614-byte Rive v7.0 binary**.
It replaces the empty placeholder. No fallback implementation or sample artwork
is used. All artwork is authored here as vectors; there are no fonts, images,
CDN requests, or third-party artwork licenses to resolve.

## Runtime contract

- Artboard: `LivingHome`, transparent, 390 × 844 portrait.
- State machine: `Living`.
- Trigger input: `WordChanged`.
- `Ambient`: 12-second looping sage, gold, and mist radial-gradient shapes;
  cosine-sampled position/scale tracks create slow drift and breathing.
- A second layer rests invisibly in `Rest`. `WordChanged` plays `WordChange`,
  a 0.6-second expanding golden ripple, then returns to `Rest`. `Ambient` keeps
  running throughout, so changing words does not jump the background position.
- Two alternating states reference the same `WordChange` timeline. This permits
  rapid triggers to restart the ripple: Rive ignores a transition to the current
  state, so a self-transition alone does **not** satisfy this contract.

The existing `LivingRiveBackground.swift` loads the resource by name, checks the
artboard/state machine/trigger, draws at 0.3 opacity, and pauses playback when
inactive, offscreen, or Reduce Motion is on. The app target's synchronized
`aniccaios` folder includes the resource; no project-file edit is necessary.

## The words keep changing

Affirmation text remains native, accessible, and localized in `QuoteCardView`.
The Rive file supplies the motion behind the words, not a second hard-coded
text deck. `FeedRootView` already drives `currentIndex` through
`HomeAutoAdvance.nextIndex`, updates `displayedWordID`, and fires `WordChanged`
through `LivingRiveBackground` whenever the displayed word changes.

- Recording: launch with `-aniccaRecordingMode`, optionally with `-uiTesting`.
  Auto-advance after **3 seconds** idle.
- Normal: auto-advance after **8 seconds** idle.
- Both require an active scene, multiple cards, and no sheet open. Ordinary UI
  tests disable auto-advance unless recording mode is explicitly enabled.
- The timer checks once per second; transitions take 0.6 seconds. Idle timing
  resets on an index change, user interaction, and foreground return.

The existing `PersonalizationPhase1Tests.swift` covers the 3s/8s thresholds,
recording + UI-testing flags, pause conditions, and deck wraparound. These
XCTest cases were inspected, **not executed on Linux**. No scheduling or text
selection logic was changed for this asset task.

## Production and regeneration

No Rive editor/exporter is installed in this Linux VM. Instead,
`scripts/rive/generate_living_home.py` deterministically writes the official
runtime binary format using Python's standard library. This is the shipping
`.riv`, not JSON disguised as a Rive file. It uses only baseline v7 vector,
keyframe, and state-machine properties.

From `apps/mobile/anicca-ios`:

```sh
python3 scripts/rive/generate_living_home.py
cd scripts/rive
npm ci
CHROMIUM_PATH=/path/to/chrome npm test
```

The verifier loads the **shipping file** with the official
`@rive-app/canvas-advanced` 2.21.3 WASM runtime in headless Chromium. Both npm
dependencies are pinned in `package-lock.json` and are development-only.
Optional `RIVE_PREVIEW_PATH=/tmp/living-home.png` saves the actual rendered
transparent ripple frame. Neither npm nor Python is needed by the iOS app.

Format references used to author the generator:

- [Official runtime format](https://github.com/rive-app/help-center/blob/master/runtimes/advanced_topics/format.md)
- [Official generated type/property IDs](https://github.com/rive-app/rive-runtime/tree/main/include/rive/generated)
- [Transition flags](https://github.com/rive-app/rive-runtime/blob/main/include/rive/animation/state_transition_flags.hpp)
- [Artboard import context](https://github.com/rive-app/rive-runtime/blob/main/src/artboard.cpp)

## Verification — Linux, 2026-11-16

- RED: verifier rejected the original zero-byte file with
  `living_home.riv must be a real asset, not a placeholder`.
- GREEN: 4,614 bytes; header `52 49 56 45 07 00 00 00` (`RIVE`, major 7,
  minor 0, unassigned file ID, no extension properties).
- SHA-256: `7328c59c44c61ebd66ca8ca1fd63b12c379deb2162fb10c5eae706b85b2e8cb1`.
- Official WASM import resolved `LivingHome`, `Living`, and the trigger-type
  `WordChanged`; all three timelines were present.
- The renderer produced nontransparent pixels and preserved transparent pixels.
  After 4 seconds, 1,133,507 RGBA channel values differed from the first frame.
- Firing the trigger changed 163,986 channel values against an independently
  advanced, untriggered control artboard at the **same animation time**.
- Triggering again mid-ripple restarted its scale. After completion, pixels
  exactly matched the untriggered control: the ripple disappeared without
  resetting Ambient. Later triggers and more than two ambient loops passed.
- The generated PNG was visually inspected: soft sage/gold fields and an
  expanding light ring, with a transparent background.
- `LivingRiveBackground.swift`, `FeedRootView.swift`, `VerticalPager.swift`,
  and `PersonalizationPhase1Tests.swift` parsed with zero error
  or missing nodes using `tree-sitter` 0.26.1 + `tree-sitter-swift` 0.7.4.
  This is a syntax check, **not Swift compiler type checking**.
- Loader initializer/method signatures were checked against the official
  [Rive iOS 6.12.2 RiveViewModel](https://github.com/rive-app/rive-ios/blob/6.12.2/Source/RiveViewModel.swift)
  and [RiveModel](https://github.com/rive-app/rive-ios/blob/6.12.2/Source/RiveModel.swift).
- Regeneration matched the shipping bytes exactly; `node --check` and
  `git diff --check` passed. Independent read-only review reran the WASM test
  and checked regeneration/SHA-256, reporting zero findings.

**Not verified here:** Swift compilation/type checking, Xcode resource bundling,
the iOS 6.12.2 native renderer, simulator/device playback, native accessibility
and lifecycle behavior, or an actual 3s/8s iOS recording. This VM has no Swift
compiler, Apple SDK, or Xcode. The Web runtime smoke test is not an iOS build.
GitHub Actions/Xcode must resolve SPM, build, run the existing XCTest coverage,
and verify word changes with the recording flag plus the normal 8s mode.
The existing workspace lockfile does not yet contain the pinned Rive 6.12.2
dependency; Xcode must resolve/update it (unchanged from the wiring commit).

Repository-boundary note: the local Life Manager boundary script rejects this
Anicca checkout by name/path. The explicit assignment override authorizes this
checkout and `codex/rive-asset`; no other checkout, push, merge, or release is
part of this task.
