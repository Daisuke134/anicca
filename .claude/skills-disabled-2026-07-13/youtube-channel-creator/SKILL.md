---
name: youtube-channel-creator
description: Create a YouTube Brand-Account channel under the existing Google login via the daily-driver CloakBrowser, verify-baked. Drives the FULL real flow incl. the one-time phone verification YouTube demands for 3rd+ channels (advanced-features gate → SMS step1/step2). Use when you need a NEW YouTube channel without creating a new Google credential.
---

# YouTube Channel Creator

Create a YouTube **Brand-Account** channel by driving Dais's already-logged-in CloakBrowser (daily-driver,
CDP `http://localhost:9222`). A Brand Account is a channel managed UNDER the existing Google login
(keiodaisuke@gmail.com) — **NO new Google credential is created**, no re-login, no bot block.

## Usage (2-phase — phone verification is now INTEGRATED)
```bash
PY=~/.openclaw/skills/_shared/venv-cloak/bin/python3
SK=~/.claude/skills/youtube-channel-creator/scripts/create_channel.py
# Phase A — start. If a 3rd+ channel needs phone verification, this sends the SMS and exits
#           with {"needs_code": true} (SMS → --phone, default 08046270314). If no verification
#           is needed, it creates the channel directly.
$PY $SK --name "Money Blueprint" --handle "moneyblueprintdaily"
# Phase B — finish: pass the 6-digit SMS code; it enters the code, then creates the channel.
$PY $SK --name "Money Blueprint" --handle "moneyblueprintdaily" --code 123456 [--desc "..."]
```
Outputs one JSON line (`created`, `needs_code`, `resume`, `error`, `url`, `shot`). Then VERIFY (always):
open `youtube.com/channel_switcher` and confirm the new `@handle` row appears.

### The ONE human/service touchpoint = the SMS code
The 6-digit code is sent to the phone (`--phone`). Reading it is the only non-automatable step:
either a human reads it (the number's owner), or wire an SMS-receiving service number (SMSPool/5sim/
Google Voice) as `--phone` and read the code via that service's API, then pass it as `--code`.
(2026-06-29: started on keiodaisuke's number but the owner was abroad → code pending; flow itself
verified working up to step 2/2.)

## The flow (what the script does)
1. `goto youtube.com/channel_switcher` → click "チャンネルを作成" (Create a channel).
2. A dialog "チャンネルのプロフィール" opens with 2 text inputs (名前 / Name, ハンドル / Handle) + a
   "チャンネルを作成" button. It's a Brand Account linked to keiodaisuke@gmail.com.
3. Fill name + handle, click create, wait, screenshot.

## ★ GOTCHAS (each cost a round-trip — follow exactly) ★
- **The dialog inputs have NO `type` attribute.** `querySelectorAll('input[type=text]')` (attribute selector)
  returns 0. You MUST select `querySelectorAll('input')` then filter by the `.type==='text'` **property**.
  This single bug caused every "dialog did not open" / "inputs:0" failure. (Search box has placeholder "検索"
  — exclude it.)
- **Fill via the native value setter** (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set`)
  + dispatch `input`+`change` — plain `.value=` does not register with YouTube's framework.
- **Opening the dialog is flaky.** `get_by_role("button", name="チャンネルを作成")` times out (it's not a real
  button role); the working sequence is: try the role-button (it fails but settles the page) → then
  `get_by_text("チャンネルを作成").first.click()` → poll until the 2 inputs appear. Retry up to 3×.
- **Post-create transient:** right after create the page may show "このチャンネルは存在しません" (channel doesn't
  exist) for a moment — that's eventual consistency, NOT a failure. Verify via the switcher, where the new
  channel appears within seconds.
- **Click the create button with a REAL Playwright click** (`get_by_text("チャンネルを作成", exact=True).last`),
  not `evaluate(el.click())`.

## ★ The anti-abuse gate (3rd+ channel) — now HANDLED by the script ★
Creating a 3rd+ channel pops "上級者向け機能を利用する" (use advanced features) → 認証 → a one-time
**phone verification** at `youtube.com/verify`. The script now drives this automatically:
1. clicks 認証 → goes to `youtube.com/verify` (step 1/2).
2. selects 日本 (best-effort) + fills 電話番号 (placeholder contains "555") via the native setter + clicks 次へ.
   ★ The COUNTRY box may DISPLAY the phone number — that is NORMAL and the form still validates (confirmed
   by Dais 2026-06-29). Don't fight it. ★ → advances to step 2/2 and SENDS the SMS.
3. Phase B (`--code`) enters the 6-digit code in step 2/2 and clicks 送信 → verified → create proceeds.
Constraints: **1 phone number can verify max 2 accounts / year.** If logged out, YouTube bounces to
accounts.google.com and the script returns `NOT_SIGNED_IN` (login = email+password+2FA "tap Yes on phone").

## Verify-baked rule
Never report a channel "created" from the script's `created:true` alone (that only means the button was
clicked). ALWAYS open `youtube.com/channel_switcher` and confirm the `@handle` row is listed.
