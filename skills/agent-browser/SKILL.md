---
name: agent-{{profile.lateness.stakeholders.channel}}
description: Fast {{profile.lateness.stakeholders.channel}} automation CLI for AI agents. Replaces manual {{profile.lateness.stakeholders.channel}} tasks (form-filling, sign-up flows, scraping, screenshot capture) with reproducible CLI commands. Use when registering accounts, filling Stripe/Postiz/Apify dashboards, scraping competitor profiles, capturing UI screenshots, performing OAuth flows, or any web task previously labeled "manual". Refs from `agent-{{profile.lateness.stakeholders.channel}} snapshot -i` give compact @eN handles in ~200-400 tokens.
metadata:
  tags: {{profile.lateness.stakeholders.channel}}, automation, signup, scraping, screenshots, oauth, forms
  requires:
    bins: [agent-{{profile.lateness.stakeholders.channel}}, node]
---

# agent-{{profile.lateness.stakeholders.channel}}

`/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}` — installed 2026-05-04. Chrome 148.0.7778.97 in `~/.agent-{{profile.lateness.stakeholders.channel}}/{{profile.lateness.stakeholders.channel}}s/`.

## Core loop

```bash
agent-{{profile.lateness.stakeholders.channel}} open <url>
agent-{{profile.lateness.stakeholders.channel}} snapshot -i        # @e1, @e2, ... refs (stale after any page change)
agent-{{profile.lateness.stakeholders.channel}} click @e3
agent-{{profile.lateness.stakeholders.channel}} fill @e5 "text"
agent-{{profile.lateness.stakeholders.channel}} screenshot out.png
agent-{{profile.lateness.stakeholders.channel}} close
```

## Full reference

See `CORE.md` (full agent-{{profile.lateness.stakeholders.channel}} skill from upstream).

## Use cases (Anicca)

| 旧 manual task | 新 automated |
|--------------|------------|
| TT/IG/X アカ作成 | agent-{{profile.lateness.stakeholders.channel}} で signup form 自動入力 (要 Dais の {{profile.lateness.stakeholders.channel}} + password) |
| Postiz integration ID 取得 | login → /dashboard/integrations snapshot → ID 抽出 |
| Stripe product metadata 追加 | dashboard.stripe.com 自動操作 (API 直接が早い場合は API 優先) |
| Printful T-shirt 入稿 | printful.com 自動 + Anicca app icon upload |
| Tokyo Comedy Bar open mic 申込 | tokyocomedybar.com/open-mic-sign-up form 自動入力 |
| 寺/霊園 問合せフォーム | 各寺サイトのフォーム自動 |
| ZIPAIR 予約 | zipair.net 自動 (要 passport/credit card) |
| Resend signup + DNS | resend.com 自動 (DNS は別途) |
| Pipeboard signup | pipeboard.co/auth/signup 自動 |
| AI Tinkerers Tokyo CFP | Connpass form 自動 |

## ガードレール

| ルール | 値 |
|------|---|
| 認証が要るログイン flow | Dais の credentials を `~/.agent-{{profile.lateness.stakeholders.channel}}/sessions/` に保存して再利用、または初回のみ Dais が手動 login → cookie 保存 |
| 2FA / SMS 認証 | 自動化不可、Dais 介入要 |
| 支払い操作 | Dais 確認後のみ実行 (passport / credit card 入力は人間目視) |
| Cookie 同意 | accept で進める |
