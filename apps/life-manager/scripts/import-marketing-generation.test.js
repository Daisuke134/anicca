"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { importMarketingGeneration } = require("./import-marketing-generation.js");

test("one-time generation import copies every legacy asset into Life Manager object ownership", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-generation-import-"));
  const dataDir = path.join(root, "runtime");
  const flags = ["bank", "call-audio", "stock", "telegram-proof", "whisper-ass"];
  const args = ["--data-dir", dataDir, "--tenant", "tenant-a"];
  for (const flag of flags) {
    const source = path.join(root, flag);
    fs.writeFileSync(source, `fixture-${flag}`);
    args.push(`--${flag}`, source);
  }

  const imported = importMarketingGeneration(args);
  assert.equal(imported.tenant_id, "tenant-a");
  for (const key of [
    "bank_ref",
    "call_audio_ref",
    "stock_ref",
    "telegram_proof_ref",
    "whisper_ass_ref",
  ]) {
    assert.match(imported[key], /^object:\/\/sha256\/[0-9a-f]{64}$/);
    const digest = imported[key].split("/").pop();
    const stored = path.join(dataDir, "objects", "sha256", digest);
    assert.equal(fs.statSync(stored).mode & 0o777, 0o600);
  }
  assert.doesNotMatch(JSON.stringify(imported), new RegExp(root.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});
