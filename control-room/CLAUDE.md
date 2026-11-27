# CLAUDE.md — control-room context loader


**One Bible · One Model（Manager）· One Eval（ManagerBench）· One Product（Aniccaモバイルアプリ）** — 成田さん 2026-11-27 t4388u / t4389u. Canonical: https://github.com/Daisuke134/anicca-ops/blob/main/team/BIBLE.md . The four Ones are the engine, not a cap. Many products (6 apps, Capafy, services on every platform, data sales, client work) run on Manager + ManagerBench + the data flywheel. The flagship is the Anicca mobile app. Goal: a monopoly on every platform, App Store included.

## Company rules (GitHub, all agents) — 2026-11-27 t4385u–t4391u

- **RULE LIVENESS-CHECK:** Before assigning work to another worker, run `python3 team/scripts/worker_liveness.py` in [anicca-ops](https://github.com/Daisuke134/anicca-ops) (or read `team/WORKER-LIVENESS.md` if generated in the same minute). Never assign to a DEAD worker. For a STALE worker, assign with an ALIVE backup owner. If every specialist is dead, the assigner (参謀's executor or a Cursor cloud agent) runs the work — do not wait. ALIVE = real self-output or heartbeat within 6h; STALE = 6–48h; DEAD = >48h or never. Routing/ASSIGN lines are not proof of life.
- **RULE IMPLEMENT-ORDER:** Implementation tasks go to Gemini first, then OpenCode, then Command Code. Check liveness first and skip anyone DEAD.
- **RULE ONE-OF-EACH:** One Bible, one model (Manager), one eval (ManagerBench), one flagship product (the Anicca mobile app). Not a cap: many products run on that engine and may be pitched.
- **RULE COMPANY-WIDE-FIX:** When any agent is corrected, put the fix into the shared identity files on GitHub first, not only that agent's own settings or memory. Shared files: `AGENTS.md`, `IDENTITY.md` / `identity.md`, `CLAUDE.md`, `GEMINI.md`, `team/ONBOARDING.md`, `team/RULES.md` in anicca-ops, and the same filenames in the anicca, anicca-products, and life-manager repos.

Canonical rules: https://github.com/Daisuke134/anicca-ops/blob/main/team/RULES.md

> When invoked in this `control-room/` directory, you (Claude / Codex / any
> LLM agent) are acting as an **operator of the Anicca fleet**, not the
> agent itself. Read in the order below before doing any fleet work.

## Priority reading order (every task)

| # | File | Why |
|---|---|---|
| 1 | `README.md` | system map, architecture diagram, what this dir is / is not |
| 2 | `shared/architecture.md` | why 10 profiles per instance × N colony |
| 3 | `profiles/<target-name>/inventory.md` | target profile's role + scope + tools |
| 4 | `profiles/<target-name>/runbook.md` | restart / debug / logs / kickstart |
| 5 | `shared/commands.md` | common ops syntax (`hermes status`, `bws`, etc.) |
| 6 | `shared/security.md` | secret rotation policy, never-commit list |
| 7 | the spec it derives from (`specs/07-HERMES-PIVOT.md` or `specs/05-SERVER-NATIVE-DEPLOY.md`) | authoritative source of truth |

## HARD RULES (inherited from repository root `../AGENTS.md`)

| Rule | Applied here as |
|---|---|
| Superpowers workflow | any change to this directory reads the current applicable skills, verifies, reviews, integrates, and removes the exact worktree |
| Verification before completion | every "done" claim needs fresh evidence (run command, paste output, check exit code) |
| Shared resource safety | serialize edits to the same profile, account, state, or branch |
| Secrets | never paste raw `CDP_*`, `OPENROUTER_API_KEY`, `BWS_*`, wallet privkey, or any value from `~/.openclaw/.env` into any file under this directory |

## What you may NEVER do here

1. Paste raw secrets (any value from `~/.openclaw/.env` or Bitwarden vault).
2. Paste operator personal info (MUFG / マイナンバー / phone / personal Gmail / address).
3. Edit `CONSTITUTION.md` (it is hash-pinned; changes break propagation to children).
4. Copy `~/.openclaw/identity/` contents into any file here (PII isolation).
5. Add a profile without registering it in `shared/architecture.md` § profiles table.
6. Run `git commit` from a sub-agent context unless the operator explicitly approved.
7. Skip the verification gate when claiming a profile is "live."

## What you SHOULD do

1. Read the spec section that the file derives from before editing.
2. Use placeholders sparingly — every file should be useful to a fresh LLM agent.
3. Keep tables where they make the operator workflow clearer.
4. When scope is unclear, resolve it against the applicable repository spec before editing.
5. Cite the spec line numbers when claiming "this is what the system does."

## When operator says "spawn a new instance"

→ `templates/new-instance.md` (Daytona provision + CDP wallet derive + 10-profile copy + Constitution hash verify + colony ledger register).

## When operator says "add an 11th profile"

→ `templates/new-profile.md` (copy template + fill 6 standard files + register in `shared/architecture.md` + restart Hermes).

## When operator says "rotate API keys"

→ `api-keys-sop.md` (Bitwarden update → vault propagation → restart all profiles → verify with `bws secret list`).

## When operator says "the fleet is broken"

1. `hermes status` (= daemon up?)
2. `hermes profile list` (= 10 profiles registered?)
3. `~/.hermes/logs/daemon.err` last 100 lines
4. `profiles/fixer/runbook.md` (= the heal protocol)
5. `profiles/constitution/runbook.md` if hash mismatch suspected

---

**END OF CLAUDE.md.**
