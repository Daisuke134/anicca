"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const TOKEN = /^[a-z][a-z0-9_-]{1,63}$/;
const VERSION = /^[a-z][a-z0-9_-]{1,127}$/;
const CONTROL = /^[a-z][a-z0-9_-]{1,63}$/;
const EXPECTED_EFFECT = "registered_or_pending";
const ALLOWED = new Map([
  ["observe", new Set(["ax_inspect", "dom_inspect", "parent_readback"])],
  ["fill", new Set(["ax_fill", "dom_fill", "ax_check", "ax_select"])],
  ["submit", new Set(["ax_click", "coordinate_click", "keyboard_submit"])],
  ["readback", new Set(["parent_readback", "ax_inspect", "dom_inspect"])],
]);

function invalid() {
  throw new Error("Connector action cache invalid");
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function exactInstant(value) {
  const instant = String(value || "");
  if (!Number.isFinite(Date.parse(instant)) || new Date(Date.parse(instant)).toISOString() !== instant) invalid();
  return instant;
}

function key(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const provider = String(input.provider || "");
  const workflowVersion = String(input.workflowVersion || "");
  const pageState = String(input.pageState || "");
  const expectedEffect = String(input.expectedEffect || "");
  if (
    !TOKEN.test(provider) || !VERSION.test(workflowVersion) || !TOKEN.test(pageState)
    || expectedEffect !== EXPECTED_EFFECT
  ) invalid();
  return Object.freeze({ provider, workflowVersion, pageState, expectedEffect });
}

function action(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const purpose = String(input.purpose || "");
  const method = String(input.method || "");
  const control = String(input.control || "");
  if (!ALLOWED.has(purpose) || !ALLOWED.get(purpose).has(method) || !CONTROL.test(control)) invalid();
  return Object.freeze({ purpose, method, control });
}

function actions(input) {
  if (!Array.isArray(input) || input.length < 1 || input.length > 10) invalid();
  return Object.freeze(input.map(action));
}

function sameKey(entry, expected) {
  return entry.provider === expected.provider
    && entry.workflow_version === expected.workflowVersion
    && entry.page_state === expected.pageState
    && entry.expected_effect === expected.expectedEffect;
}

function freezeEntry(entry) {
  return Object.freeze({
    cache_entry_id: entry.cache_entry_id,
    provider: entry.provider,
    workflow_version: entry.workflow_version,
    page_state: entry.page_state,
    expected_effect: entry.expected_effect,
    actions: Object.freeze(entry.actions.map((row) => Object.freeze({ ...row }))),
    updated_at: entry.updated_at,
  });
}

function createConnectorActionCache(options = {}) {
  const file = path.resolve(String(options.path || ""));
  if (!path.isAbsolute(file) || file === path.parse(file).root) invalid();

  function readDocument() {
    let source;
    try {
      const stat = fs.statSync(file);
      if (stat.size > 1_000_000) invalid();
      source = fs.readFileSync(file, "utf8");
    } catch (error) {
      if (error && error.code === "ENOENT") return { schema_version: 1, entries: [] };
      throw error;
    }
    let document;
    try { document = JSON.parse(source); } catch { invalid(); }
    if (
      !document || typeof document !== "object" || Array.isArray(document)
      || document.schema_version !== 1 || !Array.isArray(document.entries)
      || document.entries.length > 100
    ) invalid();
    const entries = document.entries.map((entry) => {
      const expected = key({
        provider: entry.provider,
        workflowVersion: entry.workflow_version,
        pageState: entry.page_state,
        expectedEffect: entry.expected_effect,
      });
      const normalizedActions = actions(entry.actions);
      const updatedAt = exactInstant(entry.updated_at);
      const core = {
        provider: expected.provider,
        workflow_version: expected.workflowVersion,
        page_state: expected.pageState,
        expected_effect: expected.expectedEffect,
        actions: normalizedActions,
        updated_at: updatedAt,
      };
      const id = `connector-action-cache:${createHash("sha256").update(stableJson(core)).digest("hex")}`;
      if (entry.cache_entry_id !== id) invalid();
      return freezeEntry({ cache_entry_id: id, ...core });
    });
    return { schema_version: 1, entries };
  }

  function writeDocument(document) {
    const parent = path.dirname(file);
    fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
    const temporary = path.join(parent, `.${path.basename(file)}.${process.pid}.tmp`);
    fs.writeFileSync(temporary, `${JSON.stringify(document)}\n`, { encoding: "utf8", mode: 0o600 });
    fs.renameSync(temporary, file);
    fs.chmodSync(file, 0o600);
  }

  function read(input) {
    const expected = key(input);
    const entry = readDocument().entries.find((candidate) => sameKey(candidate, expected));
    return entry ? freezeEntry(entry) : null;
  }

  function saveVerifiedRepair(input = {}) {
    const expected = key(input);
    if (!input.providerState || !["registered", "pending"].includes(input.providerState.status)) invalid();
    const normalizedActions = actions(input.actions);
    const updatedAt = exactInstant(input.observedAt);
    const core = {
      provider: expected.provider,
      workflow_version: expected.workflowVersion,
      page_state: expected.pageState,
      expected_effect: expected.expectedEffect,
      actions: normalizedActions,
      updated_at: updatedAt,
    };
    const cacheEntryId = `connector-action-cache:${createHash("sha256").update(stableJson(core)).digest("hex")}`;
    const entry = freezeEntry({ cache_entry_id: cacheEntryId, ...core });
    const document = readDocument();
    const retained = document.entries.filter((candidate) => !sameKey(candidate, expected));
    retained.push(entry);
    retained.sort((left, right) => (
      left.provider.localeCompare(right.provider)
      || left.workflow_version.localeCompare(right.workflow_version)
      || left.page_state.localeCompare(right.page_state)
    ));
    writeDocument({ schema_version: 1, entries: retained });
    return Object.freeze({ status: "saved", cache_entry_id: cacheEntryId });
  }

  async function replay(input = {}) {
    if (typeof input.performAction !== "function" || typeof input.readExpectedState !== "function") invalid();
    if (!input.page || typeof input.page !== "object") invalid();
    const entry = read(input);
    if (!entry) return Object.freeze({ status: "cache_miss" });
    for (const cachedAction of entry.actions) {
      let effect;
      try { effect = await input.performAction({ page: input.page, action: cachedAction }); }
      catch { return Object.freeze({ status: "failed", safe_reason: "cached_action_failed" }); }
      if (!effect || effect.status !== "success") {
        return Object.freeze({ status: "failed", safe_reason: "cached_action_failed" });
      }
    }
    const providerState = await input.readExpectedState({ page: input.page });
    if (!providerState || !["registered", "pending"].includes(providerState.status)) {
      return Object.freeze({ status: "failed", safe_reason: "cached_readback_failed" });
    }
    return Object.freeze({
      status: "completed",
      provider_state: Object.freeze({ ...providerState }),
      actions: entry.actions,
    });
  }

  return Object.freeze({ read, replay, saveVerifiedRepair });
}

module.exports = { createConnectorActionCache };
