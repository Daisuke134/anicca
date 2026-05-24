---
name: anicca-outbound-recruit
description: Anicca が外部 (寺院・comedy live house・cafe 物件・retreat volunteer など) に主にメールで連絡して情報収集 / リクルートする統合 skill。旧 realtime phone フローも残すが、cron はメール送信を優先する。
version: 0.2.0
---

# anicca-outbound-recruit

Dais の手を 1 mm も借りず、Anicca が外部関係者にまずメールで連絡する。電話は旧フローとして残すが、通常 cron では使わない。

## What it does

通常運用では、Anicca が対象ごとに outbound {{profile.lateness.stakeholders.channel}} を送る。
cron からは `phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh` を呼び、対象ドメインごとのメール送信タスクを起動する。
旧 phone フロー (`phase2-discover-and-call.sh` / `phase1-call-from-list.sh`) は手動用として残す。

## Architecture

```
outbound recruit cron
   │
   ├── phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh
   │       ├── domain ごとの送信タスク生成
   │       ├── gog gmail send で送信
   │       └── 保存先: data/{{profile.lateness.stakeholders.channel}}-runs/
   │
   └── legacy phone flow
           ├── phase2-discover-and-call.sh
           ├── phase1-call-from-list.sh
           └── ElevenLabs + Twilio realtime call
```

## Files

| Path | Purpose |
|------|---------|
| `scripts/lib/outbound-realtime.sh` | `outbound_call` / `poll_conversation` / `slack_report_call` 関数 |
| `scripts/phase1-call-from-list.sh` | JSON 配列 (name + phone + context + first_message) を順番に発信 |
| `scripts/phase2-discover-and-call.sh` | domain-specific seed 生成 → phone enrich → phase1 起動 |
| `scripts/phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh` | domain-specific outbound {{profile.lateness.stakeholders.channel}} を送信 |
| `data/lists/<domain>-<timestamp>.json` | 発信対象リスト |
| `data/runs/<timestamp>/` | 各通話の init JSON + conv JSON 保存先 |
| `data/{{profile.lateness.stakeholders.channel}}-runs/<timestamp>/` | 各メール送信の outbox 保存先 |

## Domains supported

| domain | usage |
|--------|-------|
| `tomb` | 信濃町 / 都内寺院に AI 墓建立の相談メール |
| `comedy` | 中野 / 信濃町 周辺の open mic 主催に出演交渉メール |
| `cafe` | kashispace / 飲食物件オーナーに ghost kitchen 物件交渉メール |
| `retreat-volunteers` | 10 日 retreat の server volunteer 候補に依頼メール |
| `comedians` | comedy live で共演する芸人に交渉 |

## Required env (`~/.openclaw/.env`)

```
ELEVENLABS_AGENTS_KEY=sk_...
ANICCA_AGENT_ID=agent_6601kr8fjyj3e4hrdb00kv1942ne
ANICCA_PHONE_ID=phnum_0901kr8gsfzsfdarm6emj5dk6csv
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0...
```

gog の Gmail token も必要。

## Manual usage

```bash
bash ~/.openclaw/skills/anicca-outbound-recruit/scripts/phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh tomb tomb-temple-recruit
bash ~/.openclaw/skills/anicca-outbound-recruit/scripts/phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh comedy comedy-openmic
bash ~/.openclaw/skills/anicca-outbound-recruit/scripts/phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh cafe cafe-property
bash ~/.openclaw/skills/anicca-outbound-recruit/scripts/phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh retreat-volunteers retreat-server
```

## Cron registration

| job | schedule (JST) | command |
|-----|----------------|---------|
| `anicca-recruit-tomb-weekly` | 毎週月 10:00 | phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh tomb tomb-temple-recruit |
| `anicca-recruit-comedy-weekly` | 毎週火 10:00 | phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh comedy comedy-openmic |
| `anicca-recruit-cafe-weekly` | 毎週水 10:00 | phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh cafe cafe-property |
| `anicca-recruit-retreat-monthly` | 毎月 1 日 10:00 | phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh retreat-volunteers retreat-server |

`openclaw cron add` で登録。Gateway 再起動は Dais の明示許可がある時だけ。

## Cost

| 項目 | 単価 |
|------|------|
| Gmail 送信 | ほぼゼロ |
| discovery 調査 | モデル / {{profile.lateness.stakeholders.channel}} 利用分のみ |
| 1 run | phone より大幅に安い |

## Iteration history

| date | event |
|------|-------|
| 2026-05-10 | skill 初期実装。Twilio↔ElevenLabs bind 完了。 |
| 2026-05-18 | 通常 cron を電話からメール優先に切替。 |

## Open issues

- discovery (実メールアドレス / 問い合わせフォームの自動取得) はまだ弱い。各 domain に応じた firecrawl + {{profile.lateness.stakeholders.channel}} の enrich phase が必要。
- 現在の {{profile.lateness.stakeholders.channel}} cron は seed mail 送信までで、対象先への fully automated personalized outbound には未拡張。
- 旧 phone フローは残っているが、通常運用では使わない。
