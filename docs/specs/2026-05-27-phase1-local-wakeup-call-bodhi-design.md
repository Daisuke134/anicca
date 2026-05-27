# Phase 1 SPEC — 起こし電話を bodhi VoiceSession 化（滑らか・ツール・位置認識）

作成: 2026-05-27 / 状態: GATE1 (SPEC) / 親プロジェクト: Anicca 自律会話エージェント

> 全要件は MUST（CLAUDE.md 0.7）。proven な実装のコピーのみ・オリジナル禁止（HARD RULE #1: 車輪の再発明は罪）。

---

## リポジトリ配置原則（重要）

| 層 | repo | この spec での役割 |
|----|------|------------------|
| **能力(capability)＝真実** | **`anicca-oss/skills/wake-me-up`** | bodhi bridge + scheduler を一般スキルとして収容。billions of Anicca が継承する本体 |
| 実行(runtime) | `~/.openclaw/workspace/imokenet`（gitなし・実行時） | 我々の Anicca がそのスキルを動かす実体 |
| 製品(product) | `anicca-products-oss/apps/alarm-backend`（Railway SaaS） | wake-me-up スキルの「他人向けデプロイ」 |
| コピー元 | `work/sutando-study/.../conversation-server.ts`（bodhi VoiceSession） | proven 実装 |

原則: **能力は1回だけ anicca-oss に作る。runtime と SaaS はそれを動かす/配るだけ。** 旧 `anicca`/`anicca-products`（漏洩・引退）には置かない。

---

## 0. 開発環境

| 項目 | 値 |
|------|-----|
| 作業方法 | `anicca-oss` 内 worktree `feature/bodhi-wakeup` |
| 起点ブランチ | `anicca-oss` の `main` |
| 真実のソース | `anicca-oss/skills/wake-me-up/`（bridge をここに収容） |
| 実行マシン | Mac mini（anicca-mac-mini-1, JST） |
| デプロイ | Phase 1 はローカル（~/.openclaw 経由で実通話）まで。SaaS 反映は Phase 2 |

### 触るファイル境界（これ以外は触らない）

| パス | 操作 |
|------|------|
| `anicca-oss/skills/wake-me-up/bridge/server.js`（新規） | Twilio WS 入口 → bodhi VoiceSession 配線 |
| `anicca-oss/skills/wake-me-up/bridge/audio.js`（新規） | mu-law⇄PCM 変換（sutando 実装移植） |
| `anicca-oss/skills/wake-me-up/bridge/tools/*.ts`（新規） | inline tools |
| `anicca-oss/skills/wake-me-up/bridge/package.json`（新規） | `bodhi-realtime-agent` 依存 |
| `anicca-oss/skills/wake-me-up/scripts/ensure-bridge.sh` | 新 bridge を起動するよう更新 |
| `anicca-oss/skills/wake-me-up/scripts/{wake_loop,alarm_scheduler}.py` | 位置認識発信ロジック強化 |
| `anicca-oss/skills/lateness-guard/scripts/lateness_check.py` | 位置認識（移動中なら鳴らさない）強化 |

> 旧 `~/.openclaw/imokenet` と `anicca-products-oss/apps/alarm-backend` の bridge は本スキルの bridge を参照するよう Phase 2 で切替（Phase 1 ではローカル実行で skill 内 bridge を直接起動して検証）。

---

## 1. 目的

Anicca が Mac mini からローカルに起こし電話をかけ、**自然・低遅延・双方向**で会話し、**会話中にツールを使え**、**移動中で間に合うなら鳴らさない**（位置認識）。E2E は実際に Dais に電話して録音で検証する。能力は `anicca-oss/skills/wake-me-up` に置き、誰の Anicca でも継承できる一般形にする。

---

## 2. 現状 (as-is) — 実コード根拠

`~/.openclaw/workspace/imokenet/geminiBridge.js` + `server.js` を実読して確認：

| 観点 | 現状 | 影響 |
|------|------|------|
| モデル | `gemini-2.5-flash-native-audio-latest` | 旧世代。sutando は `gemini-3.1-flash-live-preview` |
| ツール | `tools` 宣言ゼロ | 会話中に何もできない |
| VAD | `realtimeInputConfig` 無し（デフォルト） | 間が悪い・無言落ち・割り込み精度低 |
| 音声変換 | naive upsample/downsample（8↔16↔24k 手書き） | 音質劣化＝不自然 |
| 再接続 | なし | WS 切断で無言死 |
| 割り込み | `serverContent.interrupted` → Twilio `clear`（実装済み） | 維持する |
| 配置 | 能力が runtime(~/.openclaw)に直書き、anicca-oss に未収容 | billions が継承できない |

**結論**: 遅さ/不自然/無言落ちの真因はモデル旧・VAD未調整・手書き再サンプリング・ツール無し・再接続無し。全て sutando の bodhi `conversation-server.ts` で解決済み。さらに能力が runtime に埋もれている＝一般化の修正も必要。

---

## 3. 目標 (to-be)

| 観点 | 目標 |
|------|------|
| 配置 | bridge を `anicca-oss/skills/wake-me-up/bridge/` に収容（真実のソース） |
| エンジン | sutando `conversation-server.ts`（bodhi `VoiceSession`）移植 |
| モデル | native-audio `gemini-3.1-flash-live-preview` + 推論/ツール用テキストモデル |
| 音声 | sutando 実証済み mu-law 8k ⇄ PCM16k(in)/24k(out) |
| ツール | inline tools（プロセス内即時）を会話中に使用 |
| VAD/割り込み | bodhi のターン検出 + barge-in |
| 再接続 | bodhi の transport close 分類 + 再接続 |
| 発信判断 | 位置 + カレンダーで「移動中＆間に合う→鳴らさない」を fail-closed 判定 |
| 一般性 | 鍵/プロフィールは owner の gitignore `.env` + `identity/profile.json` から読む（ハードコード禁止） |

---

## 4. アーキテクチャ

```
[scheduler(Python, skills/wake-me-up)] 位置認識で発信判断
   gcal逆算 + loco live位置:
     ・出発時刻前 & 未移動            → 起こす/催促
     ・目的地方向へ移動中 & 間に合う   → 鳴らさない（buzzering防止）
     ・位置取得不能                   → fail-closed（鳴らす＝安全）
        │ 発信(REST) /twiml?name=&mode=&ctx=
        ▼
[Twilio] owner に発信 → TwiML <Connect><Stream> → /media-stream WS
        │
        ▼
[bridge (anicca-oss/skills/wake-me-up/bridge, Node)] ← sutando移植
   Twilio mulaw8k ─(audio.js)→ PCM16k → VoiceSession.handleAudioFromClient()
   Gemini Live(3.1-flash-live) ─ handleAudioOutput() ─(pcm24kToMulaw8k)→ Twilio
   inline tools: get_current_time / end_call
   barge-in: interrupted → Twilio clear ／ reconnect: close分類→再接続
   ペルソナ/鍵: owner の .env + profile.json から
        │
        ▼
[E2E] 実際に owner(Dais)に発信 → 録音fetch → 双方向/割り込み/ツール/自然さ検証
```

---

## 5. コンポーネント & 責務

| コンポーネント | 責務 | 依存 |
|---------------|------|------|
| `scripts/`（Python） | 位置認識で発信可否判定し Twilio 発信 | loco, gcal, Twilio |
| `bridge/server.js` | Twilio WS 受け口・VoiceSession ライフサイクル | bodhi-realtime-agent, audio.js |
| `bridge/audio.js` | mu-law 8k ⇄ PCM 16k/24k（sutando 移植） | なし |
| `bridge/tools/*.ts` | inline tools | bodhi `ToolDefinition` |
| ペルソナ | 起こし/催促 systemInstruction（owner profile を差し込む） | profile.json |

---

## 6. データフロー（音声チェーン・sutando 準拠）

| 方向 | 変換 | 根拠 |
|------|------|------|
| 受信 | Twilio mulaw8k → `mulawTopcm16k` → PCM16k → `handleAudioFromClient()` | conversation-server.ts:244-258 |
| 送信 | Gemini PCM24k → `handleAudioOutput()` override → `pcm24kToMulaw8k` → Twilio media | conversation-server.ts:827-844 |
| 割り込み | `interrupted` → Twilio `{event:'clear'}` | 既存実装を維持 |

---

## 7. inline tools 仕様（Phase 1 範囲）

| tool | 機能 | execution |
|------|------|-----------|
| `get_current_time` | 現在時刻（JST）を即時返す | inline |
| `end_call` | 起床確認後に通話終了（Twilio hangup） | inline |

> 会話スコープのみ。重い処理は Phase 5 の task-bridge に回す。

---

## 8. 位置認識発信ロジック（scheduler 強化）

| 入力 | ソース |
|------|--------|
| 次予定・出発必要時刻 | Google Calendar（移動時間込み） |
| live 位置 | loco（OwnTracks, tailnet 100.99.82.95:8788） |

| 状況 | 判定 |
|------|------|
| 出発時刻前 & 未移動（自宅圏内） | 起こす/催促する |
| 目的地方向へ移動中 & 到着見込み間に合う | 鳴らさない |
| 位置取得不能 / 判定不能 | **fail-closed＝鳴らす**（memory feedback_safety_gates_must_fail_closed） |

---

## 9. エラー処理・再接続

| 事象 | 挙動 |
|------|------|
| Gemini Live transport close（retryable） | bodhi 分類で再接続 |
| close（non-retryable） | ログ + 継続不能なら Twilio 切断 |
| GEMINI_API_KEY 不正 | 起動時 fail-fast（sutando `assertGeminiKey` 移植） |
| 音声フレーム破損 | 当該フレーム drop・通話継続 |

---

## 10. テスト（GATE2 TDD + GATE3 E2E判定）

### 単体（変更部分のみ・CLAUDE.md 0.6）

| 対象 | テスト |
|------|--------|
| `audio.js` 変換 | mulaw→pcm16k→mulaw 往復で既知波形が許容誤差内 |
| 発信判断 | 「移動中＆間に合う→false」「未移動→true」「位置不能→true」 |
| inline tools | `get_current_time` が JST、`end_call` が hangup 呼ぶ |

### E2E判定（このフェーズは E2E **必須**）

理由: 起こし電話は実通話でしか naturalness/遅延/割り込み/ツールを証明できない（HARD RULE #8/#11、dry-run 禁止）。

| 手順 | 合格条件 |
|------|---------|
| Anicca が実際に Dais に発信 | 着信し会話成立 |
| 双方向会話 | 発話に 1.5 秒以内応答・無言落ちなし |
| 割り込み | 話し被せで Anicca 即停止 |
| ツール | 「今何時?」で `get_current_time` 発火・正答 |
| 終了 | 起床確認後 `end_call` で切断 |
| 検証 | 録音を `fetch_recording.py` で取得→全部聞く→旧実装と比較 |

`superpowers:verification-before-completion` の 5 step gate を通すまで完了宣言禁止。

---

## 11. スコープ外（Phase 1 では作らない）

| 項目 | どの Phase |
|------|-----------|
| SaaS(products-oss/alarm-backend)反映 | Phase 2 |
| 会議への電話 dial-in（DTMF PIN） | Phase 2 |
| 通話中の位置取得 inline tool | Phase 2+ |
| reveal.js 発表・アバター・画面共有 | Phase 3-4 |
| heartbeat→taskmaster→presenter-mode | Phase 5 |

---

## 12. 受け入れ基準 (Definition of Done)

1. bridge を `anicca-oss/skills/wake-me-up/bridge/` に収容、`feature/bodhi-wakeup` worktree で実装。
2. 単体テスト緑（変更部分のみ）。
3. E2E: Anicca→Dais 実通話で双方向・割り込み・ツール・自然さを録音検証し、旧実装より明確に改善。
4. `codex-review` ok:true。
5. proven 根拠（§13）から逸脱したオリジナル実装ゼロ。
6. 鍵/個人情報は owner の gitignore .env + profile.json からのみ（リポに秘密ゼロ）。

---

## 13. proven 根拠（ソース）

| 主張 | ソース | 核心 |
|------|--------|------|
| bodhi VoiceSession が滑らか会話の実装 | `work/sutando-study/.../conversation-server.ts:81,759` | 「Twilio Media Streams + bodhi VoiceSession」 |
| 音声変換チェーン | 同 :244-258, :827-844 | mulaw8k⇄PCM16/24k |
| native-audio モデル | `work/sutando-study/src/voice-agent.ts:120` | `gemini-3.1-flash-live-preview` |
| inline tools = 即時 | 同 :677 / meeting-tools.ts | `execution:'inline'` |
| 安全ゲートは fail-closed | memory `feedback_safety_gates_must_fail_closed` | 判定不能は危険側に倒さない |
| 一般化(12-factor) | memory `feedback_build_anicca_oss_general_12factor` | code=anicca-oss / 秘密=gitignore .env+profile |
| bodhi-realtime-agent 実在 | `npm view bodhi-realtime-agent` | v0.2.1 realtime voice framework |
