"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runNativePass } = require("../native-pass.js");
const {
  acquireLock,
  heartbeat,
  readHealth,
  releaseLock,
} = require("../lib/native-state.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const HEALTHCHECK = path.join(REPO_ROOT, "skills/connector/healthcheck.sh");
const RENDERER = path.join(REPO_ROOT, "skills/connector/render-launchd.sh");

const OWNER_TOKEN = "native-pass-test-owner-123456";

function temporaryDirectory() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-entrypoint-"));
}

test("native-pass invokes the direct runtime and keeps open coverage as a continuation", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async (input) => {
        observed.push(input);
        return {
        status: "incomplete",
        coverage: { counts: { open: 21 } },
        selection: {
          inventory_event_count: 27,
          calendar_gate_event_count: 12,
          calendar_eligible_count: 4,
          luna_ranked_count: 4,
          spend_ordered_count: 3,
          unsuppressed_count: 2,
          write_attempt_count: 0,
        },
        continuation: { status: "continue" },
        };
      },
    });

    assert.equal(result.exitCode, 1);
    assert.equal(observed.length, 1);
    assert.equal(observed[0].config.tenantId, "dais-local");
    assert.deepEqual(JSON.parse(fs.readFileSync(
      path.join(stateDir, "continuation.json"), "utf8",
    )), {
      reason: "runtime_incomplete",
      status: "pending",
    });
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "last-result.json"), "utf8")), {
      status: "incomplete",
      coverage_counts: { open: 21, covered_existing: 0, covered_new: 0, unavailable: 0 },
      selection: {
        inventory_event_count: 27,
        calendar_gate_event_count: 12,
        calendar_eligible_count: 4,
        luna_ranked_count: 4,
        spend_ordered_count: 3,
        unsuppressed_count: 2,
        write_attempt_count: 0,
      },
      write: null,
    });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass durably reports every incomplete wake and stores the positive Telegram receipt", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const sent = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      observationContext: {
        wakeId: "connector-wake-outbox-1",
        runId: "connector-run-outbox-1",
        observedAt: "2026-08-06T15:00:00.000Z",
      },
      config: { tenantId: "dais-local", telegramTarget: "opaque-target" },
      sendWakeReport: async (message, delivery) => {
        sent.push({ message, delivery });
        return { messageId: 9001 };
      },
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 18 } },
        selection: {
          inventory_event_count: 27, calendar_gate_event_count: 0,
          calendar_eligible_count: 0, luna_ranked_count: 0,
          spend_ordered_count: 0, unsuppressed_count: 0, write_attempt_count: 0,
        },
        continuation: { status: "continue" },
      }),
    });

    assert.equal(result.status, "incomplete");
    assert.equal(sent.length, 1);
    assert.match(sent[0].message, /Connector.*継続/);
    assert.equal(sent[0].delivery.telegramTarget, "opaque-target");
    assert.deepEqual(
      fs.readFileSync(path.join(stateDir, "wake-report-outbox.jsonl"), "utf8").trim().split("\n").map(JSON.parse),
      [{
        schema_version: 1,
        wake_id: "connector-wake-outbox-1",
        report_kind: "continuing",
        safe_reason: "runtime_incomplete",
        cursor: "provider:none",
        open_count: 18,
        attempt_count: 0,
        created_at: "2026-08-06T15:00:00.000Z",
      }],
    );
    assert.deepEqual(
      fs.readFileSync(path.join(stateDir, "wake-report-deliveries.jsonl"), "utf8").trim().split("\n").map(JSON.parse),
      [{
        schema_version: 1,
        wake_id: "connector-wake-outbox-1",
        telegram_provider_id: "9001",
        delivered_at: "2026-08-06T15:00:00.000Z",
      }],
    );
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass records runtime completion and failure through the same observer replay", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const observationContext = {
    wakeId: "connector-wake-200",
    runId: "connector-run-200",
    ownerGeneration: 1,
    codeCommit: "27506a703",
    cursor: "connpass:2026-08-07:0:2",
    observedAt: "2026-08-06T13:36:51.928Z",
  };
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" }, observationContext,
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 18 } },
        selection: {
          inventory_event_count: 27, calendar_gate_event_count: 0,
          calendar_eligible_count: 0, luna_ranked_count: 0,
          spend_ordered_count: 0, unsuppressed_count: 0, write_attempt_count: 0,
        },
        continuation: { status: "continue" },
      }),
    });
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      observationContext: { ...observationContext, wakeId: "connector-wake-201" },
      runRuntime: async () => {
        const error = new Error("private person@example.com https://example.com/event/1");
        error.code = "CONNECTOR_NATIVE_PROVIDER_DISCOVERY_FAILED";
        throw error;
      },
    });
    const rows = fs.readFileSync(path.join(stateDir, "observer-replay.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.equal(rows.length, 2);
    assert.deepEqual(rows.map((row) => row.observed_effect), ["success", "tool_failure"]);
    assert.equal(JSON.stringify(rows).includes("person@example.com"), false);
    assert.equal(JSON.stringify(rows).includes("example.com"), false);
    const incidents = fs.readFileSync(path.join(stateDir, "observer-incidents.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.equal(incidents.length, 1);
    assert.equal(incidents[0].observed_effect, "tool_failure");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass classifies a provider deadline as an observer timeout", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local", now: "2026-08-06T13:36:51.928Z" },
      runRuntime: async () => {
        const error = new Error("deadline");
        error.code = "CONNECTOR_NATIVE_PROVIDER_DISCOVERY_TIMEOUT_FAILED";
        throw error;
      },
    });
    const row = JSON.parse(fs.readFileSync(path.join(stateDir, "observer-replay.jsonl"), "utf8").trim());
    assert.equal(row.observed_effect, "timeout");
    assert.equal(row.incident_class, "timeout");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass persists one privacy-safe self-heal incident when suppression prevents every Apply attempt", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "candidate-attempts.jsonl"), `${JSON.stringify({
    event_ref: "luma-event://event/private-event-ref",
    outcome: "known_no_effect",
    safe_reason: "LUMA_FORM_INPUT_REQUIRED",
    observed_at: "2026-08-06T01:05:01.993Z",
    retry_after: null,
  })}\n`, { mode: 0o600 });
  const runtimeResult = {
    status: "incomplete",
    coverage: { counts: { open: 19, covered_new: 2 } },
    continuation: { status: "continue" },
    selection: {
      inventory_event_count: 28,
      calendar_gate_event_count: 24,
      calendar_eligible_count: 6,
      luna_ranked_count: 6,
      spend_ordered_count: 4,
      unsuppressed_count: 0,
      write_attempt_count: 0,
    },
  };
  try {
    const options = {
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      issueClient: {
        async ensureLabel() {},
        async findByMarker() {
          return { url: "https://github.com/Daisuke134/life-manager/issues/2467" };
        },
      },
      runRuntime: async () => runtimeResult,
    };
    await runNativePass(options);
    await runNativePass(options);

    const incidents = fs.readFileSync(path.join(stateDir, "self-heal-incidents.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.equal(incidents.length, 1);
    assert.deepEqual(Object.keys(incidents[0]).sort(), [
      "component", "fingerprint", "incident_class", "observed_at", "safe_reason",
      "schema_version", "selection",
    ]);
    assert.equal(incidents[0].component, "connector-native");
    assert.equal(incidents[0].incident_class, "apply_blocked_by_suppression");
    assert.equal(incidents[0].safe_reason, "LUMA_FORM_INPUT_REQUIRED");
    assert.match(incidents[0].fingerprint, /^sha256:[0-9a-f]{64}$/);
    assert.equal(JSON.stringify(incidents[0]).includes("private-event-ref"), false);
    assert.equal(fs.statSync(path.join(stateDir, "self-heal-incidents.jsonl")).mode & 0o777, 0o600);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass delivers one pending incident to the self-heal issue intake and stores its receipt", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const calls = [];
  const issueClient = {
    async ensureLabel(label) { calls.push(["label", label]); },
    async findByMarker(marker) { calls.push(["find", marker]); return null; },
    async create(issue) {
      calls.push(["create", issue]);
      return { url: "https://github.com/Daisuke134/life-manager/issues/2468" };
    },
  };
  const runtimeResult = {
    status: "incomplete",
    coverage: { counts: { open: 19, covered_new: 2 } },
    continuation: { status: "continue" },
    selection: {
      inventory_event_count: 28,
      calendar_gate_event_count: 24,
      calendar_eligible_count: 6,
      luna_ranked_count: 6,
      spend_ordered_count: 4,
      unsuppressed_count: 0,
      write_attempt_count: 0,
    },
  };
  try {
    fs.mkdirSync(stateDir, { recursive: true });
    fs.writeFileSync(path.join(stateDir, "candidate-attempts.jsonl"), `${JSON.stringify({
      event_ref: "luma-event://event/private-event-ref",
      outcome: "known_no_effect",
      safe_reason: "LUMA_FORM_INPUT_REQUIRED",
      observed_at: "2026-08-06T01:05:01.993Z",
      retry_after: null,
    })}\n`, { mode: 0o600 });
    const options = {
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" }, issueClient,
      runRuntime: async () => runtimeResult,
    };
    await runNativePass(options);
    await runNativePass(options);

    assert.equal(calls.filter(([name]) => name === "create").length, 1);
    const created = calls.find(([name]) => name === "create")[1];
    assert.deepEqual(created.labels, ["lm:type:self-heal"]);
    assert.match(created.title, /^\[error\] Connector apply blocked by suppression/);
    assert.match(created.body, /LUMA_FORM_INPUT_REQUIRED/);
    assert.match(created.body, /<!-- lm-connector-incident:sha256:[0-9a-f]{64} -->/);
    assert.equal(created.body.includes("private-event-ref"), false);

    const receipts = fs.readFileSync(path.join(stateDir, "self-heal-issue-receipts.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.equal(receipts.length, 1);
    assert.equal(receipts[0].issue_url, "https://github.com/Daisuke134/life-manager/issues/2468");
    assert.match(receipts[0].fingerprint, /^sha256:[0-9a-f]{64}$/);
    assert.equal(fs.statSync(path.join(stateDir, "self-heal-issue-receipts.jsonl")).mode & 0o777, 0o600);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass durably binds the registered-page PNG lineage to its Calendar event", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const hash = "a".repeat(64);
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 20, covered_new: 1 } },
        continuation: { status: "continue" },
        write: {
          status: "incomplete",
          outcome: "open_coverage",
          event_ref: "luma-event://event/founder-night",
          registration_receipt: {
            canonical_url: "https://luma.com/founder-night",
            evidence_observed_at: "2026-08-06T02:00:00.000Z",
            artifact_ref: `object://sha256/${hash}`,
            artifact_sha256: hash,
          },
          calendar_sync: {
            calendar_event_ref: `calendar-evidence://google/event/${"b".repeat(64)}`,
          },
          telegram: {
            provider_id: "7576",
            photo_provider_id: "7577",
            artifact_sha256: hash,
          },
          confirmation: {
            external_receipt_ref: `gmail-message://dais-local/${"c".repeat(64)}`,
          },
          ticket: {
            ticket_receipt_ref: `ticket://dais-local/${"d".repeat(64)}`,
            artifact_ref: `object://sha256/${"e".repeat(64)}`,
            telegram_provider_id: "7578",
          },
        },
      }),
    });
    const file = path.join(stateDir, "last-result.json");
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.deepEqual(JSON.parse(fs.readFileSync(file, "utf8")).write, {
      status: "incomplete",
      outcome: "open_coverage",
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
      evidence_observed_at: "2026-08-06T02:00:00.000Z",
      artifact_ref: `object://sha256/${hash}`,
      artifact_sha256: hash,
      calendar_event_ref: `calendar-evidence://google/event/${"b".repeat(64)}`,
      telegram_provider_id: "7576",
      telegram_photo_provider_id: "7577",
      confirmation_receipt_ref: `gmail-message://dais-local/${"c".repeat(64)}`,
      ticket_receipt_ref: `ticket://dais-local/${"d".repeat(64)}`,
      ticket_artifact_ref: `object://sha256/${"e".repeat(64)}`,
      ticket_telegram_provider_id: "7578",
    });
    const delivery = JSON.parse(fs.readFileSync(
      path.join(stateDir, "delivery-receipts.jsonl"), "utf8",
    ));
    assert.equal(delivery.telegram_provider_id, "7576");
    assert.equal(delivery.telegram_photo_provider_id, "7577");
    assert.equal(delivery.artifact_sha256, hash);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native loop backfills one legacy successful card with its real registered-page PNG", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const evidenceDir = path.join(stateDir, "evidence");
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const hash = require("node:crypto").createHash("sha256").update(bytes).digest("hex");
  fs.mkdirSync(path.join(evidenceDir, "objects/sha256"), { recursive: true });
  fs.mkdirSync(path.join(evidenceDir, "tenants/dais-local/outbound/luma/artifacts"), { recursive: true });
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, "objects/sha256", hash), bytes, { mode: 0o600 });
  fs.writeFileSync(
    path.join(evidenceDir, "tenants/dais-local/outbound/luma/artifacts", `${hash}.json`),
    `${JSON.stringify({ sha256: hash, event_ref: "luma-event://event/verified-one" })}\n`,
    { mode: 0o600 },
  );
  fs.writeFileSync(path.join(stateDir, "delivery-receipts.jsonl"), `${JSON.stringify({
    event_ref: "luma-event://event/verified-one",
    calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
    telegram_provider_id: "7372",
  })}\n`, { mode: 0o600 });
  let sends = 0;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: {
        tenantId: "dais-local",
        evidenceDir,
        telegramTarget: "fixture-target",
      },
      sendPhotoEvidence: async (photo, options) => {
        sends += 1;
        assert.deepEqual(photo, bytes);
        assert.match(options.caption, /verified-one/);
        return { messageId: "7577" };
      },
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 20 } },
        continuation: { status: "continue" },
      }),
    });
    assert.equal(sends, 1);
    const receipt = JSON.parse(fs.readFileSync(path.join(stateDir, "photo-delivery-receipts.jsonl"), "utf8"));
    assert.deepEqual(receipt, {
      event_ref: "luma-event://event/verified-one",
      telegram_provider_id: "7372",
      telegram_photo_provider_id: "7577",
      artifact_sha256: hash,
      observed_at: receipt.observed_at,
    });
    assert.equal(new Date(Date.parse(receipt.observed_at)).toISOString(), receipt.observed_at);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native photo backfill records a bounded send failure stage", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const evidenceDir = path.join(stateDir, "evidence");
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const hash = require("node:crypto").createHash("sha256").update(bytes).digest("hex");
  fs.mkdirSync(path.join(evidenceDir, "objects/sha256"), { recursive: true });
  fs.mkdirSync(path.join(evidenceDir, "tenants/dais-local/outbound/luma/artifacts"), { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, "objects/sha256", hash), bytes);
  fs.writeFileSync(path.join(evidenceDir, "tenants/dais-local/outbound/luma/artifacts", `${hash}.json`), `${JSON.stringify({
    sha256: hash, event_ref: "luma-event://event/verified-one",
  })}\n`);
  fs.writeFileSync(path.join(stateDir, "delivery-receipts.jsonl"), `${JSON.stringify({
    event_ref: "luma-event://event/verified-one",
    calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
    telegram_provider_id: "7372",
  })}\n`);
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local", evidenceDir, telegramTarget: "fixture-target" },
      sendPhotoEvidence: async () => { throw new Error("raw transport detail"); },
      runRuntime: async () => { throw new Error("runtime must not start"); },
    });
    assert.equal(result.status, "failed");
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "continuation.json"), "utf8")), {
      reason: "connector_native_photo_send_failed",
      status: "pending",
    });
    assert.doesNotMatch(fs.readFileSync(path.join(stateDir, "continuation.json"), "utf8"), /raw transport detail/);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass forwards the complete launchd-owned Connector loop configuration", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  let observed;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test",
        LM_CONNECTOR_PROFILE_PATH: path.join(REPO_ROOT, "apps/life-manager/config/connector/dais-local.json"),
        LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LM_CONNECTOR_CALENDAR_ID: "primary",
        LM_CONNECTOR_CALENDAR_COVERAGE_URL: "https://calendar.google.com/calendar/u/0/r",
        LIFE_HOME_ADDRESS: "Tokyo home",
        GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        observed = input.config;
        return { status: "incomplete", coverage: { counts: { open: 21 } }, continuation: { status: "continue" } };
      },
    });
    assert.equal(observed.profilePath.endsWith("config/connector/dais-local.json"), true);
    assert.equal(observed.lunaEvidenceDir, path.join(stateDir, "luna"));
    assert.equal(observed.telegramTarget, "123456");
    assert.equal(observed.calendarId, "primary");
    assert.equal(observed.homeLocation, "Tokyo home");
    assert.equal(observed.mapsKey, "maps-secret");
    assert.equal(observed.repoRoot, REPO_ROOT);
    assert.equal(observed.lumaEmail, "dais@example.test");
    assert.equal(observed.lumaName, "Dais");
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass forwards validated delivery history for coverage restoration", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "delivery-receipts.jsonl"), `${JSON.stringify({
    event_ref: "luma-event://event/verified-one",
    calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
    telegram_provider_id: "7372",
  })}\n`);
  let observed;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test", LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LIFE_HOME_ADDRESS: "Tokyo", GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        observed = input.config.deliveredReceipts;
        return { status: "incomplete", coverage: { counts: { open: 20 } }, continuation: { status: "continue" } };
      },
    });
    assert.equal(observed.length, 1);
    assert.equal(observed[0].event_ref, "luma-event://event/verified-one");
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass forwards durable candidate attempts into the next runtime wake", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  const attempt = {
    event_ref: "luma-event://event/unavailable-one",
    outcome: "known_no_effect",
    safe_reason: "LUMA_RSVP_UNAVAILABLE",
    observed_at: "2026-08-06T00:00:00.000Z",
    retry_after: null,
  };
  fs.writeFileSync(path.join(stateDir, "candidate-attempts.jsonl"), `${JSON.stringify(attempt)}\n`);
  let observed;
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test",
        LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LIFE_HOME_ADDRESS: "Tokyo",
        GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        observed = input.config.candidateAttempts;
        return { status: "incomplete", coverage: { counts: { open: 21 } }, continuation: { status: "continue" } };
      },
    });
    assert.deepEqual(observed, [attempt]);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass preserves a bounded write error code for live diagnosis", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 19 } },
        continuation: { status: "continue" },
        write: {
          status: "reconciliation_required",
          outcome: "unknown_external_effect",
          error_code: "LUMA_RESULT_UNVERIFIED",
          event_ref: "luma-event://event/pending-one",
        },
      }),
    });
    assert.equal(
      JSON.parse(fs.readFileSync(path.join(stateDir, "last-result.json"), "utf8")).write.error_code,
      "LUMA_RESULT_UNVERIFIED",
    );
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass keeps successful Calendar and Telegram receipts in append-only deduped history", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const runtimeResult = {
    status: "incomplete",
    coverage: { counts: { open: 20 } },
    continuation: { status: "continue" },
    write: {
      status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/verified-one",
      calendar_sync: { calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}` },
      telegram: { provider_id: "7372" },
    },
  };
  try {
    for (let count = 0; count < 2; count += 1) {
      await runNativePass({
        repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
        config: { tenantId: "dais-local" }, runRuntime: async () => runtimeResult,
      });
    }
    const lines = fs.readFileSync(path.join(stateDir, "delivery-receipts.jsonl"), "utf8").trim().split("\n");
    assert.equal(lines.length, 1);
    assert.deepEqual(JSON.parse(lines[0]), {
      event_ref: "luma-event://event/verified-one",
      calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
      telegram_provider_id: "7372",
    });
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass appends every bounded candidate attempt to durable history", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const candidateAttempts = [{
    event_ref: "luma-event://event/unavailable-one",
    outcome: "known_no_effect",
    safe_reason: "LUMA_RSVP_UNAVAILABLE",
    observed_at: "2026-08-06T00:00:00.000Z",
    retry_after: null,
    capability_version: "luma-form-submit-v1",
  }, {
    event_ref: "connpass-event://event/101",
    outcome: "verified_success",
    safe_reason: "open_coverage",
    observed_at: "2026-08-06T00:00:01.000Z",
    retry_after: null,
    capability_version: "luma-form-submit-v1",
  }];
  try {
    await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => ({
        status: "incomplete",
        coverage: { counts: { open: 20 } },
        continuation: { status: "continue" },
        candidate_attempts: candidateAttempts,
      }),
    });

    const rows = fs.readFileSync(path.join(stateDir, "candidate-attempts.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.deepEqual(rows, candidateAttempts);
    assert.equal(fs.statSync(path.join(stateDir, "candidate-attempts.jsonl")).mode & 0o777, 0o600);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass atomically persists a provider cursor and forwards it into the next wake", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  let cursor;
  let phase = 0;
  try {
    fs.mkdirSync(stateDir, { recursive: true });
    fs.writeFileSync(path.join(stateDir, "cursor.json"), "{\"status\":\"legacy\"}\n", { mode: 0o600 });
    const options = {
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: {
        GOG_ACCOUNT: "dais@example.test",
        LM_CONNECTOR_TELEGRAM_TARGET: "123456",
        LIFE_HOME_ADDRESS: "Tokyo",
        GOOGLE_API_KEY_DIRECTIONS: "maps-secret",
      },
      runRuntime: async (input) => {
        phase += 1;
        if (phase === 1) {
          assert.equal(input.config.providerCursor, null);
          cursor = require("../../../apps/life-manager/lib/event-provider-cursor.js")
            .createEventProviderCursor({
              registry: input.config.providerRegistry,
              date: "2026-08-05",
              observedAt: "2026-08-06T00:00:00.000Z",
            });
          return {
            status: "incomplete",
            coverage: { counts: { open: 21 } },
            continuation: { status: "continue" },
            provider_cursor: cursor,
          };
        }
        assert.deepEqual(input.config.providerCursor, cursor);
        return {
          status: "incomplete",
          coverage: { counts: { open: 21 } },
          continuation: { status: "continue" },
          provider_cursor: null,
        };
      },
    };
    await runNativePass(options);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "provider-cursor.json"), "utf8")), cursor);
    assert.equal(fs.statSync(path.join(stateDir, "provider-cursor.json")).mode & 0o777, 0o600);
    assert.equal(fs.existsSync(path.join(stateDir, "cursor.json")), false);
    await runNativePass(options);
    assert.equal(fs.existsSync(path.join(stateDir, "provider-cursor.json")), false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass migrates the previous successful last result before the next runtime", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "last-result.json"), JSON.stringify({
    status: "incomplete",
    write: {
      status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/pending-one",
      calendar_event_ref: `calendar-evidence://google/event/${"b".repeat(64)}`,
      telegram_provider_id: "7372",
    },
  }));
  try {
    await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => ({
        status: "incomplete", coverage: { counts: { open: 21 } }, continuation: { status: "continue" },
      }),
    });
    const receipt = JSON.parse(fs.readFileSync(path.join(stateDir, "delivery-receipts.jsonl"), "utf8"));
    assert.equal(receipt.telegram_provider_id, "7372");
    assert.equal(receipt.event_ref, "luma-event://event/pending-one");
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("launchd run script restores Connector credentials and Telegram owner without a manual env file", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/run.sh"), "utf8");
  assert.match(source, /\.openclaw\/\.env/);
  assert.match(source, /telegram-default-allowFrom\.json/);
  assert.match(source, /LM_CONNECTOR_TELEGRAM_TARGET/);
});

test("launchd run script uses an allowlisted Connector env reader instead of the legacy-root-rejecting loader", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/run.sh"), "utf8");
  assert.match(source, /load-connector-env\.js/);
  assert.doesNotMatch(source, /lm_load_env_file "\$LM_CONNECTOR_SHARED_ENV_FILE"/);
});

test("launchd parent records a process crash when native-pass exits by signal", () => {
  const directory = temporaryDirectory();
  const fakeNode = path.join(directory, "fake-node.sh");
  const observerCall = path.join(directory, "observer-call.txt");
  const wakeReportCall = path.join(directory, "wake-report-call.txt");
  fs.writeFileSync(fakeNode, `#!/bin/bash
case "$1" in
  -e) printf '%064d' 0; exit 0 ;;
  *load-connector-env.js) exit 0 ;;
  *native-state.js)
    [ "$2" = acquire ] && printf '{"status":"acquired"}'
    exit 0
    ;;
  *native-pass.js) exit 137 ;;
  *observer-envelope.js) printf '%s\\n' "$*" > "$OBSERVER_CALL_FILE"; exit 0 ;;
  *wake-report-outbox.js) printf '%s\\n' "$*" > "$WAKE_REPORT_CALL_FILE"; exit 0 ;;
esac
exit 2
`, { mode: 0o700 });
  try {
    const result = spawnSync("/bin/bash", [path.join(REPO_ROOT, "skills/connector/run.sh")], {
      encoding: "utf8",
      env: {
        ...process.env,
        NODE_BIN: fakeNode,
        OBSERVER_CALL_FILE: observerCall,
        WAKE_REPORT_CALL_FILE: wakeReportCall,
        LM_CONNECTOR_STATE_DIR: path.join(directory, "state"),
        LM_CONNECTOR_TELEGRAM_TARGET: "123456789",
        LM_CONNECTOR_CODE_COMMIT: "27506a703",
      },
    });
    assert.equal(result.status, 137);
    assert.match(fs.readFileSync(observerCall, "utf8"), /observer-envelope\.js process-crash/);
    assert.match(fs.readFileSync(wakeReportCall, "utf8"), /wake-report-outbox\.js process-crash/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass ignores CONNECTOR_NATIVE_WORKER_BIN and still invokes the direct runtime", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  const ignoredWorker = path.join(directory, "ignored-worker");
  fs.writeFileSync(ignoredWorker, "this file must never be executed\n", { mode: 0o600 });
  const observed = [];
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      env: { CONNECTOR_NATIVE_WORKER_BIN: ignoredWorker },
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async () => {
        observed.push(true);
        return {
          status: "incomplete",
          coverage: { counts: { open: 21 } },
          continuation: { status: "continue" },
        };
      },
    });

    assert.equal(result.exitCode, 1);
    assert.deepEqual(observed, [true]);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass exits zero only for verified open-zero coverage", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT,
      stateDir,
      ownerToken: OWNER_TOKEN,
      config: {
        tenantId: "dais-local",
        timeZone: "Asia/Tokyo",
        now: "2026-08-02T01:00:00.000Z",
        evidenceDir: path.join(directory, "evidence"),
        calendarAccount: "dais@example.test",
      },
      runRuntime: async () => ({
        status: "complete",
        coverage: { counts: { open: 0 } },
        continuation: { status: "complete" },
      }),
    });

    assert.deepEqual(result, { exitCode: 0, status: "complete" });
    assert.equal(fs.existsSync(path.join(stateDir, "continuation.json")), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("native-pass records only an allowlisted runtime failure stage", async () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const result = await runNativePass({
      repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
      config: { tenantId: "dais-local" },
      runRuntime: async () => {
        const error = new Error("private failure");
        error.code = "CONNECTOR_NATIVE_LUNA_FAILED";
        throw error;
      },
    });
    assert.equal(result.status, "failed");
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "continuation.json"), "utf8")), {
      reason: "connector_native_luna_failed", status: "pending",
    });
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test("native-pass preserves bounded Calendar gate diagnostic substages", async () => {
  for (const code of [
    "CONNECTOR_NATIVE_CALENDAR_GATE_INPUT_FAILED",
    "CONNECTOR_NATIVE_CALENDAR_GATE_EXECUTION_FAILED",
    "CONNECTOR_NATIVE_CALENDAR_GATE_RESULT_FAILED",
  ]) {
    const directory = temporaryDirectory();
    const stateDir = path.join(directory, "state");
    try {
      await runNativePass({
        repoRoot: REPO_ROOT, stateDir, ownerToken: OWNER_TOKEN,
        config: { tenantId: "dais-local" },
        runRuntime: async () => {
          const error = new Error("private failure");
          error.code = code;
          throw error;
        },
      });
      assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stateDir, "continuation.json"), "utf8")), {
        reason: code.toLowerCase(), status: "pending",
      });
    } finally { fs.rmSync(directory, { recursive: true, force: true }); }
  }
});

test("native-pass CLI terminates its bounded process after durable state is written", () => {
  const source = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/native-pass.js"), "utf8");
  assert.match(source, /process\.exit\(result\.exitCode\)/);
  assert.doesNotMatch(source, /process\.exitCode = result\.exitCode/);
});

test("rendered native templates contain only canonical launch paths", () => {
  const directory = temporaryDirectory();
  try {
    const outputDir = path.join(directory, "rendered");
    const result = spawnSync("bash", [
      RENDERER,
      "--output-dir", outputDir,
      "--repo-root", REPO_ROOT,
      "--life-manager-home", path.join(directory, "life-manager-home"),
    ], { encoding: "utf8", env: { ...process.env, HOME: directory } });

    assert.equal(result.status, 0, result.stderr);
    const nativePass = fs.readFileSync(
      path.join(outputDir, "ai.anicca.life-manager-connector-native.plist"),
      "utf8",
    );
    const healthcheck = fs.readFileSync(
      path.join(outputDir, "ai.anicca.life-manager-connector-native-healthcheck.plist"),
      "utf8",
    );
    const healer = fs.readFileSync(
      path.join(outputDir, "ai.anicca.life-manager-connector-healer-shadow.plist"),
      "utf8",
    );
    const healerRunner = fs.readFileSync(path.join(REPO_ROOT, "skills/connector/healer-shadow.sh"), "utf8");
    assert.equal(nativePass.includes(path.join(REPO_ROOT, "skills/connector/run.sh")), true);
    assert.equal(healthcheck.includes(path.join(REPO_ROOT, "skills/connector/healthcheck.sh")), true);
    assert.equal(healer.includes(path.join(REPO_ROOT, "skills/connector/healer-shadow.sh")), true);
    assert.match(healer, /<key>StartInterval<\/key><integer>900<\/integer>/);
    assert.match(healerRunner, /\/opt\/homebrew\/bin:\/usr\/local\/bin:\/usr\/bin/);
    assert.doesNotMatch(`${nativePass}\n${healthcheck}\n${healer}`, /docker|host\.docker\.internal|connector-host-bridge|profitable-claude|:9223/i);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("renderer rejects the live LaunchAgents directory after path normalization", () => {
  const directory = temporaryDirectory();
  try {
    const liveOutput = `${path.join(directory, "Library", "LaunchAgents")}/`;
    const result = spawnSync("bash", [
      RENDERER,
      "--output-dir", liveOutput,
      "--repo-root", REPO_ROOT,
      "--life-manager-home", path.join(directory, "life-manager-home"),
    ], { encoding: "utf8", env: { ...process.env, HOME: directory } });

    assert.equal(result.status, 2, result.stderr);
    assert.equal(fs.existsSync(liveOutput), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck rejects a stale heartbeat without a recovery command", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const gog = path.join(directory, "gog");
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(gog, "#!/usr/bin/env bash\nexit 0\n", { mode: 0o700 });
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    assert.deepEqual(acquireLock({
      stateDir,
      token: "health-owner-token-123456",
      pid: process.pid,
      now: "2026-08-02T00:00:00.000Z",
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token: "health-owner-token-123456",
      stage: "worker_started",
      now: "2026-08-02T00:00:00.000Z",
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token: "health-owner-token-123456" }), { status: "released" });

    const result = spawnSync("bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "1",
        GOG_BIN: gog,
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 1, result.stderr);
    assert.equal(fs.existsSync(probeCount), false);
    assert.equal(fs.readFileSync(HEALTHCHECK, "utf8").includes("launchctl"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck reports healthy only after fresh state and read-only dependencies succeed", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const gog = path.join(directory, "gog");
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(gog, "#!/usr/bin/env bash\nexit 0\n", { mode: 0o700 });
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    const token = "fresh-health-owner-token-123456";
    const now = new Date().toISOString();
    assert.deepEqual(acquireLock({
      stateDir,
      token,
      pid: process.pid,
      now,
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token,
      stage: "worker_finished",
      now,
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token }), { status: "released" });

    const result = spawnSync("bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "60000",
        GOG_BIN: gog,
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(probeCount, "utf8"), "1\n");
    assert.equal(result.stdout, '{"status":"healthy"}\n');
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("healthcheck restores the Homebrew PATH under a launchd-like minimal environment", () => {
  const directory = temporaryDirectory();
  const stateDir = path.join(directory, "state");
  try {
    const probe = path.join(directory, "healthy-browser-probe");
    const probeCount = path.join(directory, "probe-count");
    fs.writeFileSync(probe, [
      "#!/usr/bin/env bash",
      "set -eu",
      `printf '1\\n' >> ${JSON.stringify(probeCount)}`,
      "exit 0",
    ].join("\n"), { mode: 0o700 });
    const token = "launchd-path-owner-token-123456";
    const now = new Date().toISOString();
    assert.deepEqual(acquireLock({
      stateDir,
      token,
      pid: process.pid,
      now,
      staleMs: 60_000,
    }), { status: "acquired" });
    assert.deepEqual(heartbeat({
      stateDir,
      token,
      stage: "worker_finished",
      now,
    }), { status: "updated" });
    assert.deepEqual(releaseLock({ stateDir, token }), { status: "released" });

    const result = spawnSync("/bin/bash", [HEALTHCHECK], {
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: directory,
        PATH: "/usr/bin:/bin",
        LM_CONNECTOR_STATE_DIR: stateDir,
        LM_CONNECTOR_HEARTBEAT_STALE_MS: "60000",
        CONNECTOR_NATIVE_HEALTH_PROBE_BIN: probe,
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(probeCount, "utf8"), "1\n");
    assert.equal(result.stdout, '{"status":"healthy"}\n');
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
