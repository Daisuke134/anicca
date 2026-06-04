# earn-lancers Wave 1.5 — email/pw login fallback (design)

## Problem
`skills/anicca-earn-lancers/scripts/login-check.sh` only knows the Google-OAuth
path. On Lancers that path is dead: the account is registered under the
`LANCERS_EMAIL` (+anicca) alias + a raw password, NOT linked to the bare
Google account (memory `feedback_google_login_forever`, verbatim adapter note:
「この Google で会員登録されていません」). So `cf_snapshot` never finds a
"Googleでログイン" button and the script exits 4 → `run.sh` aborts → zero earning.

## Proven source of truth
`.worktrees/adapters/adapters/custom/lancers/scripts/login.sh` (adapter-smith,
live-verified 2026-06-03, submitted gig 5552409). It uses email/pw form + email
2FA. We mirror its exact selectors and flow. Do NOT reinvent.

## Root-cause finding (live probe 2026-06-05)
Two bugs, not one:
1. The Google button never renders (account uses `+anicca` alias) → `exit 4`.
2. The session-status probe itself is broken: `GET
   /sessions/$USER_ID/cookies?sessionKey=` returns an **HTML error page**, not
   JSON. So `HAS` is always 0 even when the session IS logged in. The current
   `default` session is ALREADY logged into Lancers (live `/mypage` shows
   `ランサーメニュー` + `発注者に切り替え`), yet login-check.sh would still
   fall into the dead Google path and exit 4.

Therefore the reliable login signal is the adapter's: navigate `/mypage`, parse
snapshot (python `json.loads(strict=False)` — the raw JSON contains unescaped
control chars that break `jq`), and check `url contains /mypage` AND snapshot
contains `ランサーメニュー|発注者に切り替え`. Replace the broken cookie probe
with this.

## Decision
1. **Replace** the broken cookie probe with a `/mypage` snapshot probe
   (adapter-proven). If logged in → exit 0 immediately.
2. When not logged in, **skip the dead Google path** and go straight to
   **email/pw form submission**. Selectors come verbatim from the proven
   adapter:

| field          | snapshot selector (text)            | ref pattern |
|----------------|-------------------------------------|-------------|
| email textbox  | `textbox "メールアドレス"`           | `e[0-9]+`   |
| password box   | `textbox "パスワード"`               | `e[0-9]+`   |
| login button   | `button "ログイン"`                  | `e[0-9]+`   |
| 2FA code box   | `textbox "認証コード"`               | `e[0-9]+`   |
| 2FA verify btn | `button "認証する"`                  | `e[0-9]+`   |

NOTE: `cf_snapshot` returns JSON `{snapshot, url}`. The adapter greps the
`.snapshot` string with `textbox "X"` ... `e\d+`. The existing login-check.sh
python regex `ref=(\S+)` does NOT match this format (camofox uses
`textbox "メールアドレス" [ref=e12]` style OR `... e12` depending on version).
We therefore reuse the adapter's grep approach (`grep -oE 'e[0-9]+'` after a
label grep) which is the live-verified extractor, not the unproven python regex.

## Flow (fallback branch only — Google path untouched)
```
Google button ref empty
  └─ DON'T exit 4
     ├─ guard: LANCERS_EMAIL & LANCERS_PASSWORD present? no → exit 4 (hardblock json)
     ├─ navigate TAB to https://www.lancers.jp/user/login
     ├─ snapshot → extract email/pw/login refs (grep 'textbox "メールアドレス"' → e\d+)
     ├─ refs missing → save hardblock json, exit 4
     ├─ type LANCERS_EMAIL into email ref     (cf type endpoint)
     ├─ type LANCERS_PASSWORD into pw ref
     ├─ click login ref                        (fire-and-forget, -m 60 || true)
     ├─ sleep 5; snapshot; read .url
     ├─ if url contains 'verify_code':
     │    ├─ gog gmail search 'from:lancers.co.jp subject:ログイン認証コード newer_than:1h'
     │    │     → 6-digit code  (retry up to 4× / 8s — email latency)
     │    ├─ code empty after retries → save hardblock json, exit 4
     │    ├─ snapshot → 認証コード ref + 認証する ref
     │    ├─ type code, click verify, sleep 5
     ├─ CAPTCHA guard (recaptcha/hcaptcha/turnstile/cloudflare in snapshot)
     │    → save hardblock json, exit 9
     └─ re-probe cookies (lancers.jp domain) → >0 ? exit 0 : save hardblock, exit 4
```

## Secrets
- Loaded only via `_lib.sh` `set -a; . ~/.openclaw/.env`.
- NEVER echo `LANCERS_EMAIL` / `LANCERS_PASSWORD` / codes to stdout/stderr/git.
  The cf `type` payloads are built with `jq -n --arg` (no shell interpolation
  into log), and logs use the existing `log/err` helpers with literal strings
  only. `redact()` already covers `LANCERS_PASSWORD`.

## Hard-block / exit contract (unchanged semantics)
| exit | meaning                                              |
|------|------------------------------------------------------|
| 0    | lancers cookie present (session live)                |
| 3    | camofox down                                         |
| 4    | login could not complete (no creds / refs / 2FA) — hardblock json written, task stays OPEN |
| 9    | real CAPTCHA element rendered — hardblock json, OPEN |

## Verification (5-step gate, real run — NOT offline fixture)
1. `login-check.sh` → exit 0 + "lancers cookie present/obtained".
2. `run.sh --dry-run` → envelope with ≥3 `status:"dry-run"` candidates; paste
   JIDs + titles as proof.
3. (gated `ANICCA_LIVE_SUBMIT=1`) one real submit `--confirm --max-apply 1
   --max-budget-jpy 5000` on lowest-budget candidate → `finish_url` contains
   `propose_finish`; paste it + the runs.jsonl row.

## Out of scope
- No change to scan/select/apply logic.
- No new cron wiring here (cron `0 10 * * *` is a follow-up once login proven).
- Session key stays `default` (whole skill is consistent on it).
