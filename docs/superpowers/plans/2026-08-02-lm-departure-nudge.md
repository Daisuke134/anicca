# 出発の押し切りを Telegram 連投にする（spec §3 row 2c / §5.2.1 / §5.2.2）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 出発時刻に対して T-25 / T-10 / T-5 / T-0 / T+3 / T+7 の6段を Telegram に送り、`[了解]` を押した・電話に出た・late organ に移行した のいずれかで即座に止まる。電話番号を出していない人にも全段が届く。

**Architecture:** 段の判定は wake tick が持つ（spec §5.2.2 D1）。新テーブル `lm_departure_nudge` は **1予定1行**で、`last_level_min` が単調減少する。送るかどうかの判断は **PATCH 1回**に融合する — `acked_at=is.null` かつ `last_level_min=gt.<level>` の行だけを更新し、更新できた時だけ送る（D4）。読んでから書くと 60秒 tick が重なった瞬間に二重送信になる。

**Tech Stack:** Node.js (CommonJS), Supabase PostgREST, Telegram Bot API, `node:test` + `node:assert/strict`

**先に読む file（この順）:**
1. `apps/life-manager/scheduler.js` — `WAKE_LEVELS`(60-63) / `LATE_CUTOFF_MIN`(67) / `claimWake`(105-129) / `wakeCallOnce` の due ループ(429-510)
2. `apps/life-manager/lib/wake-filter.js` — `resolveDeparture`
3. `apps/life-manager/lib/telegram.js` — `sendMessage` / `parseUpdate` / `routeCallbackData`
4. `apps/life-manager/lib/ask.js` — `closedAskMessage`(109-117) と `handleAskCallback`(544-592) = ボタンの既存の型
5. `apps/life-manager/lib/telegram-callback-visibility.js` — `reflectAnswer`
6. `apps/life-manager/lib/wake-miss.js` + `migrations/2026-08-01-lm-wake-miss.sql` = **新しい台帳と migration の書き方の見本。これに一番近い形で書く**

---

## File Structure

| file | 役割 | 変更 |
|---|---|---|
| `apps/life-manager/migrations/2026-08-02-lm-departure-nudge.sql` | 台帳の DDL | 新規 |
| `apps/life-manager/lib/departure-nudge.js` | claim（送ってよいかの判断）+ ack + 文面 | 新規 |
| `apps/life-manager/lib/departure-nudge.test.js` | 上記の単体テスト | 新規 |
| `apps/life-manager/scheduler.js` | `NUDGE_LEVELS` と wake tick への配線 | 変更 |
| `apps/life-manager/test/departure-nudge-tick.test.js` | tick の段判定・停止条件 | 新規 |
| `apps/life-manager/server.js` | `depart:ack` callback の配線 | 変更 |
| `apps/life-manager/test/departure-nudge-http-contract.test.js` | 実 HTTP で callback → 停止 | 新規 |
| `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` | 正本 spec | 変更（row 2c を DONE） |

---

### Task 1: 台帳と claim

**Files:**
- Create: `apps/life-manager/migrations/2026-08-02-lm-departure-nudge.sql`
- Create: `apps/life-manager/lib/departure-nudge.js`
- Test: `apps/life-manager/lib/departure-nudge.test.js`

`migrations/2026-08-01-lm-wake-miss.sql` を読んで、同じ体裁（コメントの density・grant・index の付け方）で書くこと。

```sql
-- spec §5.2.2 D3: 出発の押し切りは1予定につき1行。段ごとの行にはしない。
-- last_level_min は単調減少（25 → 10 → 5 → 0 → -3 → -7）。この列が「どこまで送ったか」であり、
-- 同時に「次に送ってよいか」の判定子でもある（D4: claim と停止判定を1回の PATCH に融合する）。
create table if not exists lm_departure_nudge (
  uid              text not null,
  event_key        text not null,          -- '<uid>|<startIso>' — 段は含めない
  last_level_min   integer not null,
  acked_at         timestamptz,
  ack_reason       text,                   -- 'tap' | 'call_answered' | 'left_home'(#3 で使う)
  last_message_id  bigint,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  primary key (uid, event_key)
);
```

`lib/departure-nudge.js` が持つもの:

```javascript
// 段。出発時刻からの分（正 = 出発前、負 = 出発後）。spec §5.2.1 の梯子そのもの。
const NUDGE_LEVELS = [25, 10, 5, 0, -3, -7];

// 送ってよいかを1回の書き込みで決める。読んでから書くと 60秒 tick が重なった瞬間に二重送信になる。
// 更新できた（matched===1）= この段はまだ誰も送っておらず、かつ止まっていない、の両方が同時に真。
// 行が無い時は INSERT（初段）。unique 衝突（409）は「他の tick が同じ段を取った」なので送らない。
async function claimNudgeLevel(uid, eventKey, levelMin, opts) { /* → { ok, claimed, error } */ }

// 停止。理由を残す（'tap' / 'call_answered' / 'left_home'）。既に止まっていれば no-op。
async function ackNudge(uid, eventKey, reason, opts) { /* → { ok, matched, error } */ }
```

- [ ] **Step 1: 落ちるテストを書く**

fake fetch で PostgREST の応答を作る。最低限これを pin する:

1. 行が無い状態の初段 → INSERT が飛び、`claimed === true`
2. `last_level_min = 25` の行に対する `level 10` → PATCH の URL に `last_level_min=gt.10` **と** `acked_at=is.null` の両方が入り、1行返れば `claimed === true`
3. 同じ段（`level 25` に対する `level 25`）→ `gt` 条件で 0 行 → `claimed === false`、**送信は起きない**
4. `acked_at` が入っている行 → PATCH が 0 行 → `claimed === false`
5. INSERT が 409（他 tick が先に初段を取った）→ `claimed === false`、`ok === true`（これは障害ではない）
6. PATCH が HTTP 500 → `ok === false`。**この時 `claimed` は false**（書けたか不明な時に送るのは二重送信より悪い方に倒す）
7. `ackNudge` は `acked_at=is.null` のラッチ付きで、2回押しても最初の理由が残る

- [ ] **Step 2: 落ちることを確認**

Run: `cd apps/life-manager && node --test lib/departure-nudge.test.js`
Expected: FAIL（`claimNudgeLevel is not a function`）

- [ ] **Step 3: 実装**

`lib/wake-miss.js` の `noteWakeMiss` が同じ形（upsert + filter 付き PATCH + `{ok, matched, error}` の返し方）なので、**その関数を読んでから**同じ流儀で書く。`supaHeaders` の使い方も含めて既存に合わせる。

- [ ] **Step 4: 通ることを確認**

Run: `cd apps/life-manager && node --test lib/departure-nudge.test.js`
Expected: PASS（7 tests）

- [ ] **Step 5: 本番 Supabase に migration を適用**

`migrations/2026-08-01-lm-wake-miss.sql` を適用した時と同じ手順（spec §3 row 1b に `http=201` / 読み取り `http=200` と記録がある）。**適用した実 HTTP コードを報告に書くこと。** 鍵は stdout に出さない。

- [ ] **Step 6: commit**

```bash
git add apps/life-manager/migrations/2026-08-02-lm-departure-nudge.sql apps/life-manager/lib/departure-nudge.js apps/life-manager/lib/departure-nudge.test.js
git commit -m "feat(life-manager): a ledger that decides in one write whether a nudge may be sent"
```

---

### Task 2: 文面

**Files:**
- Modify: `apps/life-manager/lib/departure-nudge.js`
- Test: `apps/life-manager/lib/departure-nudge.test.js`（追記）

- [ ] **Step 1: 落ちるテストを書く**

```javascript
// 段ごとに文が変わり、T+7 以外には [了解] が付く（T+7 は梯子の終端 = spec §5.2.2 D6）。
// callback data は 'depart:ack:<startIso>' の形（D7。64 byte 上限があるので uid は載せない）。
test("each rung says something different and carries the acknowledge button", () => {
  const ev = { summary: "打合せ", startIso: "2026-08-02T09:00:00+09:00", location: "渋谷" };
  const at = (level) => buildNudgeMessage({ level, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });

  assert.match(at(25).text, /8:05/);
  assert.match(at(25).text, /25/);
  assert.notEqual(at(10).text, at(5).text);
  assert.match(at(0).text, /🚨/);
  assert.equal(
    at(0).extra.reply_markup.inline_keyboard[0][0].callback_data,
    "depart:ack:2026-08-02T09:00:00+09:00",
  );
  assert.equal(at(-7).extra, undefined);   // 終端に押すものは無い
});

test("english users get english", () => {
  const ev = { summary: "Standup", startIso: "2026-08-02T09:00:00+09:00", location: "Shibuya" };
  const m = buildNudgeMessage({ level: 0, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "en" });
  assert.match(m.text, /leave/i);
  assert.doesNotMatch(m.text, /[ぁ-んァ-ン一-龯]/);
});

test("the callback data stays inside Telegram's 64-byte limit", () => {
  const ev = { summary: "x".repeat(300), startIso: "2026-08-02T09:00:00+09:00", location: "y".repeat(300) };
  const m = buildNudgeMessage({ level: 25, ev, departureIso: "2026-08-02T08:05:00+09:00", lang: "ja" });
  const data = m.extra.reply_markup.inline_keyboard[0][0].callback_data;
  assert.equal(Buffer.byteLength(data, "utf8") <= 64, true, `callback_data is ${Buffer.byteLength(data, "utf8")} bytes`);
});
```

- [ ] **Step 2: 落ちる → 実装 → 通る**

Run: `cd apps/life-manager && node --test lib/departure-nudge.test.js`
文面は `lib/i18n.js` の既存の書き方（言語分岐の形・絵文字の使い方）に合わせる。時刻の整形も既存 helper があればそれを使い、新しく発明しない。

- [ ] **Step 3: commit**

```bash
git add apps/life-manager/lib/departure-nudge.js apps/life-manager/lib/departure-nudge.test.js
git commit -m "feat(life-manager): the six rungs of the departure ladder, in both languages"
```

---

### Task 3: wake tick に配線する

**Files:**
- Modify: `apps/life-manager/scheduler.js`
- Test: `apps/life-manager/test/departure-nudge-tick.test.js`（新規）

`test/wake-catchup.test.js` が同じ形の tick テストなので、**それを読んで同じ骨格で書く**。

- [ ] **Step 1: 落ちるテストを書く**

pin すること:

1. 出発 25分前の tick で T-25 が1通出る（電話番号なしの user でも出る = spec #6）
2. tick が遅れて T-10 と T-5 が同時に due → **出るのは T-5 の1通だけ**（段は単調・最も緊急なもの）
3. `acked_at` が入っている予定では**1通も出ない**
4. 同じ予定の `lm_wake_log` 行に `answered_at` が入っている（電話に出た）→ 以後1通も出ない（D5 ③）
5. 出発 +15分（`LATE_CUTOFF_MIN`）を越えたら T+7 も含めて**もう出ない**（late organ の領域）
6. `daily_automation_enabled === false` の user には出ない
7. Telegram の送信が失敗した時、claim が**戻る**（次 tick が再試行できる）— `claimWake` の dial 失敗時と同じ扱い
8. 電話の梯子（`WAKE_LEVELS` の T-10 / T-5 dial）が**この変更で1本も減らない/増えない**

- [ ] **Step 2: 落ちることを確認 → 実装 → 通る**

Run: `cd apps/life-manager && node --test test/departure-nudge-tick.test.js test/wake-catchup.test.js test/wake-levels.test.js test/wake-loop-isolation.test.js`
Expected: 最初は新 file が全滅、最後は全部 PASS

実装の注意（守ること）:
- `wakeCallOnce` の中、**dial と同じ due 計算（`resolveDeparture` の結果）を使い回す**。もう一度 `resolveDeparture` を呼ぶと Composio の呼び出しが増える（1d で潰した劣化の再来）
- 送信失敗時の claim 戻しは `releaseWake` と同じ思想で、**戻せなかった事自体をログに残す**
- 20秒予算（`WAKE_USER_TIMEOUT_MS`）を超えない。通知は1 tick 1通が上限

- [ ] **Step 3: commit**

```bash
git add apps/life-manager/scheduler.js apps/life-manager/test/departure-nudge-tick.test.js
git commit -m "feat(life-manager): push the departure ladder from the wake tick"
```

---

### Task 4: `[了解]` で止まる

**Files:**
- Modify: `apps/life-manager/lib/telegram.js`（`routeCallbackData` に `depart` を追加）
- Modify: `apps/life-manager/server.js`（handler を渡す）
- Modify: `apps/life-manager/lib/departure-nudge.js`（`handleDepartureCallback`）
- Test: `apps/life-manager/test/departure-nudge-http-contract.test.js`（新規）

`lib/ask.js:544-592` の `handleAskCallback` と `test/telegram-callback-http-contract.test.js` を読んで、同じ形にする。

- [ ] **Step 1: 落ちるテストを書く（実 HTTP）**

`test/telegram-callback-http-contract.test.js` の骨格を使う（Telegram の secret token header 付きで実 `server.js` に POST）。pin すること:

1. `depart:ack:<startIso>` を押すと `lm_departure_nudge` に `acked_at` と `ack_reason='tap'` が PATCH され、**押した本人の uid の行だけ**が対象になる
2. 応答は 200 で、`answerCallbackQuery` が呼ばれる（トースト）
3. 元メッセージが編集されてキーボードが剥がれる（`reflectAnswer` 経由）
4. 未知の prefix は今までどおり無視される（回帰）
5. 他人の chat から同じ `startIso` を押しても、その人自身の行しか触れない（**tenant isolation**。`test/tenant-isolation.test.js` の思想）

- [ ] **Step 2: 落ちる → 実装 → 通る**

Run: `cd apps/life-manager && node --test test/departure-nudge-http-contract.test.js test/telegram-callback-http-contract.test.js lib/ask-callback-visibility.test.js`

- [ ] **Step 3: commit**

```bash
git add apps/life-manager/lib/telegram.js apps/life-manager/server.js apps/life-manager/lib/departure-nudge.js apps/life-manager/test/departure-nudge-http-contract.test.js
git commit -m "feat(life-manager): one tap ends the ladder"
```

---

### Task 5: #3 のための差込口だけ作る（実装はしない）

**Files:**
- Modify: `apps/life-manager/lib/departure-nudge.js`

- [ ] **Step 1**

`ackNudge(uid, eventKey, "left_home", opts)` が既に受け付けることを1テストで pin し、**まだ誰も呼んでいない**ことをコメントで明示する（#3 が位置から出発を検知した時にここを呼ぶ）。呼び出し側は作らない。「無い停止条件を実装したことにしない」ため（spec §5.2.2 D5）。

- [ ] **Step 2: commit**

```bash
git add apps/life-manager/lib/departure-nudge.js apps/life-manager/lib/departure-nudge.test.js
git commit -m "test(life-manager): reserve the left-home stop for #3 without pretending it exists"
```

---

### Task 6: spec を最新にする

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md`

- [ ] **Step 1**

§3 row 2c を DONE 化。隣の DONE 行と同じ密度で: 実装の要点・停止条件が **3本（位置は #3 待ち）** であること・実際に走らせたテスト数（実数）・migration の実 HTTP コード・★未検証★ = 実予定1件での実配信は deploy 後。

- [ ] **Step 2: commit**

```bash
git add docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md
git commit -m "docs(life-manager): record what the departure ladder does and does not stop on"
```

---

## 完了の条件（この plan の done）

| 段 | receipt |
|---|---|
| コード | 新規3 file が全 PASS。tick テストの8ケース全部 |
| 非回帰 | `node --test lib/*.test.js test/*.test.js` の fail が既知 baseline のみ（`panel-corrective-red` / `panel-corrective3-four-blockers` / `panel-corrective4-logout` / `panel-display-policy` / `browser-task-telegram-http-contract` / `event-participation-entities`）。増えたら止めて報告 |
| 台帳 | 本番 Supabase に table が存在し、PostgREST から読める（実 HTTP コードを報告） |
| 本番 | ★deploy 後★ 実予定1件で T-25 から順に届き、`[了解]` で止まることを Telegram の実画面で確認（この plan の範囲外・#2c-receipt として登録する） |
