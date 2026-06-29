# Handover prompt — finish & loop the Promote.fun clip-earn (claude -p / Sonnet, no human)

You are taking over an earn pipeline that turns short-form clips into **real USDC on Solana** via
**promote.fun** (per-view clipping, no-KYC). The hard, money-correctness core is DONE and independently
verified (106 unit tests GREEN + money probes). Your job = wire the remaining LIVE browser stages into the
existing state machine and then run it on a `claude -p` (Sonnet) loop until a real on-chain USDC payout lands.

## Ground truth (read first)
- Repo: `~/anicca` (public OSS). Push to `main` after every meaningful edit (`git add … && commit && push`).
- Slot: `~/anicca/skills/earn/clip-promote/` — `run.sh` (harness), `decide.py` (PURE state machine),
  `record-payout.mjs` (DONE executor), `select_campaigns.py` (SELECT), `_lib.sh` (emit/watchdog), `tests/`,
  `SKILL.md`, `state/clip-promote-state.json`.
- Canonical money libs: `~/anicca/skills/_shared/lib/{solana-verify,ledger,identity-guard}.mjs` (+ `__tests__`)
  and `~/anicca/skills/earn/lib/record.mjs`.
- Spec (SSOT): `~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md` (REV-1..4 +
  this handover section) and `~/anicca-project/.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 4,
  Phase-1c PASS 5/5).
- Accounts/creds: promote.fun `aniccaclips` logged in on CloakBrowser CDP **:9222** (creds
  `~/.cloak/promotefun-anicca.json`). Clip IG accounts: `~/.cloak/clip-accounts.json`. Solana payout wallet
  `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H`. OTP via `gog gmail` (`GOG_KEYRING_PASSWORD` in
  `~/.openclaw/.env`). USDC SPL mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`.

## The ONE invariant (do not violate — HARD 0.24)
**DONE = a confirmed, EXTERNAL, on-chain Solana USDC inflow recorded to the ledger. NOTHING else is earning.**
Posted/submitted/views = `earned_usdc:0`. The ONLY wake that may print `earned_usdc>0` is RECORD, and only
after `record-payout.mjs` verifies the withdrawal signature on-chain (`sigStatus.confirmed===true` AND
`usdcDeltaForSig>0` to our ATA AND not already recorded). No mocks, no dry runs, no "would have posted".

## The slot contract (every transition obeys this)
`run.sh` reads `state/clip-promote-state.json` → `decide(state, now)` returns ONE transition → run.sh runs
exactly that step → prints ONE line `{slot,did,earned_usdc,cost_usdc}` → exit 0. Every browser/IO step is
wrapped in `run_step "$STEP_DEADLINE_S" <cmd>` (from `_lib.sh`); on timeout (124) → `blocked:human:<step>`
exit 0 (never hang, never wait for a human). RECORD runs under `env -i PATH HOME SOLANA_RPC_URL node …`
(no PII reaches the malice-guard).

State machine (`decide.py`, already built): SELECT→CLIP→POST→SUBMIT→MEASURE→WITHDRAW→RECORD; STALLED frees
the slot (0 views past DEAD_ZERO_HOURS=48h, or submission rejected/dead).

## What is already done
- ✅ `solana-verify.mjs` (sigStatus / usdcDeltaForSig [owner+mint filter, accountIndex pre/post, absent-pre=0,
  null-uiAmount fallback] / usdcBalance) — real-RPC-shape verified.
- ✅ `ledger.mjs` generalized: `isProfitable` = net>0 ∧ external ∧ not-swap ∧ (EVM `0x1` ∨ Solana `sig+confirmed`);
  `deriveLine` carries sig/confirmed/chain; `alreadyRecordedSig` (sig dedup). EVM regression preserved.
- ✅ `record-payout.mjs` = the DONE executor (refuses unconfirmed / zero-delta / duplicate). 4 tests.
- ✅ `decide.py` PURE state machine (8 tests). `run.sh` harness + portable watchdog + env-i (7 tests).
- ★ `select_campaigns.py` + run.sh `SELECT` = LIVE-verified: pulled 23 real campaigns from the logged-in
  promote.fun, ranked by cpm×budget, picked `crocs` ($2.50×$17,500), advanced state → CLIP.

## Your tasks (in order — wire LIVE, test each, push)
1. **CLIP** (`run.sh` `CLIP)` case). From `/campaigns/<slug>` (state.campaign_id) open the **content library**
   tab, extract a SOURCE video URL (crocs = 8 MicroDrama episodes). Run `earn-clip-rewards` (yt-dlp + faster-
   whisper + ffmpeg) → a **15–45s, 1080×1920** clip with burned subtitles + **≥1 required treatment** (crocs
   mandates: reframe 3:4 / color grade / 4K upscale / flip — raw reposts are rejected). Verify with `ffprobe`
   (15≤dur≤45, 1080×1920, audio present). Disk hygiene (HARD 0.26): work in `~/.cache/…`, clean up. Advance → POST.
2. **POST** (`POST)` case) — **TRUE Day-7 gate**. Post `ig-reels-poster --live` ONLY to an account that is
   genuinely Day-7-warmed. ★ `clip-accounts.json status=="ready"` is NOT sufficient — @aiclipsvault is day-0/1
   (created 2026-06-29, warming on port 9223). Add a real `warmup_day≥7` check before `--live`; else defer
   (`did:"no-warm-account"`, exit 0). Caption MUST carry the campaign's required tags/CTA/hashtags (crocs:
   `@crocsshop_US`, "Watch now"/"Watch what happens next", `#crocs #DejaShoe`). Capture + profile-verify the
   post URL into state. Advance → SUBMIT.
3. **SUBMIT** (`SUBMIT)` case). Submit the post URL to the campaign; read status; REJECTED → STALLED.
4. **MEASURE** (`MEASURE)` case). Read views + accrued balance each wake; 0 views past 48h → STALLED; loops
   for days until the campaign ENDS.
5. **WITHDRAW** (`WITHDRAW)` case). When the campaign ENDED and balance>0, click Withdraw → capture the Solana
   **signature** into `state.sig`, phase → RECORD. (RECORD already records the real USDC line.)
6. **#15 LOOP**. Wrap one wake in `claude -p` (Sonnet) on a cadence (`/loop` or a launchd plist), prompt =
   "run ONE wake of earn/clip-promote with EARN_MODE=execute, then report the JSON line". No human in the loop.

## Verification bar (every stage)
- Add/extend a test in `tests/` for each new handler; re-run ALL suites green before claiming a stage done:
  ```
  cd ~/anicca/skills/_shared/lib && node --test __tests__/*.test.js      # 45/45
  cd ~/anicca/skills/earn/lib && node --test __tests__/*.test.*          # 42/42
  cd ~/anicca/skills/earn/clip-promote && node --test tests/test_record_payout.mjs   # 4/4
    && python3 tests/test_decide.py && python3 tests/test_select.py && bash tests/test_run.sh
  ```
- For LIVE stages: a fresh screenshot / real post URL / ffprobe output / a real promote.fun status — no claims
  without fresh evidence. The final acceptance = a real `state/clip-earn-ledger.jsonl` line whose
  `isProfitable` is true (a confirmed Solana USDC inflow). That is the only "we made money".

## Reality check on timing
SELECT/CLIP are doable immediately. POST is gated on a TRUE Day-7-warmed account (warming is in progress).
MEASURE→WITHDRAW→RECORD span DAYS (real views accrue, the campaign must END, then withdraw). The first real
USDC is therefore a multi-day outcome — build the machine + loop so it reaches DONE on its own; never fake it.
