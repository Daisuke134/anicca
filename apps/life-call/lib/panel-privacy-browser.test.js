"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  BROWSER_LOAD_ERROR_COPY,
  SAFE_TIMELINE_SENTENCE,
  buildRecipes,
} = require("../eval/panel-privacy-contract.js");
const {
  capturePanelResponse,
  emittedPanelRuntime,
} = require("../eval/panel-privacy-harness.js");
const { renderPanelPage } = require("./panel-ui.js");

const MIRROR_SECTIONS = Object.freeze(["timeline", "scores", "ledger", "gates", "settings"]);
const INTERNAL_DISPLAY_MARKERS = Object.freeze([
  "lm_",
  "prompt",
  "source_outcome_ids",
  "uidRef",
  "csrf",
  "panel-contract-user",
  "dais@example.invalid",
  "Error:",
  "\n    at ",
]);

async function loadCaptured(section, options = {}) {
  const captured = await capturePanelResponse({ section, ...options });
  return {
    captured,
    browser: await emittedPanelRuntime(captured, section).load(),
  };
}

async function loadExactCandidate(section, candidate) {
  return loadCaptured(section, {
    responseCandidateTransform(candidateSection, original) {
      return candidateSection === section ? candidate : original;
    },
  });
}

function withGateUnlockMethod(candidate, value) {
  const next = structuredClone(candidate);
  next.gates[0].unlock_method = value;
  return next;
}

function withControlConnection(candidate, name, mutate) {
  const next = structuredClone(candidate);
  mutate(next.connections[name]);
  return next;
}

test("PANEL-8h: emitted loadPanelSection renders five projected sections as human-readable content in order", async () => {
  const page = renderPanelPage();
  let previous = -1;
  for (const section of MIRROR_SECTIONS) {
    const position = page.indexOf(`data-panel-section="${section}"`);
    assert.ok(position > previous, `${section} follows the previous mirror section`);
    previous = position;
  }

  const expectedCopy = {
    timeline: "開始の予定です。詳細はカレンダーで確認してください。",
    scores: "根拠 0件",
    ledger: "USD 10.00",
    gates: "位置情報",
    settings: "未設定",
  };
  for (const section of MIRROR_SECTIONS) {
    const { captured, browser } = await loadCaptured(section);
    assert.equal(captured.capturedBy, "handlePanelApiRequest");
    assert.equal(captured.status, 200);
    assert.equal(browser.state, "loaded", `${section} loaded`);
    assert.match(browser.html, new RegExp(expectedCopy[section]), `${section} human-readable copy`);
    assert.doesNotMatch(browser.html, /<pre\b|JSON\.stringify|\[object Object\]/);
  }
});

test("PANEL-8h: emitted timeline and ledger consume safe projected fields without source or unsafe anchors", async () => {
  for (const recipe of buildRecipes()) {
    const timeline = await loadCaptured("timeline", {
      source: "timeline-text",
      hostileValue: recipe.value,
    });
    assert.equal(timeline.browser.state, "loaded", `${recipe.id}: timeline loaded`);
    assert.match(timeline.browser.html, new RegExp(SAFE_TIMELINE_SENTENCE));
    assert.equal(timeline.browser.html.includes(recipe.value), false, `${recipe.id}: timeline source absent`);

    const ledger = await loadCaptured("ledger", {
      source: "ledger-href",
      hostileValue: recipe.value,
    });
    assert.equal(ledger.browser.state, "loaded", `${recipe.id}: ledger loaded`);
    assert.doesNotMatch(ledger.browser.html, /<a\b[^>]*class="ledger-link"/);
    assert.equal(ledger.browser.html.includes(recipe.value), false, `${recipe.id}: ledger source absent`);
  }
});

test("PANEL-8h: emitted settings and control center preserve closed null placeholders and generic identity", async () => {
  const settings = await loadCaptured("settings", { source: "settings-null-call-language" });
  assert.equal(settings.browser.state, "loaded");
  assert.match(settings.browser.html, />未設定</);

  const control = await loadCaptured("control-center", { source: "control-center-null-call-language" });
  assert.equal(control.browser.state, "loaded");
  assert.match(control.browser.html, /<strong>Life Manager user<\/strong>/);
  assert.match(control.browser.html, /<option value="" selected disabled>Not configured<\/option>/);
  assert.doesNotMatch(control.browser.html, /panel-contract-user|dais@example\.invalid|user:[0-9a-f]{12}/);
});

test("PANEL-8h: emitted loader renders only the fixed error for every closed section HTTP 422", async () => {
  for (const section of ["scores", "gates", "settings", "control-center"]) {
    const { captured, browser } = await loadCaptured(section, { malformed: true });
    assert.equal(captured.status, 422);
    assert.deepEqual(captured.body, { error: "section_unavailable", section });
    assert.equal(browser.state, "error");
    assert.equal(browser.html, `<p class="error">${BROWSER_LOAD_ERROR_COPY}</p>`);
    assert.doesNotMatch(browser.html, /section_unavailable|stack|Error:|lm_|prompt|table/i);
  }
});

test("PANEL-8h: emitted browser never displays internal names, raw objects, stacks, identity, or the 19 synthetic secrets", async () => {
  const rendered = [];
  for (const section of [...MIRROR_SECTIONS, "control-center"]) {
    rendered.push((await loadCaptured(section)).browser.html);
  }
  for (const recipe of buildRecipes()) {
    rendered.push((await loadCaptured("timeline", {
      source: "timeline-text",
      hostileValue: recipe.value,
    })).browser.html);
  }
  const display = rendered.join("\n");
  for (const marker of INTERNAL_DISPLAY_MARKERS) {
    assert.equal(display.includes(marker), false, `internal marker absent: ${marker}`);
  }
  for (const recipe of buildRecipes()) {
    assert.equal(display.includes(recipe.value), false, `${recipe.id}: secret absent`);
  }
  assert.doesNotMatch(display, /<pre\b|JSON\.stringify|\[object Object\]/);
});

test("PANEL-8h: emitted page has desktop grid structure and a 375px one-column no-overflow contract", () => {
  const page = renderPanelPage();
  assert.match(page, /\.panel-grid\s*\{[^}]*grid-template-columns:\s*repeat\(12,\s*minmax\(0,\s*1fr\)\)/s);
  assert.match(page, /\.panel-section:nth-child\(1\)\s*\{[^}]*grid-column:\s*span 7/s);
  assert.match(page, /\.panel-section:nth-child\(2\)\s*\{[^}]*grid-column:\s*span 5/s);
  assert.match(page, /@media\s*\(max-width:\s*640px\)\s*\{[\s\S]*?\.panel-grid\s*\{[^}]*grid-template-columns:\s*1fr/s);
  assert.match(page, /@media\s*\(max-width:\s*640px\)\s*\{[\s\S]*?\.panel-section:nth-child\(n\)\s*\{[^}]*grid-column:\s*1/s);
  assert.match(page, /body\s*\{[^}]*overflow-x:\s*hidden/s);
  assert.match(page, /\.panel-section\s*\{[^}]*min-width:\s*0/s);
  assert.match(page, /\.section-body\s*\{[^}]*overflow-wrap:\s*anywhere/s);
});

test("PANEL-8h: every API-accepted gate text boundary loads from the exact same candidate", async () => {
  const baseline = (await capturePanelResponse({ section: "gates" })).body;
  for (const [label, unlockMethod] of [
    ["normal safe text", "Telegramで位置情報を共有してください。"],
    ["maximum 1000 characters", "A".repeat(1000)],
  ]) {
    const { captured, browser } = await loadExactCandidate(
      "gates",
      withGateUnlockMethod(baseline, unlockMethod),
    );
    assert.equal(captured.status, 200, `${label}: API accepted`);
    assert.equal(browser.state, "loaded", `${label}: emitted loadPanelSection parity`);
    assert.equal(browser.html.includes(unlockMethod), true, `${label}: safe text rendered`);
  }

  for (const [label, unlockMethod] of [
    ["empty text", ""],
    ["overlong safe text", "A".repeat(1001)],
  ]) {
    const { captured, browser } = await loadExactCandidate(
      "gates",
      withGateUnlockMethod(baseline, unlockMethod),
    );
    assert.equal(captured.status, 422, `${label}: API rejects browser-invalid candidate`);
    assert.deepEqual(captured.body, { error: "section_unavailable", section: "gates" });
    assert.equal(browser.state, "error", `${label}: emitted loader stays closed`);
    assert.equal(browser.html, `<p class="error">${BROWSER_LOAD_ERROR_COPY}</p>`);
  }
});

test("PANEL-8h: control-center optional action fields have identical API and emitted-browser semantics", async () => {
  const baseline = (await capturePanelResponse({ section: "control-center" })).body;
  const accepted = [
    ["real buildControlCenter DTO", baseline],
    ["actions absent", withControlConnection(baseline, "telegram", (item) => { delete item.actions; })],
    ["actions array", withControlConnection(baseline, "telegram", (item) => { item.actions = []; })],
    ["actionLabel absent", withControlConnection(baseline, "calendar", (item) => { delete item.actionLabel; })],
    ["actionLabel safe string", withControlConnection(baseline, "calendar", (item) => { item.actionLabel = "Connect calendar"; })],
  ];
  for (const [label, candidate] of accepted) {
    const { captured, browser } = await loadExactCandidate("control-center", candidate);
    assert.equal(captured.status, 200, `${label}: API accepted`);
    assert.equal(browser.state, "loaded", `${label}: emitted loadPanelSection parity`);
  }

  const rejected = [
    ["actions null", withControlConnection(baseline, "telegram", (item) => { item.actions = null; })],
    ["actionLabel null", withControlConnection(baseline, "calendar", (item) => { item.actionLabel = null; })],
  ];
  for (const [label, candidate] of rejected) {
    const { captured, browser } = await loadExactCandidate("control-center", candidate);
    assert.equal(captured.status, 422, `${label}: API rejects browser-invalid candidate`);
    assert.deepEqual(captured.body, { error: "section_unavailable", section: "control-center" });
    assert.equal(browser.state, "error", `${label}: emitted loader stays closed`);
    assert.equal(browser.html, `<p class="error">${BROWSER_LOAD_ERROR_COPY}</p>`);
  }
});
