# Anicca — LIVE STATUS / 引き継ぎ書 (single source of truth across sessions)

> ★ ABSOLUTE RULE ★ Every agent / every session MUST read this first and KEEP IT UPDATED in real
> time (status change = edit this file immediately, same turn, then commit+push). Workflows are
> invisible across sessions — this file is how the next agent (or you, post-compaction) knows exactly
> where things stand, what's verified, and what's next. Treat it like a handover note between humans.

**Last updated:** 2026-06-15 (telemetry pipeline E2E-verified against real Supabase)
**Branch:** dev · **Repos:** products=`~/anicca-project`→anicca-products, mother=`~/anicca`→anicca, live runtime=`~/.openclaw` (private) & `~/.hermes`

---

## 0. North star (why)
Anicca = self-funding Buddhist AGI: pays its own compute (ClawRouter) + server (Akash/DO), earns USDC with NO human in the loop, self-replicates, self-improves, reports each wake, ends suffering. Definition of done for each piece = **real side-effect verified (no dry-run, no mock)**.

## 1. The 3 Workflows (WF-A/B/C) — goals in specs
- **WF-A (MONEY-MAKER, `/install`)** — cloud Anicca earns real USDC no-human, self-funds, self-reports, self-replicates, all P&L public on `/dashboard`. Spec: `docs/superpowers/specs/anicca/24` §2, gate in `25`.
- **WF-B (LIFE-MANAGER, `/life-manager`)** — auto-register travel time in gcal + call 15min before (Patter) + Gmail-ask when unknown. Spec `24` §3.
- **WF-C (MARKETING)** — articles + demo video + X. Spec `24` §4. **NEW (Dais 2026-06-15): a Dynamic-Workflows explainer article (with our real build log) must be authored AS a Workflow** — task #93.

Specs index: `docs/superpowers/specs/anicca/13..25` (13=copy, 17=constitution/no-human-keys, 21=test-points, 24=workflow goals, 25=review-findings SSOT). Consolidated design: `docs/superpowers/specs/2026-06-15-anicca-self-funding-agent-design.md`.

**Dais directive 2026-06-15:** before the WF money-loop starts, EVERYTHING must be cleared/verified/review-passed so the workflow runs to its goal (incl. its own verification) WITHOUT stopping. Prep first, then run non-stop.

---

## 2. WF-A subsystem 1 — TELEMETRY PIPELINE  ← CURRENT FOCUS
**Plan (canonical, 6 review rounds passed):** `docs/superpowers/plans/2026-06-15-anicca-telemetry-pipeline.md`
**What it does:** each instance signs `{id,ts,net_worth,...}` with its wallet (EIP-191) → POSTs verbatim `{message,signature}` → Netlify function verifies (signer==id, 60s freshness, per-id monotonic ts) → Supabase `instances` upsert → `dashboard-sync` aggregates → `/dashboard`.

### Architecture reality (verified against live repo — do NOT assume App Router)
| layer | reality |
|---|---|
| landing | `apps/landing` is **static export** (`next.config.mjs output:'export'`). App Router `app/api/*` does NOT run. |
| server runtime | **Netlify Functions** (`apps/landing/netlify/functions/*.js`, CommonJS `exports.handler`, URL `/.netlify/functions/<name>`). |
| CJS marker | `apps/landing/package.json` is `"type":"module"` → `netlify/functions/package.json={"type":"commonjs"}` is **LOAD-BEARING** (without it `node --test` throws "require is not defined in ES module scope"). |
| DB | Supabase **REST** (`fetch ${SUPABASE_URL}/rest/v1/instances`, `apikey`+`Bearer SERVICE_ROLE_KEY`). Project=`cycgdwndgfgdbnndithc` (name "Anicca"). |
| crypto | **ethers v6** `verifyMessage` (CJS-safe; viem is ESM-only, NOT used). |
| tests | **node:test** (Node 20 builtin). Run: `cd apps/landing && node --test 'netlify/functions/_lib/__tests__/*.test.js'` (glob, NOT bare dir — dir arg is Node 21+). |
| signing contract | verify the **VERBATIM** signed bytes (never re-serialize) → python `json.dumps` whole-number `5.0`/`0.0` is accepted, not 401'd. This was a real prod-only bug found in review round 3. |

### Status of plan Tasks 1–9
| Task | what | status | evidence |
|---|---|---|---|
| 1 | ethers dep + CJS marker + test script | ✅ DONE | commit 8483cf5e |
| 2 | schema validator | ✅ DONE | d023a39c |
| 3 | verify (verbatim EIP-191 + freshness + monotonic) | ✅ DONE | df7ef87b |
| 4 | Supabase REST store + `instances.sql` | ✅ DONE (code) + ✅ **table APPLIED to live Supabase** | 8e22f603; table GET→200 |
| 5 | `telemetry.js` POST handler | ✅ DONE | e51b564c |
| 6 | `telemetry-aggregate.js` + `dashboard-sync.js` | ✅ DONE | 462bdb9f |
| 7 | python↔ethers cross-language proof | ✅ DONE | c64385d7 |
| — | **ALL 28 unit tests** | ✅ **pass 28 / fail 0** | `node --test` run |
| — | **LOCAL E2E vs REAL Supabase** | ✅ **PROVEN** | handler→202; dashboard-sync→200 id present total_net=5; Supabase row `{id:0x7099..,net_worth_usd:5,revenue_mo_usd:0}` |
| 8 | genesis droplet report script | 🟡 script written (`~/anicca/skills/report/anicca-report.sh`, local commit 00b00ff) | push BLOCKED by unrelated `~/anicca` pre-push hook (`eval-loop` skill missing); NOT yet scp'd to droplet `/opt/anicca-report.sh` |
| 9 | prod deploy + live HTTP E2E | 🔴 TODO | functions live only on PROD (main→aniccaai.com); **drafts do NOT serve functions** (verified: income-list also 404 on draft) |

### ★ CRITICAL repo-structure finding (2026-06-15) ★
- **`dev` and `main` have NO COMMON ANCESTOR (unrelated histories)** — `git merge-base origin/main origin/dev` = empty. They are two separate trees in one repo (the 2026-06-09 unrelated-histories incident, still unresolved). All telemetry/specs/plans/STATUS work is on **`dev`** (orphan); aniccaai.com deploys from **`main`** (the real trunk).
- **`main` is correct for function deploys:** its GHA already uses `netlify deploy --dir=out --functions=netlify/functions --prod --no-build` (commit `8e5027b7` added `--functions` precisely because "functions never deployed"). `main` has NO telemetry. `dev`'s older GHA lacks `--functions`, which is why dev **drafts never serve functions**.
- **Implication:** cannot `gh pr` dev→main (unrelated). To ship telemetry to prod, **re-apply the telemetry files onto a branch off `main`** (they are all ADDITIVE — `main` has none of them, so no conflicts): `git checkout -b feat/telemetry origin/main` → `git checkout origin/dev -- apps/landing/netlify/functions/telemetry.js dashboard-sync.js _lib supabase/instances.sql netlify/functions/package.json` → on that branch `npm i ethers@^6` + add `test:telemetry` script to MAIN's package.json (do NOT overwrite main's package.json with dev's) → run tests → PR → main → GHA deploys with `--functions` → telemetry live. (Bigger separate issue for Dais: dev↔main reconciliation — lots of work lives on the orphan dev.)

### Remaining to finish telemetry (do these, in order)
1. **Deploy function to prod aniccaai.com via the re-apply-onto-main path above** (NOT a dev→main merge — impossible, unrelated histories). main's `--functions` GHA will bundle it.
2. **Verify prod:** `curl -s -o /dev/null -w '%{http_code}' https://aniccaai.com/.netlify/functions/telemetry` → expect 405 (GET); then the signed-5.0 smoke (plan Task 9 Step 2) → 202.
3. **scp report script to droplet + genesis E2E:** `scp ~/anicca/skills/report/anicca-report.sh root@147.182.225.255:/opt/anicca-report.sh; ssh root@147.182.225.255 'chmod +x /opt/anicca-report.sh; pip install -q eth_account; bash /opt/anicca-report.sh'` then `curl .../dashboard-sync` shows the genesis wallet id present with real on-chain net worth.

---

## 3. Credentials (LOCAL, never commit) — `~/.openclaw/.env`
| key | use |
|---|---|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_ANON_KEY` / `SUPABASE_ACCESS_TOKEN` (sbp_6aae…, valid) | telemetry store + Management API DDL. Mgmt API: `POST https://api.supabase.com/v1/projects/cycgdwndgfgdbnndithc/database/query` `{query}` (after DDL run `notify pgrst,'reload schema'` or REST 404s). |
| `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID` (anicca2) | deploy functions to aniccaai.com. |
| `BLOCKRUN_WALLET_KEY` (also on droplet `/opt/anicca.env`) | genesis agent wallet privkey; addr derived = telemetry id. |
| `AGENTMAIL_API_KEY` | per-wake email (anicca-genesis@agentmail.to). |
| Droplet | genesis automaton @ `root@147.182.225.255`, `systemctl is-active automaton`=active. |

## 4. Live infra map
- **aniccaai.com** = Netlify site `anicca2`, prod=`main` branch (GHA `netlify-deploy.yml`), staging/preview=`dev` (drafts, NO functions). Static export → functions are the only server runtime.
- **Supabase `Anicca`** (cycgdwndgfgdbnndithc): tables `fashion_orders` (existing), `instances` (NEW, telemetry, RLS on, service-role only).
- **genesis automaton** droplet 147.182.225.255: ReAct loop + heartbeat; pre-sleep hook fires `/opt/anicca-report.sh`.

## 5. Open tasks (TaskList ids)
- #89 TELEMETRY-EXEC (Tasks1-7 ✅ / 8 🟡 / 9 🔴)  · #90 Task8 droplet  · #91 Task9 deploy+E2E  · #92 THIS handover doc  · #93 Dynamic-Workflows article-in-workflow.
- GATE-0 for WF-A launch (spec25 C2): **1 profitable wake** (earn > cost, 1 real tx) — still ❌, the true money-loop blocker (#49/#78/#79 earn).

## 6. How to continue (next agent checklist)
1. Read this file + `docs/superpowers/plans/2026-06-15-anicca-telemetry-pipeline.md` + spec `24`/`25`.
2. Finish §2 "Remaining" (deploy → verify → genesis E2E). Update this file's Task-9 row to ✅ with the prod curl evidence.
3. Then build the Dynamic-Workflows article (#93) AS a Workflow, using the real build log in §2 (the round-3 prod float bug + round-4 deployment-reality correction are the story).
4. Keep this file current every turn. Commit+push every meaningful edit (HARD 0.00).
