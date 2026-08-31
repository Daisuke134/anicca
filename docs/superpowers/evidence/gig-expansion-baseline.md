# Gig Expansion Production Baseline

This is the Task 0 observation required by
`docs/superpowers/plans/2026-08-22-mr-bot-gig-economy-loop.md`. It records the production
boundary before any provider-generalization code is added. It contains no credential, customer
content, private authorization evidence or runtime-state contents.

## Source and release

Observed at `2026-08-22T08:08:25Z` after `git fetch origin main`:

| Item | Authoritative value |
|---|---|
| `origin/main` | `7ddc6af05bca941dc9916cbd902b9606dd553695` |
| `origin/main` subject | `docs(gig): distinguish head from active release` |
| Current release symlink | `/Users/anicca/gig/releases/mr-bot/current` |
| Current release directory | `92174b7932f9691109a537e3a90a95b8f6759227` |
| Release versus `origin/main` | release is behind by two commits; neither release activation nor symlink mutation was performed |

`origin/main` moved from `92174b7932f9691109a537e3a90a95b8f6759227` to
`7ddc6af05bca941dc9916cbd902b9606dd553695` during baseline collection. The final fetched value
above is the source baseline; the symlink target is the deployed-release baseline. A release
directory has no nested `.git`, so its directory name—not a parent repository lookup—is its release
identity.

## Coconala owners

Observed through `launchctl print gui/501/<label>` at `2026-08-22T08:08:05Z`:

| Lane | Owner label | State | Runs | PID | Last exit |
|---|---|---:|---:|---:|---:|
| Apply | `ai.anicca.hf-gig-apply-direct` | `not running` | 394 | none | 1 |
| Negotiate | `ai.anicca.hf-gig-reply-detector` | `spawn scheduled` | 787 | none | 1 |
| Storefront | `ai.anicca.hf-gig-storefront-direct` | `not running` | 394 | none | 1 |
| Paid/Submission | `ai.anicca.hf-gig-paid-direct` | `running` | 2 | 43752 | none reported |

The Paid/Submission process was independently present with PPID 1 and argv resolving through
`/Users/anicca/gig/releases/mr-bot/current/skills/earn/gig/scripts/paid_direct.py`. The table
does not claim four concurrent processes: it records the four loaded owner identities and their
actual observed states.

The shared browser owner was `ai.anicca.hf-gig-browser`, `state=running`, `runs=1`, PID 787. Its
process used CDP port 9223 and the private `gig-daily-driver` profile. No browser profile content was
read.

## Active production cursor

`skills/earn/gig/TODO.md` states that **Paid/Submission is the active development cursor**. The
non-skippable order is:

```text
Paid/Submission → Negotiate → Storefront → four-lane durability → OSS third-device acceptance
```

The current Paid/Submission stage remains open until natural context-complete artifact, independent
validation, exactly-once delivery/readback and continuation/replay evidence close its unchecked
acceptance items. This expansion branch did not move or check any Coconala production item.

## Disk and private state boundary

Observed at `2026-08-22T08:07:29Z`:

```text
Filesystem: /dev/disk3s1s1
Available: 2,764,604 KiB
Capacity: 80%
Configured gig floor: 524,288 KiB / 536,870,912 bytes
```

Command:

```bash
python3 skills/earn/gig/scripts/gig_disk_guard.py /usr/bin/true
```

Result: exit 1 with `status=failed`, `reason=disk_writers_stop`, `effect=0`, `readback=0` and
`available_bytes=2830954496`. The blocking source was the regular control flag
`/Users/anicca/.openclaw/state/disk-writers.stop`. Free space exceeded the configured floor, but the
shared stop contract took precedence. Running the guard atomically refreshed its normal private
receipt at `~/gig/state/disk-headroom.json`; it did not start the child command or a marketplace
effect.

Only path existence and permissions were inspected:

| Private path | Observed mode | Purpose |
|---|---|---|
| `/Users/anicca/gig` | `drwx------` | Gig state, evidence, projects, locks and releases |
| `/Users/anicca/gig/logs` | `drwxr-xr-x` | Launchd logs |
| `/Users/anicca/gig/state` | `drwxr-xr-x` | Brake and guard receipts |
| `/Users/anicca/.local/state/mr-bot` | `drwx------` | Shared Mr.bot loop state |
| `/Users/anicca/.config/anicca/gig` | `drwxr-xr-x` | Private Gig installation/config directory |
| `/Users/anicca/.cloak/profiles/gig-daily-driver` | `drwx------` | Coconala browser profile |

## Focused test baseline

Command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_application_direct_reconcile.py \
  skills/earn/gig/tests/test_storefront_direct.py
```

Fresh result:

```text
28 passed in 12.31s
```

Pass count: 28. Failure count: 0. The tests establish the focused application-reconciliation and
storefront-code baseline only; they do not override the live owner states, disk guard failure or
open Paid/Submission cursor above.
