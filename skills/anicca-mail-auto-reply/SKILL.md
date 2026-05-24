---
name: anicca-mail-auto-reply
description: {{profile.contact.personalEmail}} の INBOX を 3 時間毎に巡回し、未返信の人手要のメール (recruit / business / 出演交渉 等) に Anicca が即返信する。MUFG/明細/プロモは無視。Jordan Belfort speed。
version: 0.1.0
---

# anicca-mail-auto-reply

`{{profile.contact.personalEmail}}` の受信箱に来た **人手返信要のメール** を 3 時間毎に拾い、
Anicca が即返信する skill。Dais が打ち返しを忘れて機会を逃すのを防ぐ。

## What it does

1. `gog gmail search` で過去 48 時間以内の未読 / 未返信 thread を抽出
2. 各 thread を分類:
   - **REPLY**: 出演交渉 / 物件 / リクルート / 法人問合せ / 寺院 / カフェ / 顧客 / 締切つきの申請依頼や事務連絡
   - **SKIP**: 明細 (MUFG, EPOC, Stripe), MUFG デビットの「ご利用のお知らせ」や請求・引落・カード利用通知, promo, newsletter, system notification, 自動配信, 自分宛てや自分の配信元のメール ({{profile.contact.personalEmail}}, <your-name>, <your-name>, Anicca from Anicca), CAMPFIRE / skyticket / クラウドファンディング系の販促メール, 求人・転職の自動配信（応募リクエスト / オススメ求人 / 求人速報 / 求人特集 / 「Your background could be a match」「Please submit a quick application」系の Indeed 通知）
   - ニュースレター / ダイジェスト / ラウンドアップは、本文に founder / meeting / call / zoom などの一般語があっても SKIP
3. REPLY 候補は OpenClaw に投げて短い返信ドラフトを作成
4. `gog gmail send --reply-to-message-id` で返信送信
5. Slack `#metrics`（channel id: `{{profile.channels.reportChannel}}`）に「返信した thread 一覧 + 1行サマリ」報告

## Required env (`~/.openclaw/.env`)

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID={{profile.channels.reportChannel}}
```
gog の `-a {{profile.contact.personalEmail}}` token は既存。

## Files

| Path | Purpose |
|------|---------|
| `scripts/lib/triage.py` | thread を REPLY / SKIP / FOLLOWUP に分類するルール (regex + LLM) |
| `scripts/lib/draft.py` | OpenClaw に投げて Anicca persona で返信ドラフトを作る |
| `scripts/phase1-scan.sh` | INBOX 巡回 → triage → 候補 JSON 出力 |
| `scripts/phase2-reply.sh` | 候補 JSON を順に処理して gog gmail send |
| `scripts/run.sh` | phase1 + phase2 を順番に実行 + Slack 報告 |
| `data/state.json` | 既に返信した thread id を記録して二重送信を防ぐ |
| `data/skip-patterns.json` | 永続的に無視する from / subject regex リスト |

## Triage rules (default)

| カテゴリ | 例 from / subject | アクション |
|---------|-----------------|---------|
| 出演交渉 | 下北GRIP, oasis, 中野, 新宿, open mic 主催 | REPLY |
| 物件 | kashispace, suumo, athome, 賃貸 | REPLY |
| 法人問合せ | founders@*, info@*, hello@* | REPLY |
| 寺院 | お寺, 寺, temple, 慈恵院 | REPLY |
| カフェ供給 | kumato, mango, 食材, supply | REPLY |
| 自動配信 | system, no-reply, noreply, 自動 | SKIP |
| 明細 | mufg, epoc, stripe, square | SKIP |
| Promo | mid-tenshoku, asahi, newsletter | SKIP |
| LinkedIn 等 | invitations@linkedin, notify@ | SKIP |

`skip-patterns.json` で per-instance 拡張可能。

## Cron

| schedule | 内容 |
|---------|----|
| `0 */3 * * *` JST | `phase1-scan.sh && phase2-reply.sh` 連続実行 |

## Guards

- 返信前に `state.json` に thread id を記録 → 失敗時 rollback
- 同 thread に 24h 以内に既存返信あれば SKIP (フラグ `--allow-double` で上書き)
- 1 run で最大 5 通まで送信 (暴走防止)
- 送信は **draft → 5 秒 sleep → send** の 2 段階で、Slack approve UI で停止できる版を future にする (v0.1 は即送)
- Anicca name で送信する。Anicca 名 NG なリクエストは SKIP (Dais 個人宛は対象外)

## Implementation phases

| Phase | やること | 状態 |
|-------|---------|-----|
| 0 | skill scaffold (SKILL.md + dir) | ✅ |
| 1 | lib/triage.py + lib/draft.py 実装 | ✅ |
| 2 | phase1-scan.sh + phase2-reply.sh 実装 | ✅ |
| 3 | 手動 dry-run (`DRY_RUN=1`) で 1 回確認 | ✅ |
| 4 | cron `0 */3 * * *` JST 登録 + gateway restart | 🔴 |
| 5 | 実走 1 cycle で動作確認 | 🔴 |
| 6 | 1 週間運用後 false-positive / miss を triage rules に反映 | 🔴 |
