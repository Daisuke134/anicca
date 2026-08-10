"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const http = require("node:http");

const { renderCfoTelegram, callbackData, evidenceLabel, handleCfoTelegramCallback } = require("./cfo-telegram.js");

function completeSnapshot() {
  return {
    schemaVersion: 1,
    reportingDate: "2026-08-08",
    revision: 1,
    state: "complete",
    currency: "JPY",
    totals: {
      assetsMinor: 420000,
      liabilitiesMinor: 30000,
      netWorthMinor: 390000,
      changeMinor: 1200,
    },
    sources: [{
      sourceId: "moneytree_mufg",
      label: "三菱UFJ銀行",
      status: "fresh",
      asOf: "2026-08-08T06:02:00+09:00",
      amountMinor: 420000,
      verificationStatus: "provider_reported",
    }],
    excluded: [],
    repair: null,
    action: null,
  };
}

function partialSnapshot() {
  const snapshot = completeSnapshot();
  snapshot.state = "partial";
  snapshot.totals.netWorthMinor = null;
  snapshot.excluded = [{ label: "未接続のカード", reason: "残高を確認できません" }];
  return snapshot;
}

function recoveredSnapshot() {
  const snapshot = completeSnapshot();
  snapshot.state = "recovered";
  snapshot.repair = { sourceLabel: "Moneytree", freshReread: true, reconciled: true };
  return snapshot;
}

function actionRequiredSnapshot(kind = "reconsent") {
  const snapshot = completeSnapshot();
  snapshot.state = "action_required";
  snapshot.totals = {
    assetsMinor: null,
    liabilitiesMinor: null,
    netWorthMinor: null,
    changeMinor: null,
  };
  snapshot.sources[0].status = "unavailable";
  snapshot.sources[0].amountMinor = null;
  snapshot.sources[0].verificationStatus = "unavailable";
  snapshot.action = {
    kind,
    sourceLabel: "Moneytree",
    retryLabel: kind === "provider_outage" ? "30分後に自動再確認" : "接続後に自動再確認",
    nextRetryAt: "2026-08-08T06:30:00+09:00",
  };
  return snapshot;
}

function assertInvalid(input, reason) {
  assert.throws(
    () => renderCfoTelegram({ locale: "ja", view: "summary", snapshot: input }),
    new RegExp(`^Error: cfo_telegram_invalid:${reason}$`),
  );
}

test("complete Japanese summary answers amount, change, freshness, and action", () => {
  const result = renderCfoTelegram({ locale: "ja", view: "summary", snapshot: completeSnapshot() });
  assert.match(result.text, /今日のお金/);
  assert.match(result.text, /確認できた資産\s+¥420,000/);
  assert.match(result.text, /差し引き\s+¥390,000/);
  assert.match(result.text, /前回から\s+\+¥1,200/);
  assert.match(result.text, /三菱UFJ銀行/);
  assert.match(result.text, /今すること：ありません/);
});

test("partial and action-required never claim a complete net worth", () => {
  for (const snapshot of [partialSnapshot(), actionRequiredSnapshot()]) {
    const text = renderCfoTelegram({ locale: "ja", view: "summary", snapshot }).text;
    assert.doesNotMatch(text, /純資産/);
    assert.doesNotMatch(text, /¥0(?:\D|$)/);
    assert.match(text, /不明|合計に入れていません/);
  }
});

test("canonical action-required accepts reconsent and provider outage", () => {
  for (const kind of ["reconsent", "provider_outage"]) {
    assert.doesNotThrow(() => renderCfoTelegram({ locale: "ja", view: "summary", snapshot: actionRequiredSnapshot(kind) }));
  }
});

test("canonical action rejects unknown kind, missing or extra keys, and bad retry timestamp", () => {
  const unknownKind = actionRequiredSnapshot();
  unknownKind.action.kind = "unknown";
  assertInvalid(unknownKind, "invalid_action");

  const missingRetryAt = actionRequiredSnapshot();
  delete missingRetryAt.action.nextRetryAt;
  assertInvalid(missingRetryAt, "missing_key");

  const extraKey = actionRequiredSnapshot();
  extraKey.action.extra = true;
  assertInvalid(extraKey, "unknown_key");

  for (const nextRetryAt of ["", "not-a-timestamp", "2026-02-31T06:30:00+09:00", "2026-08-08T24:00:00+09:00", "2026-08-08T06:30:00+24:00"]) {
    const invalidTimestamp = actionRequiredSnapshot();
    invalidTimestamp.action.nextRetryAt = nextRetryAt;
    assertInvalid(invalidTimestamp, "invalid_action");
  }
});

test("recovered is impossible without fresh reread and reconciliation", () => {
  const snapshot = recoveredSnapshot();
  snapshot.repair.freshReread = false;
  assert.throws(
    () => renderCfoTelegram({ locale: "ja", view: "summary", snapshot }),
    /^Error: cfo_telegram_invalid:recovery_unproven$/,
  );
});

test("recovered summary states its repair without leaking diagnostics", () => {
  const text = renderCfoTelegram({ locale: "ja", view: "summary", snapshot: recoveredSnapshot() }).text;
  assert.match(text, /自動修復|再確認/);
  assert.doesNotMatch(text, /stack|error|debug|exception|Error|at /i);
});

test("English summary uses the same facts without technical language", () => {
  const text = renderCfoTelegram({ locale: "en", view: "summary", snapshot: completeSnapshot() }).text;
  assert.match(text, /Today.s money/);
  assert.match(text, /Confirmed assets\s+JPY 420,000/);
  assert.match(text, /Nothing right now/);
});

test("amount totals accept only safe integers or null", () => {
  for (const value of ["420000", Number.NaN, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
    const snapshot = completeSnapshot();
    snapshot.totals.assetsMinor = value;
    assertInvalid(snapshot, "invalid_amount");
  }
  for (const key of ["assetsMinor", "liabilitiesMinor", "netWorthMinor", "changeMinor"]) {
    const snapshot = completeSnapshot();
    snapshot.totals[key] = null;
    if (key === "netWorthMinor") snapshot.state = "partial";
    if (snapshot.state === "partial") snapshot.excluded = [{ label: "未接続のカード" }];
    if (key !== "netWorthMinor") assertInvalid(snapshot, "inconsistent_totals");
    else assert.doesNotThrow(() => renderCfoTelegram({ locale: "ja", view: "summary", snapshot }));
  }
});

test("reporting date, revision, enum fields, and sources are closed and strict", () => {
  for (const reportingDate of ["2026-8-08", "2026-08-08T00:00:00Z", "08/08/2026"]) {
    const snapshot = completeSnapshot();
    snapshot.reportingDate = reportingDate;
    assertInvalid(snapshot, "invalid_reporting_date");
  }
  for (const revision of [0, -1, 1.2, "1"]) {
    const snapshot = completeSnapshot();
    snapshot.revision = revision;
    assertInvalid(snapshot, "invalid_revision");
  }
  for (const field of ["locale", "view", "state", "currency"]) {
    const snapshot = completeSnapshot();
    if (field === "locale") assert.throws(() => renderCfoTelegram({ locale: "fr", view: "summary", snapshot }), /cfo_telegram_invalid:unsupported_locale/);
    if (field === "view") assert.throws(() => renderCfoTelegram({ locale: "ja", view: "unknown", snapshot }), /cfo_telegram_invalid:unsupported_view/);
    if (field === "state") { snapshot.state = "unknown"; assertInvalid(snapshot, "unsupported_state"); }
    if (field === "currency") { snapshot.currency = "USD"; assertInvalid(snapshot, "unsupported_currency"); }
  }
  const missingSources = completeSnapshot();
  missingSources.sources = [];
  assertInvalid(missingSources, "missing_sources");
});

test("freshness and state invariants fail closed", () => {
  for (const status of ["stale", "unavailable"]) {
    const snapshot = completeSnapshot();
    snapshot.sources[0].status = status;
    if (status === "unavailable") {
      snapshot.sources[0].amountMinor = null;
      snapshot.sources[0].verificationStatus = "unavailable";
    }
    assertInvalid(snapshot, "source_not_fresh");
  }
  const recovered = recoveredSnapshot();
  recovered.sources[0].status = "stale";
  assertInvalid(recovered, "source_not_fresh");

  const partialWithoutLabel = partialSnapshot();
  partialWithoutLabel.excluded = [];
  assertInvalid(partialWithoutLabel, "partial_excluded_required");
  const partialWithTotal = partialSnapshot();
  partialWithTotal.totals.netWorthMinor = 390000;
  assertInvalid(partialWithTotal, "partial_net_worth_forbidden");

  const actionWithoutAction = actionRequiredSnapshot();
  actionWithoutAction.action = null;
  assertInvalid(actionWithoutAction, "action_required_missing_action");
  const actionWithTotal = actionRequiredSnapshot();
  actionWithTotal.totals.netWorthMinor = 1;
  assertInvalid(actionWithTotal, "action_required_net_worth_forbidden");
});

test("interpolated source and repair labels are Telegram-HTML escaped", () => {
  const snapshot = completeSnapshot();
  snapshot.sources[0].label = "銀行 <普通預金> & 家計";
  const text = renderCfoTelegram({ locale: "ja", view: "summary", snapshot }).text;
  assert.match(text, /銀行 &lt;普通預金&gt; &amp; 家計/);
  assert.doesNotMatch(text, /銀行 <普通預金>/);
});

test("all drill-down callbacks are deterministic and at most 64 bytes", () => {
  for (const view of ["summary", "accounts", "accuracy", "why"]) {
    const result = renderCfoTelegram({ locale: "ja", view, snapshot: completeSnapshot() });
    for (const row of result.extra.reply_markup.inline_keyboard) {
      for (const button of row) {
        assert.ok(Buffer.byteLength(button.callback_data, "utf8") <= 64);
        assert.match(button.callback_data, /^cfo:(summary|accounts|accuracy|why):20260808:1$/);
      }
    }
  }
});

test("drill-downs explain accounts and evidence without private payload fields", () => {
  const snapshot = completeSnapshot();
  snapshot.sources[0].label = "三菱UFJ銀行 <普通預金>";
  snapshot.sources[0].accountNumber = "1234567";
  snapshot.rawPayload = { credential: "secret-value" };
  const outputs = ["summary", "accounts", "accuracy", "why"]
    .map((view) => renderCfoTelegram({ locale: "ja", view, snapshot }));
  const serialized = JSON.stringify(outputs);
  assert.doesNotMatch(serialized, /1234567|secret-value|rawPayload|credential/);
  assert.match(outputs[1].text, /&lt;普通預金&gt;/);
  assert.match(outputs[2].text, /実測/);
  assert.match(outputs[3].text, /資産.*負債/s);
  for (const view of ["accounts", "accuracy", "why"]) {
    assert.ok(outputs[["summary", "accounts", "accuracy", "why"].indexOf(view)]
      .extra.reply_markup.inline_keyboard.flat()
      .some((button) => button.callback_data === callbackData({ view: "summary", reportingDate: "2026-08-08", revision: 1 })));
  }
  for (const locale of ["ja", "en"]) {
    for (const [status, expected] of Object.entries({
      provider_billed: locale === "ja" ? "確定" : "Confirmed",
      provider_reported: locale === "ja" ? "実測" : "Measured",
      locally_estimated: locale === "ja" ? "推定" : "Estimated",
      unavailable: locale === "ja" ? "不明" : "Unknown",
    })) assert.equal(evidenceLabel(locale, status), expected);
    const unavailable = renderCfoTelegram({ locale, view: "accounts", snapshot: actionRequiredSnapshot() }).text;
    assert.match(unavailable, locale === "ja" ? /不明/ : /Unknown/);
  }
  assert.doesNotMatch(serialized, /stack|exception|JSON|payload|token/i);
});

test("fixed callback builder rejects invalid view, date, and revision", () => {
  assert.equal(callbackData({ view: "accounts", reportingDate: "2026-08-08", revision: 1 }), "cfo:accounts:20260808:1");
  for (const input of [
    { view: "connect", reportingDate: "2026-08-08", revision: 1 },
    { view: "accounts", reportingDate: "2026/08/08", revision: 1 },
    { view: "accounts", reportingDate: "2026-08-08", revision: 0 },
  ]) assert.throws(() => callbackData(input), /^Error: cfo_telegram_invalid:/);
});

test("action-required why names unavailable sources among excluded items", () => {
  const snapshot = actionRequiredSnapshot();
  snapshot.sources[0].label = "三菱UFJ銀行 <普通預金>";
  const text = renderCfoTelegram({ locale: "ja", view: "why", snapshot }).text;
  assert.match(text, /合計に入れていません.*三菱UFJ銀行.*&lt;普通預金&gt;/s);
  assert.doesNotMatch(text, /合計に入れていません：なし/);
});

test("unconfirmed source amounts fail closed for complete and partial in both locales", () => {
  for (const factory of [completeSnapshot, partialSnapshot]) {
    for (const verificationStatus of ["locally_estimated", "unavailable"]) {
      for (const locale of ["ja", "en"]) {
        const snapshot = factory();
        snapshot.sources[0].verificationStatus = verificationStatus;
        assert.throws(
          () => renderCfoTelegram({ locale, view: "summary", snapshot }),
          /^Error: cfo_telegram_invalid:unconfirmed_amount$/,
        );
      }
    }
  }
});

test("English drill-down punctuation is localized while Japanese punctuation stays unchanged", () => {
  const snapshot = partialSnapshot();
  snapshot.excluded = [
    { label: "カードA", reason: "未接続" },
    { label: "カードB", reason: "確認待ち" },
  ];
  const outputs = Object.fromEntries(["summary", "accounts", "accuracy", "why"]
    .map((view) => [view, {
      ja: renderCfoTelegram({ locale: "ja", view, snapshot }).text,
      en: renderCfoTelegram({ locale: "en", view, snapshot }).text,
    }]));
  for (const output of Object.values(outputs)) assert.doesNotMatch(output.en, /：|（|）|、/);
  assert.match(outputs.summary.ja, /合計に入れていません：カードA（未接続）、カードB（確認待ち）/);
  assert.match(outputs.summary.en, /Not included in the total: カードA \(未接続\), カードB \(確認待ち\)/);
  assert.match(outputs.accounts.ja, /¥420,000（最新）/);
  assert.match(outputs.accounts.en, /JPY 420,000 \(Fresh\)/);
  assert.match(outputs.accuracy.ja, /合計に入れていません：カードA（未接続）、カードB（確認待ち）/);
  assert.match(outputs.accuracy.en, /Not included in the total: カードA \(未接続\), カードB \(確認待ち\)/);
  assert.match(outputs.why.ja, /合計に入れていません：カードA（未接続）、カードB（確認待ち）/);
  assert.match(outputs.why.en, /Not included in the total: カードA \(未接続\), カードB \(確認待ち\)/);
});

function callbackSnapshot() {
  const snapshot = completeSnapshot();
  snapshot.reportingDate = "2026-08-10";
  return snapshot;
}

function callbackInput(overrides = {}) {
  return {
    data: "cfo:accounts:20260810:1",
    uid: "owner-uid",
    actorId: "100",
    chatId: "100",
    messageId: "900",
    callbackQueryId: "callback-1",
    telegramToken: "telegram-token",
    ...overrides,
  };
}

function callbackOptions({ rows = [{ report_payload: callbackSnapshot() }], fetchError = null, calls = [] } = {}) {
  return {
    supaUrl: "https://db.example",
    supaKey: "service-role-key",
    fetchImpl: async (input, init) => {
      calls.push(["fetch", new URL(String(input)), init]);
      if (fetchError) throw fetchError;
      return { ok: true, status: 200, json: async () => rows };
    },
    tgCall: async (token, method, body) => {
      calls.push([method, token, body]);
      if (method === "sendMessage") throw new Error("must not send");
      return { ok: true, result: { message_id: 900 } };
    },
  };
}

test("exact CFO callback reads one owner/date/revision snapshot, edits once, and answers once", async () => {
  const calls = [];
  const result = await handleCfoTelegramCallback(callbackInput(), callbackOptions({ calls }));
  assert.deepEqual(result, { status: "edited", view: "accounts", reportingDate: "2026-08-10", revision: 1 });
  assert.equal(Object.isFrozen(result), true);
  const fetchCall = calls.find(([kind]) => kind === "fetch");
  assert.ok(fetchCall);
  assert.equal(fetchCall[2].method, "GET");
  assert.deepEqual(Object.fromEntries(fetchCall[1].searchParams), {
    uid: "eq.owner-uid", reporting_date: "eq.2026-08-10", revision: "eq.1", select: "report_payload", limit: "1",
  });
  const edits = calls.filter(([method]) => method === "editMessageText");
  const answers = calls.filter(([method]) => method === "answerCallbackQuery");
  assert.equal(edits.length, 1);
  assert.equal(answers.length, 1);
  assert.deepEqual(edits[0][2], {
    chat_id: "100", message_id: 900, parse_mode: "HTML",
    text: renderCfoTelegram({ locale: "ja", view: "accounts", snapshot: callbackSnapshot() }).text,
    reply_markup: renderCfoTelegram({ locale: "ja", view: "accounts", snapshot: callbackSnapshot() }).extra.reply_markup,
  });
  assert.deepEqual(answers[0][2], { callback_query_id: "callback-1" });
  assert.equal(calls.filter(([method]) => method === "sendMessage").length, 0);
});

test("invalid, unavailable, duplicate, and mismatched CFO callbacks fail closed with one fixed toast", async () => {
  const cases = [
    ["actor/chat mismatch", callbackInput({ actorId: "999" }), {}],
    ["malformed data", callbackInput({ data: "cfo:accounts:2026-08-10:1" }), {}],
    ["missing owner", callbackInput({ uid: "" }), {}],
    ["zero rows", callbackInput(), { rows: [] }],
    ["duplicate rows", callbackInput(), { rows: [{ report_payload: callbackSnapshot() }, { report_payload: callbackSnapshot() }] }],
    ["provider failure", callbackInput(), { fetchError: new Error("provider amount 420000 credential secret") }],
    ["payload date mismatch", callbackInput(), { rows: [{ report_payload: { ...callbackSnapshot(), reportingDate: "2026-08-09" } }] }],
    ["payload revision mismatch", callbackInput(), { rows: [{ report_payload: { ...callbackSnapshot(), revision: 2 } }] }],
  ];
  const toasts = [];
  for (const [name, input, optionOverrides] of cases) {
    const calls = [];
    const result = await handleCfoTelegramCallback(input, callbackOptions({ ...optionOverrides, calls }));
    assert.deepEqual(result, { status: "failed" }, name);
    assert.equal(Object.isFrozen(result), true, name);
    assert.deepEqual(calls.filter(([kind]) => kind === "editMessageText"), [], name);
    assert.deepEqual(calls.filter(([kind]) => kind === "sendMessage"), [], name);
    const answers = calls.filter(([kind]) => kind === "answerCallbackQuery");
    assert.equal(answers.length, 1, name);
    toasts.push(answers[0][2].text);
    assert.doesNotMatch(JSON.stringify(result), /420000|credential|secret|provider|Error|stack/i, name);
  }
  assert.ok(toasts.every((toast) => toast === toasts[0] && /もう一度/.test(toast)));
});

test("CFO owner lookup failure still answers once without edit/send or raw error logging", async () => {
  const env = {
    LM_TELEGRAM_BOT_TOKEN: "fixture-token",
    LM_TELEGRAM_WEBHOOK_SECRET: "fixture-webhook-secret",
    SUPABASE_URL: "https://fixture.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY: "fixture-service-role",
    LIFE_RUN_LOOPS: "false",
  };
  const previousEnv = Object.fromEntries(Object.keys(env).map((key) => [key, process.env[key]]));
  Object.assign(process.env, env);
  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  const originalConsoleError = console.error;
  let productionServer;
  let answers = 0;
  let edits = 0;
  let sends = 0;
  const logs = [];
  http.createServer = (handler) => { productionServer = originalCreateServer(handler); return productionServer; };
  global.fetch = async (input) => {
    const url = new URL(String(input));
    if (url.hostname === "api.telegram.org") {
      if (url.pathname.endsWith("/answerCallbackQuery")) answers += 1;
      if (url.pathname.endsWith("/editMessageText")) edits += 1;
      if (url.pathname.endsWith("/sendMessage")) sends += 1;
      return { ok: true, status: 200, json: async () => ({ ok: true, result: true }) };
    }
    if (url.pathname === "/rest/v1/lm_users") throw new Error("raw owner lookup provider secret");
    throw new Error(`unexpected provider ${url.pathname}`);
  };
  console.error = (...args) => { logs.push(args); };
  const serverPath = require.resolve("../server.js");
  delete require.cache[serverPath];
  try {
    require("../server.js");
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));
    const body = JSON.stringify({ callback_query: {
      id: "cfo-owner-failure", from: { id: 100 }, data: "cfo:accounts:20260810:1",
      message: { message_id: 900, chat: { id: 100 } },
    } });
    const status = await new Promise((resolve, reject) => {
      const request = http.request(`http://127.0.0.1:${productionServer.address().port}/telegram`, {
        method: "POST", headers: {
          "content-type": "application/json", "content-length": Buffer.byteLength(body),
          "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
        },
      }, (response) => { response.resume(); response.on("end", () => resolve(response.statusCode)); });
      request.on("error", reject); request.end(body);
    });
    assert.equal(status, 200);
    assert.equal(answers, 1);
    assert.equal(edits, 0);
    assert.equal(sends, 0);
    assert.doesNotMatch(JSON.stringify(logs), /raw owner lookup provider secret/);
  } finally {
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    console.error = originalConsoleError;
    delete require.cache[serverPath];
    if (productionServer && productionServer.listening) await new Promise((resolve) => productionServer.close(resolve));
    for (const [key, value] of Object.entries(previousEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
});

module.exports = { completeSnapshot, partialSnapshot, recoveredSnapshot, actionRequiredSnapshot };
