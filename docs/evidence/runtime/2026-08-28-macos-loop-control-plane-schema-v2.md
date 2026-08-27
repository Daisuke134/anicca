# macOS Loop Control Plane — TODO 2 schema v2

`config/loop-registry.json` is upgraded to schema v2 and contains all 172
installed, loaded, classified Life Manager jobs. The registry preserves the
pre-existing stable IDs `x-repost` and `x-tweeter`; other IDs are stable
label-derived identifiers. No launchd lifecycle command is executed in this
slice.

| Contract | Readback |
|---|---:|
| Registry entries / unique labels | 172 / 172 |
| Domain | growth 49, earn 42, system 41, financial 33, physical 5, mental 2 |
| Effect | none 111, publish 31, message 14, application 9, money 6, trade 1 |
| Provider route | deterministic 94, shared-agent-runner 78 |
| Structurally invalid entries | 0 |
| Active classified inventory labels absent from registry | 0 |
| Registry labels absent from active classified inventory | 0 |

`runtime.loop.macos_loop_registry.validate_registry` rejects missing, unknown,
secret-like, absolute-path, invalid cadence, invalid cleanup, duplicate-label,
domain, effect, and provider-route values. Rendering sorts by loop ID and emits
canonical JSON bytes. The checked fixture is
`runtime/loop/tests/fixtures/macos-loop-jobs.json`, SHA-256
`8ac7027ef34651a60d8a70eb56236ff7ad920a60974f25d9af0efc1a866eef69`.

The focused suite runs four tests: missing/secret rejection, insertion-order
stability, exact active-label coverage plus safety-critical classifications,
and production fixture byte equality.

## Fail-closed migration boundary

Eighty-two registry entrypoints name their intended repository-relative
destination but are not present at the current commit. This is recorded debt,
not an executable compatibility shim. `apply` must reject any generation with
a missing entrypoint; TODO 9 must copy and verify exact behavior before each
affected label migrates. Until then the existing loaded job remains untouched.

The existing CEO budget gate still knows how to enumerate schema-v2 loop IDs,
but its historical hard-breach writer can add an `allocation` field that schema
v2 rejects. `apply` must therefore remain unavailable until mutable allocation
state is separated from the immutable registry and the enforcement reader is
updated. No such mutation occurs in this slice.
