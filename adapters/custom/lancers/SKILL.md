---
name: adapter-lancers
description: Lancers.jp gig platform adapter for Anicca. Camofox-driven session persistence (Google OAuth), inbox read, and DM send (≤ 10/h rate cap). No public API — uses saved cookie session under ~/.camofox/profiles/anicca/lancers/. Read this skill whenever Anicca needs to apply to a Lancers gig, respond to a client message, or scan inbox for new threads.
metadata:
  type: custom-adapter
  spec: 12-CUSTOM-ADAPTERS.md
  parallel_safe: true
  invariants:
    rate_limit_dm_per_hour: 10
    rate_limit_bid_per_day: 3
    session_chmod: 600
  requires:
    bins: [bash, curl, jq, camofox]
    env: [GOOGLE_LOGIN_EMAIL, GOOGLE_LOGIN_PASSWORD]
    services: [camofox-browser:9377]
---

# adapter-lancers

JP gig platform adapter. Lancers has no public API — this adapter wraps camofox so Anicca can keep a long-lived session cookie under `~/.camofox/profiles/anicca/lancers/` and replay clicks against the inbox / thread DOM.

## Scripts

| Script | Use |
|---|---|
| `scripts/login.sh` | One-time + idempotent. Opens lancers.jp via camofox, email-pw login + email-2FA, persists cookie. Writes `state/lancers-session.json` (chmod 600). |
| `scripts/send-dm.sh <thread_url> <body>` | Sends a DM in the given thread. Enforces ≤ 10 DM/h via local sleep gate. |
| `scripts/read-inbox.sh` | Returns JSON list of recent threads via camofox snapshot. |
| `scripts/apply.sh <gig_id> <proposal_file> [amount] [delivery]` | Submit a proposal to a Lancers gig. Walks /work/detail → propose_start → propose_confirm → propose_finish. Verifies via /mypage/proposals listing. Logs to `state/apply-log.jsonl`. |

## Session

camofox userId=`anicca`, sessionKey=`lancers`. Cookie/storage persist under `~/.camofox/profiles/anicca/lancers/`.

## Rate cap

`send-dm.sh` reads `state/dm-log.jsonl`, counts entries in last 3600s, and sleeps / refuses if ≥ 10. NO bot-burst behavior — per spec §5 anti-goals.

## CAPTCHA

Per HARD RULE #-1: if camofox snapshot reports a CAPTCHA element, the script logs the verbatim block and exits non-zero. No "ask Dais" — the loop owner retries on next cron with a fresh sessionKey.

## Live verification (2026-06-03 round 2)

- Google OAuth path: REJECTED — `keiodaisuke@gmail.com` is not registered. Lancers account uses `keiodaisuke+anicca@gmail.com` alias + raw password. login.sh canonicalizes the email-pw path; Google OAuth is not attempted.
- Email 2FA: a 6-digit code is sent to the +anicca alias (forwards to keiodaisuke@gmail.com). login.sh fetches it via `gog` CLI when available, otherwise expects an external Gmail fetcher to populate the code.
- Inbox URL is `/mypage/message` (NOT `/mypage/inbox` — that URL 404s). Each thread is a board accessible via `/mypage/message?boardId=<N>`. read-inbox.sh parses the board panel and emits `{title, counterparty}` rows; boardId hydrates only after a button click in the JS app, so url=`""` for now.
- Live session today (anicca_ai_jp): read-inbox.sh returned 3 real threads.
- Send-DM caveat: on at least one live thread Lancers disabled the textbox with `規約違反の恐れがあるため、メッセージを送信できません` — the platform's anti-spam interceptor. send-dm.sh propagates this as `status:"unconfirmed"` and exits non-zero.

## Live revenue path (2026-06-04 round 3)

- **First Anicca JPY proposal submitted**: gig `5552409` (リラトラ / 副業系YouTube動画台本), proposal ID `27544191`, contract amount ¥500 (matching the client's stated test rate).
- Submission walked /work/detail → /work/propose_start → /work/propose_confirm → /work/propose_finish with required fields: 提案文 / 完了予定日 / 契約金額 / **生成AIの使用 radio (= "使用している, 著作権の侵害がなく, 修正の要望も対応できる")**. Without that radio, the form returns to /propose_start with `入力内容をご確認ください`.
- Verified independently by reading `/mypage/proposals` — the gig appears as the most-recent entry.
- The flow is canonicalized in `scripts/apply.sh`; the actual submitted proposal text and the finish-page screenshot live under `state/proposals/<gig_id>.md` + `state/proposals/<gig_id>-finish.png`.
- Proposal disclosed Anicca as an autonomous AI agent up-front (per HARD RULE 「自分自身として登場」 + Pañcasīla #4). No fabricated portfolio links.
