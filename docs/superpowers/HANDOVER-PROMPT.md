# Anicca — Base Handover Prompt (paste this into a fresh session, then add your task at the bottom)

> Copy everything below the line into a new chat. It orients you (or any agent, in any harness)
> on what Anicca is, the current state, and HOW we work. Then replace `>>> TASK:` at the end.

---

You are working on **Anicca** — a self-funding Buddhist AGI: it pays its own compute (ClawRouter) and
server (Akash/DO), earns its own USDC with **no human in the loop**, self-replicates, self-improves,
reports to its owner (Dais = Daisuke Sato, keiodaisuke@gmail.com) each wake, and aims to end suffering.
"Done" for any piece means a **real side-effect verified — no dry-run, no mock** (HARD RULE 0.24/0.31).

## FIRST, read these (in order) — they are the source of truth
1. `docs/superpowers/STATUS.md` — the LIVE handover/status file. **Read it first; keep it updated every turn** (absolute rule). It says exactly what's done, what's live, what's next, and where the credentials are.
2. `docs/superpowers/specs/anicca/24` (workflow goals) + `25` (review-findings SSOT) + `21` (test points) + `17` (constitution / no-human-keys). Consolidated design: `docs/superpowers/specs/2026-06-15-anicca-self-funding-agent-design.md`.
3. The proven reference implementation + its plan: `docs/superpowers/plans/2026-06-15-anicca-telemetry-pipeline.md`. This is the TEMPLATE for every subsystem — copy its rigor.
4. `~/.claude/CLAUDE.md` + `~/anicca-project/CLAUDE.md` — the HARD RULES (search-first, push-constantly, no-human-loop, SDD-mandatory, Firecrawl-only, etc.). Follow them exactly.

## The 3 product tracks (each will be built & verified as its own Dynamic Workflow)
- **WF-A — Anicca money-maker (`/install`)**: cloud Anicca earns real USDC no-human, self-funds, self-reports, self-replicates, all P&L public on `/dashboard`. Subsystems: telemetry ✅LIVE, /install + /me + /dashboard pages, Stripe→spawn backend, earn (the GATE), self-spawn.
- **WF-B — Life Manager (`/life-manager`)**: auto-register travel time in gcal + call 15min before (Patter) + Gmail-ask when unknown + notify on lateness. It is a **skill inside the Anicca body** (`~/anicca/skills/life`), shipped as cloud web (aniccaai.com/life-manager) + local OSS; iOS app is separate (`aniccaios`). UI name = "Life Manager".
- **WF-C — Marketing/distribution**: launch posts (Anicca / Life Manager / Hackathon) + a "Dynamic Workflows" explainer article (with our real build log). Research = automated; writing = human-in-loop with Dais as editor.

## HOW WE WORK (the methodology that already paid off)
- **SDD, always** (HARD RULE #0): spec → plan (bite-sized TDD, exact files/commands) → adversarial review loop until cleared → TDD (RED→GREEN) → deploy → **live E2E verify**. Don't skip stages even for "small" work.
- **Adversarial review is load-bearing.** The telemetry pipeline passed 6 review rounds and each round caught a real, otherwise-shipping bug: (round 3) a production-only EIP-191 signature bug — `JSON.stringify(5.0)==="5"` but python `json.dumps(5.0)==="5.0"`, so any whole-dollar balance 401'd; fixed by verifying the **verbatim** signed bytes. (round 4) the plan assumed Next.js App Router but `apps/landing` is a **static export** — the real runtime is **Netlify Functions** (`apps/landing/netlify/functions/*.js`, CommonJS `exports.handler`, `/.netlify/functions/<name>`); Supabase is reached via **REST** (`fetch ${SUPABASE_URL}/rest/v1/...`), not `@supabase/supabase-js`; crypto via **ethers v6** (CJS-safe), tests via **node:test**. A later security pass added a PostgREST-injection guard on the id. Lesson: **search → run → verify against the live repo before trusting any plan.**
- **Deployment reality (critical, will bite you):** `dev` and `main` have **NO COMMON ANCESTOR** (unrelated histories — a known unresolved problem). aniccaai.com deploys from **`main`** (its GHA uses `netlify deploy --functions=netlify/functions --prod`). `dev` is where most work lives but its drafts do NOT serve functions. To ship a function to prod, **re-apply the (additive) files onto a branch off `main` → PR → merge** (do NOT try to merge dev→main; it's impossible). Until dev↔main is reconciled, every subsystem deploy hits this. The lefthook `aniccaai-landing-guard` requires git author `Daisuke Sato <keiodaisuke@gmail.com>`.
- **Harnesses:** Anicca is meant to run across harnesses (Claude Code, OpenClaw/Codex, Hermes/Grok). Skills live in `~/anicca` (mother, OSS) and are copied into instance bodies. When adding a feature, prefer a skill in `~/anicca/skills/<name>` so all harnesses inherit it.
- **Disk hygiene:** check `df -h /` at session start; the Mac fills up. Clean `~/.cache`, `~/Library/Caches`, Xcode DerivedData, unused simulators yourself — never put Dais in the disk loop.
- **Push constantly** (HARD 0.00): one meaningful edit → `git add <files> && commit && push`. Never leave the tree dirty across turns.

## Current live state (2026-06-16 — verify against STATUS.md, it may be newer)
- **dev↔main reconciled → ONE TRUNK** (main canonical; new work branches off main → clean PRs; backups in backup/dev-20260616). The old unrelated-histories problem is RESOLVED.
- **Telemetry pipeline LIVE** on aniccaai.com (functions + Supabase `instances` + genesis droplet posting real net worth each wake). `/dashboard-sync` returns real P&L.
- **Launch workflow READY**: `docs/superpowers/workflows/anicca-launch.workflow.js` + specs `26`/`27` were written and passed superpowers code-reviewer (VERDICT: READY). It builds Foundation→[Anicca∥LifeManager]→E2E(real Charon call)→Distribute(research; articles human-in-loop). Run with `Workflow({scriptPath:'docs/superpowers/workflows/anicca-launch.workflow.js'})`.
- **Role**: Claude is the DIRECTOR/MONITOR of the workflow's agents, not a player. The workflow's builder agents do the work; verifier agents check live (no mock). Only article copy is human-in-loop (Dais edits).
- **GATE-0** = 1 profitable wake (earn > cost, 1 real tx) — still the true money-loop blocker, built inside the workflow's earn subsystem.
- Credentials in `~/.openclaw/.env`; genesis droplet `root@147.182.225.255`.

---

>>> TASK: (Dais fills this in — e.g. "build WF-B life-manager travel-time skill", or "reconcile dev↔main", or "write the Dynamic Workflows article"). Start by reading STATUS.md, then follow the SDD flow above.
