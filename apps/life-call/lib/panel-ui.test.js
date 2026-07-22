"use strict";

const test = require("node:test");
const assert = require("node:assert");

let renderPanelPage = null;
try {
  ({ renderPanelPage } = require("./panel-ui.js"));
} catch (error) {
  if (error.code !== "MODULE_NOT_FOUND") throw error;
}

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
  assert.match(html, /準備中/);
  assert.match(html, /まだ収益はありません/);
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
