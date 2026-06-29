# NO-HUMAN — earn/gig = Coconala loop (human-funded ¥ → Dais MUFG)

The DAILY operation has NO human in the loop. The ONLY human element is Dais's one-time
Coconala account + KYC + bank link (a setup fact, not a runtime step).

## Mechanism (audited by __tests__/no-human-loop.test.mjs)
| concern | how it's handled, no human |
|---|---|
| login lapsed | core re-logs in via「Googleでログイン」on the daily-driver (stored Daisuke session) |
| CAPTCHA | CapSolver (Turnstile/hCaptcha) per tier-a-bypass |
| OTP / verification mail | `gog gmail` auto-read (redacted@example.invalid) |
| 応募 (apply) | model drives CDP :9222 per scripts/coconala/APPLY_RUNBOOK.md (real-mouse datepicker, setFileInputFiles attach, 投稿前モーダル) — no human click |
| talk-room reply / 納品 / 評価 | model acts on the live DOM each cron pass |
| a blocker | "A blocker is NOT a stop" — the core tries the autonomous path + reports; it never asks a human |

## NO-FAKE-EARN
- ¥ is human-funded (settles to Dais's Coconala account → MUFG). There is NO on-chain USDC,
  NO wallet, NO record-earn in this loop. The cron prompt forbids claiming USDC.
- A ¥ earn is recorded to `~/gig/earnings.jsonl` ONLY when Coconala UI shows a settled status
  (検収/支払) AND evidence is captured. `monitor.sh` + `run.sh` enforce this deterministically
  (status whitelist + non-empty evidence); an applied/in-progress/fabricated row is never summed.

## Files audited
`gig-cli.sh` (the live core + cron prompt), `monitor.sh`, `gig-healthcheck.sh`. The old dealwork +
on-chain-USDC machinery (run.sh detect/bid/settle, lib/*) lives in `archive/` and is NOT part of
this loop. (Coconala is the ACTIVE rail — earlier notes that called Coconala "removed" were the
pre-pivot self-funded-USDC framing and are obsolete.)
