# /test-call の留守電 hangup（spec §3 row 2d）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/test-call` が留守電に当たった時に、wake 呼び出しと同じように Telnyx へ hangup を打ち、120秒の録音上限まで Gemini Live を喋らせない。

**Architecture:** 原因は `/test-call` が `client_state` を積まないこと。`amdDialOptions()` は `streamUrl` のクエリから `wakeUid`/`wakeEventKey` を読むが、`/test-call` の stream URL にはそれが無いので `client_state` が空になり、webhook が `decodeWakeClientState()` → `null` → `"no wake context"` で早期 return する。よって hangup 経路に到達しない。
直し方は **client_state に「種類」を持たせる**。wake 呼び出しは今までどおり `{wakeUid, wakeEventKey}`、test 呼び出しは `{testUid}`。webhook は種類で分岐し、**test は Supabase に何も書かず**（対応する `lm_wake_log` 行が存在しないため）、AMD が human 以外を返した時だけ hangup する。
★stream URL には手を触れない★ — あれは `signCtx([...])` で署名済みで、bridge 側が同じ順序の配列で検証している。新しいクエリ項目を足すと署名の意味が変わる。代わりに `placeCall({ to, streamUrl, clientState })` に任意項目を1つ足して透過させる。

**Tech Stack:** Node.js (CommonJS), `node:test` + `node:assert/strict`, Telnyx Call Control v2

---

## File Structure

| file | 役割 | 変更 |
|---|---|---|
| `apps/life-manager/lib/telnyx-webhook.js` | client_state の符号化・復号 + Telnyx 署名検証 | 変更（`encodeTestCallClientState` / `decodeCallClientState` を追加） |
| `apps/life-manager/lib/telnyx-webhook.test.js` | 上記の単体テスト | 新規 |
| `apps/life-manager/lib/dial.js` | Telnyx への発信・hangup | 変更（`placeCall` / `amdDialOptions` が `clientState` を受ける） |
| `apps/life-manager/lib/dial.test.js` | `amdDialOptions` の単体テスト | 新規 |
| `apps/life-manager/server.js` | HTTP 経路（`/test-call` と `/telnyx-events`） | 変更 |
| `apps/life-manager/test/testcall-amd-hangup.test.js` | webhook の test 分岐の contract テスト | 新規 |
| `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` | 正本 spec | 変更（row 2d を DONE + §5.2.1 に設計を追記） |

---

### Task 1: client_state が「種類」を持つ

**Files:**
- Modify: `apps/life-manager/lib/telnyx-webhook.js`
- Test: `apps/life-manager/lib/telnyx-webhook.test.js`（新規）

- [ ] **Step 1: 落ちるテストを書く**

```javascript
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  encodeWakeClientState, encodeTestCallClientState, decodeCallClientState, decodeWakeClientState,
} = require("./telnyx-webhook.js");

test("a wake client_state decodes as kind=wake", () => {
  const encoded = encodeWakeClientState({ wakeUid: "lm_abc", wakeEventKey: "lm_abc|2026-08-02T09:00:00+09:00|10" });
  assert.deepEqual(decodeCallClientState(encoded), {
    kind: "wake", wakeUid: "lm_abc", wakeEventKey: "lm_abc|2026-08-02T09:00:00+09:00|10",
  });
});

test("a test-call client_state decodes as kind=test", () => {
  const encoded = encodeTestCallClientState({ testUid: "lm_abc" });
  assert.deepEqual(decodeCallClientState(encoded), { kind: "test", testUid: "lm_abc" });
});

test("a test-call client_state is NOT mistaken for a wake row", () => {
  // 取り違えると存在しない lm_wake_log 行に amd_result を書きに行く（matched=0 のノイズ）。
  assert.equal(decodeWakeClientState(encodeTestCallClientState({ testUid: "lm_abc" })), null);
});

test("empty and unreadable client_state stay null", () => {
  assert.equal(decodeCallClientState(""), null);
  assert.equal(decodeCallClientState("not-base64-json"), null);
  assert.equal(decodeCallClientState(Buffer.from(JSON.stringify({ other: 1 }), "utf8").toString("base64")), null);
});

test("encodeTestCallClientState requires a uid", () => {
  assert.equal(encodeTestCallClientState({}), "");
  assert.equal(encodeTestCallClientState(), "");
});
```

- [ ] **Step 2: 落ちることを確認**

Run: `cd apps/life-manager && node --test lib/telnyx-webhook.test.js`
Expected: FAIL（`encodeTestCallClientState is not a function`）

- [ ] **Step 3: 最小実装**

`lib/telnyx-webhook.js` の `decodeWakeClientState` の直後に足す。`decodeWakeClientState` は既存の呼び出し元のために残す（挙動も変えない）。

```javascript
// spec §3 row 2d: /test-call にも client_state を持たせる。wake 呼び出しには対応する lm_wake_log 行が
// あるが test 呼び出しには無い。だから「種類」を持たせて、書き込み先の無い呼び出しに amd_result を
// 書きに行かせない。hangup（金）と記録（証拠）はここで初めて別々に扱える。
function encodeTestCallClientState({ testUid } = {}) {
  if (!testUid) return "";
  return Buffer.from(JSON.stringify({ testUid }), "utf8").toString("base64");
}

// 1つの復号器が両方を返す。server.js は種類で分岐するだけでよくなる。
function decodeCallClientState(value) {
  const wake = decodeWakeClientState(value);
  if (wake) return { kind: "wake", ...wake };
  if (!value) return null;
  try {
    const parsed = JSON.parse(Buffer.from(String(value), "base64").toString("utf8"));
    if (!parsed || typeof parsed.testUid !== "string" || !parsed.testUid) return null;
    return { kind: "test", testUid: parsed.testUid.slice(0, 100) };
  } catch {
    return null;
  }
}
```

`module.exports` に `encodeTestCallClientState` と `decodeCallClientState` を足す。

- [ ] **Step 4: 通ることを確認**

Run: `cd apps/life-manager && node --test lib/telnyx-webhook.test.js`
Expected: PASS（5 tests）

- [ ] **Step 5: commit**

```bash
git add apps/life-manager/lib/telnyx-webhook.js apps/life-manager/lib/telnyx-webhook.test.js
git commit -m "feat(life-manager): client_state carries the kind of call it belongs to"
```

---

### Task 2: 発信側が client_state を明示できる

**Files:**
- Modify: `apps/life-manager/lib/dial.js`
- Test: `apps/life-manager/lib/dial.test.js`（新規）

- [ ] **Step 1: 落ちるテストを書く**

```javascript
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { amdDialOptions } = require("./dial.js");
const { encodeTestCallClientState, decodeCallClientState } = require("./telnyx-webhook.js");

const WAKE_URL = "wss://life-call-production.up.railway.app/ws?summary=x&wakeUid=lm_abc&wakeEventKey=k1";
const TEST_URL = "wss://life-call-production.up.railway.app/ws?summary=x&wakeUid=&wakeEventKey=";

test("a wake stream url still derives its client_state from the url", () => {
  const opts = amdDialOptions(WAKE_URL, { LM_AMD: "on" });
  assert.deepEqual(decodeCallClientState(opts.client_state), { kind: "wake", wakeUid: "lm_abc", wakeEventKey: "k1" });
});

test("an explicit client_state wins over the url", () => {
  const clientState = encodeTestCallClientState({ testUid: "lm_abc" });
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "on" }, { clientState });
  assert.equal(opts.answering_machine_detection, "detect");
  assert.deepEqual(decodeCallClientState(opts.client_state), { kind: "test", testUid: "lm_abc" });
});

test("without either, AMD still runs but no client_state is sent", () => {
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "on" });
  assert.equal(opts.answering_machine_detection, "detect");
  assert.equal("client_state" in opts, false);
});

test("LM_AMD=off disables AMD even with an explicit client_state", () => {
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "off" }, { clientState: encodeTestCallClientState({ testUid: "lm_abc" }) });
  assert.deepEqual(opts, {});
});
```

- [ ] **Step 2: 落ちることを確認**

Run: `cd apps/life-manager && node --test lib/dial.test.js`
Expected: FAIL（「an explicit client_state wins over the url」が `client_state` undefined で落ちる）

- [ ] **Step 3: 最小実装**

`lib/dial.js`:

```javascript
function amdDialOptions(streamUrl, env = process.env, opts = {}) {
  if (!amdEnabled(env)) return {};
  const url = new URL(streamUrl);
  const wakeUid = url.searchParams.get("wakeUid") || "";
  const wakeEventKey = url.searchParams.get("wakeEventKey") || "";
  const webhookProtocol = url.protocol === "ws:" ? "http:" : "https:";
  // 明示された client_state が勝つ。stream URL は signCtx で署名済みなので、種類を運ぶために
  // クエリ項目を足すと署名の意味が変わる（bridge 側が同じ配列で検証している）。
  const clientState = opts.clientState || encodeWakeClientState({ wakeUid, wakeEventKey });
  return {
    answering_machine_detection: "detect",
    webhook_url: `${webhookProtocol}//${url.host}/telnyx-events`,
    webhook_url_method: "POST",
    ...(clientState ? { client_state: clientState } : {}),
  };
}

async function placeCall({ to, streamUrl, clientState }) {
  // …既存のまま…
  const dialBody = {
    ...telnyxDialBody({ connectionId: CONN, to, from: FROM, streamUrl }),
    ...amdDialOptions(streamUrl, process.env, { clientState }),
  };
  // …既存のまま…
}
```

- [ ] **Step 4: 通ることを確認**

Run: `cd apps/life-manager && node --test lib/dial.test.js test/scheduler.test.js`
Expected: PASS（dial 4 tests + scheduler の既存 test）

- [ ] **Step 5: commit**

```bash
git add apps/life-manager/lib/dial.js apps/life-manager/lib/dial.test.js
git commit -m "feat(life-manager): let a caller pass an explicit client_state to placeCall"
```

---

### Task 3: webhook が test 呼び出しの留守電を切る

**Files:**
- Modify: `apps/life-manager/server.js:288-333`（`/telnyx-events`）
- Modify: `apps/life-manager/lib/late-notice.js`（決定を1か所に置く）
- Test: `apps/life-manager/test/testcall-amd-hangup.test.js`（新規）

**設計の要点（守ること）:**
1. test 呼び出しは **Supabase に触らない**。対応する `lm_wake_log` 行が無いので、書けば毎回 `matched=0` のエラー行が出る。
2. hangup の条件は wake と**同一**にする — `human` は切らない、**空/欠落の result も切らない**（読めなかった payload は AMD の判定ではない。ここで切ると Telnyx の schema 変更ひとつで「全部の呼び出しが即切れる」に化ける）。`not_sure` は切る（spec §5.2.1 の実測比 human 3 / machine 17）。
3. 判定は `lib/late-notice.js` に置き、`applyAmdDetection` と共有する。server.js は transport（署名・復号・HTTP 応答）のみ。

- [ ] **Step 1: 落ちるテストを書く**

`test/testcall-amd-hangup.test.js`。既存の `test/telegram-slash-http-contract.test.js` と同じ流儀で、実 HTTP は使わず lib の関数を直接叩く。

```javascript
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { applyTestCallDetection } = require("../lib/late-notice.js");

function hangupSpy() {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, method: init && init.method });
    return { ok: true, status: 200, json: async () => ({}) };
  };
  return { calls, fetchImpl };
}

test("a machine on a test call is hung up on", async () => {
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "machine", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.result, "machine");
  assert.equal(out.hangup.ok, true);
  assert.equal(spy.calls.length, 1);
  assert.match(spy.calls[0].url, /\/calls\/v2%3Aabc\/actions\/hangup$/);
  assert.equal(spy.calls[0].method, "POST");
});

test("not_sure is hung up on too", async () => {
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "not_sure", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup.ok, true);
  assert.equal(spy.calls.length, 1);
});

test("a human is never hung up on", async () => {
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "human", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup, null);
  assert.equal(spy.calls.length, 0);
});

test("an unreadable result hangs up on nobody", async () => {
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup, null);
  assert.equal(spy.calls.length, 0);
});

test("a failed hangup is reported, never thrown", async () => {
  const fetchImpl = async () => ({ ok: false, status: 422, json: async () => ({ error: "gone" }) });
  const out = await applyTestCallDetection({
    result: "machine", callControlId: "v2:abc", fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup.ok, false);
  assert.match(out.hangup.error, /422/);
});
```

- [ ] **Step 2: 落ちることを確認**

Run: `cd apps/life-manager && node --test test/testcall-amd-hangup.test.js`
Expected: FAIL（`applyTestCallDetection is not a function`）

- [ ] **Step 3: 最小実装**

`lib/late-notice.js` に足す（`applyAmdDetection` の直後）。

```javascript
// spec §3 row 2d: /test-call には対応する lm_wake_log 行が無い。書ける記録が無いというだけで、
// 留守電に2分喋る金は wake 呼び出しと同額かかる。だから記録はせず hangup だけを、wake と
// 完全に同じ条件で行う（human は切らない・読めない result は誰も切らない・not_sure は切る）。
async function applyTestCallDetection(opts = {}) {
  const result = typeof opts.result === "string" ? opts.result.trim() : "";
  if (!result || shouldMarkAnswered({ amdEnabled: true, signal: "amd", result })) {
    return { result, hangup: null };
  }
  const hangup = await hangupCall(opts.callControlId, {
    fetchImpl: opts.fetchImpl, apiKey: opts.telnyxApiKey,
  });
  return { result, hangup };
}
```

`module.exports` に `applyTestCallDetection` を足す。

- [ ] **Step 4: 通ることを確認**

Run: `cd apps/life-manager && node --test test/testcall-amd-hangup.test.js lib/late-notice.test.js`
Expected: PASS（新規 5 tests + late-notice の既存 test 全部）

- [ ] **Step 5: commit**

```bash
git add apps/life-manager/lib/late-notice.js apps/life-manager/test/testcall-amd-hangup.test.js
git commit -m "feat(life-manager): hang up on a test call that reached voicemail"
```

---

### Task 4: 経路をつなぐ（server.js）

**Files:**
- Modify: `apps/life-manager/server.js:42`（require）, `:288-294`（webhook の分岐）, `:388`（`/test-call` の placeCall）

- [ ] **Step 1: `/test-call` が test 用 client_state を積む**

`server.js:388` 付近:

```javascript
        const streamUrl = buildStreamUrl(ev, urgency, lang, u.name);
        // spec §3 row 2d: この呼び出しにも「自分が誰か」を持たせる。これが無いと webhook が
        // "no wake context" で早期 return し、留守電を切る経路に一生到達しない。
        const result = await placeCall({
          to: phone, streamUrl, clientState: encodeTestCallClientState({ testUid: body.uid }),
        });
```

`server.js:42` の require を差し替える:

```javascript
const { decodeCallClientState, encodeTestCallClientState, verifyTelnyxSignature } = require("./lib/telnyx-webhook.js");
```

- [ ] **Step 2: webhook が種類で分岐する**

`server.js:288-294` を差し替える（以降の wake 経路のコードは触らない）:

```javascript
      const call = decodeCallClientState(payload.client_state);
      if (call && call.kind === "test") {
        // 書ける lm_wake_log 行が無い呼び出し。金だけは同じようにかかるので hangup はする。
        const detection = await applyTestCallDetection({
          result: payload.result, callControlId: payload.call_control_id,
        });
        if (detection.hangup && !detection.hangup.ok) {
          console.error(`[telnyx-events] test-call hangup FAILED (${detection.hangup.error}) uid=${call.testUid.slice(0, 12)} — still speaking to a machine`);
        } else if (detection.hangup) {
          console.log(`[telnyx-events] test-call hung up on a ${detection.result} uid=${call.testUid.slice(0, 12)}`);
        } else {
          console.log(`[telnyx-events] test-call result=${detection.result || "missing"} uid=${call.testUid.slice(0, 12)}; left running`);
        }
        res.writeHead(200); res.end(detection.hangup ? "test hangup" : "test noop"); return;
      }
      const wake = call && call.kind === "wake" ? call : null;
      if (!wake) {
        // Not one of our calls, or a client_state we cannot decode. Either way nothing correlates, and
        // saying so out loud beats writing amd_result onto no row at all.
        console.log(`[telnyx-events] AMD result=${payload.result || "missing"}; no wake context`);
        res.writeHead(200); res.end("no wake context"); return;
      }
```

`applyTestCallDetection` を `server.js:60` 付近の `late-notice.js` の require に足す。

- [ ] **Step 3: 構文と全 suite**

Run: `cd apps/life-manager && node --check server.js && node --test lib/*.test.js test/*.test.js`
Expected: `node --check` 無出力、`node --test` は `fail 0`。★既知の baseline★ = `lib/panel-corrective-red.test.js` の1件は本変更と無関係に落ちる（spec 文書の文字列 assertion）。落ちた場合は `git stash` して同じ1件が落ちることを確認し、その事実を報告に書く。

- [ ] **Step 4: commit**

```bash
git add apps/life-manager/server.js
git commit -m "fix(life-manager): route test calls through the voicemail hangup path"
```

---

### Task 5: spec を最新にする

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md`

- [ ] **Step 1: §3 の row 2d を DONE にする**

`| **2d** |` の行の作業欄を `~~/test-call も留守電に当たったら切る~~ ✅ **コード DONE 2026-08-02 / 実架電の receipt は別途**` に変え、done 欄に **実際に走らせたテスト数と、どう決めたか**を書く（他の DONE 行と同じ密度で。「実装した」だけの行は書かない）。

- [ ] **Step 2: §5.2.1 に設計を1段落足す**

なぜ stream URL に項目を足さず client_state に種類を持たせたか（署名済み URL / bridge の検証配列）、なぜ test は Supabase に書かないか（行が存在しない）、なぜ hangup 条件を wake と同一にしたか（空 result で切ると schema 変更が全断に化ける）。

- [ ] **Step 3: commit**

```bash
git add docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md
git commit -m "docs(life-manager): record the 2d test-call hangup design and result"
```

---

## 完了の条件（この plan の done）

| 段 | receipt |
|---|---|
| コード | `node --test lib/*.test.js test/*.test.js` が `fail 0`（既知 baseline の1件を除く。除外するなら stash で同じ1件が落ちることを示す） |
| 経路 | `/test-call` の dial body に `client_state` が入り、それが `decodeCallClientState` で `kind:"test"` に戻る（Task 2 のテストが pin 済） |
| 本番 | ★別途★ deploy 後に実 `/test-call` を留守電へ当て、通話秒数が2分でなく数秒であることを Telnyx 側で実測する（この plan の範囲外・spec の receipt 欄に書く） |
