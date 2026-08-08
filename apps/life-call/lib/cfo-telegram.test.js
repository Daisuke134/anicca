"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { renderCfoTelegram } = require("./cfo-telegram.js");

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

function actionRequiredSnapshot() {
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
    kind: "reconsent",
    sourceLabel: "Moneytree",
    retryLabel: "接続後に自動再確認",
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

module.exports = { completeSnapshot, partialSnapshot, recoveredSnapshot, actionRequiredSnapshot };
