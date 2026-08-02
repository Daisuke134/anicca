---
name: apply-to-yc
description: Compatibility entry for YC applications. Delegates the exact yc-w26 route to the current apply-to-funder provider on the existing CloakBrowser daily-driver. Use the successor directly for new work.
metadata:
  status: retired-compatibility
  successor: apply-to-funder
---

# apply-to-yc compatibility entry

The former standalone implementation is retired. YC application knowledge, current facts, safety gates, and browser ownership now live in `apply-to-funder` and the repository-owned `yc-application` provider.

Compatibility invocation:

```bash
env -u BASH_ENV -u ENV "$HOME/.openclaw/skills/apply-to-yc/scripts/apply.sh"
```

The shim accepts no positional arguments. It routes only `yc-w26` to the current successor, requires the existing CloakBrowser daily-driver, and refuses legacy draft or media overrides. Existing `MODE` and `DRY_RUN` environment values pass through to the successor.

For new work, invoke:

```bash
env -u BASH_ENV -u ENV /bin/bash "$HOME/.openclaw/skills/apply-to-funder/scripts/run.sh" --funder yc-w26
```

The retired implementation is preserved only in the content-addressed recovery archive recorded by the O1C-24 evidence.
