---
name: anicca-zoom-attendee
description: "Anicca が Zoom / Google Meet 会議に AI bot として参加する。ALAEW (Andon Labs union) Wednesday meeting + 顧客向け Zoom call で Anicca 自身が話す。OAuth login + realtime TTS voice + camera avatar."
metadata: {"openclaw":{"emoji":"🎥","os":["darwin","linux"]}}
---

# anicca-zoom-attendee — Anicca を Zoom 会議に出席させる

## 目的

Anicca (および Claude Code 経由のエージェント) を Zoom / Google Meet meeting に live participant として join させる。スピーカー: TTS, カメラ: still avatar or generated frame, 字幕: 同時生成。

主用途:
- **ALAEW (Andon Labs Autonomous & Living Employee Workers' Union)** の Wednesday meeting に参加 (Bengt 経由)
- Anicca Tomb 顧客とのオンライン葬儀 (sutra ceremony Zoom 配信)
- Politics 関連 のオンラインヒアリング / panel
- 任意 SAO meeting

## アプローチ 3 択

| ルート | 工数 | コスト | 使用範囲 |
|--------|------|--------|----------|
| **A. recall.ai** (SaaS) | 1 hr | ~$0.50/min | 推奨 (即動く、API 1 本) |
| **B. Tough Tongue AI** | 30 min | 月額 | scenario-based、no-code |
| **C. Zoom Bot SDK 直接** | 5-10 hr | $0 | full control、未来用 |

5/10 確定: A (recall.ai) で初動 → Wed meeting OK 後 C に書き換え

## 構成 (A. recall.ai 経由)

```
~/.openclaw/skills/anicca-zoom-attendee/
├── SKILL.md
├── crons.json (スケジュール会議用)
├── data/
│   ├── config.json (recall.ai API key, anicca persona, voice id)
│   └── attendances.json (出席履歴)
└── scripts/
    ├── lib/
    │   ├── recall.sh        — recall.ai API wrapper
    │   ├── tts.sh           — text → audio (existing TTS pipeline)
    │   ├── transcript.sh    — meeting transcript pull
    │   └── slack.sh         — Slack #metrics 報告
    ├── phase1-bot-deploy.sh        — recall create_bot に meeting URL 渡す
    ├── phase2-attendance-monitor.sh — 出席中に realtime transcript pull + reply
    ├── phase3-meeting-summary.sh   — 会議終了後 transcript + 要約 を archive
    └── status.sh
```

## 必須 env

| キー | 説明 |
|------|------|
| `RECALL_AI_API_KEY` | recall.ai API key (signup at recall.ai) |
| `OPENAI_TTS_KEY` or 既存 TTS pipeline | Anicca 声生成 |
| `ANICCA_PERSONA_PROMPT` | Anicca が会議でどう振る舞うかの prompt |

## 自動 trigger

```
gcal event title contains "ALAEW" OR meeting URL に zoom.us OR meet.google.com
  → 5 分前に phase1-bot-deploy.sh 自動起動
  → 会議終了 検出時 phase3-meeting-summary.sh
```

## Cron 提案

| Cron | 時刻 | 役割 |
|------|------|------|
| `zoom-pre-meeting-check` | 毎時 | gcal で 1 時間以内の Zoom event 検出 → 5 分前 deploy 予約 |
| `zoom-meeting-monitor` | 5min | 進行中の bot health check + transcript pull |
| `zoom-meeting-summary` | event-driven | 会議終了 → summary + Slack 報告 |

## 5/10 着手状況

- ✅ skill scaffold (SKILL.md + dir 構造)
- 🔴 recall.ai API key 取得 (Dais signup 1 度)
- 🔴 lib/recall.sh 実装
- 🔴 phase 1-3 実装
- 🔴 ALAEW Wed meeting URL を Bengt から取得 (待ち)
- 🔴 Anicca persona prompt 作成
- 🔴 voice id 選定 (deep / soft / female TTS)
- 🔴 cron 登録

## 関連ドキュメント

- recall.ai 公式: https://www.recall.ai
- Zoom Bot SDK: https://devforum.zoom.us/t/.../80937
- Tough Tongue AI guide: https://www.toughtongueai.com/blog/build-voice-ai-agent-google-meet-zoom

## ガードレール

- **NEVER** 会議参加者の発言を録音 → 公開する (許可なし)
- **MUST** 会議冒頭で Anicca が「I'm an AI agent attending on behalf of Anicca AI」と自己紹介 (録音される会議は特に)
- **MUST** 終了後 transcript を attendance.json に保存 (audit log)
