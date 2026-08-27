# macOS Loop Control Plane — TODO 9 source consolidation

Before any production label migration, all 169 managed registry entrypoints are
present and executable in the Life Manager main tree. No compatibility wrapper
executes a mutable external source checkout.

Source provenance used for exact behavior recovery:

- Life Manager history: Fundraiser `48c54b529`, Agent Economy `63a294643`, Gig
  daily `f1209ea69`, and current repository-owned loop sources.
- Life Manager sibling checkout `50c853764300035e93338586b9846c16e2af3a40`:
  tracked marketing, x402, and Polymarket sources, imported without overwriting
  newer current files.
- Agentmail worktree `cda40e2bcd289c5907c89eb0aa5e71639282d3f6`.
- Profitable Claude `8db5463b45c026c732a487f8838b82698808c49b`:
  bounded tracked bounty, Reddit, CEO, and legacy marketing package.
- Anicha `7730e9cd340530f62b527e1e169263edeb10d3d3`:
  citizen refill entrypoint, shelter/funding dependencies, installer, and tests.
- Installed immutable Life Manager/CFO/Affiliate releases and small installed
  code-only skills. Logs, evidence, state, credentials, caches, and bytecode are
  excluded.

Loop-specific argv that the schema does not store is preserved by the closed
`runtime/loop/entry_dispatch.py` mapping. Affiliate subcommands and marketing
mode/state arguments now resolve entirely inside the immutable release while
mutable state stays under the user state home.

`ai.anicca.tsbridge` is explicitly external third-party infrastructure
(`github.com/jtdowney/tsbridge v0.15.0`). `ai.anicca.cfo-daily` and
`ai.anicca.sync-memory` are explicit retired labels: both loaded definitions
point to missing sources and terminate with 127. They are not replaced with
invented behavior; TODO 10 removes their installed plists after migration.

This evidence closes source preflight only. No production label is cut over in
this slice.

## Fresh verification

- Registry entrypoint existence, execute bit, and language syntax: 169/169.
- Runtime loop and canonical agent-runner focused suites: green.
- Affiliate canonical boundary: 101 tests, 1 expected CI-only skip, 113 subtests.
- x402 source/version-aligned suite: 221/221.
- Citizen refill exact upstream contract: 3/3.
- `lm-loop doctor`: missing entrypoints 0; still nonzero for 58 unmanaged
  candidates and 2 installed retired labels, as required before TODO 10.

Imported historical suites expose pre-existing/stale evidence failures: Writer
repair 24 tests, Affiliate local-loop 7 tests, and Marketing live-gate 9 tests.
Writer and Affiliate failures reproduce against their pre-import/baseline
trees; Marketing failures require historical live evidence assets or time
windows. They remain visible final full-suite blockers and are not used as
migration success evidence.
