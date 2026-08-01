"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync, spawnSync } = require("node:child_process");

const SCRIPT = path.resolve(__dirname, "../../../skills/self/retire-legacy-connector-launchd.sh");
const LABELS = [
  "ai.anicca.connector-fill-gaps",
  "ai.anicca.connector-daily-report",
];

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-retire-"));
  const agents = path.join(root, "LaunchAgents");
  const archive = path.join(root, "retired");
  const calls = path.join(root, "launchctl.calls");
  const fake = path.join(root, "launchctl");
  fs.mkdirSync(agents);
  for (const label of LABELS) {
    fs.writeFileSync(path.join(agents, `${label}.plist`), `plist:${label}\n`, { mode: 0o600 });
  }
  fs.writeFileSync(path.join(agents, "ai.anicca.outbound-runtime-healthcheck.plist"), "guardian\n");
  fs.writeFileSync(fake, `#!/bin/bash\nprintf '%s\\n' "$*" >> ${JSON.stringify(calls)}\nexit 0\n`, { mode: 0o700 });
  return {
    root, agents, archive, calls, fake,
    env: {
      ...process.env,
      LM_LAUNCH_AGENTS_DIR: agents,
      LM_RETIRED_LAUNCHD_DIR: archive,
      LM_LAUNCHCTL_BIN: fake,
      LM_LAUNCH_DOMAIN: "gui/501",
    },
  };
}

test("retires only the two fixed legacy Connector jobs with a recoverable manifest", () => {
  const fx = fixture();
  const output = execFileSync("/bin/bash", [SCRIPT], { env: fx.env, encoding: "utf8" });
  const result = JSON.parse(output);
  assert.equal(result.status, "retired");
  assert.deepEqual(result.labels.map((row) => row.label), LABELS);
  for (const label of LABELS) {
    assert.equal(fs.existsSync(path.join(fx.agents, `${label}.plist`)), false);
    assert.equal(fs.existsSync(path.join(fx.archive, `${label}.plist`)), true);
  }
  assert.equal(fs.readFileSync(
    path.join(fx.agents, "ai.anicca.outbound-runtime-healthcheck.plist"), "utf8",
  ), "guardian\n");
  const manifest = JSON.parse(fs.readFileSync(path.join(fx.archive, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.labels.map((row) => row.label), LABELS);
  assert.equal(manifest.labels.every((row) => /^[a-f0-9]{64}$/.test(row.sha256)), true);
  assert.match(manifest.rollback, /launchctl enable/);
  const calls = fs.readFileSync(fx.calls, "utf8");
  for (const label of LABELS) {
    assert.match(calls, new RegExp(`bootout gui/501/${label.replaceAll(".", "\\.")}`));
    assert.match(calls, new RegExp(`disable gui/501/${label.replaceAll(".", "\\.")}`));
  }
});

test("a second retirement is idempotent and never overwrites the archive", () => {
  const fx = fixture();
  execFileSync("/bin/bash", [SCRIPT], { env: fx.env });
  const before = execFileSync("shasum", ["-a", "256", path.join(fx.archive, `${LABELS[0]}.plist`)], { encoding: "utf8" });
  const result = JSON.parse(execFileSync("/bin/bash", [SCRIPT], { env: fx.env, encoding: "utf8" }));
  const after = execFileSync("shasum", ["-a", "256", path.join(fx.archive, `${LABELS[0]}.plist`)], { encoding: "utf8" });
  assert.equal(result.status, "already_retired");
  assert.equal(after, before);
});

test("refuses broad or relative filesystem targets before launchctl", () => {
  const fx = fixture();
  for (const [agents, archive] of [["/", fx.archive], ["relative", fx.archive], [fx.agents, "/"]]) {
    const result = spawnSync("/bin/bash", [SCRIPT], {
      env: { ...fx.env, LM_LAUNCH_AGENTS_DIR: agents, LM_RETIRED_LAUNCHD_DIR: archive },
      encoding: "utf8",
    });
    assert.notEqual(result.status, 0);
  }
  assert.equal(fs.existsSync(fx.calls), false);
});

test("secures verified fallback plists before launchctl when live files are already absent", () => {
  const fx = fixture();
  for (const label of LABELS) {
    fs.unlinkSync(path.join(fx.agents, `${label}.plist`));
  }
  const result = JSON.parse(execFileSync("/bin/bash", [SCRIPT], {
    env: fx.env,
    encoding: "utf8",
  }));
  assert.equal(result.status, "retired");
  for (const label of LABELS) {
    assert.equal(fs.existsSync(path.join(fx.archive, `${label}.plist`)), true);
  }
  assert.match(fs.readFileSync(fx.calls, "utf8"), /^print /m);
});
