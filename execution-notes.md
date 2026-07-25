# execution-notes.md — sprint-4 M1+M2

## Active /goal
`GOAL-sprint-4-M1-M2.md` (mailed to Dais via Resend id `0493d1f1-...`).

## Sub-feature status

| # | feature | phase | notes |
|---|---|---|---|
| a2 | earnings-to-settle-mirror | ✅ COMPLETE (Phase 6) | Full pipeline PROVEN LIVE on production gig: p-1782887987 roi 0→25000 |
| a1 | LAYER C STARTUP prompt update | ✅ DEPLOYED 2026-07-01 | 3 injections in gig-cli.sh: PRE-B1 CURRENT_PASS_ID binding from oldest tasks/*.json; B2 per-apply task-request-map.jsonl append; EARNED CHECK jq exact-match historical pass_id lookup + task-request-map.errors.jsonl fallback. Restarted per REQ-L3, --status=ALIVE < 30s. M2 auto-closes on first real Coconala 検収. |
| b | earn-roi-reconciler | ✅ COMPLETE | Feature (b) sprint-4 done |
| c | dispatcher-live-dormant | ✅ COMPLETE | Phase 6 converged + live E2E on prod gig; .slot_created marker deployed |
| d | recipe-6-actions | ✅ COMPLETE | 6 real wires (kill_server/send_keys/login/npm_install/git_checkout/escalate_via_bot2bot); 503 tests GREEN; INV-P1/INV-4 preserved |

## Milestone gates
- ✅ **M1** (settle pipeline ready) — reconciler + mirror COMPLETE. Full flow PROVEN LIVE.
- ⏳ **M2** (first real ¥) — pipeline FULLY WIRED including (a1) STARTUP update. Waiting on first real Coconala 検収 in production. Loop is LIVE via launchctl `ai.anicca.gig-proactive` (5-min tick) + hourly reconciler menu item.

## Regression baseline
503/503 tests GREEN.

## Block conditions
1. No settle event in 30 days across ANY slot
2. INV regression uncloseable in 3 iters
3. crypto primitive fails

## sprint-4 (a1) post-deploy notes (2026-07-01)

- (a1) STARTUP deployed successfully; gig-cli.sh --status=ALIVE
- **task #6 hook fix**: `~/.claude/settings.json` PreToolUse:Bash hook was `rtk hook claude` (PATH-dependent). Headless tmux sessions couldn't resolve `rtk` → repeated "PreToolUse:Bash hook error". Fixed by pinning to `/opt/homebrew/bin/rtk hook claude`. Post-fix: session runs clean, no more hook errors.
- **First post-fix pass**: correctly detected concurrency (multiple restarts + healthcheck cron) and skipped browser-driving to avoid collision. Registered cron `52b154a2` for future ticks. This is the CORRECT anti-collision behavior spec'd in HARD 0.36's INV-4.
- **task-request-map.jsonl materialization**: waiting for first uncontested B2 apply pass (next hourly cron fire).
- M2 auto-close path: unchanged. First real Coconala 検収 → gig-cli.sh a1 lookup → earnings row w/ pass_id → (a2) mirror → (b) reconciler → roi_jpy_realized > 0 → M2 satisfied.

## task #2 diagnosis (2026-07-01)

- `~/clips/queue/` is empty because it's fed by `producer.sh` (creates mp4+caption)
  while the proactive-loop dispatcher enqueues `produce-clip` task descriptors to
  `~/loops/clip/tasks/` (34 descriptors queued, 5-min tick, none consumed).
- The clip LAYER C session's STARTUP (`clip-cli.sh:21`) only invokes `run.sh`
  (POSTS from queue), never `producer.sh` (FILLS queue). No consumer bridges
  `~/loops/clip/tasks/` → `producer.sh`.
- FIX (out of scope for M2 sprint-4, deferred to sprint-5): mirror the gig-cli.sh a1
  pattern in clip-cli.sh STARTUP:
    1. Read oldest `~/loops/clip/tasks/*.json`
    2. If `picked.name == "produce-clip"`, invoke `producer.sh` with the task's
       platform/params
    3. Move the consumed task descriptor to `~/loops/clip/tasks/done/`
- Impact: without this fix, `produce-clip` tasks pile up indefinitely and no
  clips are ever posted. NOT a M1/M2 blocker (gig is the M1/M2 primary slot).
- Sprint-5 candidate feature: `clip-cli.sh a1-equivalent` for task-descriptor
  consumption + producer.sh wire.

## task #5 status (山本さん #5123100 あい庵 SNS ¥40k/月) — CLOSED/lost

Full timeline from gig data (2026-06-30 → 07-01):
1. Applied w/ site-specific 3-improvement proposal — buyer replied "契約手続きを進めたい"
2. Formal 見積り sent via direct_offer/4857277 (¥40,000/月, 定期購入, 期限 7/7)
3. Two follow-ups sent (2026-06-30 23:38, 07-01 01:17)
4. **Result**: 公開募集終了 + direct_offer/4857277 → 404 (offer link dead)
   → outcome=`ignored_closed`, lesson: "高額見積りは決断を促す締切設定が必要"

M2 candidate: NO (deal closed). The gig-cli.sh a1 pipeline still stands
ready for the next buyer that reaches 検収 stage. Cron 52b154a2 next
:27 tick continues the discovery.

## task #6 follow-up: hook wrapper (2026-07-01, deeper root cause)

- Absolute-path fix (`/opt/homebrew/bin/rtk hook claude`) alone was NOT enough.
- Continued observing "Failed with non-blocking status code:
  node:internal/modules/cjs/loader:1458" in gig session — Claude Code's own
  internal Node.js error trying to interpret rtk's empty stdout on
  non-rewrite pass-through cases.
- FIX: `/Users/operator/.claude/hooks/rtk-hook-wrapper.sh` (installed +
  settings.json pointed at it) — always emits valid JSON:
  * rtk rewrite? → forward rtk's JSON
  * rtk silent? → emit `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}`
- Will take effect on next gig-cli restart (currently: 28min-subagent completed
  with 0 applies but tmux still ALIVE; no active hook errors right now).

## task #6 further follow-up: wrapper newline (2026-07-01, +30min)

- After installing rtk-hook-wrapper.sh, hook errors REDUCED but not to zero
  (dropped from 8+/500lines to 3/500lines).
- Root cause: wrapper output was missing trailing newline (`printf '%s'` →
  `printf '%s\n'`). Some Claude Code hook parser paths need line-terminated
  output.
- After fix + gig-cli --restart: session progressing through Coconala gig
  pass 45 with proper phase structure (B1 nurture → B2 apply → B3 learn →
  B4 improve → B5 share → finalize + .last-pass).
- Expected: task-request-map.jsonl materialized during B2 apply; task #1
  verified on B5+finalize.

---

## 8i REPO-CONSOLIDATE — execution log (in progress)

**Source:** Daisuke134/anicca-products @ `540b7a428e8e259e47acaa715812802fdb19f947`, path `apps/life-call/`
**Target:** Daisuke134/life-manager (id 1248111245), path `apps/life-manager/`
**Branch:** `claude/life-manager-e2e-handover-qkp2q6`

### Completed gates
- [x] Read-only source access obtained (add_repo, shallow clone at /workspace/anicca-products)
- [x] Source manifest: 184 tracked files under apps/life-call (183 migrated, .vcsdd/ metadata excluded)
- [x] Snapshot copy apps/life-call -> apps/life-manager (183 files) + canonical spec -> docs/superpowers/specs/
- [x] Byte-equivalence proven: 0 diffs across all 183 files (docs/manifests/8i-life-call-source-manifest.txt, sha256 per file)
- [x] Secret/PII scan: clean (only synthetic fixture phones, no keys/real PII)

### Remaining gates (blockers noted)
- [x] Focused tests on migrated lib/** (all green)
- [x] Full Life Manager test suite: 633 TAP pass / 0 fail (reviewer-measured; earlier 606 was a count-method imprecision)
- [x] Every eval suite: calendar 21/21, late 12/12, context 12/12, score 27/27, panel-privacy pass
- [x] Production build smoke: server.js/scheduler.js syntax OK; nixpacks entrypoints valid
- [x] Fresh-context adversarial review from detached candidate commit 8752cf35: VERDICT APPROVE, 0 blockers, 7 notes (manifest 183/183 sha256 verified vs source AND target; exactly 1 differing line = documented path rename; boot with empty env verified; history-safety PASS)
- [ ] Normal PR + merge
- [ ] Railway deploy of exact merged commit  — NEEDS Railway credentials
- [ ] Prove active Railway commit == canonical main
- [ ] Real production L3: /health, Telegram, canonical /panel  — NEEDS production access
- [ ] Archive + redirect anicca-products (ONLY after cutover)  — NEEDS admin on source repo

### Adversarial review notes (2026-07-24, fresh-context agent, commit 8752cf35)
- APPROVE. Non-blocking notes: test-count label (633 actual), landing subset is 5 migrated + 1 new README, Mac-host paths in daily-preflight-collectors.js carried byte-identically (gateway-host code, not Railway boot), residual "life-call" identity strings consistent, diff secrets/PII clean.
- Reviewer flagged PRE-EXISTING PII on main (predates this PR): execution-notes.md task #5 section names a Coconala counterparty. Scrub separately — public repo.
- Railway boot check: server.js starts with EMPTY env (PORT defaults, no boot-required secrets); all providers lazily guarded.

## 10g BRAIN-a — done (2026-07-24, L2)
- intent-graph.js closed schema (6 kinds, provenance/confidence/expiry), correction-expires-prediction contract, 3 persona fixtures. Tests 7/7; full suite fail 0. Spec §10 row updated in same commit.

## 10h BRAIN-b — done (2026-07-24, L2)
- opportunity-engine.js six-factor gate over 10g graph; intent-cases.jsonl 18/18 (100%); contract 4/4; wired into test+eval chains; full suite fail 0. Spec §10 updated (26 pending).

## 12a MEN-a — done (2026-07-24, L2)
- mental-trigger.js context-driven trigger engine (pre_event/between_events/pre_sleep), cap 3/day, fixed-time impossible by construction; men-cases.jsonl 15/15 (100%); contract 4/4; full suite fail 0. Spec §10 updated (25 pending).

## 11a PHY-a — L2 done (2026-07-24); L3 (real calendar detection) pending
- care-detector.js personal-cadence + explicit-goal detection, no fixed cycle (0-1 visits never flag), no diagnosis fields; phy-cases.jsonl 12/12 (100%); contract 4/4; full suite fail 0. Spec §10 updated (row stays pending, L2 recorded).

## 8i REPO-CONSOLIDATE — DONE (2026-07-24, production cutover complete)
- Cutover executed on the Mac-side agent with Railway access: service re-pointed to life-manager/apps/life-manager, active deployment 6806b0d4 = commit a7ac84d4 (exact main), /health 200 build lm27-voicemail-v1, zero-downtime 358/358, real TG message id 217, authenticated /panel all sections 200.
- Independently verified from cloud session: anicca-products archived=true via GitHub API readback; evidence report in docs/evidence/8i-cutover-report.md (PR #1077); merge containment of a7ac84d4 in origin/main.
- §10: 8i done. Pending count 24.

## 9b MKT-b / M-2 — done
- Existing `ai.anicca.life-manager-daily` label, 10:15 cadence, rotation, account, and shared
  agent-runner remain in place. The slideshow/card creative contract is replaced by the canonical
  16-row local FFmpeg video renderer.
- TDD: missing generator/runtime RED, then generator `5/5` and runtime/launchd `6/6` GREEN.
  Controlled method 1 exposes recursive wrapper invocation; corrective exit-73 guard is RED→GREEN.
  Method 2 exposes combined generation/distribution self-monitoring; it is stopped before side
  effects. Method 3 locks distribution for 9c and succeeds as a bounded generation-only pass.
- Fresh Luna probe returns `LM_LUNA_PROVIDER_OK`. launchd run count advances and finishes exit 0
  with `marketing-agent` → `luna-medium-decision` → `codex/gpt-5.6-luna`, attempt 1.
- Production rotation reads back A01/A02/A03 on three consecutive logical days. All three are
  1080×1920 H.264/AAC, 34.666667s and fresh full-decode exit 0.
- Runtime ledger records provider-reported token counts, subscription cost tier, null unavailable
  provider-equivalent price, and actual marginal cost USD 0 without inventing a price.
- PR #1079 security-gate audit: accepted main run 30069163816 already has the identical
  repository-wide baseline failures (PII shapes 60, gitleaks findings 24, Python workflow missing
  pytest/hypothesis). Changed-path secret scan and every 9b test/eval pass; no detector or test is
  weakened to make the PR green.
- Evidence: `docs/evidence/9b-marketing-video-runtime.md`. Pending count becomes 23; next is 9c.

## 9c MKT-c / M-3 — done
- Reuses the existing `anicca.affirms2` IG account, shared instagrapi poster, and TikTok Postiz
  integration `cmp9txjdp01c8oh0yb6dhlarr`; no account or loop is created.
- TDD binds the same local MP4 and caption file to both adapters and records the same creative id,
  video SHA, and caption SHA in a mode-600 append-only ledger.
- Real IG Reel: `https://www.instagram.com/reel/DbKkdfjsaTZ/`; deterministic logged-out checker
  returns `found=true`, `verdictMaterial=pass`.
- Real TikTok video:
  `https://www.tiktok.com/@anicca_buddha/video/7665973874504256785`; provider id
  `cmryjod3q0193pe0yastxx34h`; logged-out metadata and full public decode pass.
- Corrective TDD rejects Postiz's profile-only release URL and resolves only a recent,
  caption-matching `/video/<id>` artifact. The original profile-only private ledger row remains
  append-only and honest.
- Corrective launchd pass exits 0 on Luna, distribution ledger stays `3→3` (no repost), and the
  existing Telegram report returns message id `3378`.
- Evidence: `docs/evidence/9c-marketing-distribution.md`. Pending count becomes 22; next is 9d.

## 9d MKT-d / M-4 — started; real-time gate pending
- Adds an append-only, mode-600 daily metrics ledger keyed by real JST date and the exact 9c
  creative/video/caption hash pair. Same-day runs are idempotent; gaps reset the streak; simulated
  backfill cannot satisfy the seven-day gate.
- Real Day 1 reads Instagram `17/0/0` and TikTok `9/0/0` views/likes/comments from their public
  URLs. Unavailable watch-time/completion/click/signup values remain null.
- Corrective TDD fixes the integration schema from `reason` to canonical `next_change_reason`.
  Core/runtime tests are `5/5 + 8/8`.
- Controlled launchd finishes exit 0 with Luna attempt 1, distribution `3→3`, measurement `1→1`,
  and real Telegram message id `3379`.
- Evidence: `docs/evidence/9d-marketing-self-improve-started.md`. Pending count remains 22 because
  six distinct real dates remain; cursor advances to independent row 9e.

## 9e MKT-e — equivalence PASS; authentication gate pending
- Direct TikTok Studio adapter uses the existing CloakBrowser CDP context, exact MP4/caption paths,
  and the same terminal fields as Postiz. It requires individual public URL, exact logged-out
  readback, real date, and direct cost USD 0.
- Distribution/direct tests are `10/10 + 8/8`. Only two consecutive real direct days can retire
  Postiz; duplicate/gap/simulation/failure rows cannot.
- Postiz remains the default and its ledger stays at three rows. The exact direct migration env
  gate remains unset.
- Real target login reaches TikTok email verification, but the designated masked mailbox is absent
  from connected Gmail, Keychain/env, and an authenticated domain mail route. No code is guessed,
  no file is uploaded, and no post is created.
- Evidence: `docs/evidence/9e-tiktok-direct-migration-started.md`. Pending remains 22; next is 9f,
  whose Phase 1 prerequisite is evaluated before any X handoff.

## 9f MKT-f — prerequisite blocked; no owner handoff
- A closed gate reads the canonical §10 statuses for 8e/8f/9b/9c/9d/9e. The live blockers are
  `8e, 8f, 9d, 9e`.
- Live output keeps both owner handoff and agent posting false. X credential/session/draft/upload/
  post side effects are zero.
- Even with all prerequisites done, the gate permits only a minimal owner handoff and never agent
  impersonation. A real owner status URL makes the launch permanently one-time.
- Contract tests are `5/5`. Evidence: `docs/evidence/9f-x-owner-launch-blocked.md`.
- Pending remains 22; cursor advances to independent 10a.

## 10a DEV-a — done (real Telegram + DB)
- Explicit feedback is classified and scrubbed at the Telegram edge. The database receives only
  summary, allowlisted labels, and an HMAC source reference; it has zero raw/identity columns.
- Real user message id `3922` receives real bot acknowledgement id `3923`. Railway Postgres row
  id `1` is queued with `feedback,calendar,panel` and a PII-free summary.
- Staging deployment `ac0f6b9a-2a15-4762-88fc-52b7fe92caa4` succeeds after two source-root methods
  fail before build. Production webhook is restored with pending 0/error null; temporary staging
  secrets are removed.
- Focused `8/8`, full fail 0, every eval 100%, changed-path secret/PII 0.
- Evidence: `docs/evidence/10a-telegram-feedback-intake.md`. Pending becomes 21; next is 10b.

## 10b DEV-b — done (real GitHub issue + existing D0)
- The worker atomically claims one privacy-safe production intake row with `FOR UPDATE SKIP LOCKED`,
  creates or recovers a GitHub issue by deterministic HMAC-derived marker, and writes the exact URL
  back to the row. A failed provider call releases the claim; a stale incomplete claim is reclaimable.
- Real production row `1` creates [issue #1085](https://github.com/Daisuke134/life-manager/issues/1085).
  GitHub readback is OPEN with `lm:type:self-heal`; DB readback is `issued` with the exact URL.
- A second pass is `no-op`, the exact marker exists on one issue only, and the existing D0 picker
  selects `#1085`.
- The single `ai.anicca.life-manager-dev` 04:10 launchd job points to the canonical wrapper, which
  runs issue generation before delegating to the existing D0.
- Focused tests are `7/7`; full tests exit 0; all evals remain 100%; changed-path secret/PII scans
  are clean.
- Evidence: `docs/evidence/10b-feedback-to-github-issue.md`. Pending becomes 20; next is 10c.

## 10c DEV-c — done (real fresh-agent PR)
- The existing launchd D0 now targets only canonical `Daisuke134/life-manager`, `origin/main`, and
  `apps/life-manager`. It uses the shared fresh-agent runner and performs full tests/evals before
  creating a PR; it contains no merge or deploy action.
- Run 1 exposes a missing required runner loop argument: fresh agent exits 2 and PR #1087 initially
  contains only D0 infrastructure. The PR is not merged. Corrective TDD makes a nonzero agent exit
  fail closed before test/PR gates.
- Run 2 selects real issue #1085, fresh agent exits 0, commits `9c93bf36…`, and changes the missing
  Calendar model/UI action to exact `Connect Calendar` with focused regression coverage.
- D0 independently passes full tests and every eval, updates real PR
  [#1087](https://github.com/Daisuke134/life-manager/pull/1087), appends a `pr_open` state row, and
  reports to Telegram with message id `3386`.
- Evidence: `docs/evidence/10c-feedback-dev-loop-auto-pr.md`. Pending becomes 19; next is 10d.

## 10d DEV-d — done (real production error intake)
- Reuses `lm_feedback_intake`, its unique `source_ref`, the existing issue worker, the
  `lm:type:self-heal` label, and D0. No second incident queue or developer loop is introduced.
- The closed builder maps provider timeout, failed call/email/post, 5xx, and eval regression into
  three incident classes. Raw provider/error content has no output field and is not part of the
  HMAC fingerprint.
- Controlled live probes observe a timer deadline, child-process side-effect exit 23, and local
  HTTP 503 plus eval exit 1 before persistence.
- Production rows `2/3/4` create real issues
  [#1088](https://github.com/Daisuke134/life-manager/issues/1088),
  [#1089](https://github.com/Daisuke134/life-manager/issues/1089), and
  [#1090](https://github.com/Daisuke134/life-manager/issues/1090).
- A second injection is duplicate for all three; a fourth worker pass is no-op. DB and GitHub
  marker readbacks match, and forbidden-content checks are zero.
- Focused tests are `22/22`. Evidence: `docs/evidence/10d-production-error-intake.md`.
  Pending becomes 18; next is 10e.

## 10e DEV-e — pending after three fresh-adversary stops
- Real production error #1088 produces exactly one open PR #1092.
- Three independent fresh-adversary methods stop before merge. The final boundaries are reviewer
  credential/filesystem/network isolation, complete open-PR pagination, and rollback target
  binding to the active exact deployment commit.
- PR #1092 and issue #1088 remain open. Merge, deploy, provider mutation, and issue closure are
  zero; production remains on successful deployment `73afe498…`.
- Resume requires all three boundaries to move into a trusted promoter outside candidate code.
  Evidence: `docs/evidence/10e-auto-merge-deploy.md`.

## 10f DEV-f — pending, real Day 1/7
- The existing D0 is wrapped by one daily bounded runner; no duplicate queue, agent, or service is
  introduced.
- Closed mode-0600 state provides exclusive execution, dead stale-lock recovery, a 25-minute hard
  timeout, append-only daily receipts, and distinct-consecutive-day readiness.
- Real Day 1 selects issue #1090, fresh agent commit `b649393c…`, independently passes full
  test/eval/privacy, opens real PR #1094, appends `pr_created/147499ms`, and sends real Telegram
  message id `3390`.
- `ai.anicca.life-manager-dev` is loaded at 04:10 with the canonical daily runner. Focused tests are
  `7/7`; all full gates pass.
- Six distinct real days remain. The loop owns readiness calculation; fixtures, duplicate same-day
  runs, simulation, and backfill cannot complete the row. Pending remains 18; next is independent
  10i. Evidence: `docs/evidence/10f-daily-self-build-started.md`.

## 10i BRAIN-c — done (real personalized action E2E)
- Production paid/calendar-connected context yields five real upcoming event candidates; one real
  provider event `2ft16f…` is selected without persisting title/location/account identity.
- The current explicit user instruction supplies `explicit_goal` and `delegation` provenance.
  Existing `opportunity-engine.js` returns delegated/reversible/low-risk `act`; approval questions
  remain zero.
- Real Gmail send id `19f9380e8cbc40f9` is read back with RFC Message-ID
  `<CAFe2jSZ67NfG8FML7qkRPpkKxzO9XAJim8i1Hc8GN=6-9dO-BQ@mail.gmail.com>`.
- Post-action receipts are confirmed Google Calendar event `fd7rvh2u2sbqa0e4q4vl6vo0rs` and real
  Telegram message id `3392`.
- The missing production profile-email boundary fails before providers. Corrective account
  selection is RED `3/4` → GREEN, and the provider-side completion marker is RED `4/5` → GREEN
  `9/9`. A real rerun refuses with zero duplicate side effects.
- Full tests and every eval/privacy gate pass. Pending becomes 17; next is 11a L3. Evidence:
  `docs/evidence/10i-personalized-action-e2e.md`.

## 11a PHY-a — done (real calendar L3)
- The existing personal-cadence detector is wired to the current managed Google Calendar using
  only provider id and start/end fields.
- Real haircut history (5) and health-check history (3) correctly produce no candidate. Two real
  clinic history events produce one `personal-cadence-overdue` visit-gap observation from the
  user's own 9-day interval.
- Exact source provider event IDs are `89ll4pq50l499alj2njcosqdhc` and
  `sg08fnoe37loddogdp4ov8ub8s`; titles, locations, account/user identity, and notes are absent from
  the receipt.
- No diagnosis, recommendation, booking, notification, or provider write occurs. Focused
  runtime/contract tests are `7/7`; full tests and all eval/privacy gates pass.
- Pending becomes 16; next is 11b. Evidence: `docs/evidence/11a-real-care-detection.md`.

## 11b PHY-b — done (real public candidates)
- Production home context is consumed only inside the browser search and never persisted or
  printed.
- Two historical labels do not prove one usual provider, so all candidates honestly remain
  `usual=false`; no provider preference is invented.
- Public Google Maps and official sites verify three providers and non-phone routes: 小滝橋そら
  内科 (DigiKar), 新宿なないろ (public web endpoint/general walk-in), and ヒロオカ
  (reserve.ne.jp).
- Closed selector tests are `3/3`; full tests/evals/privacy pass. Provider writes are zero.
- Selected/frozen provider for 11c is `otakibashi-sora`. Pending becomes 15; next is 11c.
  Evidence: `docs/evidence/11b-real-care-candidates.md`.

## 11c PHY-c — done (real booking boundary + honest Telegram)
- The 11b provider remains frozen as `otakibashi-sora`; no fallback provider is attempted.
- The logged-out DigiKar flow reaches outpatient, initial visit, and a real available slot. The
  selected slot redirects to patient verification requiring a mobile number and SMS code.
- Life Manager has no SMS receive channel, so phone-number submission, code guessing, bypass,
  and false booking claims are all zero. Booking id remains `null`.
- Real Telegram message id `3394` honestly reports the measured boundary, unchanged provider, and
  unconfirmed reservation without asking a question.
- Closed contract tests are `4/4`; full tests/evals/privacy pass. Pending becomes 14; next is 11d.
  Evidence: `docs/evidence/11c-real-care-booking-boundary.md`.

## 11d PHY-d — pending after three fail-closed approaches
- 11c has no confirmed booking id, so the §9.11 success copy, Calendar event, and same-day calls
  cannot truthfully be emitted.
- Three approaches are rejected: treating a selectable slot as confirmed, reusing failure TG
  `3394` as success copy, and creating tentative Calendar/call effects.
- The closed gate requires provider confirmation, booking id, and start time. Until all exist,
  Telegram success, Calendar, and call effects are `0/0/0`.
- Focused tests are `3/3`; full tests/evals/privacy pass. Pending remains 14; next is independent
  12b. Evidence: `docs/evidence/11d-physical-aftercare-blocked.md`.

## SSOT reality audit — status corrected
- The marketing loop is unloaded before its next scheduled run because the required first-video
  preview and approval gate is not implemented.
- 9b remains done. 9c reopens, 9d becomes approved Day 0/7, and 9e is corrected to keep Postiz
  rather than migrate TikTok to a local direct browser path.
- The dev loop ledger has two distinct real days; 10f is Day 2/7.
- 11a/11b/11c reopen because generic clinic cadence, internal-medicine candidate selection, and a
  local browser boundary do not prove the meaningful care chain required by the product.
- Pending becomes 17. The live list is maintained only in §10; this note points there rather than
  becoming a second source of truth.
- Evidence: `docs/evidence/ssot-reality-audit.md`.

## DEV automation paused until final phase
- `ai.anicca.life-manager-dev` is booted out; no `life-manager-dev-daily.js` process remains.
- The active LaunchAgent plist is moved to
  `/Users/operator/Library/LaunchAgents/ai.anicca.life-manager-dev.plist.disabled`.
- Pause marker: `~/.openclaw/state/life-manager-dev/PAUSED_UNTIL_FINAL_PHASE`.
- Day 1/Day 2 append-only evidence remains intact. No paused dates count toward the 7-day gate.
- Execution order ends with 10e, then 10f. Current work remains 9c preview-first.

## CORE-8e delivery proof and the claim-suppression bug — code done, L3 pending
- The unproven boundary was never the send: Resend answers with its own queue id, so the journey could
  not produce the RFC Message-ID the done condition asks for. The three earlier attempts all failed
  because the notice recipient was a mailbox we could not read.
- Resume condition is met: an external controlled `@agentmail.to` inbox exists and its API readback is
  live (HTTP 200; 20 of 20 real messages carry an RFC-shaped `message_id`).
- Added `lib/transport/mail-agentmail-receipt.js`, the AgentMail sibling of `makeGogMail().findReceipt`
  — same fail-closed contract, same safe-metadata-only return, plus the RFC Message-ID.
- Measured against the live API, `message_id` holds the RFC id and `smtp_id` is AgentMail's own handle;
  the first pass had them swapped and was corrected from the real data, not from assumption.
- Production audit found a real journey bug: a located event that was already claimed stopped the whole
  late-notice path, because the finder took only the first located event and a failed claim returned at
  once. On 2026-07-25 an all-day located event claimed at 00:31:51Z ran until evening, so every later
  event that day was unreachable. Candidates are now walked; an all-claimed run stays silent.
- Verification: `npm test` 729 pass / 0 fail, `npm run eval` 7 suites at 100%, panel privacy PASS.
- Production runs `a1f3123d`; canonical main is ahead only by docs-only commits that Railway skipped.
- Still pending: the real L3 run (real call recording, real calendar event, real Telegram id, real RFC
  Message-ID readback, and the not-late case).

## CORE-8e — production L3 PASS, closed 2026-07-25
- Every leg of the DAILY journey is now backed by a real-world readback rather than a self-report:
  real calendar event (attendee readback `external=1/self=false/organizer=false`), travel autofill with a
  real outbound block, real T-10 call answered 11s later and transcribed by whisper as a two-way English
  conversation, live-location late decision, two real RFC Message-IDs, real Telegram id `245`, and the
  not-late case measured as zero claim rows and a strict receipt of `null`.
- Both email receipts were re-checked with the sender and subject pinned, so neither can be the Google
  calendar invitation that the receipt inbox also receives.
- Two real defects were found by running against production, not by reading code: a claimed meeting
  silenced every later event that day, and a calendar invitation could pass as delivery proof.
- Canonical main and Railway production both at `5c855632`. PRs #1104 and #1105.
- Evidence: `docs/evidence/core-8e-daily-journey-l3.md`.
- Cleanup: all events and travel blocks created for the run were deleted and the calendar was re-read to
  confirm only the user's own events remain. No third party was emailed at any point.
- Remaining: 16 atomics. Next is 8f.

## 8f premise corrected from live measurement — 2026-07-25
- The recorded blocker said typed `source=telegram_live_location` persistence failed with
  `live_location_unlock / poll_timeout`. Production contradicts that today: the row exists with
  `telegram_message_id=199` and its `observed_at` advances roughly every 20 seconds.
- So typed live-location persistence works in production; what failed earlier was specifically the path
  where the agent injected a location over MTProto. 8e's production L3 used this same real row to reach a
  late decision, claimed at `2026-07-25T01:57:51Z`.
- 8f therefore resumes scoped to what is still unproven: never asking the same closed question twice,
  context provenance, and zero forbidden-topic utterances — not the manufacturing of a real location.

## 8f — measured progress, closing on the callback readback
- Unlocked gates are provably never re-asked: against real production data the locked set is `["payout"]`
  alone, so the now-unlocked location gate drops out of selection, and the rotation moves `location` →
  `payout`.
- Real announcement delivered as Telegram message `246`; DB provenance written as
  `last_discovery_at=2026-07-25T03:27:14.263Z`, `last_discovery_gate=payout`; a second run is throttled.
- Forbidden-topic check: no standalone `出た？ / まだ？` prompt exists in shipped source. The one i18n hit
  is the discovery copy explaining that sharing a location removes that check — the rule matches only a
  whole-message prompt, so it is not an occurrence.
- Gap found and closed: a discovery answer left no trace in production, so a press could not be audited.
  The webhook now records action and gate, and deliberately logs no chat or user identifier.
- Pressing the payout button registers nothing today — payout registration belongs to 13b, which is not
  built. Verified: `payout_destination` is still null after the press.
- Verification: `npm test` 738 pass / 0 fail, `npm run eval` 7 suites at 100%, panel privacy PASS.

## CORE-8f — production L3 PASS, closed 2026-07-25
- The real press travelled the production webhook and was read back from the log as
  `[discovery] callback action=register gate=payout` — the piece that had never been observable before.
- Unlocked gates are provably never re-asked, the announcement carries real DB provenance, a repeat run is
  throttled, and no standalone forbidden prompt exists in shipped source.
- Evidence: `docs/evidence/core-8f-context-discovery-l3.md`.
- Handed to 13b: the payout announcement's "register" button acknowledges and then dead-ends, because the
  closed-question round trip it should open does not exist yet (`payout_destination` still null after the
  press). Recorded rather than patched, so 13b keeps ownership of the §9.11 FINANCIAL wording.
- Remaining: 15 atomics. Next is 9c.

## 9c — renderer corrected to MoneyPrinterTurbo, preview delivered
- Grafting a voice layer onto the bespoke ffmpeg renderer was reinventing a wheel we already had.
  MoneyPrinterTurbo is now installed and drives the render end to end.
- Measured, not assumed: MPT's voice is `edge_tts` (`app/services/voice.py:18`), so the "MPT voice" and
  the edge-tts already on this machine are the same thing. `cli.py --video-script` accepts our own script,
  so no LLM is in the loop. With no Pexels/Pixabay key, `--video-source local` plus the nine existing
  b-roll clips is enough — the render needs no external API key at all.
- First real render: task `69b7d234-af5c-499e-b60b-e25e4ffa76f0`, 1080x1920, 14.33s, AI narration, and
  subtitles generated word-by-word from that narration. The dependence on a real call recording and its
  whisper transcript is gone.
- Preview sent to Dais as Telegram message `251`. No approval receipt yet, so the distribution gate stays
  shut and no Instagram or TikTok call has been made.

## 9c — TikTok is live, Instagram is blocked by a suspended account
- Approved in chat, so the receipt was written against the exact bytes and distribution ran.
- Real post: https://www.tiktok.com/@anicca_buddha/video/7666359498763750676 — logged-out readback
  returns 200 and the page carries the same video id and handle. Account is the one the spec names,
  and its integration id is distinct from the unrelated comedy account, so nothing was mis-posted.
- The rotation works: the ledger row moved the loop on to A02 without being told.
- Instagram did not go out, and the reason is not a missing feature. Four measurements: the in-repo
  adapter is a stub that always returns failure; the configured handle `anicca.affirms2` has no Postiz
  integration; the browser session the daily driver holds lands on
  `https://www.instagram.com/accounts/suspended/`; and no `post_reel.py` exists — only the carousel
  poster does. Posting to a different account on a guess would be an irreversible public mistake, so
  nothing was posted there.

## 9c is deferred, NOT done — come back to it
- TikTok is live; Instagram is not, because the account the browser holds is suspended by Instagram.
- Dais chose to move on to 9d rather than wait, so 9c stays `pending` and must be reopened before the
  final phase. Do not let a later pass mistake it for finished.
- Reopening needs one decision only Dais can make: appeal the suspension himself, or name which of the
  already-connected Instagram accounts is the Life Manager one. Implementation is ready to follow either
  way — a real Reel path (`post_reel.py` does not exist yet), then distribution through the gate and a
  logged-out URL readback.

## 9d is blocked by 9c, not failed
- `select_latest_pair` in `skills/video/lm-self-improve/daily.py` demands the same creative published to
  BOTH Instagram and TikTok under identical video and caption digests, and raises otherwise.
- TikTok went live today; Instagram cannot, because that account is suspended. So the seven-day streak
  has no day one to start from.
- Relaxing the pair rule to TikTok alone would weaken the done condition, so it was left intact.
- 9d therefore waits on 9c. Moving to the next independent row rather than idling.
