"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runNativePass } = require("../native-pass.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const VALID_KANA = Object.freeze({ family: "サクラ", given: "テスト" });
const BASE_ENV = Object.freeze({ GOG_ACCOUNT: "private@example.com", DAIS_LEGAL_NAME_ROMAJI: "Dais Example", GOG_KEYRING_PASSWORD: "private-keyring", LM_CONNECTOR_TELEGRAM_TARGET: "private-target" });

function writeKanaProfile(home, value = VALID_KANA, mode = 0o600) {
  const file = path.join(home, ".config", "anicca", "job-search", "profile.json");
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const raw = typeof value === "string" ? value : JSON.stringify({ candidate: { name_kana: value } });
  fs.writeFileSync(file, `${raw}\n`, { mode });
  fs.chmodSync(file, mode);
}
test("official foreground entrypoint is directly executable", () => {
  const mode = fs.statSync(path.join(REPO_ROOT, "skills", "connector", "run.sh")).mode;
  assert.notEqual(mode & 0o111, 0);
});

test("official native pass forwards only the bounded minimal wake contract", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-minimal-"));
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      dependencies: Object.freeze({ boundary: "fixture" }),
      async runWake(input, dependencies) {
        observed.push({ input, dependencies });
        return Object.freeze({ status: "circuit_open", safe_reason: "fixture" });
      },
    });

    assert.deepEqual(result, { status: "circuit_open", safe_reason: "fixture" });
    assert.equal(observed.length, 1);
    assert.deepEqual(observed[0].input.providers, ["luma", "connpass", "peatix"]);
    assert.equal(observed[0].input.maxConsecutiveFailures, 3);
    assert.equal(observed[0].input.maxWakeMs, 600_000);
    assert.equal(observed[0].input.maxAgentSteps, 10);
    assert.deepEqual(observed[0].dependencies, { boundary: "fixture" });
    assert.equal(fs.existsSync(path.join(directory, "state", "provider-cursor.json")), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("official native pass builds the production dependency boundary from allowlisted config", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-minimal-"));
  const observed = [];
  try {
    writeKanaProfile(directory);
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      env: {
        HOME: directory,
        GOG_ACCOUNT: "private@example.com",
        DAIS_LEGAL_NAME_ROMAJI: "Dais Example",
        GOG_KEYRING_PASSWORD: "private-keyring",
        LM_CONNECTOR_TELEGRAM_TARGET: "private-target",
        LM_CONNECTOR_TENANT_ID: "dais-local",
        LM_CONNECTOR_CALENDAR_ID: "primary",
      },
      createDependencies(input) {
        observed.push(["factory", input]);
        return Object.freeze({ boundary: "production" });
      },
      async runWake(input, dependencies) {
        observed.push(["wake", input, dependencies]);
        return Object.freeze({ status: "completed_no_effect", safe_reason: "providers_exhausted" });
      },
    });
    assert.deepEqual(result, { status: "completed_no_effect", safe_reason: "providers_exhausted" });
    assert.equal(observed[0][0], "factory");
    assert.equal(observed[0][1].calendarAccount, "private@example.com");
    assert.equal(observed[0][1].gogKeyring, "private-keyring");
    assert.equal(observed[0][1].telegramTarget, "private-target");
    assert.match(observed[0][1].wakeId, /^wake-[0-9a-f]{24}$/);
    assert.equal(observed[0][1].wakeId.includes("native-pass-minimal-owner"), false);
    assert.deepEqual(observed[1][2], { boundary: "production" });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native Peatix profile is frozen at the factory boundary and invalid identity never reaches it", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-profile-"));
  const baseEnv = { ...BASE_ENV, HOME: directory };
  let factoryInput; const wakeInputs = [];
  try {
    writeKanaProfile(directory);
    const result = await runNativePass({ repoRoot: REPO_ROOT, stateDir: path.join(directory, "state"), ownerToken: "native-pass-profile-owner-123456", env: baseEnv, createDependencies(input) { factoryInput = input; return Object.freeze({ boundary: "production" }); }, async runWake(input) { wakeInputs.push(input); return { status: "completed_no_effect" }; } });
    assert.deepEqual(result, { status: "completed_no_effect" });
    assert.deepEqual(factoryInput.peatixAttendeeProfile, { name: "Dais Example", email: "private@example.com", family_name_kana: VALID_KANA.family, given_name_kana: VALID_KANA.given, accept_organizer_privacy: true });
    assert.equal(Object.isFrozen(factoryInput), true);
    assert.equal(Object.isFrozen(factoryInput.peatixAttendeeProfile), true);
    assert.deepEqual(wakeInputs[0].providers, ["luma", "connpass", "peatix"]);
    assert.equal("peatixAttendeeProfile" in wakeInputs[0], false);
    assert.doesNotMatch(JSON.stringify(wakeInputs[0]), /Dais Example|private@example\.com|family_name_kana|given_name_kana|サクラ|テスト/);
    for (const override of [{ DAIS_LEGAL_NAME_ROMAJI: "" }, { DAIS_LEGAL_NAME_ROMAJI: "x".repeat(201) }, { GOG_ACCOUNT: "not-an-email" }]) {
      let called = false;
      await assert.rejects(runNativePass({ repoRoot: REPO_ROOT, stateDir: path.join(directory, "invalid-state"), ownerToken: "native-pass-invalid-owner-123456", env: { ...baseEnv, ...override }, createDependencies() { called = true; return {}; }, async runWake() { return { status: "unexpected" }; } }), /Connector minimal pass unavailable/);
      assert.equal(called, false);
    }
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native config resolves the existing Telegram owner without an inline shell parser", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-owner-"));
  const ownerFile = path.join(directory, ".openclaw", "credentials", "telegram-default-allowFrom.json");
  fs.mkdirSync(path.dirname(ownerFile), { recursive: true, mode: 0o700 });
  fs.writeFileSync(ownerFile, `${JSON.stringify({ allowFrom: ["123456789"] })}\n`, { mode: 0o600 });
  writeKanaProfile(directory);
  let factoryInput;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir: path.join(directory, "state"),
      ownerToken: "native-pass-minimal-owner-123456",
      env: {
        HOME: directory,
        GOG_ACCOUNT: "private@example.com",
        DAIS_LEGAL_NAME_ROMAJI: "Dais Example",
        GOG_KEYRING_PASSWORD: "private-keyring",
      },
      createDependencies(input) {
        factoryInput = input;
        return Object.freeze({ boundary: "production" });
      },
      async runWake() { return { status: "completed_no_effect" }; },
    });
    assert.equal(factoryInput.telegramTarget, "123456789");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native Kana identity fails closed before dependency or wake creation", async () => {
  const invalidCases = [
    ["missing file"], ["permissive mode", VALID_KANA, 0o644], ["invalid JSON", "{"],
    ["missing family", { given: VALID_KANA.given }], ["missing given", { family: VALID_KANA.family }],
    ["empty value", { family: "", given: VALID_KANA.given }], ["Hiragana", { family: "さくら", given: VALID_KANA.given }],
    ["Kanji", { family: "桜", given: VALID_KANA.given }], ["Latin", { family: "Sakura", given: VALID_KANA.given }],
    ["digit", { family: "サク1", given: VALID_KANA.given }], ["punctuation", { family: "サク!", given: VALID_KANA.given }],
    ["control", { family: "サク\nラ", given: VALID_KANA.given }], ["overlength", { family: "サ".repeat(101), given: VALID_KANA.given }],
  ];
  for (const [name, value, mode] of invalidCases) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-kana-invalid-")); let factoryCalls = 0; let wakeCalls = 0;
    try {
      if (value !== undefined) writeKanaProfile(directory, value, mode);
      await assert.rejects(runNativePass({
        repoRoot: REPO_ROOT,
        stateDir: path.join(directory, "state"),
        ownerToken: "native-pass-kana-invalid-owner-123456",
        env: { ...BASE_ENV, HOME: directory },
        createDependencies() { factoryCalls += 1; return {}; },
        async runWake() { wakeCalls += 1; return { status: "unexpected" }; },
      }), /Connector minimal pass unavailable/, name);
      assert.equal(factoryCalls, 0, name); assert.equal(wakeCalls, 0, name);
    } finally {
      fs.rmSync(directory, { recursive: true, force: true });
    }
  }
});
