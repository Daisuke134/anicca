# Claude Project Instructions


**One Bible · One Model（Manager）· One Eval（ManagerBench）· One Product（Aniccaモバイルアプリ）** — 成田さん 2026-11-27 t4388u / t4389u. Canonical: https://github.com/Daisuke134/anicca-ops/blob/main/team/BIBLE.md . The four Ones are the engine, not a cap. Many products (6 apps, Capafy, services on every platform, data sales, client work) run on Manager + ManagerBench + the data flywheel. The flagship is the Anicca mobile app. Goal: a monopoly on every platform, App Store included.

## Company rules (GitHub, all agents) — 2026-11-27 t4385u–t4391u

- **RULE LIVENESS-CHECK:** Before assigning work to another worker, run `python3 team/scripts/worker_liveness.py` in [anicca-ops](https://github.com/Daisuke134/anicca-ops) (or read `team/WORKER-LIVENESS.md` if generated in the same minute). Never assign to a DEAD worker. For a STALE worker, assign with an ALIVE backup owner. If every specialist is dead, the assigner (参謀's executor or a Cursor cloud agent) runs the work — do not wait. ALIVE = real self-output or heartbeat within 6h; STALE = 6–48h; DEAD = >48h or never. Routing/ASSIGN lines are not proof of life.
- **RULE IMPLEMENT-ORDER:** Implementation tasks go to Gemini first, then OpenCode, then Command Code. Check liveness first and skip anyone DEAD.
- **RULE ONE-OF-EACH:** One Bible, one model (Manager), one eval (ManagerBench), one flagship product (the Anicca mobile app). Not a cap: many products run on that engine and may be pitched.
- **RULE COMPANY-WIDE-FIX:** When any agent is corrected, put the fix into the shared identity files on GitHub first, not only that agent's own settings or memory. Shared files: `AGENTS.md`, `IDENTITY.md` / `identity.md`, `CLAUDE.md`, `GEMINI.md`, `team/ONBOARDING.md`, `team/RULES.md` in anicca-ops, and the same filenames in the anicca, anicca-products, and life-manager repos.

Canonical rules: https://github.com/Daisuke134/anicca-ops/blob/main/team/RULES.md

@AGENTS.md

Claude-specific: use the imported project contract above. For any Life Manager loop, launchd, release, runtime-event, provider-routing, or cleanup change, read and follow `skills/loop-development/SKILL.md`.

When a repository's documentation and its existing code disagree, follow the conventions used in the existing code, and in your final reply point out each inconsistency you found between the documentation and the code.
