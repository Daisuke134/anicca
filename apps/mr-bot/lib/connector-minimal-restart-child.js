"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");

const { createMinimalEvidenceChain } = require("./connector-minimal-evidence.js");

const LEDGER_NAME = "restart-ledger.json";
const ALLOWED_STAGES = new Set([
  "evidence_effect",
  "calendar_effect",
  "message_effect",
  "photo_effect",
  "none",
]);

function invalid() {
  throw new Error("Connector minimal restart child invalid");
}

function stateDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.chmodSync(directory, 0o700);
  return directory;
}

function initialLedger() {
  return {
    provider_count: 1,
    evidence_count: 0,
    calendar_count: 0,
    message_count: 0,
    photo_count: 0,
    bundle_count: 0,
    submit_count: 0,
    cache_count: 0,
    direct_count: 0,
    harness_count: 0,
    last_disposition: null,
    pid_runs: [],
    provider_identities: {
      "peatix-event://event/5075819": {
        provider: "peatix",
        event_ref: "peatix-event://event/5075819",
        status: "registered",
      },
    },
    evidence_identities: {},
    calendar_identities: {},
    message_identities: {},
    photo_identities: {},
    bundle_identities: {},
  };
}

function ledgerFile(stateDir) {
  const directory = stateDirectory(stateDir);
  return path.join(directory, LEDGER_NAME);
}

function readLedger(stateDir) {
  const file = ledgerFile(stateDir);
  if (!fs.existsSync(file)) {
    const ledger = initialLedger();
    writeLedger(stateDir, ledger);
    return ledger;
  }
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o777) !== 0o600) invalid();
  let ledger;
  try { ledger = JSON.parse(fs.readFileSync(file, "utf8")); } catch { invalid(); }
  if (!ledger || typeof ledger !== "object" || Array.isArray(ledger)) invalid();
  return ledger;
}

function writeLedger(stateDir, ledger) {
  const file = ledgerFile(stateDir);
  const temporary = `${file}.${process.pid}.tmp`;
  const bytes = Buffer.from(`${JSON.stringify(ledger, null, 2)}\n`, "utf8");
  try {
    fs.writeFileSync(temporary, bytes, { flag: "wx", mode: 0o600 });
    fs.renameSync(temporary, file);
    fs.chmodSync(file, 0o600);
  } finally {
    try { fs.unlinkSync(temporary); } catch (error) { if (error && error.code !== "ENOENT") throw error; }
  }
}

function parseCli(argv) {
  if (!Array.isArray(argv) || argv.length !== 4) invalid();
  const stateDir = stateDirectory(argv[2]);
  const stage = String(argv[3] || "");
  if (!ALLOWED_STAGES.has(stage)) invalid();
  return Object.freeze({ stateDir, stage });
}

const { stateDir, stage } = parseCli(process.argv);
const candidate = Object.freeze({
  provider: "peatix",
  event_ref: "peatix-event://event/5075819",
  canonical_url: "https://peatix.com/event/5075819",
  title: "Restart Fixture Event",
  starts_at: "2026-08-10T10:00:00.000Z",
  ends_at: "2026-08-10T11:00:00.000Z",
  venue_name: "Tokyo",
});
const png = fs.readFileSync(path.resolve(__dirname, "../../../scratch_step1.png"));
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
if (png.length <= 5_000 || !png.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)) invalid();

function validateProviderReadback(ledger) {
  if (ledger.provider_count !== 1) invalid();
  const identities = ledger.provider_identities;
  if (!identities || typeof identities !== "object" || Array.isArray(identities)) invalid();
  const keys = Object.keys(identities);
  if (keys.length !== 1 || keys[0] !== candidate.event_ref) invalid();
  const identity = identities[candidate.event_ref];
  if (!identity || typeof identity !== "object" || Array.isArray(identity)
    || Object.keys(identity).sort().join(",") !== "event_ref,provider,status"
    || identity.provider !== "peatix"
    || identity.event_ref !== candidate.event_ref
    || identity.status !== "registered") invalid();
  return Object.freeze({ status: identity.status });
}

function evidenceRecord(ledger) {
  const identities = ledger.evidence_identities;
  if (!identities || typeof identities !== "object" || Array.isArray(identities)) invalid();
  return Object.values(identities).find((value) => value && value.event_ref === candidate.event_ref) || null;
}

function createLedgerEvidenceStore(ledger) {
  return Object.freeze({
    async record(input = {}) {
      const existing = evidenceRecord(ledger);
      if (existing) {
        return Object.freeze({
          external_receipt_ref: existing.external_receipt_ref,
          artifact_ref: existing.artifact_ref,
        });
      }
      const artifactSha256 = createHash("sha256").update(input.screenshot).digest("hex");
      const providerId = createHash("sha256")
        .update(`${input.tenantId}\n${input.eventRef}\n${input.observedAt}\n${artifactSha256}`, "utf8")
        .digest("hex");
      const value = {
        provider_id: providerId,
        event_ref: input.eventRef,
        observed_at: input.observedAt,
        artifact_sha256: artifactSha256,
        external_receipt_ref: `provider-receipt://peatix/${providerId}`,
        artifact_ref: `object://sha256/${artifactSha256}`,
      };
      ledger.evidence_identities[providerId] = value;
      ledger.evidence_count += 1;
      writeLedger(stateDir, ledger);
      if (stage === "evidence_effect") process.exit(42);
      return Object.freeze({
        external_receipt_ref: value.external_receipt_ref,
        artifact_ref: value.artifact_ref,
      });
    },
    async readExternalReceipt(_tenantId, ref) {
      const identity = Object.values(ledger.evidence_identities).find((value) => value && value.external_receipt_ref === ref);
      if (!identity) throw new Error("evidence receipt unavailable");
      return Object.freeze({
        kind: "provider_response",
        provider_id: identity.provider_id,
        observed_at: identity.observed_at,
        event_ref: identity.event_ref,
        artifact_sha256: identity.artifact_sha256,
      });
    },
    async readArtifact(_tenantId, ref) {
      const identity = Object.values(ledger.evidence_identities).find((value) => value && value.artifact_ref === ref);
      if (!identity || identity.artifact_sha256 !== createHash("sha256").update(png).digest("hex")) {
        throw new Error("evidence artifact unavailable");
      }
      return png;
    },
  });
}

function createPage() {
  let currentUrl = "about:blank";
  return Object.freeze({
    async goto(url) { currentUrl = String(url); },
    url() { return currentUrl; },
    async evaluate() { return true; },
    async screenshot() { return png; },
  });
}

function createLedgerCalendar(ledger) {
  return Object.freeze({
    async findConnectorEvents(input = {}) {
      const idempotencyValue = String(input.idempotencyValue || "");
      const identity = ledger.calendar_identities[idempotencyValue];
      return identity ? [Object.freeze({ id: identity.id, htmlLink: identity.htmlLink })] : [];
    },
    async createConnectorEvent(input = {}) {
      const idempotencyValue = String(input.idempotencyValue || "");
      if (!idempotencyValue) throw new Error("calendar idempotency unavailable");
      const existing = ledger.calendar_identities[idempotencyValue];
      if (existing) return Object.freeze({ id: existing.id, htmlLink: existing.htmlLink });
      const value = {
        id: "restart-calendar-event",
        htmlLink: "https://www.google.com/calendar/event?eid=restart-calendar-event",
        idempotency_value: idempotencyValue,
      };
      ledger.calendar_identities[idempotencyValue] = value;
      ledger.calendar_count += 1;
      writeLedger(stateDir, ledger);
      if (stage === "calendar_effect") process.exit(43);
      return Object.freeze({ id: value.id, htmlLink: value.htmlLink });
    },
  });
}

function ledgerDelivery(ledger, kind, options) {
  const key = options && options.idempotencyKey;
  if (typeof key !== "string" || key.length < 1) throw new Error(`${kind} idempotency unavailable`);
  const identities = kind === "message" ? ledger.message_identities : ledger.photo_identities;
  const countKey = kind === "message" ? "message_count" : "photo_count";
  const existingKeys = Object.keys(identities);
  if (existingKeys.length > 1 || (existingKeys.length === 1 && existingKeys[0] !== key)) {
    throw new Error(`${kind} idempotency collision`);
  }
  if (identities[key]) return identities[key];
  const providerId = kind === "message" ? "9401" : "9402";
  identities[key] = { idempotency_key: key, provider_id: providerId };
  ledger[countKey] += 1;
  writeLedger(stateDir, ledger);
  if (stage === (kind === "message" ? "message_effect" : "photo_effect")) process.exit(kind === "message" ? 44 : 45);
  return identities[key];
}

function createLedgerTelegram(ledger) {
  return Object.freeze({
    async sendMessage(_message, options = {}) {
      const value = ledgerDelivery(ledger, "message", options);
      return Object.freeze({ messageId: value.provider_id });
    },
    async sendPhoto(_bytes, options = {}) {
      const value = ledgerDelivery(ledger, "photo", options);
      return Object.freeze({ messageId: value.provider_id });
    },
  });
}

async function main() {
  const ledger = readLedger(stateDir);
  const providerState = validateProviderReadback(ledger);
  if (!Array.isArray(ledger.pid_runs)) invalid();
  ledger.pid_runs.push({ stage, pid: process.pid });
  writeLedger(stateDir, ledger);
  const chain = createMinimalEvidenceChain({
    stateDir,
    tenantId: "dais-local",
    calendarId: "primary",
    telegramTarget: "restart-test-target",
    peatixEvidenceStore: createLedgerEvidenceStore(ledger),
    calendar: createLedgerCalendar(ledger),
    sendMessage: createLedgerTelegram(ledger).sendMessage,
    sendPhoto: createLedgerTelegram(ledger).sendPhoto,
    now: () => new Date("2026-08-07T08:30:00.000Z"),
  });
  const result = await chain.completeEvidence({
    provider: "peatix",
    candidate,
    page: createPage(),
    providerState,
  });
  const bundlesDir = path.join(stateDir, "applied-bundles");
  const bundleEntries = fs.readdirSync(bundlesDir);
  const exactBundles = bundleEntries.filter((name) => /^[0-9a-f]{64}\.json$/.test(name));
  ledger.bundle_count = exactBundles.length;
  ledger.last_disposition = result.completion_disposition;
  writeLedger(stateDir, ledger);
  process.stdout.write(`${JSON.stringify({ pid: process.pid, disposition: result.completion_disposition })}\n`);
}

main().catch(() => { process.exitCode = 1; });
