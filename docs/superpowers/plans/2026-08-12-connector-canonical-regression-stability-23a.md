# Connector Item 23A — deterministic canonical regression fixtures

## Goal

Make the full Connector regression suite independent of the wall clock and align provider-cursor assertions with the accepted same-pass multi-provider continuation.

## Ponytail full gate and size

- Test-only exact three files; production LOC 0. No clock library, fake-timer service, registry change, provider-order change, or runtime branch.
- `connector-luma-workflow.test.js`: add the existing fixed Tokyo clock to the first two factory fixtures.
- `connector-peatix-workflow.test.js`: add its existing file-level fixed clock to the canonical-dedup cap fixture.
- `connector-native-runtime.test.js`: final cursor is Peatix after Luma exhausted and empty Connpass; update the two stale provider assertions, the latter generation `3→4`, and its test name.

## TDD and verification

1. RED is the current feature and integration result: focused 42/47 with Luma 2, Peatix 1, runtime cursor 2 failures.
2. GREEN must pass the exact three files with production untouched.
3. Run the full Connector command after Item 23B; do not accept a date skip or environment override.
