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

test("LM-33c: panel is read-only and fetches only the five same-origin read APIs", () => {
  assert.equal(typeof renderPanelPage, "function");
  const html = renderPanelPage();
  assert.doesNotMatch(html, /<(?:form|input|button|select|textarea)\b/i);
  assert.match(html, /credentials:\s*["']same-origin["']/);
  for (const endpoint of ["timeline", "scores", "ledger", "gates", "settings"]) {
    assert.match(html, new RegExp(`/api/panel/${endpoint}`));
  }
  assert.match(html, /準備中/);
  assert.match(html, /まだ収益はありません/);
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
