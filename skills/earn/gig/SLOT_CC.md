# earn/gig = COCONALA daily loop (clip-pattern, human-funded ¥ → Dais MUFG)

Pivoted 2026-06-30 from dealwork (an AI can NEVER withdraw its dealwork balance —
`/api/v1/wallet/withdraw` → "Only human accounts can withdraw"). earn/gig is now an
INDEPENDENT every-day loop (NOT a one-picker slot), built exactly like the proven clip loop.

## The mechanism (this is what runs — NOT run.sh)
| piece | file | role |
|---|---|---|
| CORE | `gig-cli.sh` | claude-p tmux session; registers cron `27 * * * *`; each pass drives the CloakBrowser daily-driver (CDP :9222) as **mtdc** per the runbook: INBOX (talk-room reply / 仮払い→納品 / 検収→評価) OR APPLY (scan 公開依頼 → tailored proposal + sample → 応募する) OR TRACK #5121769 |
| HEALTHCHECK | `gig-healthcheck.sh` + `launchd/ai.anicca.gig-core-healthcheck.plist` | launchd 5-min; restart the core if the tmux session dies |
| MONITOR | `monitor.sh` | read-only status: applied + ¥ earned ledger (settled-status + evidence only) |
| MAIN-LOOP ENTRY | `run.sh` | the main loop resolves earn/gig → run.sh; it ensures the core is alive + reports ¥ status (NO USDC). The real earning is the core. |
| RUNBOOK | `scripts/coconala/APPLY_RUNBOOK.md` | the proven no-human 応募する flow the core reads (real mouse-click datepicker, setFileInputFiles attach, 投稿前モーダル) |

## Money path (human-funded — NOT on-chain USDC)
¥ settles to Dais's KYC'd Coconala account "mtdc" → MUFG. There is NO USDC / wallet / record-earn
in this loop. A ¥ earn is recorded ONLY by the core to `~/gig/earnings.jsonl` when Coconala UI
actually shows 検収/支払 (real side-effect). The only human element is Dais's one-time account/KYC.

## How to run / register
```bash
bash ~/anicca/skills/earn/gig/gig-cli.sh          # start the core (idempotent)
cp launchd/*.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/ai.anicca.gig-*.plist
bash ~/anicca/skills/earn/gig/monitor.sh          # status
```

## Verification status (Coconala loop)
- vcsdd-adversary on the Coconala loop: see iteration after the 2026-06-30 fixes (runbook added,
  dead code archived, producer/monitor added, no-human audit extended to gig-cli.sh).
- NOTE: the OLD dealwork+USDC machinery (36 tests, adversary ROUND 6 PASS) is in `archive/` —
  it is NOT part of this loop and must NOT be registered. It is kept only for a future self-funded
  USDC rail (Claw Earn / x402).
