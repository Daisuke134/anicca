# PLAN — LM-5 v1: 遅刻検知 + 遅刻連絡メール自動化 (apps/life-call)

Task #6 / spec = docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-lop.md → 正: 2026-07-17-life-manager-cloud-alignment-and-dev-loop.md (§3 LM-5, §12 C7)
Branch: feature/lm5-late-notice (base origin/main c85cbea7a)。変更範囲は apps/life-call/** のみ。
Rules: no deploys, no secret access, no prod API calls, migrations は ADD COLUMN IF NOT EXISTS のみ。既存テストを弱めない。CommonJS 流儀を踏襲。

## 現状（実読済み事実 — まず自分でも読み直せ）
- lib/notify.js に sendLateNotice(uid, text, opts) が既存（受動: ユーザーが「遅れる」と打った時のみ発火）。
- wave1 (LM-23) で TG callback_query 配線済み: lib/telegram.js parseUpdate kind="callback"、server.js:243 answerCallbackQuery。
- T-0「出た？」[出た/まだ] の送信は wake 側。lm_wake_log 現 schema = (id, uid, event_key, called_at)。
- test = `cd apps/life-call && npm test`（node --test 連結、現在 all green）。

## 不変条件（全部 MUST、これが spec）
1. **migration**: `migrations/2026-07-18-lm-wake-log-late-notice.sql` 新設。lm_wake_log に
   `answered_at timestamptz` / `notified_late_at timestamptz` を ADD COLUMN IF NOT EXISTS で追加。
2. **answered 記録**: call にユーザーが出た（既存の call 状態遷移/webhook のうち answered を示す箇所）で
   該当 lm_wake_log 行の answered_at を更新。
3. **「まだ」→ 自動遅刻連絡**: T-0「出た？」の callback data =「まだ」系受信で既存 sendLateNotice を
   そのイベント文脈で呼ぶ（text は「running late to <event summary>」相当を合成）。成功時 notified_late_at 記録。
4. **10min 無応答 fallback**: T-0 送信後 10 分以内に callback も message も無ければ scheduler tick から
   同フローを 1 回だけ発火。判定は DB の値のみ（送信時刻 + answered/notified の null 判定）。
   in-memory タイマー禁止（Railway 再起動で消える）。
5. **dedup**: 同一 (uid, event_key) で遅刻連絡は最大 1 回。判定 = notified_late_at IS NOT NULL。
   並行 tick でも二重送信しない（既存 wake claim の atomic update パターンを踏襲）。
6. **宛先不在時**: 外部宛先が見つからなければメール送信せず、TG に 1 通だけ通知して notified_late_at を
   記録（無限リトライ禁止）。クラッシュ禁止。
7. **GPS 使わない**（v1 設計）。位置情報コードを追加しない。
8. **テスト**: 判定ロジックを pure function に切り出し `lib/late-notice.test.js`（node --test、
   ネットワーク・DB 実接続なし、I/O は注入）。package.json の test チェーンに追加。既存テスト全 green 維持。
9. Stripe/課金・既存 wake/travel/ask の挙動を変えない。apps/life-call/** 以外を触らない。

## Done 条件（自己申告でなく実行結果を貼る）
- `cd apps/life-call && npm test` 全 green（新規含む）。
- 触った全 JS に `node --check` pass。
- `git diff --stat` が apps/life-call/** のみ。
- **commit するな**（Fable が独立検証後に commit する）。

## 連絡線（agmsg）
質問: `~/.agents/skills/agmsg/scripts/send.sh lm sol-codex fable-main '<質問>'`
受信: `~/.agents/skills/agmsg/scripts/inbox.sh lm sol-codex`
完了報告も同経路: 「DONE + 変更ファイル一覧 + npm test 結果末尾 20 行」。
