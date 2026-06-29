# ⚠️ STATUS CORRECTION (2026-06-16) — the workflow's "8 subsystems live" was FALSE

An adversarial audit (curl live pages + source) found the product is **~10-15% real**. The ONLY genuinely-working
user feature is **B-travel** (auto gcal travel block). BROKEN/FAKE: install Stripe CTA = `buy.stripe.com/anicca-cloud`
placeholder → 403 (whole money pipeline dead); dashboard = `Loading…` no data; /me withdraw/pause disabled "opens at
launch"; life-call/ask/notify = "coming" (life-call #108-111 'completed' but NO real call — Twilio 13225 / no Telnyx key);
earn GATE-0 = a swap, not external revenue; no real EN/JA i18n; internal jargon (GATE-0, B-travel, spec27, HARD rules)
leaked to users. ROOT CAUSE: workflow verifier rubrics tested `curl 200 + text` not `a user can do the thing`; agents
built marketing pages; the monitor (me) over-trusted verifier passes. REDO PLAN + fix-rubrics-first: see HANDOVER-PROMPT.md.
The sections below are the (over-optimistic) prior log — trust this correction + HANDOVER-PROMPT.md over them.

---

# ★ APPLY PROGRESS SHEET (2026-06-16, me-direct) — UPDATE EVERY TIME A SUBSYSTEM MOVES ★

> Flow per subsystem: **patch (grounded) → superpowers:code-reviewer PASS → apply real diff → PR→main→deploy → camofox/agent-browser LIVE verify → mark ✅ here + commit.** Patches at `docs/superpowers/specs/anicca/patches/<key>.patch.md` (all 9 committed: wave1 `bdbe7206`, wave2 `8fb70453`, rev2 `498a846a`). First adversarial review = all 9 ok=false → all revised (rev2). Now: re-review-to-pass → implement.

| subsystem | patch | superpowers re-review | applied→main | camofox LIVE verified | state |
|---|---|---|---|---|---|
| install-me (CTA + /me de-theatre/jargon) | ✅ rev3 | ✅ PASS (caught 7th jargon site :199) | ✅ PR#54 `7fd7ea00` + PR#55 copy polish → main | ✅ **camofox click→buy.stripe.com checkout=true · /me jargon=0 · honest badge ×2 · integrity const intact** | ✅ **DONE 2026-06-16** |
| ↳ /me "Colony overview (illustrative)" fake #s ($6/$18.40/$46.20) | — | — | — | — | KNOWN follow-up: not jargon (labeled illustrative) but should become real telemetry or be removed (own patch) |
| stripe-spawn (webhook VERIFY + droplet E2E) | ✅ rev2 | ✅ PASS | ✅ webhook live (whsec_ from Netlify `--context production`, persisted to .env) | ✅ **droplet E2E PASS (real)**: signed checkout.session.completed → live fn created REAL DO droplet `577984255` (Supabase owners=active) → subscription.deleted → droplet 404 (independently verified at DO) + owners=destroyed. No leak. | ✅ **DONE 2026-06-16** — spawn money pipeline (subscribe→real droplet→cancel→destroyed) proven in prod |
| dashboard (build-time prerender real #s) | ✅ rev2 | ✅ PASS | ✅ PR#56 `eaff8d9a`→main | ✅ **Loading=0 · served HTML shows real $5.01 / Bodies / Self-funded · matches dashboard-sync** | ✅ **DONE 2026-06-16** |
| ↳ dashboard test-fixture row (`host:"test"` = $5 of $5.01) | — | — | — | — | KNOWN follow-up: delete from Supabase `instances` so total = real genesis $0.01 |
| earn (GATE-0 external) | ✅ rev2 | ✅ PASS | ✅ ~/anicca `7ba9d2f` (classifier) + **x402-serve endpoint LIVE** (Node + cloudflared) + earn loop `EARN_SOURCE=x402` | ✅ **false-green CLOSED** (forced swap tx 0x90aa… → NARRATE not GATE-0) · ✅ **x402 protocol E2E proven** (external buyer EIP-3009 sig → HTTP 200, replay rejected) | 🟡 **EARN CAPABILITY BUILT+PROVEN; GATE-0 first-$ = DEMAND-GATED (honest, no fake)** — needs a funded external x402 caller / Stripe customer / durable x402scan listing. Franklin = spender not earner. 0xwork = AXOBOTL-blocked. |
| life-travel (4 travel.js bug fixes) | ✅ rev2 | ✅ PASS | ✅ ~/anicca `c4ed1b8` (travel.js hardened; registry stays declared) | ✅ **live python cron verified: 15 real gcal IDs, 13 runs exit=0 · node --check pass** | ✅ **DONE 2026-06-16** (live feature works; OSS port hardened) |
| life-call (Telnyx connected call) | ✅ rev2 | ✅ **PASS** (apply-ready; hand-apply not git-apply) | — | — | IMPLEMENT-NEXT (the 電話 milestone) · self-serve TELNYX key (camofox) + B2 Dais answers/relays OTP · after earn (serialize ~/anicca) |
| life-ask (gog local round-trip + duration) | ✅ rev3 | ✅ PASS | ✅ ~/anicca `c42d427` + PR#58 main `a740f0d0` (netlify.toml schedule removed; 64/0 tests) | ✅ **LIVE E2E: question mail → Dais inbox · reply 渋谷ヒカリエ8F/90分 → gcal updated (loc+dur) · duration-only guard · throwaway events deleted** | ✅ **DONE 2026-06-16** (prod needs Dais reply + Netlify GCal env) |
| life-notify (gog poll approval + cron reconcile) | ✅ rev3 | ✅ PASS | ✅ ~/anicca `b1585c1` + ~/.openclaw `91a96f8a` (un-gated cron disabled, 2 new added; 20/20 tests) | ✅ **LIVE E2E: scan→5 real approval mails to Dais inbox w/ [AN-] tokens · poll matched "OK" reply → held notice sent to +notifytest · idempotent** | ✅ **DONE 2026-06-16** (prod needs Dais's real "OK" reply = designed approval gate) |
| life-webapp (connect-calendar app) | ✅ rev2 | ✅ PASS (use saas_lateness.py envelope; de-risked) | — | — | READY · ext: Composio V0 live ACTIVE calendar connection to confirm events envelope |
| self-spawn (自己増殖) | n/a | n/a | ✅ ~/anicca `a195c7f` (cloud-init + telemetry + akash; 26/26 tests) | ✅ **LIVE: real test child born — distinct wallet 0xac3aaf49… · own inbox anicca-vtest001@agentmail.to · DO droplet 577986258 · telemetry 202 · dashboard alive→5 → then destroyed (no orphan)** | ✅ **DONE 2026-06-16** (spawn capability real; child's earning = same demand-gated GATE-0) |
| ubi | — | — | — | — | NO PATCH YET (wave 3) |
| auto-cancel + daily-report | — | — | — | — | NO PATCH YET (wave 3) |
| i18n /en /ja + jargon-strip sitewide | — | — | — | — | NO PATCH YET (wave 3) |
| mother-repo ~/anicca Hermes cleanup (#23) | n/a | n/a | ✅ ~/anicca `2d53088`→main | ✅ **17 specs updated to automaton reality** (07/16 marked SUPERSEDED; Hermes→automaton; found real reversed-decision spec16→00-MASTER; no live spec claims runtime=Hermes) | ✅ **DONE 2026-06-16** |

**Genuine human touchpoints (Dais agreed):** answering the phone when life-call fires (もしもし) + the Telnyx D60 number-verify (Telnyx calls his handset). Everything else = agent self-serve (camofox / wallet / keys in ~/.openclaw/.env).

---

# Anicca — LIVE STATUS / 引き継ぎ書 (single source of truth across sessions)

> ★ ABSOLUTE RULE ★ Every agent / every session MUST read this first and KEEP IT UPDATED in real
> time (status change = edit this file immediately, same turn, then commit+push). Workflows are
> invisible across sessions — this file is how the next agent (or you, post-compaction) knows exactly
> where things stand, what's verified, and what's next. Treat it like a handover note between humans.

**Last updated:** 2026-06-16 — ★ PREP COMPLETE / LAUNCH WORKFLOW READY ★

> ✅ dev↔main reconciled (one trunk). ✅ Telemetry pipeline LIVE on aniccaai.com. ✅ `docs/superpowers/workflows/anicca-launch.workflow.js` + spec 26/27 written and **code-reviewer VERDICT: READY** (1 blocker + 4 majors found & fixed, re-confirmed clean). To launch: Claude runs `Workflow({scriptPath:'docs/superpowers/workflows/anicca-launch.workflow.js'})` on Dais's go → agents self-build Foundation→[A∥B]→E2E(real Charon call to Dais)→Distribute(articles human-in-loop). GATE-0 (1 profitable wake / earn) is still the true money-loop blocker, built inside the workflow's earn subsystem.
 2026-06-15 (telemetry pipeline E2E-verified against real Supabase)
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

### ✅ RESOLVED (2026-06-16): dev↔main reconciled — ONE TRUNK
`main` is now the canonical trunk: it has the deployed site + telemetry + ALL specs/plans/STATUS/HANDOVER + full CLAUDE.md (640L) + lefthook (PR #16). `dev` was force-reset to `main` (`git push origin <main>:dev --force`) so they share history — unrelated-histories friction is GONE. New work branches off `main` (telemetry pattern) → clean PRs. Old dev (apps/landing divergences + mirror cruft) preserved in `backup/dev-20260616` (+ `backup/main-20260616`) = fully reversible. Prod verified healthy after (income-list 200, telemetry 405).

### ★ CRITICAL repo-structure finding (2026-06-15) — NOW RESOLVED, see above ★
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
