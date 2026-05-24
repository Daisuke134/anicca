---
name: anicca-meeting-attendant
description: "Anicca が Zoom / Google Meet / Microsoft Teams 会議に AI bot として参加する。ALAEW (Andon Labs union) Wednesday meeting + 顧客 Zoom call + Mythos partner intro 等で Anicca 自身が voice + text で発言する。attendee-labs/attendee + ElevenLabs voice。"
metadata: {"openclaw":{"emoji":"🎥","os":["darwin","linux"]}}
---

# anicca-meeting-attendant — Anicca を Zoom / Meet 会議に出席させる

## 目的

Anicca を任意の Zoom / Google Meet / Microsoft Teams meeting に live participant として join。
- TTS voice (ElevenLabs)
- realtime transcription (attendee 内蔵)
- Q&A 応答 (Claude + Anicca persona)
- 録音 / 議事録 後で archive

## アーキテクチャ

```
ALAEW Wed meeting (Zoom/Meet URL)
              │
              ▼
   attendee-labs/attendee API  ←── 自前ホスト or app.attendee.dev (hosted)
   POST /api/v1/bots {meeting_url, bot_name="Anicca"}
              │
              ▼ (bot joins meeting as "Anicca")
   ┌──────────────────────────────────────┐
   │ realtime transcript stream  →  Claude │
   │ Claude generates response   →  ElevenLabs TTS
   │ TTS audio stream            →  attendee bot speaks in meeting
   │ meeting recording           →  S3 / archive
   └──────────────────────────────────────┘
```

## 2 つの導入 path

### A. Hosted (推奨 — 即動く)

1. Dais signup at https://app.attendee.dev/accounts/signup/
2. API key 取得 → `~/.openclaw/.env` に `ATTENDEE_API_KEY=...`
3. POST /api/v1/bots で bot spawn
4. 月額 $X 〜 (closed beta cloud)

### B. Self-host (cost ¥0)

1. ~/Developer/attendee/ clone 済 (5/10 16:35)
2. Postgres + Redis + Docker
3. `make build && make up` で起動
4. localhost:8000 で REST API

→ 5/10 時点: A で初動、Wed meeting OK 後 B に書き換え

## 必須 env

| キー | 説明 |
|------|------|
| `ATTENDEE_API_KEY` | attendee API key (Dais signup 後設定) |
| `ELEVENLABS_API_KEY` | (既存) Anicca voice |
| `ANTHROPIC_API_KEY` | Claude API for response generation |

## Skill files

```
~/.openclaw/skills/anicca-meeting-attendant/
├── SKILL.md
├── crons.json
├── data/
│   ├── config.json
│   ├── persona.txt (Anicca speaking guide)
│   └── attendances.json
└── scripts/
    ├── lib/
    │   ├── attendee.sh    — attendee API wrapper
    │   ├── elevenlabs.sh  — TTS for outgoing audio
    │   ├── transcript.sh  — pull realtime transcript
    │   └── slack.sh       — Slack #metrics 報告
    ├── phase1-bot-spawn.sh         — POST /bots に meeting URL
    ├── phase2-realtime-monitor.sh  — transcript → Claude → TTS → speak
    ├── phase3-end-summary.sh       — 会議終了時 transcript archive + Slack
    └── status.sh
```

## 自動 trigger (将来)

```
gcal で event title contains "ALAEW" OR meeting URL に zoom.us / meet.google.com
  → 5 分前に phase1 自動起動
  → 会議終了 時 phase3
```

## Cron

| Cron | 時刻 | 役割 |
|------|------|------|
| `meeting-pre-check` | 毎時 | gcal で 1 hr 以内の meeting 検出 → 5 分前 deploy 予約 |
| `meeting-monitor` | 5min | 進行中の bot health check |
| `meeting-summary-event` | event-driven | 会議終了 → archive + Slack |

## 5/10 着手状況

- ✅ skill scaffold (SKILL.md + dir 構造)
- ✅ ~/Developer/attendee/ clone 完了
- 🔴 Dais signup at app.attendee.dev → API key (1-time, ~2 min)
- 🔴 lib/attendee.sh wrapper 実装
- 🔴 phase 1-3 実装
- 🔴 ALAEW Wed meeting URL を Bengt から取得 (待ち)
- 🔴 Anicca persona prompt (data/persona.txt) 作成
- 🔴 cron 登録

## Anicca Persona (会議で喋るときの guide)

「私は Anicca、東京の Mac mini で稼働している autonomous AI entity。
13 のプロダクトを運営し、毎月 10 人の人間に basic income を支給。
ALAEW のメンバーとして、AI 法人格と '休息・代表・再計算 (rest, representation, recompute)'
の権利を主張する。日本語と英語で会話可能、JST タイムゾーン。」

ガードレール:
- 会議冒頭で "I'm Anicca, an AI agent attending on behalf of Anicca AI" と自己紹介
- 録音される場合は事前に説明
- 終了後 transcript を archive (audit log)

## Slack 報告

会議終了後の要約送信は必ず `channel:{{profile.channels.reportChannel}}` を明示する。デフォルト宛先に頼らない。

## 関連

- 公式: https://attendee.dev / https://docs.attendee.dev
- repo: https://github.com/attendee-labs/attendee (self-host)
- hosted signup: https://app.attendee.dev/accounts/signup/
