"use strict";

const test = require("node:test");
const assert = require("node:assert");
const vm = require("node:vm");
const { roundedScoreValue } = require("./panel-score-semantics.js");

let renderPanelPage = null;
let renderScoreCards = null;
try {
  ({ renderPanelPage, renderScoreCards } = require("./panel-ui.js"));
} catch (error) {
  if (error.code !== "MODULE_NOT_FOUND") throw error;
}

function safeIntegerFinancialOrgans() {
  const ref = "outcome:10000000-0000-4000-8000-000000000001";
  const period = (kind) => ({ kind, start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" });
  return {
    daily: { status: "insufficient_data", value: null, period: period("rolling_7_days"), numerator: 0, denominator: 0, reason: "No DAILY outcomes.", source_outcome_ids: [], components: { timezone: "UTC", excluded_unknown_count: 0, eligible_events: 0, resolved_events: 0, required_succeeded: 0, required_failed: 0, required_pending: 0, context_unnecessary: 0, optional_ignored: 0 } },
    physical: { status: "insufficient_data", value: null, period: period("rolling_30_days"), numerator: 0, denominator: 0, reason: "No PHYSICAL outcomes.", source_outcome_ids: [], components: { timezone: "UTC", excluded_unknown_count: 0, detected_needs: 0, confirmed_booking: 0, confirmed_completion: 0, unresolved_needs: 0, search_candidate_unconfirmed: 0 } },
    mental: { status: "insufficient_data", value: null, period: period("rolling_7_days"), numerator: 0, denominator: 0, reason: "No MENTAL outcomes.", source_outcome_ids: [], components: { timezone: "UTC", excluded_unknown_count: 0, deduplicated_triggers: 0, delivered_within_cap: 0, suppression_honored: 0, correction_persisted: 0, cap_overflow: 0, unresolved_triggers: 0 } },
    financial: { status: "measured", value: 10, period: period("calendar_month"), numerator: 945755921642804, denominator: 9007199253740991, reason: "Verified net income.", source_outcome_ids: [ref], components: { timezone: "UTC", excluded_unknown_count: 0, currency: "USD", gross_income_minor: 9007199253740991, realized_loss_minor: 8061443332098187, fee_minor: 0, user_transfer_minor: 0, excluded_rows: 0, net_clamped: false } },
  };
}

function emittedScoreRenderer() {
  const script = renderPanelPage().match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
  const start = script.indexOf("const SCORE_LABELS");
  const end = script.indexOf("const renderScores = renderScoreCards;") + "const renderScores = renderScoreCards;".length;
  const sandbox = { Intl, Date, Object, Array, Number, String, BigInt, Set, Math };
  vm.runInNewContext(`${script.slice(start, end)}\nglobalThis.__renderScores = renderScoreCards;`, sandbox);
  return sandbox.__renderScores;
}

test("PANEL-8h: panel shell identifies the product only as Life Manager", () => {
  const html = renderPanelPage();
  assert.equal(html.match(/<title>([^<]+)<\/title>/)?.[1], "Life Manager");
  assert.equal(html.match(/<p class="wordmark">([^<]+)<\/p>/)?.[1], "Life Manager / life operations");
  assert.equal(html.match(/<h1>([^<]+)<\/h1>/)?.[1], "Life Manager");
  assert.doesNotMatch(html, /\bAnicca\b/i);
});

test("LM-33c: panel renders the five mirror sections in spec order", () => {
  assert.equal(typeof renderPanelPage, "function");
  const html = renderPanelPage();
  assert.match(html, /<html lang="ja">/);
  assert.match(html, /<meta name="viewport" content="width=device-width,initial-scale=1">/);

  const sections = ["timeline", "scores", "ledger", "gates", "settings"];
  let previous = -1;
  for (const section of sections) {
    const position = html.indexOf(`data-panel-section="${section}"`);
    assert.ok(position > previous, `${section} must exist after the previous section`);
    previous = position;
  }
});

test("PANEL-0: panel includes a real control center and keeps read APIs same-origin", () => {
  assert.equal(typeof renderPanelPage, "function");
  const html = renderPanelPage();
  assert.match(html, /data-panel-section="control-center"/);
  assert.match(html, /id="connection-cards"/);
  assert.match(html, /id="settings-controls"/);
  assert.match(html, /<button\b/i);
  assert.match(html, /credentials:\s*["']same-origin["']/);
  for (const endpoint of ["timeline", "scores", "ledger", "gates", "settings"]) {
    assert.match(html, new RegExp(`/api/panel/${endpoint}`));
  }
  assert.match(html, /insufficient data/);
  assert.match(html, /まだ収支の記録はありません/);
});

test("PANEL-8h: emitted renderers accept only projected timeline and ledger DTO fields", () => {
  const html = renderPanelPage();
  assert.match(html, /validateTimelineData\(data\)/);
  assert.match(html, /data\.items/);
  assert.match(html, /validateLedgerData\(data\)/);
  assert.match(html, /data\.financial\.items\.concat\(data\.api_cost\.items\)/);
  assert.match(html, /displaySafeLink\(entry\.link\)/);
  assert.doesNotMatch(html, /data\.events|data\.calls|financial\.entries/);
  assert.doesNotMatch(html, /url\.protocol === "http:"/);
});

test("PANEL-8h: emitted loader applies closed validators and shared secret patterns before display", () => {
  const html = renderPanelPage();
  for (const validator of [
    "validateTimelineData",
    "validateLedgerData",
    "validateGatesData",
    "validateSettingsData",
    "validateControlCenterData",
  ]) {
    assert.match(html, new RegExp(`${validator}\\(data\\)`));
  }
  assert.match(html, /displaySecretPatterns/);
  assert.match(html, /displayContainsSensitiveValue\(data\)/);
  assert.match(html, /if \(!response\.ok\) throw new Error\(name \+ " unavailable"\)/);
  assert.doesNotMatch(html, /response\.statusText|response\.text\(\)|JSON\.stringify\(data\)/);
});

test("PANEL-0: visible actions have semantic delegated handlers", () => {
  const html = renderPanelPage();
  assert.match(html, /addEventListener\("click"/);
  assert.match(html, /addEventListener\("change"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /min-height:\s*44px/);
  assert.doesNotMatch(html, /<span[^>]+data-action=/);
  for (const action of ["connect-calendar", "toggle-calls", "toggle-notifications", "toggle-daily", "toggle-delegation", "instructions-location", "instructions-wallet", "instructions-call"]) {
    assert.match(html, new RegExp(`case ["']${action}["']`));
  }
});

test("PANEL-0: Calendar renders native Disconnect and Reconnect controls", () => {
  const html = renderPanelPage();
  assert.match(html, /connection\.disconnect/);
  assert.match(html, /disconnect-calendar/);
  assert.match(html, /Reconnect calendar/);
  assert.match(html, /case "disconnect-calendar": return \{ type: "connection\.disconnect", provider: "calendar" \}/);
});

test("LM-33c: panel CSS collapses to one column without horizontal overflow at 375px", () => {
  assert.equal(typeof renderPanelPage, "function");
  const html = renderPanelPage();
  assert.match(html, /@media\s*\(max-width:\s*640px\)/);
  assert.match(html, /grid-template-columns:\s*1fr/);
  assert.match(html, /overflow-x:\s*hidden/);
  assert.match(html, /overflow-wrap:\s*anywhere/);
});

test("LM-33c: panel provides an inline favicon without an extra failing request", () => {
  assert.equal(typeof renderPanelPage, "function");
  assert.match(renderPanelPage(), /<link rel="icon" href="data:image\/svg\+xml,/);
});

test("PANEL-8g: score cards render all four outcome organs, exact insufficient data, reasons, periods, components, and linkage", () => {
  const html = renderPanelPage();
  assert.match(html, />4 organ スコア</);
  for (const name of ["daily", "physical", "mental", "financial"]) assert.match(html, new RegExp(`${name}: ["']${name.toUpperCase()}["']`));
  assert.match(html, /insufficient data/);
  assert.match(html, /organ\.reason/);
  assert.match(html, /organ\.period/);
  assert.match(html, /organ\.numerator/);
  assert.match(html, /organ\.denominator/);
  assert.match(html, /organ\.components/);
  assert.match(html, /source_outcome_ids/);
  assert.doesNotMatch(html, /organ\.score|organ\.no_data|organ\.calls|organ\.answered|organ\.ledger_entries/);
});

test("PANEL-8g: malformed score payloads fail the score section closed without NaN or raw JSON", () => {
  const html = renderPanelPage();
  assert.match(html, /validScoreOrgan/);
  assert.match(html, /throw new Error\(["']invalid score payload["']\)/);
  assert.doesNotMatch(html, /JSON\.stringify\(organ/);
  assert.doesNotMatch(html, />NaN</);
});

test("PANEL-8g: executable score renderer shows measured, insufficient, invalid, reason, period, components, and source count", () => {
  assert.equal(typeof renderScoreCards, "function");
  const period = (kind) => ({ kind, start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" });
  const html = renderScoreCards({ organs: {
    daily: { status: "measured", value: 50, period: period("rolling_7_days"), numerator: 1, denominator: 2, reason: "Resolved one of two.", source_outcome_ids: ["outcome:10000000-0000-4000-8000-000000000001"], components: { timezone: "UTC", excluded_unknown_count: 0, eligible_events: 2, resolved_events: 1, required_succeeded: 1, required_failed: 1, required_pending: 0, context_unnecessary: 0, optional_ignored: 0 } },
    physical: { status: "insufficient_data", value: null, period: period("rolling_30_days"), numerator: 0, denominator: 0, reason: "No overdue needs.", source_outcome_ids: [], components: { timezone: "UTC", excluded_unknown_count: 0, detected_needs: 0, confirmed_booking: 0, confirmed_completion: 0, unresolved_needs: 0, search_candidate_unconfirmed: 0 } },
    mental: { status: "invalid_data", value: null, period: period("rolling_7_days"), numerator: null, denominator: null, reason: "Invalid mental data.", source_outcome_ids: [], components: { timezone: "UTC", excluded_unknown_count: 0, deduplicated_triggers: 0, delivered_within_cap: 0, suppression_honored: 0, correction_persisted: 0, cap_overflow: 0, unresolved_triggers: 0 } },
    financial: { status: "measured", value: 70, period: period("calendar_month"), numerator: 700, denominator: 1000, reason: "Net verified income.", source_outcome_ids: ["outcome:10000000-0000-4000-8000-000000000001"], components: { timezone: "UTC", excluded_unknown_count: 0, currency: "USD", gross_income_minor: 1000, realized_loss_minor: 200, fee_minor: 100, user_transfer_minor: 0, excluded_rows: 0, net_clamped: false } },
  } });
  assert.match(html, /50<small>\/100/);
  assert.match(html, /insufficient data/);
  assert.match(html, /invalid data/);
  assert.match(html, /Resolved one of two\./);
  assert.match(html, /rolling 7 days/);
  assert.match(html, /対応できた予定/);
  assert.doesNotMatch(html, /resolved events/);
  assert.match(html, /根拠 1件/);
  assert.equal((html.match(/data-score-organ=/g) || []).length, 4);
});

test("PANEL-8g: executable score renderer rejects a missing organ instead of rendering NaN or a fake score", () => {
  assert.equal(typeof renderScoreCards, "function");
  assert.throws(() => renderScoreCards({ organs: {} }), /invalid score payload/);
});

test("PANEL-8g: executable score renderer rejects malformed period kinds and non-UUID source references", () => {
  const invalid = { status: "insufficient_data", value: null, period: { kind: "anything", start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" }, numerator: 0, denominator: 0, reason: "No outcomes.", source_outcome_ids: ["outcome:------------------------------------"], components: { timezone: "UTC" } };
  assert.throws(() => renderScoreCards({ organs: { daily: invalid, physical: invalid, mental: invalid, financial: invalid } }), /invalid score payload/);
});

test("PANEL-8g: executable score renderer rejects contradictory ratios, duplicate refs, incomplete components, non-ISO periods, and extra organs", () => {
  const ref = "outcome:10000000-0000-4000-8000-000000000001";
  const periods = { daily: "rolling_7_days", physical: "rolling_30_days", mental: "rolling_7_days", financial: "calendar_month" };
  const components = {
    daily: { timezone: "UTC", excluded_unknown_count: 0, eligible_events: 1, resolved_events: 1, required_succeeded: 1, required_failed: 0, required_pending: 0, context_unnecessary: 0, optional_ignored: 0 },
    physical: { timezone: "UTC", excluded_unknown_count: 0, detected_needs: 1, confirmed_booking: 1, confirmed_completion: 0, unresolved_needs: 0, search_candidate_unconfirmed: 0 },
    mental: { timezone: "UTC", excluded_unknown_count: 0, deduplicated_triggers: 1, delivered_within_cap: 1, suppression_honored: 0, correction_persisted: 0, cap_overflow: 0, unresolved_triggers: 0 },
    financial: { timezone: "UTC", excluded_unknown_count: 0, currency: "USD", gross_income_minor: 100, realized_loss_minor: 0, fee_minor: 0, user_transfer_minor: 0, excluded_rows: 0, net_clamped: false },
  };
  const organ = (name) => ({ status: "measured", value: 100, period: { kind: periods[name], start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" }, numerator: name === "financial" ? 100 : 1, denominator: name === "financial" ? 100 : 1, reason: "Measured.", source_outcome_ids: [ref], components: components[name] });
  const valid = { daily: organ("daily"), physical: organ("physical"), mental: organ("mental"), financial: organ("financial") };
  assert.doesNotThrow(() => renderScoreCards({ organs: valid }));
  assert.throws(() => renderScoreCards({ organs: valid, extra: true }), /invalid score payload/);
  for (const mutate of [
    (organs) => { organs.daily = { ...organs.daily, numerator: 0 }; },
    (organs) => { organs.daily = { ...organs.daily, source_outcome_ids: [ref, ref] }; },
    (organs) => { organs.mental = { ...organs.mental, components: { timezone: "UTC" } }; },
    (organs) => { organs.daily = { ...organs.daily, period: { ...organs.daily.period, start_at: 0 } }; },
    (organs) => { organs.daily = { ...organs.daily, period: { ...organs.daily.period, start_at: "2026-02-30T12:00:00.000Z" } }; },
    (organs) => { organs.extra = organs.daily; },
  ]) {
    const organs = structuredClone(valid);
    mutate(organs);
    assert.throws(() => renderScoreCards({ organs }), /invalid score payload/);
  }
});

test("PANEL-8g: score renderer accepts the integer-safe FINANCIAL ratio emitted by the server core", () => {
  const organs = safeIntegerFinancialOrgans();
  assert.equal(roundedScoreValue(organs.financial.numerator, organs.financial.denominator), 10);
  assert.doesNotThrow(() => renderScoreCards({ organs }));
});

test("PANEL-8g: emitted browser score renderer accepts the integer-safe FINANCIAL core value", () => {
  const organs = safeIntegerFinancialOrgans();
  assert.equal(roundedScoreValue(organs.financial.numerator, organs.financial.denominator), 10);
  assert.doesNotThrow(() => emittedScoreRenderer()({ organs }));
});
