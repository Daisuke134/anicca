// build-commands.js — generate the `openclaw cron` registration commands from crons.json.
// Extracted into a PURE, testable function (the double-JSON.stringify round-trip is the most
// error-prone part, so it is unit-tested directly — see crons.test.js).
//
// command-cron flags used (VERIFIED present in openclaw@latest 2026.6.10 via
// `npx -y openclaw@latest cron create --help`): --command-argv (JSON argv, no shell parsing),
// --command-cwd, --name, --description. NO --message/--model/--agent → deterministic, ZERO model tokens.
// (Local openclaw 2026.6.1 LACKS command-cron; the product gateway runs latest — live reg = B4.)
"use strict";

// PURE: jobs[] + cwd → array of {rm, create} shell command strings (idempotent: rm before create).
// The inner argv is JSON.stringify'd ONCE to a JSON array string, then JSON.stringify'd AGAIN to a
// shell-safe double-quoted token so bash hands openclaw the literal JSON array. Round-trip:
//   commandArgv ["node","x.js"] -> '["node","x.js"]' -> "\"[\\\"node\\\",\\\"x.js\\\"]\""
// which bash unquotes back to the literal  ["node","x.js"]  that openclaw parses.
function buildRegisterCommands(jobs, cwd) {
  if (!Array.isArray(jobs)) throw new TypeError("jobs must be an array");
  if (!cwd || typeof cwd !== "string") throw new TypeError("cwd must be a non-empty string");
  return jobs.map((j) => {
    const argv = JSON.stringify(j.commandArgv); // -> '["node","skill-life-manager/scripts/tick.js"]'
    const create =
      "openclaw cron create " + JSON.stringify(j.cron) +
      " --name " + JSON.stringify(j.name) +
      " --command-argv " + JSON.stringify(argv) +
      " --command-cwd " + JSON.stringify(cwd) +
      " --description " + JSON.stringify(j.description);
    const rm = "openclaw cron rm " + JSON.stringify(j.name) + " >/dev/null 2>&1 || true";
    return { name: j.name, rm, create };
  });
}

module.exports = { buildRegisterCommands };

// CLI: `node build-commands.js <cwd>` emits the rm+create lines (consumed by register-crons.sh | bash -e).
if (require.main === module) {
  const fs = require("node:fs");
  const path = require("node:path");
  const cwd = process.argv[2];
  if (!cwd) { console.error("usage: node build-commands.js <gateway-life-call-dir>"); process.exit(1); }
  const { jobs } = JSON.parse(fs.readFileSync(path.join(__dirname, "crons.json"), "utf8"));
  for (const c of buildRegisterCommands(jobs, cwd)) { console.log(c.rm); console.log(c.create); }
}
