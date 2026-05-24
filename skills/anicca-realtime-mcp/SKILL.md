---
name: anicca-realtime-mcp
description: LiveKit Agents で realtime voice + OpenClaw MCP tool calling を提供。phone / Zoom / Meet で Anicca が gemini-2.5-flash で会話しながら 60+ skill を実行できる。
version: 0.1.0
---

# anicca-realtime-mcp

ElevenLabs Conv AI で詰まった「realtime 中の tool calling」を LiveKit Agents +
OpenClaw MCP loopback で解決する skill。

## What it does

- Voice realtime (gemini-2.5-flash + ElevenLabs Adam) を LiveKit room 内で提供
- `mcp.MCPServerHTTP(url="http://127.0.0.1:60161/mcp")` で OpenClaw 全 skill を tool として注入
- phone (Twilio SIP trunk → LiveKit), Zoom/Meet (attendee voice_agent_settings.url で room 参加 URL を渡す), web (LiveKit JS SDK) すべて同じ agent

## Files

| Path | Purpose |
|------|---------|
| `main.py` | LiveKit JobContext entrypoint。ElevenLabs STT/TTS + gemini-2.5-flash LLM + Silero VAD + MCP wired |
| `requirements.txt` | livekit-agents[elevenlabs,google,silero,mcp] 等 |
| `scripts/run.sh` | venv bootstrap + `python main.py {dev|start|connect}` |

## Required env (`~/.openclaw/.env`)

```
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
ELEVENLABS_AGENTS_KEY=sk_...
GOOGLE_API_KEY=...                   # Gemini API key (or GOOGLE_APPLICATION_CREDENTIALS)
OPENCLAW_MCP_URL=http://127.0.0.1:60161/mcp   # default OK
ANICCA_VOICE_ID=pNInz6obpgDQGcFmaJgB    # optional: override
ANICCA_TTS_MODEL=eleven_flash_v2        # optional
ANICCA_LLM_MODEL=gemini-2.5-flash       # optional
```

## Usage

### Local dev (LiveKit Cloud sandbox UI)

```bash
bash ~/.openclaw/skills/anicca-realtime-mcp/scripts/run.sh dev
# Open the sandbox URL printed in stdout, hit "Start" → realtime convo
```

### Production worker

```bash
bash ~/.openclaw/skills/anicca-realtime-mcp/scripts/run.sh start
```

### Connect to a specific room (debug)

```bash
ROOM=anicca-test \
  bash ~/.openclaw/skills/anicca-realtime-mcp/scripts/run.sh connect
```

## Phone (Twilio → LiveKit)

1. LiveKit SIP inbound trunk 作成 (`livekit-cli sip inbound-trunk create ...`)
2. Twilio +1 (336) 652-6842 の voice URL を SIP origination URI へ向ける
3. LiveKit dispatch rule で着信を `agent_name=anicca-realtime-mcp` の room にマッピング
4. agent worker (`run.sh start`) を Mac mini で常時稼働

## Meet / Zoom (attendee voice_agent_settings)

`scripts/phase4-realtime-join.sh` の `VOICE_AGENT_URL` を
`https://aniccaai.com/voice-agent-livekit/?room=<room-id>` に書き換え。
landing app に LiveKit JS SDK ベースの voice-agent ページを追加する (TODO Phase 5)。

## Implementation Phases (本 skill)

| Phase | やること | 状態 |
|-------|---------|-----|
| 0 | skill scaffold (この repo) | ✅ |
| 1 | venv + livekit-agents install | 🔴 |
| 2 | LiveKit Cloud project 作成 + API key 取得 → `~/.openclaw/.env` | 🔴 |
| 3 | `run.sh dev` で sandbox 動作確認 ({{profile.lateness.stakeholders.channel}} で realtime convo) | 🔴 |
| 4 | OpenClaw MCP tool が voice 中で呼べることを smoke test (例: 「最新メール 5 件」) | 🔴 |
| 5 | aniccaai.com に LiveKit voice-agent page 追加 → attendee 経由 Meet/Zoom 統合 | 🔴 |
| 6 | Twilio SIP trunk → LiveKit room 接続 → phone realtime + tool 動作確認 | 🔴 |
| 7 | cron / systemd で worker 永続化 + Slack 監視 | 🔴 |

## ElevenLabs Native agent との関係

| 用途 | どっちを使う |
|------|-------------|
| シンプル realtime 通話受け (会話だけ) | ElevenLabs Native (既存 `agent_6601kr8fjyj3e4hrdb00kv1942ne`) |
| tool / skill 起動 / データ取得 | **LiveKit Agents (この skill)** |

Phase 6 完了後、ElevenLabs Native は廃止検討。
