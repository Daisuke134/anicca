# macOS Loop Control Plane — TODO 5 lifecycle

`bin/lm-loop start|stop|restart <loop-id|all>` now resolves labels exclusively
from the schema-v2 registry and routes every mutation through
`bin/launchctl-safe` after Aqua/user preflight.

## Semantics

- `start`: kickstarts an already loaded service; otherwise bootstraps its
  installed plist; then requires `launchctl print` readback.
- `stop`: boots the service out and reports the launchctl return code.
- `restart`: boots out, bootstraps the installed plist, and requires readback.
- `all`: expands sorted loop IDs from the registry, records every operation and
  return code, catches per-label exceptions as return code 1, and never stops
  before later labels run.
- Unknown IDs and missing command targets are rejected before preflight.

The focused suite contains four lifecycle tests: collect-all continuation,
unloaded start, restart ordering/readback, and unknown-ID zero execution.

## Isolated real launchd evidence

`ai.anicca.lm-loop-lifecycle-e2e` produced:

```text
start   0  [print, bootstrap, print]
restart 0  [bootout, bootstrap, print]
stop    0  [bootout]
```

Cleanup readback returned `launchctl print` code 113.

A second three-label isolated run intentionally omitted the middle plist.
`start all` returned `[a:0, b:2, c:0]`, proving the third label ran after the
second failed. All three labels were booted out afterward; remaining labels
were `[]`. No production label was started, stopped, or restarted.

