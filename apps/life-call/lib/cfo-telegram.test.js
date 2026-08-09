"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { renderCfoTelegram, callbackData, evidenceLabel } = require("./cfo-telegram.js");

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
    retryLabel: kind === "reconsent" ? "Moneytreeを再接続してください" : "30分後に自動再試行します",
    nextRetryAt: "2026-08-08T06:32:00+09:00",
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

test("provider outage explains automatic retry at the persisted time without asking reconnection", () => {
  for (const locale of ["ja", "en"]) {
    const text = renderCfoTelegram({ locale, view: "summary", snapshot: actionRequiredSnapshot("provider_outage") }).text;
    assert.match(text, locale === "ja" ? /自動再試行/ : /automatically retry/i);
    assert.match(text, /2026-08-08T06:32:00\+09:00/);
    assert.doesNotMatch(text, /再接続|接続を.*更新|reconnect|connection update/i);
    assert.doesNotMatch(text, /420,000|390,000|stack|Error|https?:\/\/|provider_5xx|moneytree_mufg/i);
  }
});

test("reconsent asks for one Moneytree connection update and keeps copy distinct", () => {
  for (const locale of ["ja", "en"]) {
    const text = renderCfoTelegram({ locale, view: "summary", snapshot: actionRequiredSnapshot("reconsent") }).text;
    assert.match(text, locale === "ja" ? /接続を1回だけ更新/ : /Reconnect Moneytree once/);
    assert.doesNotMatch(text, locale === "ja" ? /自動再試行/ : /automatically retry/i);
    assert.doesNotMatch(text, /420,000|390,000|stack|Error|https?:\/\/|provider_5xx|moneytree_mufg/i);
  }
});

test("action reports have only the four public keys and require RFC3339 nextRetryAt", () => {
  const valid = actionRequiredSnapshot("provider_outage");
  assert.deepEqual(Object.keys(valid.action).sort(), ["kind", "sourceLabel", "retryLabel", "nextRetryAt"].sort());
  for (const nextRetryAt of ["2026-08-08", "not-a-time", "2026-08-08T06:32:00"]) {
    const snapshot = actionRequiredSnapshot("provider_outage");
    snapshot.action.nextRetryAt = nextRetryAt;
    assertInvalid(snapshot, "invalid_action");
  }
  const extra = actionRequiredSnapshot("reconsent");
  extra.action.rawError = "provider body";
  assertInvalid(extra, "unknown_key");
});

module.exports = { completeSnapshot, partialSnapshot, recoveredSnapshot, actionRequiredSnapshot };
