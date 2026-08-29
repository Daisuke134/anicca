"use strict";

const test = require("node:test");
const assert = require("node:assert");
const vm = require("node:vm");
const { roundedScoreValue } = require("./panel-score-semantics.js");

let renderPanelPage = null;
let renderScoreCards = null;
let renderPanelOnboardingPage = null;
try {
  ({ renderPanelPage, renderScoreCards, renderPanelOnboardingPage } = require("./panel-ui.js"));
} catch (error) {
  if (error.code !== "MODULE_NOT_FOUND") throw error;
}

test("Task 7B: Telegram-native onboarding page is server-state driven and safe at 375px", () => {
  assert.equal(typeof renderPanelOnboardingPage, "function");
  const html = renderPanelOnboardingPage({ csrf: 'csrf-<>&"\'' });
  assert.match(html, /data-panel-onboarding/);
  assert.match(html, /data-csrf="csrf-&lt;&gt;&amp;&quot;&#39;"/);
  assert.match(html, /\/api\/panel\/onboarding/);
  assert.match(html, /\/api\/panel\/onboarding\/calendar\/start/);
  assert.match(html, /\/api\/panel\/onboarding\/calendar\/status/);
  assert.match(html, /@media\s*\(max-width:\s*375px\)/);
  assert.match(html, /replaceChildren\(/);
  assert.match(html, /\.textContent\s*=/);
  assert.match(html, /\.value\s*=/);
  assert.doesNotMatch(html, /\.innerHTML\s*=/);
  assert.doesNotMatch(html, /localStorage|sessionStorage|Sign in with Google|Supabase auth|\/auth\//i);
  assert.match(html, /credentials:\s*["']same-origin["']/);
  assert.match(html, /idempotency-key/);
  assert.match(html, /x-lm-csrf/);
  assert.match(html, /paymentLink/);
  assert.match(html, /buy\.stripe\.com/);
  assert.match(html, /090-1234-5678/);
  assert.match(html, /\+81 90-1234-5678/);
  assert.match(html, /ライブ位置情報/);
  assert.match(html, /共有が終わった後/);
  assert.match(html, /自宅住所/);
  assert.match(html, /直近の予定/);
  assert.doesNotMatch(html, /現在.*ライブ位置情報/);
  assert.match(html, /window\.location\.(?:assign|replace)\(/);
  const order = ["name", "calendar", "home", "notifications", "phone", "call", "payment", "dashboard"];
  let previous = -1;
  for (const step of order) {
    const position = html.indexOf(`case "${step}"`);
    assert.ok(position > previous, `${step} must be dispatched from server step order`);
    previous = position;
  }
  assert.match(html, /phone\.skip/);
  assert.match(html, /call\.skip/);
  assert.match(html, /payment\.skip/);
  assert.match(html, /primary-action/);
  assert.match(html, /overflow-wrap:\s*anywhere/);
});

test("Task 7B: onboarding UI never interpolates server copy into markup and keeps static labels escaped", () => {
  const html = renderPanelOnboardingPage({ csrf: "safe-token" });
  assert.doesNotMatch(html, /\.insertAdjacentHTML\(/);
  assert.match(html, /createElement\(["'](?:input|button|a|label|p|span)["']\)/);
  assert.match(html, /textContent\s*=/);
  assert.match(html, /new URL\(value\)/);
  assert.match(html, /url\.hostname\s*!==\s*["']buy\.stripe\.com["']/);
});

class OnboardingFakeNode {
  constructor(tagName, parent = null) {
    this.tagName = tagName.toUpperCase();
    this.parentNode = parent;
    this.children = [];
    this.dataset = {};
    this.className = "";
    this.attributes = {};
    this.textContent = "";
    this.value = "";
  }

  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener() {}
  setAttribute(name, value) { this.attributes[name] = String(value); }
  matches(selector) {
    if (selector === "[data-panel-onboarding]") return this.dataset.panelOnboarding !== undefined;
    const dataAction = /^\[data-onboarding-action\]$/.test(selector);
    if (dataAction) return this.dataset.onboardingAction !== undefined;
    if (selector === "input") return this.tagName === "INPUT";
    return false;
  }
  querySelector(selector) {
    if (selector === "[data-onboarding-title]" && this.dataset.onboardingTitle !== undefined) return this;
    if (selector === "[data-onboarding-copy]" && this.dataset.onboardingCopy !== undefined) return this;
    if (selector === "[data-onboarding-form]" && this.dataset.onboardingForm !== undefined) return this;
    if (selector === "[data-onboarding-actions]" && this.dataset.onboardingActions !== undefined) return this;
    if (selector === "[data-onboarding-status]" && this.dataset.onboardingStatus !== undefined) return this;
    if (this.matches(selector)) return this;
    for (const child of this.children) { const found = child.querySelector(selector); if (found) return found; }
    return null;
  }
  closest(selector) { let node = this; while (node) { if (node.matches(selector)) return node; node = node.parentNode; } return null; }
}

function onboardingFakeDocument() {
  const root = new OnboardingFakeNode("main"); root.dataset.panelOnboarding = ""; root.dataset.csrf = "csrf";
  const title = new OnboardingFakeNode("h1"); title.dataset.onboardingTitle = "";
  const copy = new OnboardingFakeNode("p"); copy.dataset.onboardingCopy = "";
  const form = new OnboardingFakeNode("div"); form.dataset.onboardingForm = "";
  const actions = new OnboardingFakeNode("div"); actions.dataset.onboardingActions = "";
  const status = new OnboardingFakeNode("p"); status.dataset.onboardingStatus = "";
  root.append(title, copy, form, actions, status);
  return { root, document: { querySelector: (selector) => root.querySelector(selector), createElement: (tag) => new OnboardingFakeNode(tag) } };
}

async function runOnboardingInline(state) {
  const html = renderPanelOnboardingPage({ csrf: "csrf" });
  const script = html.match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
  const fake = onboardingFakeDocument();
  const response = { status: 200, ok: true, json: async () => state };
  vm.runInNewContext(script, {
    document: fake.document,
    fetch: async () => response,
    URL,
    Promise,
    Date,
    Math,
    Object,
    String,
    globalThis: {},
    window: { location: { reload() {}, assign() {} } },
  });
  await new Promise((resolve) => setImmediate(resolve));
  return fake;
}

test("Task 7B: every server-provided step has exactly one primary action and only phone/call/payment have skips", async () => {
  const states = [
    { step: "name", name: "A" },
    { step: "calendar" },
    { step: "home", homeAddress: "home" },
    { step: "notifications" },
    { step: "phone", phone: "" },
    { step: "call" },
    { step: "payment", paymentLink: "https://buy.stripe.com/test_life_manager?client_reference_id=server" },
    { step: "dashboard", paid: false, paymentLink: "https://buy.stripe.com/test_life_manager?client_reference_id=server" },
    { step: "dashboard", paid: false },
    { step: "dashboard", paid: true },
  ];
  for (const state of states) {
    const fake = await runOnboardingInline(state);
    const actions = fake.root.querySelector("[data-onboarding-actions]").children;
    const expectedPrimary = state.step === "dashboard" && state.paid !== true ? 0 : 1;
    assert.equal(actions.filter((node) => node.className.includes("primary-action")).length, expectedPrimary, state.step);
    const secondary = actions.filter((node) => node.className.includes("secondary-action"));
    const expectedSecondary = ["phone", "call", "payment"].includes(state.step)
      || (state.step === "dashboard" && state.paid !== true && state.paymentLink);
    assert.equal(secondary.length, expectedSecondary ? 1 : 0, state.step);
    if (state.step === "dashboard" && state.paid === true) assert.equal(actions[0].href, "/panel");
  }
});

test("Task 7B: inline onboarding renderer ignores forged identity/payment fields and uses server step only", async () => {
  const fake = await runOnboardingInline({ step: "phone", phone: "", paid: true, uid: "forged", tg: "forged", paymentLink: "https://evil.example/collect" });
  const actions = fake.root.querySelector("[data-onboarding-actions]").children;
  assert.equal(actions.filter((node) => node.className.includes("primary-action")).length, 1);
  assert.equal(actions.some((node) => node.href), false);
  const visible = [];
  const walk = (node) => { visible.push(node.textContent, node.value, node.href || "", node.dataset.onboardingAction || ""); for (const child of node.children) walk(child); };
  walk(fake.root);
  assert.doesNotMatch(visible.join("\n"), /forged|evil\.example/);
});

test("Task 3: ready dashboard shows value, trial, and next event without requiring checkout", async () => {
  const fake = await runOnboardingInline({
    step: "dashboard",
    paid: false,
    trialExpiresAt: "2026-08-31T12:00:00.000Z",
    trialActive: true,
    nextEvent: { summary: "<img src=x onerror=alert(1)>", startAt: "2026-08-28T14:00:00.000Z" },
    paymentLink: "https://buy.stripe.com/test_life_manager?client_reference_id=server",
  });
  const actions = fake.root.querySelector("[data-onboarding-actions]").children;
  assert.equal(actions.filter((node) => node.className.includes("primary-action")).length, 0);
  assert.equal(actions.filter((node) => node.className.includes("secondary-action")).length, 1);
  const visible = [];
  const walk = (node) => { visible.push(node.textContent, node.value, node.href || ""); for (const child of node.children) walk(child); };
  walk(fake.root);
  const text = visible.join("\n");
  assert.match(text, /準備できました/);
  assert.match(text, /移動時間を自動追加/);
  assert.match(text, /出発5分前/);
  assert.match(text, /無料期間/);
  assert.match(text, /2026-08-31T12:00:00\.000Z/);
  assert.match(text, /<img src=x onerror=alert\(1\)>/);
  assert.match(text, /2026-08-28T14:00:00\.000Z/);

  const withoutCheckout = await runOnboardingInline({ step: "dashboard", paid: false, trialActive: true });
  assert.equal(withoutCheckout.root.querySelector("[data-onboarding-actions]").children.length, 0);
});

test("Task 3: ready copy follows server-owned paid and trial state", async () => {
  const visibleText = async (state) => {
    const fake = await runOnboardingInline(state);
    const visible = [];
    const walk = (node) => { visible.push(node.textContent, node.value, node.href || ""); for (const child of node.children) walk(child); };
    walk(fake.root);
    return { fake, text: visible.join("\n") };
  };

  const paid = await visibleText({ step: "dashboard", paid: true, trialActive: false, trialExpiresAt: "2026-08-31T12:00:00.000Z" });
  assert.match(paid.text, /移動時間を自動追加/);
  assert.match(paid.text, /出発5分前/);
  assert.match(paid.text, /有料プランが有効/);
  assert.doesNotMatch(paid.text, /無料期間/);

  const ended = await visibleText({ step: "dashboard", paid: false, trialActive: false, paymentLink: "https://buy.stripe.com/test_life_manager?client_reference_id=server" });
  assert.match(ended.text, /無料期間は終了/);
  assert.match(ended.text, /停止中/);
  assert.doesNotMatch(ended.text, /移動時間を自動追加|出発5分前/);
  const endedActions = ended.fake.root.querySelector("[data-onboarding-actions]").children;
  assert.equal(endedActions.length, 1);
  assert.equal(endedActions[0].className, "secondary-action");
  assert.match(endedActions[0].href, /^https:\/\/buy\.stripe\.com\//);
});

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

test("Money Printer panel renders one six-lane control room", () => {
  const html = renderPanelPage();
  assert.match(html, /data-panel-section="money-printer"/);
  assert.match(html, /\/api\/panel\/money-printer/);
  for (const label of ["Paid & verified", "Agents working", "Needs You", "Opportunity value", "Found", "Working", "Waiting", "Done", "Paid"]) {
    assert.match(html, new RegExp(label));
  }
});

test("Money Printer panel embeds focused WebMCP tools with only page CSRF for the write header", () => {
  const html = renderPanelPage({ csrf: "csrf-value" });
  const scripts = [...html.matchAll(/<script>\s*([\s\S]*?)\s*<\/script>/g)].map((match) => match[1]);
  const webmcp = scripts.find((script) => script.includes("inspect_money_printer"));
  assert.ok(webmcp);
  assert.match(webmcp, /document\.modelContext\.registerTool\(/);
  assert.match(webmcp, /\/api\/panel\/money-printer/);
  assert.match(webmcp, /add_opportunity/);
  assert.match(webmcp, /inspect_workroom/);
  assert.match(webmcp, /csrf-value/);
  assert.match(webmcp, /x-lm-csrf/);
  assert.match(webmcp, /idempotency-key/);
  assert.doesNotMatch(webmcp, /authorization|bearer/i);
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

test("#1085: Calendar connect action is rendered as Connect Calendar", () => {
  const html = renderPanelPage();
  assert.match(html, /item && item\.actionLabel === "Reconnect calendar" \? "Reconnect calendar" : "Connect Calendar"/);
  assert.doesNotMatch(html, /item && item\.actionLabel === "Reconnect calendar" \? "Reconnect calendar" : "Connect calendar"/);
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
