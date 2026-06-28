# SPEC — Money Loops Runner + Loop Form (supplement to 2026-06-28-money-loops-design.md)

Date: 2026-06-28 · Status: LIVE direction · Author: main agent (me) per Dais 2026-06-28 verbatim direction.
Parent (= canonical source of truth on WHAT to earn): `2026-06-28-money-loops-design.md`.
Per Dais verbatim: "we have to make a loop that earns money" + "It's a loop that runs every single day that earns money" + "go search how to use this" (= /loop).
Replaces my superseded `~/anicca/docs/superpowers/specs/2026-06-28-anicca-as-installable-claude-sub-earner.md` (= confused Anicca with the profitable Claude wrapper).

## §0 Two products kept separate (= the confusion I keep making)

| | Claude (this spec) | Anicca (= existing) |
|---|---|---|
| Funded by | Dais's Claude Code $200/mo sub | self-funded (no human in loop, ever) |
| Where it runs | Dais's Mac mini (always-on) via this loop | already lives at `~/anicca/` (Daisuke134/anicca OSS) with its own runtime/loop, skills/earn/ |
| Earn skills | THIS spec writes them (= the runner) | already has `ensure-gas`, `execute-yield`, `x402-sell`, `hl-trade`, `token-launch` — ★ I do NOT touch them ★ |
| Goal | earn > $200/mo to Dais's Payhip/note/Stripe (= "Claude pays for itself") | earn > spend, no human in loop, takeoff |
| Relationship | the FORMER finds/funds the LATTER (Dais verbatim) — when this loop crosses surplus, it spawns an Anicca child | exists independently |

★ NEVER conflate them. NEVER put profitable-Claude code into Daisuke134/anicca repo. NEVER touch Anicca's existing earn skills under this spec. ★

## §1 What the loop earns (= cribbed from money-loops-design.md, source of truth)

Per parent spec §2: ★ Monk Factory → Ebook Funnel ★. Cost ~$0, demonetization-proof (= sells products, not ads). Pipeline:

```
DeepSeek picks theme + writes value-add script (no template, varies each time = ban-avoid)
  ↓
monk-factory free stack — still image / Kling i2v + VOICEVOX 青山龍星 (JP) / ElevenLabs (EN)
  + ffmpeg karaoke captions, ≥60s
  ↓
Postiz (self-host free) / upload-post (free 10/mo). MEDIA_UPLOAD method (= trending sound
  auto-finish, reach max). NOT DIRECT_POST.
  ↓
Video description / pinned comment → comment-to-DM (CTR 12-18% = 4-6x bio link) → email capture
  ↓
Sell ebook/journal:
  EN: $7-27 PDF on Payhip (5%) / Stan + $4.99 KDP (70% royalty band $2.99-9.99)
  JP: note ¥1,800 article + ¥500/mo membership + KDP JP
  ↓
record earn (= ONLY real settled webhook/payout, never "would-have-sold")
```

Existing local assets: `~/.openclaw/skills/watercolor-monk-factory` (= the monk-factory pipeline), `~/MoneyPrinterTurbo` (cloned), VOICEVOX 青山龍星 key live, agent-reach skill for trend input.

## §2 The loop form — THREE options, ONE pick (= the central question Dais asked)

Per `~/.claude/rules/loop-command.md` + `code.claude.com/docs/en/scheduled-tasks` + `~/.claude/projects/-Users-anicca-anicca-project/memory/reference_loop_engineering.md` (= our 9-source synthesis):

| Form | Runs on | Mac on? | Session open? | Min interval | Verdict for "every single day" |
|---|---|---|---|---|---|
| **`/loop`** (= alias `/proactive`, requires Claude Code v2.1.72+) | the open session | yes | ★ YES — kills on terminal close ★ | 1 min | Good for SOAK TEST (= W3), not daily-forever (= session must stay open) |
| **`claude -p` + launchd plist** (= sutando model) | the user's Mac (background) | ★ YES — Mac mini always-on ★ | no | 1 min | Good if the Mac is always on. macOS-specific. |
| **`/schedule`** (= alias `/routines`, Anthropic cloud) | Anthropic cloud | ★ NO — Mac can be off ★ | no | 1 hour | ★ CHOSEN for the final "runs every single day" wrapper (W4) ★ |

★ Decision ★: `/schedule` for the durable daily-forever wrapper. `/loop` for the 2-3 day soak test before promoting. `claude -p`+launchd is the FALLBACK if the Routines daily-run-allowance is exceeded.

Verbatim from Anthropic docs (Bash search of installed docs cache):
> "`/loop [interval] [prompt]` Skill. Run a prompt repeatedly while the session stays open. … Alias: `/proactive`."
> "Tasks survive `--resume` if unexpired; 7-day hard expiry on every scheduled task."
> "`/schedule` / Routines: Create, update, list, or run routines, which execute on Anthropic-managed cloud infrastructure. … Alias: `/routines`."
> "Cloud (`/schedule` → Routines): Requires machine on = No. Requires open session = No. Minimum interval = 1 hour. Persistent across restarts = Yes."

## §3 Boris Cherny's 4-step ladder = our W1-W6 tasks

Per addy osmani's `loop-engineering` post quoting Boris (Anthropic, head of Claude Code, verbatim):

> "Get one manual run reliable first. Turn it into a skill. Wrap it in a loop. Then schedule it."

Our task ladder maps 1:1:

| Boris step | Our task |
|---|---|
| 1. one manual run reliable | **W1**: monk-factory → ebook → 1 real Payhip/note sale verified (= record-earn row with a webhook id) |
| 2. turn into a skill | **W2**: `~/.claude/skills/money-loops-runner/SKILL.md` orchestrates W1 in one call |
| 3. wrap in a loop | **W3**: `/loop 24h /money-loops-runner` soak for 2-3 days while terminal open |
| 4. schedule it | **W4**: `/schedule every day at 09:00 JST /money-loops-runner` (= Anthropic cloud Routine, durable) |

Plus the maker-checker discipline from loop-engineering memory (= Boris's "the model that wrote the code is way too nice grading its own homework"):

| | Our task |
|---|---|
| 5. fresh-context verifier (maker ≠ checker) | **W5**: `/goal Daily realised earn from Payhip+note+Stripe over 7d >= $7 (or stop after 60 days at $0)`. Haiku judges from conversation-visible numbers only. record-earn-style INV: count only rows with real webhook/payout id. |
| 6. real money settled | **W6**: ★ FIRST REAL $1 settled to Payhip OR note OR Stripe ★, recorded with the webhook/payout id in `~/.smtm/money-loops/state/earn-ledger.jsonl`. NOT "I posted, would have sold." Per HARD 0.31 E2E. |

## §4 Where state lives (= sutando-shape, local only on Dais's Mac mini)

```
~/.smtm/money-loops/
  state/
    build_log.md            — sutando-style, appended each wake
    earn-ledger.jsonl       — record-earn pattern, real settlements only
    core-status.json        — {"status":"running","step":"posting","ts":epoch}
    cron-jobs.json          — CronList snapshot (job IDs)
  loop.md                   — the runner prompt (= what /loop / claude -p reads)
  tasks/ + results/         — sutando-style bridge for inbound work (= self-fix issues, manual overrides)
```

`.claude/loop.md` (= the canonical /loop prompt location per Anthropic docs) is a SYMLINK to `~/.smtm/money-loops/loop.md` so `/loop` (bare) runs our prompt directly.

★ NEVER write to aniccaai.com. NEVER touch Dais's Railway. NEVER push to Dais's anicca-project code (= apps/ etc.). Spec files in `docs/superpowers/specs/` are fine (this very file lives there). Money goes to Dais's note / Payhip / Stripe accounts because this is HIS loop on HIS machine for HIS surplus — explicitly Dais's instruction. ★

## §5 Web-search receipts (= cited from 3 parallel forks ran 2026-06-28)

| Claim | Source |
|---|---|
| "/loops doesn't exist; canonical is /loop singular" | code.claude.com/docs/en/commands; code.claude.com/docs/en/scheduled-tasks |
| "/loop = session-scoped, 7-day expiry" | Anthropic scheduled-tasks docs verbatim |
| "/schedule = cloud-managed cron, 1-hour min, Mac-off OK" | Anthropic routines docs verbatim |
| Boris Cherny "I don't prompt Claude anymore. I have loops running that prompt Claude. My job is to write loops." | addyosmani.com/blog/loop-engineering (Jun 7 2026) via Boris @rohanpaul_ai 2063289804708835412 |
| "Loop engineering: 5+1 blocks — automations / worktrees / skills / connectors / sub-agents + memory/state" | Addy Osmani blog, X 230M views |
| "Maker ≠ checker. The model that wrote the code is way too nice grading its own homework." | Addy Osmani; matches our VSDD adversary discipline |
| "ad revenue = TRAP (YouTube + TikTok demonetize AI templates); reliable profit = digital products" | parent spec money-loops-design.md §0; tubebuddy.com; support.google.com/youtube/answer/1311392 |
| "ALBA (alba-run.vercel.app) = closest precursor (Claude Code in loop building micro-MVPs), credits not USDC" | hn.algolia.com Show HN July 2026 |
| "0 public founders claim their Claude $200 sub now nets >$200 from autonomous Claude work" | Google verbatim "no results found" for `"my Claude Code earned" "$" 2026` |
| "sutando ports — 5 items min: start-cli.sh / schedule-crons / fswatch / proactive-loop / health-check" | github.com/sonichi/sutando deep read |

## §6 DONE (this spec)

Direction locked, definitively, with citations. The runner = a single skill `money-loops-runner` orchestrating Monk Factory → Ebook Funnel; the loop form = `/schedule` daily on Anthropic cloud after a `/loop` soak test; the verifier = `/goal` with a Haiku fresh-context judge reading only on-disk receipts; the surplus = Dais's accounts (Payhip / note / Stripe); the next concrete action = ★ task W1 = one manual run end-to-end with a real $1 sale ★, no skill, no loop, just the manual proof.
