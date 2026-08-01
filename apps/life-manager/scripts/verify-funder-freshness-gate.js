#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const { validateFunderAssetFreshnessGate, verifyFunderSubmissionBinding } = require("../lib/funder-asset-freshness.js");

try {
  const [gateFile, specFile, payloadFile] = process.argv.slice(2);
  if (!gateFile) throw new Error("usage: verify-funder-freshness-gate <gate.json> [spec.json payload.json]");
  const gate = validateFunderAssetFreshnessGate(JSON.parse(fs.readFileSync(gateFile, "utf8")));
  if ((specFile || payloadFile) && !(specFile && payloadFile)) throw new Error("spec and payload must be supplied together");
  if (specFile) verifyFunderSubmissionBinding(gate, specFile, payloadFile);
  process.stdout.write(`${gate.gate_id}\tverified\n`);
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
