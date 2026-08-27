# macOS Loop Control Plane — TODO 4 atomic apply

`bin/lm-loop apply` resolves `~/loops/current` (or an explicit release root)
to one immutable release, reads `RELEASE.json` and the schema-v2 registry from
that release, renders canonical plists, and validates the complete generation
before invoking `launchctl-safe preflight` or any launchd mutation.

## Contract evidence

The focused apply suite has five tests: deterministic exact-release plist
rendering; missing-entrypoint zero mutation; non-executable-entrypoint zero
mutation; valid generation after complete preflight; and failed-swap restoration
of prior plist bytes plus prior loaded argv.

Changed jobs use `bin/launchctl-safe` for preflight, bootout, bootstrap, and
readback. Success requires `launchctl print` arguments to exactly equal rendered
`ProgramArguments`. Byte-identical jobs with matching loaded argv are not
reloaded.

## Production fail-closed readback

The current immutable release was
`d8e9c255689929344a3e40ef7b10641fc9ed4f02`. Production apply stopped at the
first missing entrypoint with exit 1:

```text
affiliate-browser: missing entrypoint skills/_shared/venv-cloak/bin/python
```

| Truth | Before | After |
|---|---|---|
| Installed `ai.anicca.*` plist-set hash | `daf5f73f82b46a17e5d9088a534076e51d6c59013e4791702b4bcbeeabbf18b7` | same |
| Sorted `launchctl list` hash | `4bec1837959f27b2c7733e0784c37e77dcc58e8b7b09bbe6159da579259e4cf9` | same |
| Preflight receipt mtime/size | `1787846317:1421` | same |

Invalid-generation handling therefore performs zero plist, launchd, or
preflight mutation.

## Isolated real launchd E2E

The isolated label `ai.anicca.lm-loop-apply-e2e` passed Aqua/user preflight,
bootstrapped, and read back exact loaded argv `["/usr/bin/true"]`. The test then
booted the label out and removed its temporary plist. Final `launchctl print`
returned 113, proving the isolated job did not remain loaded. No production
label was changed.

Production apply remains fail-closed until TODO 9 supplies and verifies every
missing or non-executable repository entrypoint.

