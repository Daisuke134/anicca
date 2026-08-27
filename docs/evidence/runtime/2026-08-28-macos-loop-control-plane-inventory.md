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
| Installed, classified Life Manager-owned | 211 | 43 | 129 | 39 | 0 |
| Full plist/loaded/disabled union | 266 | 48 | 129 | 74 | 15 |

Ownership uses the previous explicit owner classification first, then only
known Life Manager checkout/release roots. A second readback resolved 20 active
affiliate, marketing, finance, earn, and system labels from their installed
argv and existing family ownership. The union classifies 221 Life
Manager-owned, 2 external, and 43 ambiguous labels. Of the installed set, 211
are Life Manager-owned, 1 is external, and 14 disabled/unloaded labels are
ambiguous. All individual owner/domain/effect/state/release
values and parse errors are in the JSON evidence.

## Gaps that must fail closed during import

- All 211 installed Life Manager-owned jobs were unmanaged at capture time.
  TODO 2 imports the 172 loaded jobs; the 39 disabled jobs remain visible but
  are not active definitions.
- 141 initially classified installed Life Manager-owned rows have no immutable release SHA readable
  from plist argv. Twenty explicitly run from a mutable
  `/Projects/life-manager-main` checkout. TODO 2 may import their definitions,
  but TODO 4/9 must not migrate a label until immutable release and loaded argv
  readback pass.
- The 35 initially unresolved active domains are resolved during TODO 2;
  `unknown` is never emitted into schema v2.
- Three installed plists are not parseable: `ai.anicca.cfo-daily`,
  `ai.anicca.fleet-daily`, and `ai.anicca.tsbridge`. They remain visible with
  `parse_error`; none can be migrated from inferred argv.
- Four loaded jobs have no installed plist:
  `ai.anicca.provision-browser.buyma.na-l5-client`,
  `ai.anicca.provision-browser.instagram.capafy-provision`,
  `ai.anicca.provision-browser.x.anicca`, and
  `ai.anicca.provision-browser.x.diceai0`.
- The remaining 43 ambiguous labels are the rows whose `owner` is `ambiguous`
  in the JSON evidence. Fourteen have installed plists, but all are disabled or
  unloaded. They remain explicit migration-review inputs rather than active
  registry definitions.

## Live blocker readback

`ai.anicca.fundraiser` is loaded but not running. `launchctl print` reports 136
runs and terminal `75: EX_TEMPFAIL`; its loaded argv points to release
`48c54b52`. The root filesystem has only 135 MiB available. Inventory made no
launchd or cleanup mutation. The existing release/state/receipt data remains
untouched.

The evidence file scans to zero credential assignment and bearer-token matches.
