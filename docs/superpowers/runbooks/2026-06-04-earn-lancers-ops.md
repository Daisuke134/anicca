# anicca-earn-lancers Wave 1 — autonomous ops note

Wave 1 is dry-run-only and runs autonomously. No human reads, eyeballs, or taps anything. This note exists ONLY to document the kill-switch path and the exit-code semantics that the autonomous loop honors. Real-submit / `--confirm` lives in the Wave 2 plan: `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`.

## Daily beat

`hermes cron` fires `~/.hermes/scripts/anicca-earn-lancers.sh` (a real wrapper, not a symlink — Hermes rejects scripts that escape `~/.hermes/scripts/` via symlink traversal) at `0 10 * * *` JST. The wrapper execs the canonical `run.sh` in the worktree with default `--dry-run`. The script runs `login-check.sh → scan.sh → select.sh → apply.sh --dry-run` and writes:
- `~/.hermes/state/earn-lancers-dry-run-latest.json` — latest envelope.
- `~/.hermes/state/earn-lancers-cron-fire.log` — last fire's stdout/stderr.

## Login = autonomous (no human, no 2FA tap-on-phone, no "Dais reviews")

`login-check.sh` does everything itself:
1. Probe Camofox `/sessions/anicca/cookies` for a `lancers.jp` cookie. If present → done.
2. Otherwise open `https://www.lancers.jp/user/login` and click "Googleでログイン".
3. Type `GOOGLE_LOGIN_EMAIL`, Enter, type `GOOGLE_LOGIN_PASSWORD`, Enter.
4. If a 2-step challenge appears:
   - `GOOGLE_TOTP_SECRET` present → `oathtool --totp -b "$GOOGLE_TOTP_SECRET"` → type code.
   - Else → `hermes chat -q --model <mini>` reads the latest 2-step email at `person@example.com` and returns the 6-digit code → type code.
5. Re-probe cookie. If present → exit 0.

## Hard-block (only — HARD RULE #-2)

A genuine hard-block is recognized only when:
- a real CAPTCHA iframe (`recaptcha`, `hcaptcha`, `turnstile`) renders in the Camofox snapshot, OR
- the page asks for a financial broadcast (= money send / withdraw signature).

When this happens the script saves the verbatim subset of the Camofox snapshot to `~/.hermes/state/earn-lancers-login-hardblock.json` and exits non-0. The earn task stays OPEN. The next cron beat retries automatically. No human is asked to "tap" or "review" — the loop self-heals on the next beat.

## Exit-code semantics (login-check.sh + run.sh)

| Exit | Meaning |
|------|---------|
| 0    | session ready / dry-run envelope produced |
| 3    | Camofox not running |
| 4    | Google-login button missing on Lancers login page |
| 5    | Google email field ref not found (OAuth UI redesign) |
| 6    | autonomous 2FA did not converge this beat; verbatim snapshot saved to hardblock file; next beat retries |
| 7    | `login-check` aborted (run.sh) — inspect hardblock file |
| 8    | no JIDs found in scan |
| 9    | real CAPTCHA iframe rendered (HARD RULE #-2 genuine hard-block); verbatim snapshot saved; next beat retries |

## Kill switch

```bash
hermes cron pause anicca-earn-lancers
```

This freezes the daily cron until `hermes cron resume anicca-earn-lancers`. Use only if a Wave 2 real-submit beat lands a clearly out-of-niche proposal or Lancers serves a TOS warning.

## What advances `#325` (LAUNCH MATRIX row ④)

Wave 1 (this plan) does NOT advance row ④. Advancement requires the Wave 2 plan's exit conditions:
1. ≥1 row in `~/.hermes/state/earn-lancers-runs.jsonl` with `status:"applied"` AND a verified `finish_url` (Camofox-confirmed the proposal page renders).
2. CFO `cfo-bank` shows the incoming Lancers deposit on Dais's bank account (`anicca_runtime` income classification).
3. Wave 2 plan's Task closing-condition is met and `#325` is then closed by the Wave 2 plan, not by this one.
