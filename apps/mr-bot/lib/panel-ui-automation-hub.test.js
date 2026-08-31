"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const { renderPanelPage } = require("./panel-ui.js");

test("signed-in panel exposes a searchable Automation Hub with one master switch", () => {
  const html = renderPanelPage({ csrf: "csrf-fixture" });
  assert.match(html, /data-panel-section="automation-hub"/);
  assert.match(html, /id="automation-search"/);
  assert.match(html, /data-automation-toggle/);
  assert.match(html, /data-automation-save/);
  assert.match(html, /"automation-hub": "\/api\/panel\/automation-hub"/);
  assert.match(html, /function validateAutomationHubData/);
  assert.match(html, /function renderAutomationHub/);
  assert.match(html, /idempotency-key/);
  assert.doesNotMatch(html, /localStorage|sessionStorage/);
  for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) assert.doesNotThrow(() => new vm.Script(match[1]));
});

test("guest panel does not expose Automation Hub controls", () => {
  const html = renderPanelPage({ guest: true });
  const main = html.match(/<main class="panel-grid">[\s\S]*?<\/main>/)[0];
  assert.doesNotMatch(main, /data-panel-section="automation-hub"/);
  assert.doesNotMatch(main, /data-automation-toggle/);
});
