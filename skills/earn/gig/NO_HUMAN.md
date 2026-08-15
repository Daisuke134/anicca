# NO-HUMAN — earn/gig = Coconala loop (human-funded ¥ → Dais MUFG)

★ 現在状態・残TODO・実行順序の正本は `docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`（§0 と §6）。
1 pass の実行順は `SLOT_CC.md` の実測表（`QUEUE → INQUIRY_REPLY → RETAINER_FOLLOWTHROUGH → PAID_WORK →
PAID_QUEUE_DELIVERY → B0 → PROFILE → B1 → B2 → LEARN → REFLECT`）が正本。★
★ 旧「B1〜B5 の 5-behavior loop」「claude-p tmux core」「cron `27 * * * *`」は 2026-07-18 cutover で廃止済。★

The DAILY operation has NO human in the loop. The ONLY human element is Dais's one-time
Coconala account + KYC + bank link (a setup fact, not a runtime step).

## Mechanism (audited by __tests__/no-human-loop.test.mjs)
| concern | how it's handled, no human |
|---|---|
| login lapsed | core re-logs in via「Googleでログイン」on the daily-driver (stored Daisuke session) |
| CAPTCHA | CapSolver (Turnstile/hCaptcha) per tier-a-bypass |
| OTP / verification mail | `gog gmail` auto-read (operator account, `$GIG_GOG_ACCOUNT` / config, default `operator@example.com`) |
| 応募 (apply) | model drives the Gig-dedicated CDP **:9223** (profile `gig-daily-driver`, LaunchAgent `ai.anicca.hf-gig-browser`) per scripts/coconala/APPLY_RUNBOOK.md — no human click。★対話用 `:9222` とは分離されている（旧記述 `:9222` は誤り）★ |
| talk-room reply / 納品 / 評価 | model acts on the live DOM each cron pass |
| a blocker | "A blocker is NOT a stop" — the core tries the autonomous path + reports; it never asks a human |

## NO-FAKE-EARN
- ¥ is human-funded (settles to Dais's Coconala account → MUFG). There is NO on-chain USDC,
  NO wallet, NO record-earn in this loop. The cron prompt forbids claiming USDC.
- A ¥ earn is recorded to `~/gig/earnings.jsonl` ONLY when Coconala UI shows a settled status
  (検収/支払) AND evidence is captured. `monitor.sh` + `run.sh` enforce this deterministically
  (status whitelist + non-empty evidence); an applied/in-progress/fabricated row is never summed.

## Files audited by no-human-loop.test.mjs
`gig-cli.sh` (旧 core、現在どの LaunchAgent からも参照されない遺物), `monitor.sh`, `gig-healthcheck.sh`,
`auditor.sh`, `run.sh`. All new `.sh` scripts added to the loop must be listed in
`__tests__/no-human-loop.test.mjs:FILES`。★実際に本番を駆動するのは `gig_pass.sh` +
`scripts/launch_gig_worker.sh` であり、監査対象リストが cutover に追随していない（SSOT の残課題）★

## Self-improving loop files
| File | Role |
|------|------|
| `strategy.default.json` | Seed strategy (categories, templates, prices) — copied to `~/gig/strategy.json` on first pass |
| `~/gig/strategy.json` | Live strategy — `LEARN` step + `scripts/experiment_evaluator.py` だけが変更する（直接編集禁止） |
| `~/gig/lessons.jsonl` | Outcome log: {ts,requestId,category,outcome,reason,lesson} |
| `~/gig/experiment-evaluations.jsonl` | 実験の start / keep / revert / quarantine の append-only 台帳 |

★ `~/gig/shared-lessons.jsonl` と「B5 BOT-TO-BOT: GitHub issue で lesson を bot 間共有」は**実装されていない**
（2026-08-01 実測）。旧記述を復活させないこと。★

The old dealwork + on-chain-USDC machinery (run.sh detect/bid/settle, lib/*) lives in `archive/`
and is NOT part of this loop.
