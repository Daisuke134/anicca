# Loop inventory

Life Manager has one executable local registry: `config/loop-registry.json`. Cloud adapter declarations live in
`apps/life-manager/config/loop-adapters.json` until the ordered architecture migration unifies them. Do not add a
second hand-edited loop list.

## Current measured inventory

| Classification | Count | Owner meaning |
|---|---:|---|
| Managed local jobs | 174 | `life-manager`, inferred from membership in `.loops` |
| External labels | 22 | `external`, observed but not managed by Life Manager |
| Retired labels | 50 | `retired`; installation is an error |
| Cloud adapters | 12 | owner is not yet declared in the adapter manifest |

The generated snapshot at `docs/loops/current-inventory.json` contains every local label, owner, last terminal
receipt observation and official-effect receipt status, plus every cloud adapter. It pins the source commit and
SHA-256 hashes of both manifests. Regenerate it from one pinned release status capture:

```bash
release="$(readlink "$HOME/loops/current")"
"$release/bin/lm-loop" status all > /tmp/life-manager-loop-status.json
python3 scripts/freeze-loop-inventory.py \
  --status /tmp/life-manager-loop-status.json \
  --source-head "$(jq -r .sha "$release/RELEASE.json")" \
  --output docs/loops/current-inventory.json
```

`bin/lm-loop status all` keeps four layers separate: registry ownership, launchd process state, terminal runtime
event and official provider effect. A process or PASS terminal event is never treated as a payment, application,
message, publication or trade receipt.

## Visible gaps

- Four managed jobs have no terminal runtime receipt.
- The 66 effectful local jobs have no common official-provider receipt mapping.
- The 12 cloud adapters declare neither owner nor receipt source.
- `ai.anicca.job-search-browser` is retired but remains installed, so `bin/lm-loop doctor` fails closed.

The fixed next step is `ARCH-02` in the current one-repo/two-runtime design spec. It generates one `loop.json`
schema from the existing registry contract without introducing a second editable authority.
