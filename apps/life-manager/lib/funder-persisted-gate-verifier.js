"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { freezeVerifiedFunderSubmission } = require("./funder-asset-freshness.js");

async function verifyPersistedFunderGates(dayGate, freshnessGate, submission) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "funder-gates-"));
  try {
    if (!submission || typeof submission !== "object") return false;
    const frozenSubmission = freezeVerifiedFunderSubmission(freshnessGate, submission.specPath, submission.payloadPath, path.join(temp, "submission"));
    const day = path.join(temp, "day.json"), fresh = path.join(temp, "fresh.json");
    fs.writeFileSync(day, JSON.stringify(dayGate), { mode: 0o600 });
    fs.writeFileSync(fresh, JSON.stringify(freshnessGate), { mode: 0o600 });
    execFileSync("bash", [path.join(__dirname, "../scripts/verify-funder-gates-railway.sh"), day, fresh], { stdio: "ignore", timeout: 60_000 });
    return Object.freeze({ submission: frozenSubmission, cleanup: () => fs.rmSync(temp, { recursive: true, force: true }) });
  } catch {
    fs.rmSync(temp, { recursive: true, force: true });
    return false;
  }
}
module.exports = { verifyPersistedFunderGates };
