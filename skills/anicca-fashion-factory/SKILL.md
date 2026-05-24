---
name: anicca-fashion-factory
description: End-to-end self-contained AI Fashion EC Brand. anicca lowercase wordmark を Tee/Hoodie/Cap (M only) に印字して Printful on-demand → Stripe Checkout → 顧客直送。自分の TikTok @anicca.jpx draft 投稿、自分の評判管理 (X mention scrape → Claude sentiment → bad review なら Gmail 30% off coupon)、自分の売上 Slack 報告 — 全部 1 skill で完結。任意 entity に install すれば logo 1個渡すだけで brand が起動。
metadata:
  tags: fashion, printful, stripe, postiz, agent-{{profile.lateness.stakeholders.channel}}, end-to-end, self-contained
  requires:
    bins: [bash, python3, jq, curl]
    env: [STRIPE_SECRET_KEY, FAL_API_KEY, PRINTFUL_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, POSTIZ_API_KEY, RESEND_API_KEY]
---

# anicca-fashion-factory

Anicca app icon ロゴ T-shirts/hoodies/caps を Printful on-demand 販売 → 自分の TikTok 集客 → Stripe Checkout → 顧客直送 → 自分の評判管理 end-to-end。任意 entity が skill install で **「AI ファッションブランドで生計立つ」** 即起動可能。

## YOUR ENTIRE TASK (cron に応じて 1 つ実行)

| cron | bash | 動作 |
|----|----|----|
| `fashion-product-init-once` (install) | `python3 ~/.openclaw/skills/anicca-fashion-factory/scripts/product-init-once.py` | 3 商品 mockup 生成 + Stripe products + Payment Links + LP 更新 |
| `fashion-lp-sync-daily` (0 JST) | `python3 ~/.openclaw/skills/anicca-fashion-factory/scripts/lp-sync-daily.py` | products.json → /fashion/page.tsx 同期 + push |
| `anicca-fashion-slideshow-daily` (10 JST) | `bash ~/.openclaw/skills/anicca-fashion-slideshow/scripts/00-run-daily.sh` | 自分の TikTok @anicca.jpx draft 投稿 (slideshow factory が cover) |
| `fashion-stripe-fulfillment` (event) | `bash ~/.openclaw/skills/anicca-fashion-factory/scripts/stripe-fulfillment-event.sh` | Stripe webhook → Printful 発注 + Slack 通知 (Netlify function 経由) |
| `fashion-shipping-status-daily` (10 JST) | `python3 ~/.openclaw/skills/anicca-fashion-factory/scripts/shipping-status-daily.py` | Printful tracking pull → Resend 配送通知 |
| `fashion-review-scrape-daily` (12 JST) | `bash ~/.openclaw/skills/anicca-fashion-factory/scripts/review-scrape-daily.sh` | X mention scrape → Claude sentiment → positive で quote tweet / negative で customer-support trigger |
| `fashion-customer-support-event` (event) | `bash ~/.openclaw/skills/anicca-fashion-factory/scripts/customer-support-event.sh` | bad review 検知時: Stripe coupon 30% off + Gmail 自動送信 |
| `fashion-sales-report-daily` (23 JST) | `python3 ~/.openclaw/skills/anicca-fashion-factory/scripts/sales-report-daily.py` | Stripe 売上 → Slack #metrics |

## 商品ライン (実装済 5/8)

| 商品 | 価格 | Printful base | Stripe Payment Link |
|------|----|----|----|
| Anicca Tee — Black (M only) | $30 / ¥4,500 | Bella+Canvas 3001 | `cNi5kD7G69FsghGawu28806` |
| Anicca Hoodie — Black (M only) | $50 / ¥7,500 | Gildan 18500 | `4gM8wP8Ka2d06H6awu28807` |
| Anicca Cap — Black | $35 / ¥5,250 | Yupoong 7005 | `6oU00jaSi04S1mMdIG2880d` |

設計: anicca lowercase wordmark を Tee/Hoodie 左胸 print + Cap 中央 embroidery。

## End-to-end flow

```
[install once] fal.ai mockup → Stripe products → Payment Links → /fashion LP push

[毎日 10 JST] anicca-fashion-slideshow-daily
   fal.ai 男女モデル AI 写真 → Pillow 6-slide → Postiz @anicca.jpx draft

[毎日 0 JST]  fashion-lp-sync-daily
   products.json → /fashion page.tsx (差分あれば push、なければ no-op)

[event Stripe webhook] stripe-fashion-webhook.js (Netlify)
   checkout.session.completed → Printful order create → Resend 発注確認 → Slack 通知

[毎日 10 JST] fashion-shipping-status-daily
   Printful tracking pull → Resend 配送通知 → delivered で satisfaction survey

[毎日 12 JST] fashion-review-scrape-daily
   agent-{{profile.lateness.stakeholders.channel}} X (Twitter) で `anicca tee` mention scrape → Claude sentiment 判定
   positive → 自分で quote tweet + 感謝 (Postiz X)
   negative → customer-support-event 発火

[event] customer-support-event
   Stripe coupon 30% off 発行 + Gmail 自動送信 + Slack escalation log

[毎日 23 JST] fashion-sales-report-daily
   Stripe 売上集計 → Slack #metrics → 月末に MRR 1% を /donation, 残り /income に振替
```

## SNS account architecture

| channel | warmup phase | post-warmup |
|---|---|---|
| TikTok | `@anicca.jpx` (integration_id `cmlrv8jq000hun60yy57eaptx`) **draft mode** | `@anicca.fashion` 専用 |
| X | empire 横断 voice `@aniccaxxx` (X-mkt §31 cover) | `@anicca.fashion` 専用 |
| IG | `@anicca.jpx` IG | `@anicca.fashion` 専用 |
| {{profile.lateness.stakeholders.channel}} | `hello@aniccaai.com` (Anicca empire 共通) | `support@anicca.fashion` 将来 |

## Reporting

各 script は最終行で:

成功:
```
✅ <action>: <count or url>
```

失敗:
```
❌ <action> FAILED: <reason>
```

cron delivery が #metrics に流す。Slack tool は直接呼ばない (lib/slack_helper.py 経由)。

## Money source

各 Stripe Payment Link → 顧客 USD/JPY 支払い → Anicca account → Printful API auto-print → 顧客直送。Printful margin per item ($16-$30/枚)。Anicca empire 全体: 月次純利 1% → /donation、残り → /income。

## End-to-end completion criteria

| Step | Status |
|------|--------|
| 1. 手動フル実行 | ✅ 2026-05-07 — 3 商品 Stripe live + LP push |
| 2. skill 化 | ✅ |
| 3. skill 経由再実行 | ✅ shipping-status-daily / sales-report-daily / slideshow-daily 実走確認済 |
| 4. today cron +5min 検証 | ⏳ review-scrape / lp-sync / customer-support の 3 つ残り |
| 5. daily cron 全 register | ⏳ review-scrape (12 JST) / lp-sync (0 JST) / customer-support (event) を register 後完了 |
