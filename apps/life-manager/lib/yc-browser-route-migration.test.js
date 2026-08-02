"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const SHIM = path.join(__dirname, "../runtime-assets/apply-to-yc/scripts/apply.sh");
const ROUTE_MANIFEST = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/funder-form-routes.json"), "utf8"));
const PROVIDER_MANIFEST = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/yc-application-provider.json"), "utf8"));

function sha(value) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function resign(receipt) {
  const { migration_receipt_digest: _old, ...core } = receipt;
  return { ...core, migration_receipt_digest: sha(stable(core)) };
}

function migrationModule() {
  return require("./yc-browser-route-migration.js");
}

const ARTIFACT_REFS = Object.freeze({
  checked_in_skill: "repo://apps/life-manager/runtime-assets/apply-to-yc/SKILL.md",
  checked_in_shim: "repo://apps/life-manager/runtime-assets/apply-to-yc/scripts/apply.sh",
  installed_skill: "openclaw://skills/apply-to-yc/SKILL.md",
  installed_shim: "openclaw://skills/apply-to-yc/scripts/apply.sh",
  successor_run: "openclaw://skills/apply-to-funder/scripts/run.sh",
  successor_form_filler: "openclaw://skills/apply-to-funder/scripts/lib/form_filler.sh",
  recovery_inventory: "recovery://apply-to-yc/inventory.json",
});

function artifact(role, body, observedAt = "2026-08-02T01:00:10.000Z") {
  return {
    role,
    ref: ARTIFACT_REFS[role],
    observed_at: observedAt,
    body,
    body_sha256: sha(body),
    body_length: Buffer.byteLength(body),
  };
}

function makeMigrationInput() {
  const skill = "retired compatibility skill\n";
  const shim = "exact daily driver shim\n";
  const recovery = '{"files":4,"verified":true}\n';
  const artifacts = [
    artifact("checked_in_skill", skill),
    artifact("checked_in_shim", shim),
    artifact("installed_skill", skill),
    artifact("installed_shim", shim),
    artifact("successor_run", "successor run\n"),
    artifact("successor_form_filler", "successor form filler\n"),
    artifact("recovery_inventory", recovery),
  ];
  return {
    verified_at: "2026-08-02T01:00:30.000Z",
    route_manifest: structuredClone(ROUTE_MANIFEST),
    provider_manifest: structuredClone(PROVIDER_MANIFEST),
    artifacts,
    browsers: [
      {
        role: "daily_driver",
        endpoint: "http://127.0.0.1:9222",
        pid: 27542,
        preserved_pid: 27542,
        profile_ref: "cloak-profile://daily-driver",
        browser: "Chrome/145.0.7632.109",
        protocol_version: "1.3",
        observed_at: "2026-08-02T01:00:20.000Z",
      },
      {
        role: "gig_driver",
        endpoint: "http://127.0.0.1:9223",
        pid: 707,
        preserved_pid: 707,
        profile_ref: "cloak-profile://gig-daily-driver",
        browser: "Chrome/145.0.7632.109",
        protocol_version: "1.3",
        observed_at: "2026-08-02T01:00:21.000Z",
      },
    ],
    cron: {
      id: "accelerator-application-monthly-1777948324077",
      name: "accelerator-application-monthly",
      enabled: false,
      command: "bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-bash.sh apply-to-funder/scripts/run.sh --funder yc-w26",
      live_readback: true,
      durable_readback: true,
      observed_at: "2026-08-02T01:00:22.000Z",
    },
    deployment: {
      recovery_ref: `~/.openclaw/recovery/apply-to-yc/o1c24-${sha(recovery)}`,
      recovery_inventory_sha256: sha(recovery),
      installed_skill_sha256: sha(skill),
      installed_shim_sha256: sha(shim),
      retired_helpers: ["scripts/fill.js", "scripts/progress.js"],
      installed_readback_exact: true,
      gig_driver_pid_before: 707,
      gig_driver_pid_after: 707,
    },
    effects: {
      browser_launch: 0,
      owned_read_only_navigation: 1,
      form_write: 0,
      file_write: 0,
      save: 0,
      submit: 0,
      browser_close: 0,
      owned_page_close: 1,
      gig_process_signal: 0,
    },
  };
}

function fixture({ successor = "executable" } = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "yc-browser-route-"));
  const successorPath = path.join(
    home,
    ".openclaw/skills/apply-to-funder/scripts/run.sh",
  );
  const receiptPath = path.join(home, "successor-receipt.json");
  if (successor !== "missing") {
    fs.mkdirSync(path.dirname(successorPath), { recursive: true });
    fs.writeFileSync(successorPath, `#!/usr/bin/env bash
set -euo pipefail
jq -n \\
  --arg first "\${1:-}" \\
  --arg second "\${2:-}" \\
  --arg endpoint "\${BU_CDP_URL:-}" \\
  --arg mode "\${MODE:-}" \\
  --arg dry_run "\${DRY_RUN:-}" \\
  '{argv:[$first,$second],BU_CDP_URL:$endpoint,MODE:$mode,DRY_RUN:$dry_run}' > "$RECEIPT_PATH"
`, { mode: successor === "executable" ? 0o755 : 0o644 });
  }
  return {
    cleanup: () => fs.rmSync(home, { recursive: true, force: true }),
    home,
    receiptPath,
  };
}

function runShim(fx, { args = [], env = {} } = {}) {
  return spawnSync("bash", [SHIM, ...args], {
    encoding: "utf8",
    env: {
      PATH: process.env.PATH,
      HOME: fx.home,
      RECEIPT_PATH: fx.receiptPath,
      ...env,
    },
  });
}

test("legacy zero-argument entry delegates exact yc-w26 route to the :9222 successor", () => {
  const fx = fixture();
  try {
    const result = runShim(fx, {
      env: { MODE: "prepare", DRY_RUN: "true" },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(fx.receiptPath, "utf8")), {
      argv: ["--funder", "yc-w26"],
      BU_CDP_URL: "http://127.0.0.1:9222",
      MODE: "prepare",
      DRY_RUN: "true",
    });
  } finally {
    fx.cleanup();
  }
});

test("caller mode and dry-run survive an explicit exact daily-driver endpoint", () => {
  const fx = fixture();
  try {
    const result = runShim(fx, {
      env: {
        BU_CDP_URL: "http://127.0.0.1:9222",
        MODE: "submit",
        DRY_RUN: "true",
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(fx.receiptPath, "utf8")), {
      argv: ["--funder", "yc-w26"],
      BU_CDP_URL: "http://127.0.0.1:9222",
      MODE: "submit",
      DRY_RUN: "true",
    });
  } finally {
    fx.cleanup();
  }
});

test("alternate endpoint and unknown positional arguments fail before successor execution", () => {
  const endpoints = [
    "http://127.0.0.1:9223",
    "http://8.8.8.8:9222",
    "https://127.0.0.1:9222",
    "http://user:pass@127.0.0.1:9222",
    "http://127.0.0.1:9222?x=1",
    "http://127.0.0.1:9222/#fragment",
  ];
  for (const endpoint of endpoints) {
    const fx = fixture();
    try {
      const result = runShim(fx, { env: { BU_CDP_URL: endpoint } });
      assert.notEqual(result.status, 0, endpoint);
      assert.equal(fs.existsSync(fx.receiptPath), false, endpoint);
      assert.match(result.stderr, /daily-driver route refused/i);
      assert.doesNotMatch(result.stderr, /user:pass|8\.8\.8\.8/);
    } finally {
      fx.cleanup();
    }
  }

  const fx = fixture();
  try {
    const result = runShim(fx, { args: ["--legacy-option"] });
    assert.notEqual(result.status, 0);
    assert.equal(fs.existsSync(fx.receiptPath), false);
    assert.match(result.stderr, /zero arguments/i);
  } finally {
    fx.cleanup();
  }
});

test("legacy draft and media overrides fail before successor execution", () => {
  for (const variable of ["DRAFT_ID", "FOUNDER_VIDEO", "DEMO_VIDEO"]) {
    const fx = fixture();
    try {
      const result = runShim(fx, { env: { [variable]: "private-value" } });
      assert.notEqual(result.status, 0, variable);
      assert.equal(fs.existsSync(fx.receiptPath), false, variable);
      assert.match(result.stderr, /legacy content override refused/i);
      assert.doesNotMatch(result.stderr, /private-value/);
    } finally {
      fx.cleanup();
    }
  }
});

test("missing or non-executable successor fails closed without creating state", () => {
  for (const successor of ["missing", "not-executable"]) {
    const fx = fixture({ successor });
    try {
      const result = runShim(fx);
      assert.notEqual(result.status, 0, successor);
      assert.equal(fs.existsSync(fx.receiptPath), false, successor);
      assert.match(result.stderr, /successor unavailable/i);
    } finally {
      fx.cleanup();
    }
  }
});

test("fresh closed observations become a privacy-minimal daily-driver migration receipt", () => {
  const input = makeMigrationInput();
  const before = structuredClone(input);
  const receipt = migrationModule().buildYcBrowserRouteMigrationReceipt(input, {
    now: () => Date.parse("2026-08-02T01:01:00.000Z"),
  });

  assert.deepEqual(input, before);
  assert.equal(receipt.schema_version, 1);
  assert.equal(receipt.route.endpoint, "http://127.0.0.1:9222");
  assert.equal(receipt.route.successor, "apply-to-funder");
  assert.equal(receipt.route.funder_id, "yc-w26");
  assert.equal(receipt.artifacts.length, 7);
  assert.equal(receipt.browsers[0].pid, 27542);
  assert.equal(receipt.browsers[1].pid, 707);
  assert.equal(receipt.cron.enabled, false);
  assert.equal(receipt.deployment.installed_readback_exact, true);
  assert.match(receipt.migration_receipt_digest, /^[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(receipt), true);
  assert.equal(Object.isFrozen(receipt.artifacts[0]), true);
  assert.doesNotMatch(JSON.stringify(receipt), /exact daily driver shim|successor form filler|cookie|credential|websocket|form_answer|process_environment/i);
});

test("artifact inventory, bytes, digest, ref, and installed equality fail closed", () => {
  const { buildYcBrowserRouteMigrationReceipt: build } = migrationModule();
  const now = { now: () => Date.parse("2026-08-02T01:01:00.000Z") };
  const mutations = [
    (x) => x.artifacts.pop(),
    (x) => x.artifacts.push(structuredClone(x.artifacts[0])),
    (x) => { x.artifacts[0].body += "drift"; },
    (x) => { x.artifacts[0].body_length += 1; },
    (x) => { x.artifacts[0].ref = "repo://wrong"; },
    (x) => { x.artifacts[0].unknown = true; },
    (x) => { x.deployment.installed_shim_sha256 = "f".repeat(64); },
    (x) => { x.deployment.recovery_inventory_sha256 = "e".repeat(64); },
  ];
  for (const mutate of mutations) {
    const input = makeMigrationInput();
    mutate(input);
    assert.throws(() => build(input, now), /YC browser route migration/i);
  }
});

test("route and provider identity cannot drift from the current successor", () => {
  const { buildYcBrowserRouteMigrationReceipt: build } = migrationModule();
  const now = { now: () => Date.parse("2026-08-02T01:01:00.000Z") };
  const mutations = [
    (x) => { x.route_manifest.endpoint = "http://127.0.0.1:9223"; },
    (x) => { x.route_manifest.browser_ref = "browser-profile://other"; },
    (x) => { x.route_manifest.shared_context_count = 2; },
    (x) => { x.route_manifest.routes = x.route_manifest.routes.filter(({ route_id }) => route_id !== "yc-application"); },
    (x) => { x.provider_manifest.successor_provider = "legacy"; },
    (x) => { x.provider_manifest.browser_route_id = "other"; },
    (x) => { x.provider_manifest.mode = "submit"; },
    (x) => { x.provider_manifest.submit_operations = 1; },
  ];
  for (const mutate of mutations) {
    const input = makeMigrationInput();
    mutate(input);
    assert.throws(() => build(input, now), /(?:YC browser route migration|funder browser|YC application provider)/i);
  }
});

test("browser owners, disabled cron, backup, and unchanged gig PID are mandatory", () => {
  const { buildYcBrowserRouteMigrationReceipt: build } = migrationModule();
  const now = { now: () => Date.parse("2026-08-02T01:01:00.000Z") };
  const mutations = [
    (x) => { x.browsers[0].endpoint = "http://127.0.0.1:9223"; },
    (x) => { x.browsers[0].profile_ref = "cloak-profile://gig-daily-driver"; },
    (x) => { x.browsers[1].preserved_pid += 1; },
    (x) => { x.browsers[1].protocol_version = "2.0"; },
    (x) => { x.cron.enabled = true; },
    (x) => { x.cron.command = x.cron.command.replace("yc-w26", "other"); },
    (x) => { x.cron.live_readback = false; },
    (x) => { x.cron.durable_readback = false; },
    (x) => { x.deployment.recovery_ref = "~/.openclaw/missing"; },
    (x) => { x.deployment.recovery_ref = `~/.openclaw/skills/apply-to-yc/.o1c24-recovery-${x.deployment.recovery_inventory_sha256}`; },
    (x) => { x.deployment.retired_helpers = ["scripts/fill.js"]; },
    (x) => { x.deployment.gig_driver_pid_after += 1; },
    (x) => { x.deployment.installed_readback_exact = false; },
  ];
  for (const mutate of mutations) {
    const input = makeMigrationInput();
    mutate(input);
    assert.throws(() => build(input, now), /YC browser route migration/i);
  }
});

test("freshness, exact zero effects, schema closure, and receipt digest are enforced", () => {
  const {
    buildYcBrowserRouteMigrationReceipt: build,
    validateYcBrowserRouteMigrationReceiptStructure: validate,
  } = migrationModule();
  const now = { now: () => Date.parse("2026-08-02T01:01:00.000Z") };
  const mutations = [
    (x) => { x.verified_at = "2026-08-02T01:00:30Z"; },
    (x) => { x.artifacts[0].observed_at = "2026-08-02T00:40:00.000Z"; },
    (x) => { x.cron.observed_at = "2026-08-02T01:01:00.000Z"; },
    (x) => { x.effects.browser_launch = 1; },
    (x) => { x.effects.form_write = 1; },
    (x) => { x.effects.file_write = 1; },
    (x) => { x.effects.save = 1; },
    (x) => { x.effects.submit = 1; },
    (x) => { x.effects.browser_close = 1; },
    (x) => { x.effects.gig_process_signal = 1; },
    (x) => { x.effects.owned_read_only_navigation = 0; },
    (x) => { x.unknown = true; },
  ];
  for (const mutate of mutations) {
    const input = makeMigrationInput();
    mutate(input);
    assert.throws(() => build(input, now), /YC browser route migration/i);
  }
  assert.throws(
    () => build(makeMigrationInput(), { now: () => Date.parse("2026-08-02T01:06:00.001Z") }),
    /YC browser route migration/i,
  );

  const receipt = build(makeMigrationInput(), now);
  assert.doesNotThrow(() => validate(receipt));
  assert.throws(
    () => validate({ ...structuredClone(receipt), migration_receipt_digest: "0".repeat(64) }),
    /YC browser route migration/i,
  );
});

test("structural readback rejects correctly re-signed owner, role, and deployment forgeries", () => {
  const {
    buildYcBrowserRouteMigrationReceipt: build,
    validateYcBrowserRouteMigrationReceiptStructure: validate,
  } = migrationModule();
  const receipt = structuredClone(build(makeMigrationInput(), {
    now: () => Date.parse("2026-08-02T01:01:00.000Z"),
  }));
  const forgeries = [
    (x) => { x.browsers[0].endpoint = "http://127.0.0.1:9223"; },
    (x) => { x.browsers[1].role = "daily_driver"; },
    (x) => {
      x.artifacts[1].role = x.artifacts[0].role;
      x.artifacts[1].ref = x.artifacts[0].ref;
    },
    (x) => { x.deployment.installed_readback_exact = false; },
    (x) => { x.deployment.gig_driver_pid_after += 1; },
  ];
  for (const forge of forgeries) {
    const mutated = structuredClone(receipt);
    forge(mutated);
    assert.throws(() => validate(resign(mutated)), /YC browser route migration/i);
  }
});
