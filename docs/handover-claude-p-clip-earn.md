# Handover — finish & loop the Promote.fun clip-earn on a `claude -p` Sutando loop (no human)

You are taking over an earn pipeline that turns short-form clips into **real USDC on Solana** via
**promote.fun** (per-view clipping, no-KYC). The money-correctness core is DONE and independently verified
(106 unit tests GREEN + money probes). SELECT is LIVE-proven. Your job = (A) wire the remaining LIVE browser
stages into the state machine, and (B) drive it on the **Sutando always-on `claude -p` loop** pattern that
already exists in this repo. Push to `~/anicca` main after every meaningful edit.

────────────────────────────────────────────────────────────────────────────────────────────────────
## 0. The ONE invariant (never violate — HARD 0.24)
**DONE = a confirmed, EXTERNAL, on-chain Solana USDC inflow recorded to the ledger. NOTHING else earns.**
Posted / submitted / views = `earned_usdc:0`. The ONLY wake that may print `earned_usdc>0` is RECORD, and
only after `record-payout.mjs` verifies the withdrawal signature on-chain (`sigStatus.confirmed===true` AND
`usdcDeltaForSig>0` to our ATA AND not already recorded). No mocks, no dry runs, no "would have posted".

────────────────────────────────────────────────────────────────────────────────────────────────────
## 1. The Sutando loop pattern (COPY it — it already exists for the generic clip slot)
A sibling agent built the proven `claude -p` always-on harness at `~/anicca/skills/earn/clip/`. Replicate
it for the promote.fun money slot. Five roles:

```
 launchd (5min)  ── *-healthcheck.sh: tmux session dead? → restart via *-cli.sh   [OS supervisor]
        │
 *-cli.sh ── detached tmux runs `claude --dangerously-skip-permissions` with a STARTUP prompt that:
        │      1) CronList; if no earn/clip-promote job → CronCreate("7 * * * *", recurring+durable,
        │         prompt="run ONE pass of clip-promote")  2) run ONE pass now  3) idle (cron drives it)
        ▼
 cron (hourly) ── fires "ONE pass": set -a; . ~/.openclaw/.env; set +a;
        │            EARN_MODE=execute bash ~/anicca/skills/earn/clip-promote/run.sh ; then monitor.sh
        ▼
 producer.sh (daily, heavy)  →  ~/clips/queue/*.mp4+*.txt   [FUEL: make clips, separate from posting]
 run.sh      (hourly, light) →  ONE bounded state-machine transition                [the money slot]
 monitor.sh  (read-only)     →  ledger posts / recorded USDC / reel views / founder Solana wallet
```
Reference files to copy/adapt (do NOT post to aishigoto or any non-clip account; fail-closed):
`~/anicca/skills/earn/clip/{clip-cli.sh, clip-healthcheck.sh, producer.sh, monitor.sh, launchd/*.plist}`.

────────────────────────────────────────────────────────────────────────────────────────────────────
## 2. Ground truth (paths / accounts)
- Repo `~/anicca` (OSS, push main). Money slot: `~/anicca/skills/earn/clip-promote/` —
  `run.sh` (harness), `decide.py` (PURE state machine), `record-payout.mjs` (DONE executor),
  `select_campaigns.py` (SELECT), `_lib.sh` (emit/watchdog), `tests/`, `SKILL.md`, `state/clip-promote-state.json`.
- Money libs: `~/anicca/skills/_shared/lib/{solana-verify,ledger,identity-guard}.mjs` (+ `__tests__`),
  `~/anicca/skills/earn/lib/record.mjs`.
- promote.fun `aniccaclips` logged in on CloakBrowser CDP **:9222** (creds `~/.cloak/promotefun-anicca.json`).
  Clip IG accounts: `~/.cloak/clip-accounts.json`. Solana payout wallet
  `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H`. OTP via `gog gmail` (`GOG_KEYRING_PASSWORD` in
  `~/.openclaw/.env`). USDC SPL mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`.
- Spec (SSOT): `~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md`;
  `~/anicca-project/.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 4, Phase-1c PASS 5/5).

────────────────────────────────────────────────────────────────────────────────────────────────────
## 3. Slot contract (every transition obeys this — already built)
`run.sh` reads `state/clip-promote-state.json` → `decide(state, now)` returns ONE transition → run.sh runs
exactly that step → prints ONE line `{slot,did,earned_usdc,cost_usdc}` → exit 0. Every browser/IO step is
wrapped in `run_step "$STEP_DEADLINE_S" <cmd>` (`_lib.sh`); on timeout(124) → `blocked:human:<step>` exit0
(never hang / never wait for a human). RECORD runs under `env -i PATH HOME SOLANA_RPC_URL node …` (no PII).
State machine: SELECT→CLIP→POST→SUBMIT→MEASURE→WITHDRAW→RECORD; STALLED frees the slot (0 views past
DEAD_ZERO_HOURS=48h, or submission rejected/dead).

────────────────────────────────────────────────────────────────────────────────────────────────────
## 4. Already done (don't rebuild)
- ✅ `solana-verify.mjs` (sigStatus / usdcDeltaForSig [owner+mint filter, accountIndex pre/post, absent-pre=0,
  null-uiAmount fallback] / usdcBalance) — real-RPC-shape verified on-chain.
- ✅ `ledger.mjs` generalized: `isProfitable` = net>0 ∧ external ∧ not-swap ∧ (EVM `0x1` ∨ Solana `sig+confirmed`);
  `deriveLine` carries sig/confirmed/chain; `alreadyRecordedSig` (sig dedup). EVM regression preserved.
- ✅ `record-payout.mjs` = DONE executor (refuses unconfirmed / zero-delta / duplicate). 4 tests.
- ✅ `decide.py` PURE state machine (8 tests). `run.sh` harness + portable watchdog + env-i (7 tests).
- ★ `select_campaigns.py` + run.sh `SELECT` = LIVE-verified: pulled 23 real campaigns from logged-in
  promote.fun, ranked by cpm×budget, picked `crocs` ($2.50×$17,500), state → CLIP.

────────────────────────────────────────────────────────────────────────────────────────────────────
## 5. Your tasks (in order — wire LIVE, test each, push)
1. **CLIP** (`run.sh` `CLIP)` case + a campaign-aware producer). From `/campaigns/<slug>` open the **content
   library** tab, extract a SOURCE video (crocs = 8 MicroDrama episodes). Run `earn-clip-rewards` (yt-dlp +
   faster-whisper + ffmpeg) → a **15–45s, 1080×1920** clip with burned subtitles + **≥1 required treatment**
   (crocs mandates reframe 3:4 / color grade / 4K upscale / flip — raw reposts are rejected). `ffprobe`
   verify (15≤dur≤45, 1080×1920, audio present). Disk hygiene (HARD 0.26): work in `~/.cache/…`, clean up.
   Adapt `clip/producer.sh` so the source is the CAMPAIGN's library (not a generic CEO video). Advance → POST.
2. **POST** (`POST)` case) — **TRUE Day-7 gate**. `ig-reels-poster --live` ONLY to a genuinely Day-7-warmed
   account. ★ `clip-accounts.json status=="ready"` is NOT enough — @aiclipsvault is day-0/1 (created
   2026-06-29, warming on port 9223). Add a real `warmup_day≥7` check before `--live`; else defer
   (`did:"no-warm-account"`). Caption MUST carry the campaign tags/CTA/hashtags (crocs: `@crocsshop_US`,
   "Watch now"/"Watch what happens next", `#crocs #DejaShoe`). Capture + profile-verify the post URL → SUBMIT.
3. **SUBMIT** (`SUBMIT)`). Submit the post URL to the campaign; read status; REJECTED → STALLED.
4. **MEASURE** (`MEASURE)`). Read views + accrued balance each wake; 0 views past 48h → STALLED; loops for
   days until the campaign ENDS.
5. **WITHDRAW** (`WITHDRAW)`). When the campaign ENDED and balance>0, click Withdraw → capture the Solana
   **signature** into `state.sig`, phase → RECORD. (RECORD already records the real USDC line.)
6. **#15 LOOP (Sutando)**. Create `clip-promote-cli.sh` (copy `clip/clip-cli.sh`; session
   `anicca-clip-promote-core`, sock `/tmp/anicca-clip-promote-tmux.sock`; STARTUP prompt registers a cron that
   runs ONE pass of `clip-promote/run.sh` + `monitor.sh`) + `clip-promote-healthcheck.sh` + a launchd plist
   `ai.anicca.clip-promote-healthcheck` (StartInterval 300). Start it; verify `--status` ALIVE + `CronList`
   shows the job. The loop walks the state machine across wakes with no human; it reaches DONE when real USDC
   lands (multi-day — never fake).

────────────────────────────────────────────────────────────────────────────────────────────────────
## 6. Verification bar (every stage — HONESTY + HARD 0.31)
- Add/extend a test in `tests/` per new handler; re-run ALL suites green before claiming a stage done:
  ```
  cd ~/anicca/skills/_shared/lib && node --test __tests__/*.test.js          # 45/45
  cd ~/anicca/skills/earn/lib && node --test __tests__/*.test.*              # 42/42
  cd ~/anicca/skills/earn/clip-promote && node --test tests/test_record_payout.mjs   # 4/4
    && python3 tests/test_decide.py && python3 tests/test_select.py && bash tests/test_run.sh
  ```
- LIVE stages: fresh screenshot / real post URL / `ffprobe` output / real promote.fun status — no claim
  without fresh evidence. Final acceptance = a real `state/clip-earn-ledger.jsonl` line whose `isProfitable`
  is true (a confirmed Solana USDC inflow). That is the only "we made money".

## 7. Timing reality
SELECT/CLIP are doable immediately. POST is gated on a TRUE Day-7-warmed account (warming in progress).
MEASURE→WITHDRAW→RECORD span DAYS (views accrue, campaign must END, then withdraw). First real USDC is a
multi-day outcome — build the machine + Sutando loop so it reaches DONE on its own; never fake it.
