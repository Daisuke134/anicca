# webhook の PATCH 失敗で再送の権利を捨てない（spec §3 row 2a）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supabase への `lm_wake_log` PATCH が失敗した時、`/telnyx-events` が Telnyx へ 2xx を返すのをやめる。Telnyx が同じ event を再送し、その時に Supabase が生きていれば行が埋まる。

**Architecture:** 今の handler は結果に関わらず `res.writeHead(200)` で終わる。`outcome` が `"record failed"` という文字列になるだけで、Telnyx には「受け取った」と答えている。Telnyx の再送は**こちらが 2xx を返さなかった時にしか起きない**ので、これは再送の権利を自分から捨てている。
分けるべきは **一時的な失敗**（Supabase が落ちている・HTTP 5xx・fetch が throw）と **恒久的な失敗**（対応する行が存在しない = `matched === 0`）。前者だけ 5xx を返す。後者で 5xx を返すと、絶対に埋まらない行のために 6回の配送を焼き、失敗の見え方も濁る。

**裏取り（Telnyx 公式 docs、2026-08-02 実取得）:**

| 事実 | 引用 | 出典 |
|---|---|---|
| 2xx 以外は「受け取っていない」扱い = 再送/failover の対象 | "Your endpoint must return a `2xx` HTTP status code to indicate successful receipt... All response codes outside this range, including `3xx` codes, will indicate to Telnyx that you did not receive the webhook." | https://developers.telnyx.com/development/api-fundamentals/webhooks/receiving-webhooks |
| Voice 側も同じ | "If that URL does not resolve, or your application returns a non 200 OK response, the webhook will be delivered to the failover URL" | https://developers.telnyx.com/docs/voice/programmable-voice/receiving-webhooks |
| 再送は指数バックオフ。primary 3回 + failover 3回 = 最大6回（この数字は Messaging の retry policy 表に明記。Voice は同じ primary→failover 機構を数字なしで記載） | "Up to **3 attempts** per URL with exponential backoff... **Total attempts**: Up to 6 total (3 primary + 3 failover)." | https://developers.telnyx.com/docs/messaging/messages/receiving-webhooks |
| ★応答は 2秒以内★（Call Control は connection 設定 `webhook_timeout_secs` 0–30 で上書き可） | "Webhooks will be retried to each of the supplied URLs if your application does not respond in **2000 milliseconds**." | https://developers.telnyx.com/development/api-fundamentals/webhooks/receiving-webhooks |
| 再送は同一 payload（`client_state` も `data.id` も同じ）。変わるのは `meta.attempt` | "`attempt` \| `meta` \| Delivery attempt number (increments on retries)" / "Track processed event IDs (`data.id`) and skip duplicates" | https://developers.telnyx.com/docs/voice/programmable-voice/voice-api-webhooks |

再送が同一 payload である以上、再処理は安全でなければならない。実際そうなっている: `recordAmdResult` は filter 無し（最終観測が勝つ）、`markAnswered` は `answered_at=is.null` のラッチ（最初の human が勝つ）。**この plan はその性質に依存しているので、テストで固定する。**

**Tech Stack:** Node.js (CommonJS), `node:test` + `node:assert/strict`, Telnyx Call Control v2

---

## File Structure

| file | 役割 | 変更 |
|---|---|---|
| `apps/life-manager/server.js` | `/telnyx-events` の応答コード | 変更（`:325-328` 付近） |
| `apps/life-manager/test/telnyx-events-retry-http-contract.test.js` | 実 HTTP + 実 Ed25519 署名で応答コードを固定 | 新規 |
| `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` | 正本 spec | 変更（row 2a を DONE + 再送仕様の引用を §1.3 か §5.2.1 に残す） |

---

### Task 1: 一時的な失敗だけが 5xx を返す

**Files:**
- Modify: `apps/life-manager/server.js`（`/telnyx-events` の末尾、`outcome` を組み立てている箇所）
- Test: `apps/life-manager/test/telnyx-events-retry-http-contract.test.js`（新規）

既存の `test/testcall-amd-hangup-http-contract.test.js` が同じことをやっている（`http.createServer` を差し替えて実 `server.js` を require し、実 Ed25519 鍵で署名した body を投げる）。**その file を読んで、同じ骨格で書くこと。** 署名・鍵・envelope の組み立てを自分で発明しない。

- [x] **Step 1: 落ちるテストを書く**

`test/telnyx-events-retry-http-contract.test.js`。4 ケース:

```javascript
// 1) Supabase PATCH が HTTP 500 を返す（= 一時的な失敗）
//    → 応答は 5xx。Telnyx が再送し、次の配送で行が埋まる余地を残す。
test("a failed amd_result write asks Telnyx to send it again", async () => {
  const res = await postSignedAmdEvent({
    clientState: wakeClientState,          // { wakeUid, wakeEventKey }
    result: "machine",
    supabase: () => ({ ok: false, status: 500, json: async () => ({}) }),
  });
  assert.equal(res.status >= 500 && res.status < 600, true, `expected 5xx, got ${res.status}`);
});

// 2) fetch そのものが throw する（= Supabase に届いてすらいない）
test("a thrown Supabase write also asks for a retry", async () => {
  const res = await postSignedAmdEvent({
    clientState: wakeClientState,
    result: "machine",
    supabase: () => { throw new Error("ECONNREFUSED"); },
  });
  assert.equal(res.status >= 500 && res.status < 600, true, `expected 5xx, got ${res.status}`);
});

// 3) PATCH は成功したが 0 行だった（= 恒久的。行が存在しない）
//    → 200。再送しても永久に埋まらないので、6回の配送を焼く意味がない。
test("a write that matched no row is NOT retried", async () => {
  const res = await postSignedAmdEvent({
    clientState: wakeClientState,
    result: "machine",
    supabase: () => ({ ok: true, status: 200, json: async () => [] }),
  });
  assert.equal(res.status, 200);
});

// 4) 正常系は今までどおり 200
test("a recorded detection still answers 200", async () => {
  const res = await postSignedAmdEvent({
    clientState: wakeClientState,
    result: "machine",
    supabase: () => ({ ok: true, status: 200, json: async () => [{ id: 1 }] }),
  });
  assert.equal(res.status, 200);
});

// 5) test call は書く先が無いので、hangup が失敗しても 200
//    （再送された頃には通話自体が終わっている。切り直す相手がいない）
test("a test call answers 200 even when the hangup fails", async () => {
  const res = await postSignedAmdEvent({
    clientState: testClientState,          // { testUid }
    result: "machine",
    telnyx: () => ({ ok: false, status: 422, json: async () => ({}) }),
  });
  assert.equal(res.status, 200);
});
```

`postSignedAmdEvent` は既存 contract test の helper と同じ作りにする。fake `global.fetch` は **未知の host / path で throw する**こと（既存 file と同じ）。そうしないと「Supabase に書いていない」が主張になってしまう。

- [x] **Step 2: 落ちることを確認**

Run: `cd apps/life-manager && node --test test/telnyx-events-retry-http-contract.test.js`
Expected: ケース1と2が FAIL（`expected 5xx, got 200`）。3・4・5 は PASS（現状の挙動）。

- [x] **Step 3: 最小実装**

`server.js` の `/telnyx-events`、`outcome` を組み立てている箇所を差し替える:

```javascript
      // spec §3 row 2a: Telnyx は 2xx を「届いた」と読む — 2xx 以外を返した時だけ再送する
      // (developers.telnyx.com/development/api-fundamentals/webhooks/receiving-webhooks:
      //  "All response codes outside this range... will indicate to Telnyx that you did not receive
      //  the webhook"。primary 3回 + failover 3回、指数バックオフ)。だから Supabase が落ちている
      // 間に 200 を返すのは、埋められたはずの行を自分から捨てる行為になる。
      //
      // 分けるのは「もう一度なら通るかもしれない失敗」と「何度やっても通らない失敗」:
      //   * PATCH が 5xx / throw = 一時的 → 5xx を返して再送させる。再送は同じ payload なので
      //     (meta.attempt だけが増える) 再処理は安全 — amd_result は filter 無しで最終観測が勝ち、
      //     answered_at は is.null のラッチなので二度書いても最初の human が残る。
      //   * matched === 0 = その uid+event_key の行が存在しない → 再送しても永久に埋まらない。
      //     200 で閉じる。ここで 5xx を返すと6回の配送を焼いた上、本物の障害と見分けがつかなくなる。
      if (!detection.amd.ok) {
        res.writeHead(503, { "content-type": "text/plain" });
        res.end("record failed; send it again");
        return;
      }
      const outcome = detection.answered
        ? (detection.answered.matched > 0 ? "answered" : "answered_at unchanged")
        : "recorded";
      res.writeHead(200); res.end(outcome);
```

`detection.answered` 側の PATCH 失敗も同じ扱いにするかは**しない**: `answered_at` の書き込みは `amd_result` が成功した後にしか走らず、その時点で行の存在は確認できている。ここで 5xx を返すと、成功した `amd_result` の write を再送のたびに繰り返すことになる。失敗は既存の `report()` が stderr に出す。

- [x] **Step 4: 通ることを確認**

Run: `cd apps/life-manager && node --test test/telnyx-events-retry-http-contract.test.js test/testcall-amd-hangup-http-contract.test.js test/testcall-amd-hangup.test.js lib/late-notice.test.js`
Expected: すべて PASS、`fail 0`

- [x] **Step 5: commit**

```bash
git add apps/life-manager/server.js apps/life-manager/test/telnyx-events-retry-http-contract.test.js
git commit -m "fix(life-manager): let Telnyx resend a detection we failed to record"
```

---

### Task 2: 再送が安全であることをテストで固定する

**Files:**
- Test: `apps/life-manager/test/telnyx-events-retry-http-contract.test.js`（追記）

再送は同一 payload で来る。この plan は「再処理しても壊れない」に依存しているので、依存を明文化する。

- [x] **Step 1: 落ちるテストを書く**

```javascript
// 同じ event が2回届いた時（= Telnyx の再送そのもの）に何が起きるか。
// 1回目: Supabase が落ちていて 5xx を返す。2回目: 回復していて 200 と、amd_result の PATCH が
// 1回。answered_at のラッチは human の時だけ動き、二度目の human でも上書きされない。
test("the same event delivered twice records once and never rewrites answered_at", async () => {
  const patches = [];
  const supabase = (url, init) => {
    patches.push({ url, body: JSON.parse(init.body) });
    if (patches.length === 1) return { ok: false, status: 500, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => [{ id: 1 }] };
  };
  const first = await postSignedAmdEvent({ clientState: wakeClientState, result: "human", supabase });
  const second = await postSignedAmdEvent({ clientState: wakeClientState, result: "human", supabase });

  assert.equal(first.status >= 500, true);
  assert.equal(second.status, 200);
  // 2回目の配送で amd_result と answered_at の2本が出る。answered_at 側は必ず
  // answered_at=is.null の filter 付き（= 最初の human が勝つラッチ）であること。
  const answeredPatch = patches.find((p) => "answered_at" in p.body);
  assert.match(answeredPatch.url, /answered_at=is\.null/);
});
```

- [x] **Step 2: 落ちるか確認**

Run: `cd apps/life-manager && node --test test/telnyx-events-retry-http-contract.test.js`
Expected: このテストは既存実装で **通る可能性が高い**（ラッチは既にある）。通った場合は「characterization test = 番人」だと明記し、`markAnswered` から `filter: "&answered_at=is.null"` を一時的に外して**赤くなることを実測**してから戻す。赤くならないなら、その assertion は無意味なので書き直すこと。

- [x] **Step 3: commit**

```bash
git add apps/life-manager/test/telnyx-events-retry-http-contract.test.js
git commit -m "test(life-manager): pin that a resent detection is safe to process twice"
```

---

### Task 3: spec を最新にする

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md`

- [x] **Step 1: §3 の row 2a を DONE にする**

隣の DONE 行と同じ密度で。実装内容 + 一時的/恒久的をどう分けたか + 実際に走らせたテスト数。

- [x] **Step 2: Telnyx の再送仕様を spec 本文に残す**

§1.3（沈黙する全断のクラス）か §5.2.1 に、上の引用表をそのまま置く（URL 付き）。**特に「2秒で timeout」は次以降の作業に効く**: この handler は Supabase の PATCH を2本 + Telnyx の hangup を待ってから応答している。2秒を超えれば Telnyx は失敗扱いで再送する = 我々の応答コードに関係なく再送が起きうる。これは今回の変更で壊れるものではないが、spec に書いておかないと「なぜか毎回2回書かれている」の原因究明をまた1から始めることになる。

- [x] **Step 3: commit**

```bash
git add docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md
git commit -m "docs(life-manager): record the webhook retry contract and the 2a decision"
```

---

## 完了の条件（この plan の done）

| 段 | receipt |
|---|---|
| コード | 新規 contract test が全 PASS。Supabase 500 と throw で 5xx、matched=0 と正常系と test call で 200 |
| 非回帰 | `node --test lib/*.test.js test/*.test.js` の fail が既知 baseline の6件のみ（`event-participation-entities` / `panel-corrective-red` / `panel-corrective3-four-blockers` / `panel-corrective4-logout` / `panel-display-policy` / `browser-task-telegram-http-contract`）。増えていたら止めて報告 |
| 本番 | ★別途★ deploy 後、`SUPABASE_URL` を一時的に壊すような実験は**しない**（本番の書き込みを落とす）。代わりに deploy 後の `/health` build tag 更新を確認し、実 AMD event が 200 で処理され続けていることをログで見る |
