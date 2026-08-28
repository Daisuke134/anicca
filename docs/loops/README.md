# Loops — one repo, one folder, one command

Status as of 2026-08-19. Every number here was measured, not estimated; where something is not
done, it says so.

## Where things live

| Thing | Location |
|---|---|
| The repo | `Daisuke134/life-manager` — decided 2026-08-19, replacing an earlier "start a clean repo" plan |
| A loop's declaration | `loops/<name>/loop.toml` |
| A loop's code | `skills/<name>/` |
| Shared machinery | `lib/` (registry gate, budget), `bin/` (release, plist generation, job install, inventory) |
| Registry and budgets | `config/loop-registry.json`, `config/ceo-budget-config.json` |
| What launchd actually runs | `~/loops/current` → a read-only release under `~/loops/releases/<ts>-<sha>/` |
| A loop's state | `~/loops/<name>/` — outside every release, so a deploy cannot delete a ledger |

`profitable-claude` no longer holds x-repost; it carries a pointer at `docs/x-repost-moved.md`.
The other loops there have not moved yet.

## The commands

```bash
python3 bin/cut-loop-release.sh origin/main            # commit -> read-only release -> current
~/loops/current/bin/lm-loop apply                      # single-owner registry apply + readback
python3 bin/plistgen.py --loops-dir loops --out-dir ~/Library/LaunchAgents --diff   # show only
python3 bin/launchd_inventory.py --format json         # registry vs launchctl, read-only
```

`install.sh` and a single `loops` CLI wrapping these do not exist yet (see below).

## Adding a loop

1. `loops/<name>/loop.toml` — cadence, entrypoint, state dir, env, required credentials
2. `skills/<name>/` — a script that runs ONE pass and exits
3. register it in `config/loop-registry.json` and `config/ceo-budget-config.json`
4. `cut-loop-release.sh` → `lm-loop apply`

No plist is written by hand. The absolute paths are produced at install time, which is what makes
the repo portable to another Mac.

## What is done

| | Evidence |
|---|---|
| Core ported here | budget check reports `enforcement=active`; the gate resolves x-repost and writes cadence `0 */1 * * *` |
| Jobs generated from declarations | the three generated x-repost jobs matched the hand-written ones on every key, and `--diff` now reports all three `unchanged` |
| A job swap proves itself | `lm-loop apply` validates one exact release, swaps one label at a time, reads argv back, and restores on failure |
| x-repost fully migrated | release `20260819T100138-39bfb418` is cut from life-manager, `provenance: ancestor-of-origin-main`; healthcheck runs from it and reports OK |

## What is not done

- **220 of 221 loops still run from a git working tree.** A branch switch there deletes a
  scheduled job's code; it happened to x-repost on 2026-08-17.
- **170 of 241 launchd jobs are in no registry**, so the budget ceiling and the pause switch do not
  reach them. 62 are disabled and 2 have invalid plists.
- **Three of the four gig lanes are served from life-manager releases and one from
  profitable-claude.** Neither `main` holds all four. That owner has not been consulted.
- **No `install.sh`, no `loops` CLI.** The four commands above are still typed individually.
- **Never installed on another Mac.** Until that is tried, "portable" is a claim about the code,
  not an observation.

## Order

1. Move loops one at a time, each proven by a real pass before the next starts
2. Decide the 170 unregistered jobs: register, or stop and remove
3. `install.sh` + `loops` CLI
4. Install on a second Mac and run one loop there
