# macOS Loop Control Plane — TODO 1 launchd inventory

Machine-readable evidence: `2026-08-28-macos-loop-control-plane-inventory.json`.

## Capture boundary

The capture is read-only and joins four sources: all 226 installed
`~/Library/LaunchAgents/ai.anicca.*.plist` files, `launchctl list`,
`launchctl print-disabled gui/501`, and the prior classified scheduler inventory
at `docs/migrations/openclaw/runtime-inventory.json`. The union contains 266
labels because launchd retains 40 loaded/disabled labels without a current
plist. No credential values or command arguments are stored.

| Set | Count | Running | Loaded idle | Disabled | Unloaded |
|---|---:|---:|---:|---:|---:|
| Installed `ai.anicca.*` plist labels | 226 | 44 | 129 | 52 | 1 |
| Installed, classified Life Manager-owned | 191 | 38 | 114 | 39 | 0 |
| Full plist/loaded/disabled union | 266 | 48 | 129 | 74 | 15 |

Ownership uses the previous explicit owner classification first, then only
known Life Manager checkout/release roots. It does not assign ownership from a
label-name guess. The union classifies 201 Life Manager-owned, 2 external, and
63 ambiguous labels. Of the installed set, 191 are Life Manager-owned, 1 is
external, and 34 are ambiguous. All individual owner/domain/effect/state/release
values and parse errors are in the JSON evidence.

## Gaps that must fail closed during import

- All 191 installed Life Manager-owned jobs are unmanaged by the new registry;
  `config/loop-registry.json` currently contains only `x-repost` and
  `x-tweeter`, and neither is yet schema v2.
- 141 installed Life Manager-owned rows have no immutable release SHA readable
  from plist argv. Twenty explicitly run from a mutable
  `/Projects/life-manager-main` checkout. TODO 2 may import their definitions,
  but TODO 4/9 must not migrate a label until immutable release and loaded argv
  readback pass.
- 35 Life Manager-owned rows have an unresolved domain. TODO 2 must resolve or
  reject them; `unknown` is not a schema-v2 allowed value.
- Three installed plists are not parseable: `ai.anicca.cfo-daily`,
  `ai.anicca.fleet-daily`, and `ai.anicca.tsbridge`. They remain visible with
  `parse_error`; none can be migrated from inferred argv.
- Four loaded jobs have no installed plist:
  `ai.anicca.provision-browser.buyma.na-l5-client`,
  `ai.anicca.provision-browser.instagram.capafy-provision`,
  `ai.anicca.provision-browser.x.anicca`, and
  `ai.anicca.provision-browser.x.diceai0`.
- The 63 ambiguous labels are the rows whose `owner` is `ambiguous` in the JSON
  evidence. They are not silently excluded; TODO 2 must explicitly classify
  each as Life Manager-owned or external before registry coverage can pass.

## Live blocker readback

`ai.anicca.fundraiser` is loaded but not running. `launchctl print` reports 136
runs and terminal `75: EX_TEMPFAIL`; its loaded argv points to release
`48c54b52`. The root filesystem has only 135 MiB available. Inventory made no
launchd or cleanup mutation. The existing release/state/receipt data remains
untouched.

The evidence file scans to zero credential assignment and bearer-token matches.

