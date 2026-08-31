"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { readConnectorUserProfile } = require("./connector-user-profile.js");

test("reads the mode-0600 candidate SSOT without creating a derived copy", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-user-profile-"));
  const file = path.join(root, "profile.json");
  fs.writeFileSync(file, JSON.stringify({
    candidate: { name: "Dais", date_of_birth: "2002-01-30", phone: "+81 90 0000 0000" },
    facts: [{ id: "goal", claim: "Building Mr.bot", evidence: "owner profile" }],
  }), { mode: 0o600 });
  try {
    const profile = readConnectorUserProfile({ path: file });
    assert.equal(profile.candidate.date_of_birth, "2002-01-30");
    assert.equal(profile.facts[0].claim, "Building Mr.bot");
    assert.equal(Object.isFrozen(profile.candidate), true);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("rejects permissive files and secret-bearing keys", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-user-profile-"));
  try {
    for (const [name, value, mode] of [
      ["permissive.json", { candidate: { name: "Dais" } }, 0o644],
      ["secret.json", { candidate: { name: "Dais" }, api_key: "not-allowed" }, 0o600],
    ]) {
      const file = path.join(root, name);
      fs.writeFileSync(file, JSON.stringify(value), { mode });
      assert.throws(() => readConnectorUserProfile({ path: file }), /unavailable/);
    }
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
