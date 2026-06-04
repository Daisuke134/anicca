# Plan — earn-lancers email/pw login fallback (Wave 1.5)

Worktree: `/Users/anicca/anicca-oss/.worktrees/p8-earn-fix` on `feat/p8-earn-fix`
File: `skills/anicca-earn-lancers/scripts/login-check.sh` (+ `_lib.sh` helpers)

## Task 1 — add robust snapshot helpers to _lib.sh
Add two helpers after `cf_snapshot` that parse the camofox snapshot JSON with
python `json.loads(strict=False)` (jq dies on unescaped control chars):
- `cf_snapshot_text <tab>` → prints `.snapshot` string (falls back to raw).
- `cf_url <tab>` → prints `.url`.
Test: `source _lib.sh; cf_url <livetab>` prints a URL.

## Task 2 — rewrite login-check.sh
Replace body (keep header comment + `set` + source + `cf_health`):
1. Probe `/mypage`: open tab, sleep 5, `cf_snapshot_text` + `cf_url`.
   - logged-in signal: url has `/mypage` AND text has `ランサーメニュー` or
     `発注者に切り替え` → `ok`, `cf_close`, exit 0.
2. CAPTCHA guard on that snapshot (recaptcha/hcaptcha/turnstile/cloudflare) →
   write hardblock json, exit 9.
3. Not logged in → email/pw fallback:
   - guard creds present (`LANCERS_EMAIL`,`LANCERS_PASSWORD`) else hardblock+exit4.
   - navigate same tab to `/user/login`, sleep 4, snapshot.
   - extract refs: `grep -E 'textbox "メールアドレス"' | grep -oE 'e[0-9]+' | head -1`
     same for `パスワード` and `button "ログイン"`.
   - refs missing → hardblock + exit 4.
   - cf type email ref ← LANCERS_EMAIL; cf type pw ref ← LANCERS_PASSWORD.
   - cf click login ref (`-m 60 ... || true`), sleep 5.
   - `cf_url`: if contains `verify_code` → 2FA:
     - loop up to 4× (sleep 8 between): `gog gmail search
       'from:lancers.co.jp subject:ログイン認証コード newer_than:1h' --limit 1
       --json | jq '.[0].snippet' | grep -oE '[0-9]{6}'`.
     - code empty after retries → hardblock + exit 4.
     - snapshot → `textbox "認証コード"` ref + `button "認証する"` ref; type code,
       click verify, sleep 5.
4. Re-probe `/mypage` (navigate same tab, sleep 4, snapshot): logged-in signal →
   exit 0; else write hardblock json (snapshot text, head -c 4000), exit 4.
All secrets only via jq `--arg`; logs use literal strings only.

## Task 3 — verify (real run, 5-step gate)
- `bash login-check.sh; echo "exit=$?"` → exit 0.
- `bash run.sh --dry-run | jq '.candidates | length, [.[].status] '` → ≥3 dry-run.
  Paste JIDs + titles.
- gated: `ANICCA_LIVE_SUBMIT=1 bash run.sh --confirm --max-apply 1
  --max-budget-jpy 5000` → a candidate with `status:"applied"` + `finish_url`
  containing `propose_finish`; paste it + runs.jsonl tail.

## Task 4 — commit + push
`git add -A && git commit -m 'fix(earn-lancers): email/pw form fallback when
Google OAuth button absent (Wave 1.5)' && git push -u origin feat/p8-earn-fix`.
