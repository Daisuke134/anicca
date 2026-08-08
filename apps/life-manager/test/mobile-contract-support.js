"use strict";

const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const CONTRACT_DIR = path.join(__dirname, "../contracts/mobile-v1");
const GENERATED_SCRIPT_RE = /[\u3040-\u30ff\u3400-\u9fff]/u;
const ISO_INSTANT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/u;
const OPAQUE_CURSOR_RE = /^cursor:v1:[A-Za-z0-9_-]{8,}$/u;
const OPAQUE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$/u;
const FORBIDDEN_AUTHORITY_KEYS = new Set(["uid", "userId", "tenantId", "ownerId", "scopeUid"]);

function fixture(name) {
  const file = path.join(CONTRACT_DIR, name);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function fixtureNames() {
  return fs.readdirSync(CONTRACT_DIR).filter((name) => name.endsWith(".json")).sort();
}

function assertIso(value, label) {
  assert.equal(typeof value, "string", `${label} must be a string`);
  assert.match(value, ISO_INSTANT_RE, `${label} must be a UTC ISO-8601 instant`);
  assert.equal(Number.isNaN(Date.parse(value)), false, `${label} must parse as a date`);
}

function assertOpaque(value, label, pattern = OPAQUE_ID_RE) {
  assert.equal(typeof value, "string", `${label} must be a string`);
  assert.match(value, pattern, `${label} must be opaque and bounded`);
}

function walk(value, visitor, location = "$") {
  visitor(value, location);
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, visitor, `${location}[${index}]`));
    return;
  }
  if (value && typeof value === "object") {
    Object.entries(value).forEach(([key, child]) => walk(child, visitor, `${location}.${key}`));
  }
}

function assertNoClientAuthority(value, label) {
  walk(value, (current, location) => {
    if (!current || typeof current !== "object" || Array.isArray(current)) return;
    for (const key of Object.keys(current)) {
      assert.equal(FORBIDDEN_AUTHORITY_KEYS.has(key), false, `${label} exposes client authority field ${location}.${key}`);
    }
  });
}

function assertGeneratedEnglish(value, label) {
  function visit(current, location, userContent) {
    if (typeof current === "string") {
      assert.equal(userContent || !GENERATED_SCRIPT_RE.test(current), true, `${label} has non-English generated text at ${location}`);
      return;
    }
    if (Array.isArray(current)) {
      current.forEach((item, index) => visit(item, `${location}[${index}]`, userContent));
      return;
    }
    if (!current || typeof current !== "object") return;
    for (const [key, child] of Object.entries(current)) {
      visit(child, `${location}.${key}`, userContent || key === "userContent");
    }
  }
  visit(value, "$", false);
}

function assertAllowedKeys(value, allowed, label) {
  assert.deepEqual(Object.keys(value).sort(), [...allowed].sort(), `${label} keys changed`);
}

module.exports = {
  CONTRACT_DIR,
  GENERATED_SCRIPT_RE,
  ISO_INSTANT_RE,
  OPAQUE_CURSOR_RE,
  fixture,
  fixtureNames,
  assertIso,
  assertOpaque,
  assertNoClientAuthority,
  assertGeneratedEnglish,
  assertAllowedKeys,
};
