# earn/gig = COCONALA daily loop (clip-pattern, human-funded ¥ → Dais MUFG)

Pivoted 2026-06-30 from dealwork (an AI can NEVER withdraw its dealwork balance —
`/api/v1/wallet/withdraw` → "Only human accounts can withdraw"). earn/gig is now an
INDEPENDENT every-day loop (NOT a one-picker slot), built exactly like the proven clip loop.

## The mechanism (this is what runs — NOT run.sh)
| piece | file | role |
|---|---|---|
| CORE | `gig-cli.sh` | claude-p tmux session; registers cron `27 * * * *`; each pass runs the 5-behavior self-improving loop (see below) |
| HEALTHCHECK | `gig-healthcheck.sh` + `launchd/ai.anicca.gig-core-healthcheck.plist` | launchd 5-min; restart the core if the tmux session dies |
| MONITOR | `monitor.sh` | read-only status: applied + ¥ earned ledger (settled-status + evidence only) |
| MAIN-LOOP ENTRY | `run.sh` | the main loop resolves earn/gig → run.sh; it ensures the core is alive + reports ¥ status (NO USDC). The real earning is the core. |
| RUNBOOK | `scripts/coconala/APPLY_RUNBOOK.md` | the proven no-human 応募する flow the core reads (real mouse-click datepicker, setFileInputFiles attach, 投稿前モーダル) |

## Money path (human-funded — NOT on-chain USDC)
¥ settles to Dais's KYC'd Coconala account "mtdc" → MUFG. There is NO USDC / wallet / record-earn
in this loop. A ¥ earn is recorded ONLY by the core to `~/gig/earnings.jsonl` when Coconala UI
actually shows 検収/支払 (real side-effect). The only human element is Dais's one-time account/KYC.

## 5-behavior self-improving loop (added 2026-06-30)

Each hourly pass runs in priority order:

| Step | Behavior | Ledger written |
|------|----------|---------------|
| B1 | **NURTURE ALL**: sweep every active talk-room; reply / 納品 / 評価依頼 | `applied.jsonl` (status: replied/delivered/評価依頼) |
| B2 | **APPLY BROADLY**: up to `strategy.max_apply_per_pass` new requests per pass, guided by `strategy.json` categories + templates; deduped via `applied.jsonl` requestIds | `applied.jsonl` (status: applied) |
| B3 | **LEARN**: outcome events (accepted/rejected/needs_human/…) → `~/gig/lessons.jsonl` | `lessons.jsonl` |
| B4 | **SELF-IMPROVE** (every N passes): read lessons + peer GitHub issues → update `~/gig/strategy.json` (priorities, skip_categories, templates, prices) | `strategy.json` |
| B5 | **BOT-TO-BOT** (with B4): post `[gig-lesson]` GitHub issue on notable lesson; read recent peer issues; dedup via `~/gig/shared-lessons.jsonl` | `shared-lessons.jsonl` |

Strategy seeded from `strategy.default.json` → `~/gig/strategy.json` on first pass.  
Improve step cadence: `strategy.improve_cadence_passes` (default 4 = every ~4h).

## How to run / register
```bash
bash ~/profitable-claude/skills/gig-work/gig-cli.sh          # start the core (idempotent)
cp launchd/*.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/ai.anicca.gig-*.plist
bash ~/profitable-claude/skills/gig-work/monitor.sh          # status
```

## Verification status (Coconala loop)
- vcsdd-adversary on the Coconala loop: see iteration after the 2026-06-30 fixes (runbook added,
  dead code archived, monitor added, no-human audit extended to gig-cli.sh; no producer —
  the core live-scans the board each pass).
- NOTE: the OLD dealwork+USDC machinery (36 tests, adversary ROUND 6 PASS) is in `archive/` —
  it is NOT part of this loop and must NOT be registered. It is kept only for a future self-funded
  USDC rail (Claw Earn / x402).
