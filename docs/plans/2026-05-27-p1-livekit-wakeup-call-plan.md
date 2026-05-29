# P1 — LiveKit 起こし電話 Implementation Plan

> REQUIRED SUB-SKILL: 本人(Claude)が1件ずつ実行し、最後に**実際に Dais へ電話**して検証する（subagent に丸投げしない・dry-run 禁止）。

**Goal:** Anicca が LiveKit Agents で実際に Dais へ電話し、S2S でリアルタイム・滑らか・割り込み可・ツール使用可に会話して起こす。

**Architecture:** LiveKit agent worker(Python) が room に入り、`create_sip_participant` で Dais に発信。音声は AgentSession(S2S)。SIP は Twilio を outbound trunk として使う（既存 Twilio 資産再利用）。発信は scheduler から `lk dispatch`。

**Copy source (proven):** `github.com/livekit-examples/outbound-caller-python`（公式・agent.py）。
**Spec:** `anicca-oss/docs/specs/2026-05-27-livekit-recall-realtime-presence-design.md`

---

## File Structure

| パス | 責務 |
|------|------|
| `skills/wake-me-up/livekit/agent.py` | LiveKit agent worker（entrypoint + WakeAgent + tools） |
| `skills/wake-me-up/livekit/persona.py` | 起こし/遅刻 instructions（owner profile 差込） |
| `skills/wake-me-up/livekit/requirements.txt` | livekit-agents + plugins |
| `skills/wake-me-up/livekit/.env.example` | 必要 env のテンプレ（鍵は gitignore .env） |
| `skills/wake-me-up/livekit/dispatch_call.sh` | scheduler から発信を起動 |
| `skills/wake-me-up/livekit/test/test_persona.py` | persona 単体テスト |

worktree: `feature/livekit-wakeup`（anicca-oss）。

---

### Task 1: LiveKit サーバ creds + Python 環境

- [ ] **Step 1: LiveKit Cloud のプロジェクト作成 + creds 取得**（自分で・browser/CLI）
  `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` を取得し `~/.openclaw/.env` に追記（gitに入れない）。LiveKit CLI: `brew install livekit-cli` → `lk cloud auth`。
- [ ] **Step 2: venv + 依存**
  ```bash
  cd skills/wake-me-up/livekit && python3 -m venv venv && source venv/bin/activate
  pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0" livekit-plugins-noise-cancellation python-dotenv
  ```
- [ ] **Step 3: 接続 smoke**
  Run: `lk room list`（creds が効くか）→ エラーなく応答。

### Task 2: Twilio を LiveKit outbound SIP trunk に接続

- [ ] **Step 1: Twilio Elastic SIP Trunk 作成**（既存 Twilio アカウント・番号を使用）。Twilio 側 Origination/Termination URI を LiveKit SIP endpoint に向ける（docs.livekit.io/telephony/start/sip-trunk-setup の Twilio 手順に従う）。
- [ ] **Step 2: LiveKit outbound trunk 作成**
  ```bash
  lk sip outbound create --trunk '{"name":"twilio-out","address":"<twilio-termination-uri>","numbers":["<TWILIO_PHONE_NUMBER>"],"auth_username":"<...>","auth_password":"<...>"}'
  ```
  返る `SIP_OUTBOUND_TRUNK_ID` を `.env` に保存。
- [ ] **Step 3: 発信疎通テスト**（自分の番号へ素の発信が繋がるか・agent無しでも可）。

### Task 3: agent.py（outbound-caller を起こしペルソナへ改造）

- [ ] **Step 1: persona.py**（owner profile 差込・既存 imokenet 文言を移植）
  ```python
  def wake_instructions(name: str, about: str = "") -> str:
      who = name or "there"
      about_line = f"\nAbout {who}: {about}" if about else ""
      return (f"You are Anicca, {who}'s proactive wake-up companion, on a REAL phone call right now "
              f"to get them physically out of bed.{about_line}\n"
              "- Reply in the language they speak (EN->EN, JA->JA).\n"
              "- One or two short spoken sentences per turn. React to what they say.\n"
              "- Command ONE physical action at a time: sit up -> feet on floor -> stand -> light -> water.\n"
              "- Never accept 'I'm up'/'5 more minutes' — keep going until they're standing.\n"
              "- Warm but firm. When they're truly up, acknowledge and end the call.")
  ```
- [ ] **Step 2: agent.py**（livekit-examples/outbound-caller-python を移植・歯科ペルソナ→起こし）
  ```python
  from __future__ import annotations
  import asyncio, json, logging, os
  from dotenv import load_dotenv
  from livekit import rtc, api
  from livekit.agents import (AgentSession, Agent, JobContext, function_tool, RunContext,
                              get_job_context, cli, WorkerOptions, RoomInputOptions)
  from livekit.plugins import openai, silero, noise_cancellation
  from persona import wake_instructions

  load_dotenv(os.path.expanduser("~/.openclaw/.env"))
  logger = logging.getLogger("anicca-wakeup"); logger.setLevel(logging.INFO)
  OUTBOUND_TRUNK_ID = os.getenv("SIP_OUTBOUND_TRUNK_ID")

  class WakeAgent(Agent):
      def __init__(self, name: str, about: str, dial_info: dict):
          super().__init__(instructions=wake_instructions(name, about))
          self.participant: rtc.RemoteParticipant | None = None
          self.dial_info = dial_info
      def set_participant(self, p): self.participant = p
      async def hangup(self):
          jc = get_job_context()
          await jc.api.room.delete_room(api.DeleteRoomRequest(room=jc.room.name))
      @function_tool()
      async def get_current_time(self, ctx: RunContext):
          """Return the current local time in Tokyo."""
          import datetime, zoneinfo
          now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo"))
          return {"time": now.strftime("%H:%M"), "timezone": "Asia/Tokyo"}
      @function_tool()
      async def end_call(self, ctx: RunContext):
          """End the call AFTER the person has stood up and confirmed."""
          cs = ctx.session.current_speech
          if cs: await cs.wait_for_playout()
          await self.hangup()

  async def entrypoint(ctx: JobContext):
      await ctx.connect()
      dial_info = json.loads(ctx.job.metadata)
      phone = dial_info["phone_number"]
      agent = WakeAgent(dial_info.get("name","Dais"), dial_info.get("about",""), dial_info)
      session = AgentSession(
          vad=silero.VAD.load(),
          llm=openai.realtime.RealtimeModel(voice="ash"),  # S2S ~500ms (要 OPENAI_API_KEY)
      )
      started = asyncio.create_task(session.start(
          agent=agent, room=ctx.room,
          room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVCTelephony())))
      try:
          await ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
              room_name=ctx.room.name, sip_trunk_id=OUTBOUND_TRUNK_ID,
              sip_call_to=phone, participant_identity=phone, wait_until_answered=True))
          await started
          p = await ctx.wait_for_participant(identity=phone)
          agent.set_participant(p)
          await session.generate_reply(instructions="Greet them by name, warm but firm, one line to wake them up now.")
      except api.TwirpError as e:
          logger.error(f"SIP error: {e.message} {e.metadata.get('sip_status')}"); ctx.shutdown()

  if __name__ == "__main__":
      cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="anicca-wakeup"))
  ```
  > S2S モデル: OPENAI_API_KEY があれば `openai.realtime.RealtimeModel`。無ければ Gemini Live(`livekit-plugins-google` の `google.beta.realtime.RealtimeModel`, 既存 GEMINI_API_KEY 再利用)に差替。Task1で在庫鍵を確認して確定。
- [ ] **Step 3: persona 単体テスト**
  ```python
  # test/test_persona.py
  from persona import wake_instructions
  def test_name_injected(): assert "Dais" in wake_instructions("Dais")
  def test_about_injected(): assert "9-5" in wake_instructions("Dais","works 9-5")
  ```
  Run: `python3 -m pytest test/ -q` → PASS

### Task 4: 発信トリガー（worker 起動 + dispatch）

- [ ] **Step 1: worker 起動** `python agent.py dev`（待受）。
- [ ] **Step 2: dispatch スクリプト** `dispatch_call.sh`
  ```bash
  #!/bin/bash
  NAME="${1:-Dais}"; PHONE="${2:-${OSS_USER_PHONE}}"
  lk dispatch create --agent-name anicca-wakeup \
    --metadata "{\"phone_number\":\"$PHONE\",\"name\":\"$NAME\"}"
  ```

### Task 5: E2E 実走（必須・dry-run 禁止）

- [ ] **Step 1:** worker 起動中に `bash dispatch_call.sh Dais ${OSS_USER_PHONE}` で**実際に Dais に発信**。
- [ ] **Step 2:** 通話を実評価: 着信→双方向→1.5秒以内応答→話被せで即停止(barge-in)→「今何時?」で get_current_time 発火→起床確認後 end_call で切断。
- [ ] **Step 3:** 旧 imokenet と自然さ/遅延を比較。劣る点があれば S2S モデル/VAD/turn_detection を調整して再発信。
- [ ] **Step 4:** `superpowers:verification-before-completion` の 5 step gate を通す（録音/通話ログを fresh evidence に）。

---

## Self-Review
- Spec §5(起こしフロー)/§2(LiveKit/S2S)/§8(E2E必須) を Task1-5 で網羅。発信判断(§5の位置ロジック)は #20 で別途（本planは「電話が滑らかに鳴って喋れる」に集中）。
- Placeholder: S2S モデルのみ「在庫鍵で確定」と明記（推測回避）。他は実コード。
- 依存整合: OUTBOUND_TRUNK_ID(Task2)→agent.py(Task3)→dispatch(Task4)→E2E(Task5)。

## Execution
本人が Task1 から順に実行。各 Task 後に動作確認、Task5 で実電話。
