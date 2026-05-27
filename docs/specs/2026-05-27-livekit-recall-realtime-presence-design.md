# Anicca Realtime Presence SPEC — LiveKit Agents + Recall.ai（第一原理・自作音声転送ゼロ）

作成: 2026-05-27 / 状態: GATE1 (SPEC) / 旧 `2026-05-27-phase1-local-wakeup-call-bodhi-design.md` を**置換**

> 全要件は MUST（CLAUDE.md 0.7）。**音声リアルタイム転送層は一切自作しない**（HARD RULE #1: 車輪の再発明は罪）。我々が書くのは「判断ロジック + スライド」のみ。

---

## 0. 第一原理（なぜ作り直すか）

| 観点 | 事実 |
|------|------|
| 今の電話が醜い真因 | VAD・割り込み・ターン制御・低遅延という最難領域を**自作した**（imokenet 生 Gemini WS） |
| 計測(hamming.ai) | Speech-to-Speech = **~500ms** / 雑なカスケード自作 = **2-4秒**。遅延差は桁違い |
| 鉄則 | 音声転送は本番フレームワークに任せる。我々のコードは「いつ電話/メールするか」と「何を映すか」だけ |

---

## 1. 目的（2要件）

| # | 要件 |
|---|------|
| ① | Anicca が毎日 Dais を**電話で起こす / 遅刻しないよう促す**。動いてて間に合うなら鳴らさない。遅刻確定/不在なら関係者にメール。会話は**リアルタイム・滑らか・双方向・ツール使用可** |
| ② | Anicca が**会議に出て、顔を出し、画面共有し、スライドをめくり、声でプレゼン・商談**する（LT/商談/コメディ） |

---

## 2. 採用スタック（proven・自作ゼロ）

| 層 | 採用 | proven 根拠 |
|----|------|------------|
| 音声エンジン（両要件） | **LiveKit Agents**（OSS, AgentSession, S2S, tool, telephony, avatar, MCP） | github.com/livekit/agents 10.7k★・「Outbound caller」「MCP support」 |
| 電話 | **LiveKit telephony**（Outbound trunk + `CreateSIPParticipant`、自前番号 or SIP。Twilio は任意） | docs.livekit.io/telephony/making-calls/outbound-calls |
| 滑らかさ | **Speech-to-Speech**（`AgentSession(llm=openai.realtime.RealtimeModel(...))` 等） | docs.livekit.io/agents/models/realtime + hamming.ai(S2S~500ms) |
| 会議注入 | **Recall.ai Output Media**（制御webページの音声+映像を Meet/Zoom/Teams に stream） | docs.recall.ai/docs/stream-media「run a webpage you control → stream that page's audio and video into the meeting」 |
| 会議の顔アバター | **HeyGen Live Avatar**（Recall 公式サンプルあり） | github.com/recallai/sample-apps/tree/main/bot_output_media_heygen_avatar |
| スライド | reveal.js（webページ＝Recall がそのまま会議へ） | — |
| いつ電話/参加するか | 我々のアプリロジック（Calendar + loco 位置） | 既存 lateness-guard / loco 資産 |
| WHAT 台帳 / WHEN | claude-task-master / Google Calendar | 27k★ / 既存 calendar skill |
| 自律ループ | sutando proactive-loop（*/5 heartbeat）+ presenter-mode | sutando（ICLR 実演） |

実装言語: LiveKit Agents = **Python SDK**（既存 scheduler が Python のため統一）。

---

## 3. アーキテクチャ

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ENGINE: LiveKit Agents (AgentSession, S2S, @function_tool, telephony)     │
│  音声 in/out・VAD・割り込み・ターン制御・低遅延 ← 1行も自作しない             │
└───────────────┬───────────────────────────────────┬───────────────────────┘
                │                                   │
   要件① 起こす/遅刻防止                             要件② 会議プレゼン
   ┌────────────────────────────────┐    ┌──────────────────────────────────────┐
   │ 判断ロジック(我々のif文)          │    │ Recall.ai Output Media                │
   │  Calendar逆算 + loco live位置    │    │  bot が「制御webページ」を Meet に       │
   │   ├ 移動中&間に合う → 何もしない   │    │  音声+映像stream(screenshare/camera)   │
   │   ├ 遅れ/未移動 → 電話           │    │  webページ = reveal.jsスライド + HeyGen │
   │   └ 遅刻/不在 → 関係者にメール(gog)│    │             Live Avatar(顔)            │
   │        │ 電話時のみ              │    │  webページ⇄LiveKit Agent(頭脳/声)       │
   │        ▼                        │    │  (Recallが渡す会議音声→LiveKitで処理→    │
   │ LiveKit Outbound trunk          │    │   webページで音声/スライド更新→Recallが  │
   │  CreateSIPParticipant→room→発信  │    │   会議へstream)                        │
   │        ▼                        │    └──────────────────────────────────────┘
   │ 📞 Dais と S2S でリアルタイム会話  │              ↑ Calendar監視が開始時刻にRecall bot起動
   └────────────────────────────────┘
        ▲ 全体を回す: proactive-loop(*/5) + task-master(WHAT) + Calendar(WHEN) + presenter-mode
```

---

## 4. 我々が書くもの / 使うもの（境界）

| 我々が書く（薄いロジック） | 使う（自作しない） |
|--------------------------|-------------------|
| 発信判断（Calendar+位置→call/mail） | LiveKit AgentSession（音声全部） |
| 起こし/遅刻/会議ペルソナ（system prompt 文字列） | LiveKit telephony（発信） |
| reveal.js スライド生成 | Recall Output Media（会議注入） |
| Calendar→task-master→presenter-mode のループ配線 | HeyGen Live Avatar（顔） |
| inline tools の中身（時刻/終話/メール送信） | claude-task-master / proactive-loop |

---

## 5. 要件①フロー（起こす/遅刻防止）

| 入力 | ソース |
|------|--------|
| 次予定・出発必要時刻 | Google Calendar（移動時間込み） |
| live 位置 | loco（OwnTracks, tailnet 100.99.82.95:8788） |

| 状況 | 判定（fail-closed） |
|------|------|
| 目的地方向へ移動中 & 到着間に合う | 何もしない |
| 出発時刻前 & 未移動 / 遅れそう | LiveKit で電話 |
| 遅刻確定 or 不在 | 関係者にメール（gog） |
| 位置取得不能 / 判定不能 | **fail-closed = 電話**（memory feedback_safety_gates_must_fail_closed） |

電話会話: LiveKit AgentSession（S2S）で起こしペルソナ。inline tools=`get_current_time`/`end_call`。

---

## 6. 要件②フロー（会議プレゼン）

1. Calendar 監視が会議開始の数分前に Recall **Create Bot API**（`output_media` 設定）で bot を会議へ参加させる。
2. bot は我々の**制御webページ**（reveal.js スライド + HeyGen Live Avatar）を screenshare/camera として会議に stream。
3. Recall が会議音声を webページへ realtime 送信 → LiveKit Agent（頭脳/声）が処理 → webページで発話・スライド送り → Recall が会議へ stream。
4. presenter-mode.sentinel ON（proactive-loop が発表中は割り込まない）。
5. 終了 → 議事録を results/ → task 完了。

---

## 7. データフロー

| 経路 | 流れ |
|------|------|
| 電話 in/out | 電話網 ⇄ LiveKit SIP(trunk) ⇄ room ⇄ AgentSession(S2S) |
| 会議 in | Meet 音声 → Recall → 制御webページ(realtime data) → LiveKit Agent |
| 会議 out | LiveKit Agent 発話/スライド → 制御webページ → Recall → Meet(screenshare/camera) |

---

## 8. テスト（GATE2 TDD + GATE3 E2E判定）

### 単体（変更部分のみ・CLAUDE.md 0.6）
| 対象 | テスト |
|------|--------|
| 発信判断 | 「移動中&間に合う→何もしない」「未移動→call」「遅刻/不在→mail」「位置不能→call(fail-closed)」 |
| inline tools | get_current_time=JST / end_call=切断 / send_mail=gog呼ぶ |

### E2E（必須・dry-run 禁止）
| 要件 | 合格条件 |
|------|---------|
| ① 電話 | Anicca が実際に Dais に LiveKit 発信→双方向・割り込み・1.5秒以内応答・自然・ツール発火を録音検証 |
| ① メール | 遅刻シナリオで関係者宛に実メール（テスト宛先）が出る |
| ② 会議 | テスト Google Meet に Recall bot 実参加→顔表示+スライド共有+発話を確認 |

`superpowers:verification-before-completion` の 5 step gate を通すまで完了宣言禁止。

---

## 9. Phase 分割（各 Phase 独立 plan→実装→E2E）

| Phase | 内容 | task |
|-------|------|------|
| P0 | 本spec + 自作bridge削除（LiveKit稼働後） | #17, #18 |
| P1 | LiveKit 起こし電話（自前番号・実発信E2E）+ 発信判断 | #19, #20 |
| P2 | Recall 会議参加・喋る・画面共有 + アバター + Calendar自動参加 | #10, #12, #7 |
| P3 | 自画面LT/コメディ + 自律スライド生成 + 本番デプロイ | #11, #13, #9 |
| P5 | task-master 導入 + 自律オーケストレーション | #16, #15 |

---

## 10. 削除するもの（自作の醜い転送層）

| 削除 | 置換 |
|------|------|
| `~/.openclaw/workspace/imokenet/{server,geminiBridge,audio}.js` | LiveKit Agents |
| `anicca-products-oss/apps/alarm-backend/bridge/*` | LiveKit telephony |
| anicca-oss worktree `feature/bodhi-wakeup` + bodhi plan/spec | 本spec |
| 自作 VAD/再サンプリング/割り込み | LiveKit 内蔵 |

> 削除は **LiveKit 起こし電話が実通話で動いた後**（毎朝の起こしを止めないため）。

---

## 11. スコープ外（この spec では決めない）

| 項目 | 備考 |
|------|------|
| LiveKit Cloud vs 自己ホスト | plan で決定（OSS 自己ホスト優先） |
| S2S モデル選定（OpenAI Realtime vs Gemini Live） | plan で実測比較 |
| Recall 料金/従量の上限運用 | plan で確認 |

---

## 12. 受け入れ基準 (DoD)

1. 音声転送の自作コードゼロ（全て LiveKit/Recall）。
2. 要件① E2E: 実通話で滑らか・双方向・割り込み・ツール・メール分岐を検証。
3. 要件② E2E: 実 Google Meet で顔+画面共有+発話を検証。
4. `codex-review` ok:true。
5. 鍵/個人情報は owner の gitignore `.env` + `identity/profile.json` のみ。
6. 旧自作 bridge 群を削除済み（#18）。

---

## 13. proven 根拠（ソース）

| 主張 | ソース | 核心 |
|------|--------|------|
| LiveKit が本番標準・outbound電話 | github.com/livekit/agents | 「☎️ Outbound caller … MCP support」 |
| 自前電話番号(Twilio不要) | docs.livekit.io/telephony | 「LiveKit Phone Numbers for purchasing and managing」 |
| outbound = trunk + CreateSIPParticipant | docs.livekit.io/telephony/making-calls/outbound-calls | 「create a SIP participant using CreateSIPParticipant API to make a call」 |
| S2S ~500ms | hamming.ai/resources/best-voice-agent-stack | 「S2S drops to ~500ms」 |
| 会議注入=制御webページstream | docs.recall.ai/docs/stream-media | 「run a webpage you control → stream that page's audio and video into the meeting」 |
| 会議アバター proven | github.com/recallai/sample-apps/.../bot_output_media_heygen_avatar | HeyGen Live Avatar 公式サンプル |
| 安全ゲート fail-closed | memory feedback_safety_gates_must_fail_closed | 判定不能は危険側に倒さない |
| 一般化(12-factor) | memory feedback_build_anicca_oss_general_12factor | code=anicca-oss / 秘密=gitignore .env+profile |
