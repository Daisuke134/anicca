"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildRecipes, SAFE_TIMELINE_SENTENCE } = require("../eval/panel-privacy-contract.js");

let displayPolicy = {};
let presentation = {};
try {
  displayPolicy = require("./panel-display-policy.js");
  presentation = require("./panel-presentation.js");
} catch (error) {
  if (error.code !== "MODULE_NOT_FOUND") throw error;
}

const containsSensitiveDisplayValue = displayPolicy.containsSensitiveDisplayValue || (() => false);
const safeHttpsLink = displayPolicy.safeHttpsLink || ((value) => value);
const presentPanelSection = presentation.presentPanelSection || ((_section, candidate) => candidate);

test("PANEL-8h display policy detects all 19 provider and generic credential shapes", () => {
  for (const recipe of buildRecipes()) {
    assert.equal(
      containsSensitiveDisplayValue({ nested: ["safe", recipe.value] }),
      true,
      recipe.id,
    );
  }
  assert.equal(containsSensitiveDisplayValue({ nested: ["予定", "Life Manager user"] }), false);
});

test("PANEL-8h display policy only emits query-free non-credential HTTPS links", () => {
  assert.equal(safeHttpsLink("https://ledger.example/tx/abc"), "https://ledger.example/tx/abc");
  assert.equal(safeHttpsLink("https://ledger.example/tx/abc?token=visible"), null);
  assert.equal(safeHttpsLink("http://ledger.example/tx/abc"), null);
  for (const recipe of buildRecipes()) {
    assert.equal(safeHttpsLink(`https://ledger.example/tx/${recipe.value}`), null, recipe.id);
  }
});

test("PANEL-8h timeline and ledger presentation projects hostile source records", () => {
  for (const recipe of buildRecipes()) {
    const timeline = presentPanelSection("timeline", {
      date: "2026-07-21",
      timezone: "Asia/Tokyo",
      events: [{
        summary: recipe.value,
        location: recipe.value,
        start_at: "2026-07-21T14:00:00.000Z",
        interpretation: { decision: "offline" },
      }],
      calls: [],
    });
    assert.equal(timeline.items[0].sentence, SAFE_TIMELINE_SENTENCE, recipe.id);
    assert.equal(JSON.stringify(timeline).includes(recipe.value), false, recipe.id);

    const ledger = presentPanelSection("ledger", {
      apiCostEntries: [],
      financialEntries: [{
        ts: "2026-07-21T11:00:00.000Z",
        amount: "10.00",
        currency: "USD",
        on_chain_url: recipe.value,
        provider_payload: recipe.value,
      }],
    });
    assert.equal(ledger.financial.items[0].link, null, recipe.id);
    assert.equal(JSON.stringify(ledger).includes(recipe.value), false, recipe.id);
  }
});

test("PANEL-8h closed DTO validation accepts null call language and rejects malformed sections", () => {
  const settings = presentPanelSection("settings", {
    call_language: null,
    call_schedule: {
      time_zone: "Asia/Tokyo",
      minutes_before: [10, 5],
      wake_policy: "travel-only",
    },
    connections: { calendar: false, gmail: false, telegram: true },
  });
  assert.equal(settings.call_language, null);

  for (const [section, candidate] of [
    ["scores", { organs: {} }],
    ["gates", { gates: [{ id: "location", unlocked: "yes" }] }],
    ["settings", { call_language: "fr" }],
    ["control-center", { identity: { name: 7 } }],
  ]) {
    assert.throws(
      () => presentPanelSection(section, candidate),
      (error) => error && error.code === "section_unavailable" && error.section === section,
      section,
    );
  }
});
