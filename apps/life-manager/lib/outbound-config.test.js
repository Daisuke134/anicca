// lib/outbound-config.test.js — hand-written pack config validation (no new dependency).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const {
  PACK_DIR,
  validatePackConfig,
  loadPackConfig,
  isDenied,
  packDir,
} = require("./outbound-config.js");

function baseConfig(overrides = {}) {
  return {
    pack: "events",
    enabled: true,
    daily_cap: 5,
    denylist: [],
    segments: ["luma-lt-en"],
    ...overrides,
  };
}

test("a well-formed pack config validates and is returned frozen", () => {
  const config = validatePackConfig(baseConfig());
  assert.equal(config.pack, "events");
  assert.equal(Object.isFrozen(config), true);
  assert.throws(() => { config.daily_cap = 999; }, TypeError);
});

test("every required field is enforced by name", () => {
  for (const field of ["pack", "enabled", "daily_cap", "denylist", "segments"]) {
    const broken = baseConfig();
    delete broken[field];
    assert.throws(
      () => validatePackConfig(broken),
      new RegExp(`outbound pack config is missing ${field}`),
      `${field} was not enforced`,
    );
  }
});

test("field types are enforced, not coerced", () => {
  assert.throws(() => validatePackConfig(baseConfig({ enabled: "true" })), /enabled must be a boolean/);
  assert.throws(() => validatePackConfig(baseConfig({ daily_cap: "5" })), /daily_cap must be a positive integer/);
  assert.throws(() => validatePackConfig(baseConfig({ daily_cap: 0 })), /daily_cap must be a positive integer/);
  assert.throws(() => validatePackConfig(baseConfig({ denylist: "MUFG" })), /denylist must be an array of strings/);
  assert.throws(() => validatePackConfig(baseConfig({ denylist: [3] })), /denylist must be an array of strings/);
  assert.throws(() => validatePackConfig(baseConfig({ segments: [] })), /segments must be a non-empty array of strings/);
});

test("only the three known packs are accepted", () => {
  assert.throws(() => validatePackConfig(baseConfig({ pack: "connpass" })), /pack must be one of events, funders, jobs/);
});

test("isDenied matches denylist substrings case-insensitively across the whole candidate", () => {
  const config = validatePackConfig(baseConfig({
    pack: "funders",
    denylist: ["三菱UFJ", "MUFG", "MUCAP"],
  }));
  assert.equal(isDenied(config, { name: "MUFG Capital", url: "https://example.com" }), "MUFG");
  assert.equal(isDenied(config, { name: "三菱UFJキャピタル" }), "三菱UFJ");
  assert.equal(isDenied(config, { url: "https://mucap.co.jp/apply" }), "MUCAP");
  assert.equal(isDenied(config, { name: "Antler Japan" }), null);
  assert.equal(isDenied(config, "MUFG Innovation Partners"), "MUFG");
});

test("an empty denylist denies nothing", () => {
  const config = validatePackConfig(baseConfig());
  assert.equal(isDenied(config, { name: "Anything At All" }), null);
});

test("the three shipped pack configs on disk are valid", () => {
  for (const pack of ["events", "funders", "jobs"]) {
    const config = loadPackConfig(pack);
    assert.equal(config.pack, pack);
    assert.ok(config.segments.length > 0);
  }
});

test("the funders pack denies MUFG operators and CVCs per decision D3", () => {
  const funders = loadPackConfig("funders");
  for (const needle of ["三菱UFJ", "MUFG", "MUCAP", "MUIP", "Mitsubishi UFJ"]) {
    assert.ok(funders.denylist.includes(needle), `funders denylist is missing ${needle}`);
  }
  assert.equal(isDenied(funders, { name: "MUFG Innovation Partners" }), "MUFG");
  assert.equal(isDenied(funders, { name: "Mitsubishi UFJ Capital" }), "Mitsubishi UFJ");
  assert.equal(isDenied(funders, { name: "三菱UFJキャピタル" }), "三菱UFJ");
});

test("decision D3 is recorded in the funders config: an LP-only fund is NOT excluded", () => {
  const funders = loadPackConfig("funders");
  assert.match(funders.denylist_note, /LP/);
  // A fund whose only tie is an MUFG LP has no MUFG substring in its own name, so it passes.
  assert.equal(isDenied(funders, { name: "Genesia Ventures", url: "https://genesiaventures.com" }), null);
});

test("packDir points at skills/life-manager/outbound/<pack> inside the repo", () => {
  assert.equal(packDir("events"), path.join(PACK_DIR, "events"));
  assert.match(PACK_DIR, /skills\/life-manager\/outbound$/);
});

test("loading an unknown pack fails loudly", () => {
  assert.throws(() => loadPackConfig("connpass"), /pack must be one of events, funders, jobs/);
});
