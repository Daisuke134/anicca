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

---

# PLAN 追記 — LM-26: call の AI 発話を日本語にする（同 branch に積む）

実測事実: 2026-07-18 の C1v2 実録音（whisper 文字起こし）で AI が英語で発話した。ユーザーは日本の番号(+81)。
done 条件（goal 正本）: 「AI が日本語で発話」。

## 不変条件（MUST）
1. まず現状配線を実読: scheduler.js の langForPhone → buildStreamUrl → server.js /ws ctx → Gemini system prompt のどこで言語が落ちているかを特定し、PLAN 末尾に1行で記録する（推測禁止、grep/Read で）。
2. +81 ユーザーの wake call は **挨拶から日本語**。Gemini への system instruction に「lang=ja なら日本語のみで話す」を明示注入。
3. ユーザーが通話中に他言語で話しかけたら追従してよい（barge-in 会話の自然さを壊さない）。
4. lang 決定ロジックは pure function 化し node --test を追加（+81→ja、+1→en、不明→en）。既存テスト全 green 維持。
5. 変更は apps/life-call/** のみ。commit するな。完了は agmsg で DONE 報告（変更ファイル + npm test 末尾）。

原因特定: `langForPhone(+81) → buildStreamUrl(lang=ja) → server.js /ws ctx(lang=ja) → Gemini systemInstruction` は保持されていたが、setup 完了後の開始 turn が常に英語の `Begin the call now with your opening line.` だったため、初回発話を英語へ誘導していた。

---

# PLAN 追記2 — LM-6: 最小質問 onboarding + context graph（branch feature/lm6-onboarding）

現状（実読済み）: lib/telegram-onboard.js = stage machine（name → calendar → phone → pay → done、free-text 2問 = name/phone）。lib/places-memory.js 既存。Gmail stage は TG flow に無い（web の email loop は v1.5 表記）。

## 不変条件（MUST）
1. **blocking 質問 ≤1**: name は TG プロフィール（update の from.first_name/last_name）から自動取得し typed 質問から外す。typed 質問は phone の 1 個だけ。calendar/pay はタップのみ。
2. **Gmail stage（skippable）**: pay と done の間に「Gmail 接続 [接続する][スキップ]」を追加。スキップ = DB に gmail_skipped=true（additive migration 可）を記録し、Gmail 非依存機能は全部動く。接続パスは既存コード（transport/mail-unipile.js / web /lm onboarding）を実読し、既存の実接続手段があればそれに配線、無ければ /lm ページへの deep link を送る（偽の「接続しました」を絶対に出さない）。
3. **context graph**: calendar 接続完了時に直近 60 日のイベントから **≥5 fields** を推論して places-memory（既存 storage 流儀に従う）へ書く: home エリア / work 場所 / 頻出会場 top2 / 典型的な朝の開始時刻など。推論は既存の Gemini 呼び出しヘルパを使う（regex ハードコード禁止）。呼べない環境ではスキップしてログ（クラッシュ禁止）。
4. O3 維持: 途中離脱 → 再 /start で同じ stage から再開（既存挙動を壊さない）。
5. テスト: stage 遷移と name 自動取得を pure function で node --test。既存テスト全 green。ネットワーク/DB 実接続なし。
6. 変更は apps/life-call/** のみ。migration は ADD COLUMN IF NOT EXISTS のみ。commit するな。
7. 完了報告 agmsg: DONE + 変更ファイル + npm test 末尾 20 行。設計で迷ったら送信して待つのではなく、両案のうち「既存コードの流儀に近い方」を選んで PLAN 末尾に選択理由 1 行を記録して進め。

---

# PLAN 追記3 — LM-7: api-cost / outcome ledger（branch feature/lm6-onboarding に積む）

spec §3 LM-7 + §13。目的: 「このユーザーにいくら掛かってるか」を実 row で永続化。

## 不変条件（MUST）
1. migration `2026-07-18-lm-api-cost.sql`: `CREATE TABLE IF NOT EXISTS lm_api_cost (id bigint generated always as identity primary key, ts timestamptz default now(), uid text, kind text, quantity numeric, unit text, est_usd numeric, meta jsonb)`。additive のみ（既存 table への破壊的変更禁止）。
2. lib/ledger.js: `recordCost({uid,kind,quantity,unit,estUsd,meta})` — Supabase REST insert、失敗してもクラッシュせずログのみ。
3. 記録ポイント（最低3つ）: ①call 終了時（bridge close: kind=telnyx_call、quantity=秒、est_usd=quantity/60*0.002 — spec §13 実測値）②Gemini セッション終了時（kind=gemini_live、quantity=秒、est_usd=概算式をコメントに根拠付きで）③scheduler tick の calendar polling（kind=composio_poll、tick ごとでなく 1 日 1 row に集約: 判定は DB の当日 row 有無、in-memory カウンタ禁止）。
4. `businessSummary(daysBack)` pure function: rows → {calls, call_minutes, est_cost_usd, per_uid breakdown} json。node --test でテスト（I/O 注入）。
5. 既存テスト全 green、変更は apps/life-call/** のみ、commit 禁止、完了は agmsg DONE 報告。

---

# PLAN 追記4 — LM-25(part A): calendar event cache（branch feature/lm25-event-cache）

背景（spec §13 実測）: wake tick は 60s ごと。全 life-logic（events.js/ask.js/context-graph.js/late-notice.js/notify.js）が `getCalendar().listEventsRaw()` を叩く = Composio polling 46,800 call/月/user、キャッシュ皆無。これがコスト危機の本丸。
このタスクは **Composio のまま polling 回数を落とす cache 層**だけ（Unipile 置換=U17 検証は別タスク、ここでは触らない）。

## 不変条件（MUST）
1. 新 `lib/calendar-cache.js`: `makeCachedCalendar(inner, opts)` が inner（getCalendar の戻り）をラップし、`listEventsRaw(uid, {timeMin,timeMax,maxResults})` の結果を **TTL 付き in-memory cache** でメモ化する。cache key = `uid|timeMin丸め|timeMax丸め`（timeMin/timeMax は分単位に丸めて近接 tick を同一キーに寄せる）。TTL 既定 = 5分（env `LM_CAL_CACHE_TTL_MS` で上書き可）。
2. `createEvent`/`patchEvent` は inner にそのまま委譲し、**その uid の cache 全エントリを invalidate**（書込後に古い読みを返さない）。
3. cache は純粋なラッパ（inner の挙動を変えない）。inner が [] を返したら [] を返す。now は opts.now 注入可（テスト用）。TTL 切れは再 fetch。
4. transport/index.js の `getCalendar()` が既定でこの cache でラップした calendar を返すよう配線（env `LM_CAL_CACHE=off` で無効化して素の inner を返す退避口を用意）。既存の getCalendar 利用側は無改修で cache が効くこと。
5. Railway 再起動で cache が消えても**正しさは不変**（次 tick で再 fetch されるだけ）。プロセス跨ぎ永続は不要（コメントでそう明記）。
6. テスト `lib/calendar-cache.test.js`（node --test）: ①同一 window 2連続 read で inner 呼び出し 1回 ②TTL 経過後は再 fetch ③createEvent 後は同 uid の次 read が inner を再度呼ぶ（invalidate）④uid 違いは別キー。inner は call カウンタ付き fake を注入。
7. 既存テスト全 green、変更は apps/life-call/** のみ、migration 無し、commit 禁止、完了は agmsg DONE 報告。
