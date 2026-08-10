"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createLumaEvidenceStore } = require("./luma-evidence-store.js");
const { createPeatixEvidenceStore } = require("./peatix-evidence-store.js");
const {
  notifyOpenClawGateway,
  notifyOpenClawPhoto,
  parseOpenClawMessageId,
} = require("./outbound-guardian.js");

const EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;
const RECEIPT_REF = /^provider-receipt:\/\/luma\/([0-9a-f]{64})$/;
const PEATIX_EVENT_REF = /^peatix-event:\/\/event\/([1-9][0-9]*)$/;
const PEATIX_RECEIPT_REF = /^provider-receipt:\/\/peatix\/([0-9a-f]{64})$/;
const ARTIFACT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const RECEIPT_ESCAPE = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function invalid() {
  throw new Error("Connector minimal evidence invalid");
}

function receiptHtml(provider, status, eventRef) {
  const safe = (value) => String(value).replace(/[&<>"']/g, (char) => RECEIPT_ESCAPE[char]);
  return `<!doctype html><html><body><dl><dt>provider</dt><dd>${safe(provider)}</dd><dt>status</dt><dd>${safe(status)}</dd><dt>event reference</dt><dd>${safe(eventRef)}</dd></dl></body></html>`;
}

function text(value, max = 2_000) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!result || result.length > max || /[\x00-\x1f\x7f]/.test(result)) invalid();
  return result;
}

function exactInstant(value) {
  const instant = value instanceof Date ? value.toISOString() : String(value || "");
  if (!Number.isFinite(Date.parse(instant)) || new Date(Date.parse(instant)).toISOString() !== instant) invalid();
  return instant;
}

function assertNoSymlinkPath(root, target) {
  const base = path.resolve(root); const resolved = path.resolve(target); const relative = path.relative(base, resolved);
  if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) invalid();
  let current = base;
  for (const component of ["", ...relative.split(path.sep)]) {
    current = path.join(current, component);
    try { if (fs.lstatSync(current).isSymbolicLink()) invalid(); }
    catch (error) { if (error && error.code === "ENOENT") break; invalid(); }
  }
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function lumaUrl(value) {
  let url;
  try { url = new URL(String(value || "")); } catch { invalid(); }
  if (
    url.protocol !== "https:" || !["luma.com", "www.luma.com", "lu.ma"].includes(url.hostname.toLowerCase())
    || !/^\/[A-Za-z0-9_-]+\/?$/.test(url.pathname) || url.username || url.password
  ) invalid();
  return `https://${url.hostname.toLowerCase()}${url.pathname.replace(/\/$/, "")}`;
}

function peatixUrl(value, eventRef) {
  if (typeof eventRef !== "string" || typeof value !== "string") invalid();
  const match = PEATIX_EVENT_REF.exec(eventRef);
  const expected = match ? `https://peatix.com/event/${match[1]}` : "";
  if (!match || value !== expected) invalid();
  return expected;
}

function calendarReceipt(value) {
  const id = text(value && value.id, 1_024);
  let url;
  try { url = new URL(String(value && value.htmlLink || "")); } catch { invalid(); }
  if (
    url.protocol !== "https:" || !["www.google.com", "google.com", "calendar.google.com"].includes(url.hostname)
    || url.pathname !== "/calendar/event" || !url.searchParams.get("eid") || url.username || url.password
  ) invalid();
  return Object.freeze({ id, htmlLink: url.toString() });
}

function privateStateDir(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  try { if (fs.lstatSync(directory).isSymbolicLink()) invalid(); } catch (error) { if (error && error.code !== "ENOENT") invalid(); }
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.chmodSync(directory, 0o700);
  return directory;
}

function immutableJson(file, value) {
  const bytes = Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) invalid();
    return;
  }
  const temporary = `${file}.${process.pid}.${randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temporary, bytes, { flag: "wx", mode: 0o600 });
    fs.renameSync(temporary, file);
    fs.chmodSync(file, 0o600);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function providerReceiptId(tenantId, eventRef, observedAt, artifactSha) { return sha256(`${tenantId}\n${eventRef}\n${observedAt}\n${artifactSha}`); }

function checkpointPath(stateDir, provider, eventRef, eventUrl) {
  const canonicalUrlSha256 = sha256(eventUrl); const identity = sha256(`${provider}\n${eventRef}\n${canonicalUrlSha256}`);
  const file = path.join(stateDir, "evidence", "checkpoints", `${identity}.json`); assertNoSymlinkPath(stateDir, file);
  return { canonicalUrlSha256, file };
}

const CHECKPOINT_KEYS = "artifact_ref,artifact_sha256,canonical_url_sha256,event_ref,observed_at,provider,provider_receipt_ref,provider_status,schema_version,stage";

function readCheckpoint(stateDir, file, provider, candidate, canonicalUrlSha256) {
  assertNoSymlinkPath(stateDir, file);
  if (!fs.existsSync(file)) return null;
  let value;
  try { const stat = fs.statSync(file); if (!stat.isFile() || (stat.mode & 0o777) !== 0o600 || stat.size > 16_384) invalid(); value = JSON.parse(fs.readFileSync(file, "utf8")); } catch { invalid(); }
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (value.stage !== "evidence" || Object.keys(value).sort().join(",") !== CHECKPOINT_KEYS || value.schema_version !== 1
    || value.provider !== provider.name || value.event_ref !== candidate.event_ref || value.canonical_url_sha256 !== canonicalUrlSha256 || !provider.states.includes(value.provider_status)) invalid();
  const receiptRef = String(value.provider_receipt_ref || ""); const artifactRef = String(value.artifact_ref || "");
  const artifactMatch = ARTIFACT_REF.exec(artifactRef);
  if (!provider.receiptRef.test(receiptRef) || !artifactMatch || artifactMatch[1] !== value.artifact_sha256
    || !/^[0-9a-f]{64}$/.test(String(value.artifact_sha256 || ""))) invalid();
  return Object.freeze({ stage: value.stage, eventRef: value.event_ref, observedAt: exactInstant(value.observed_at), receiptRef, artifactRef, artifactSha256: value.artifact_sha256, status: value.provider_status });
}

async function validateCheckpointEvidence(provider, checkpoint, tenantId) {
  const store = provider.store;
  if (!store || typeof store.readExternalReceipt !== "function" || typeof store.readArtifact !== "function") invalid();
  let receipt;
  try { receipt = await store.readExternalReceipt(tenantId, checkpoint.receiptRef); } catch { invalid(); }
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt) || receipt.kind !== "provider_response") invalid();
  const receiptMatch = provider.receiptRef.exec(checkpoint.receiptRef);
  if (!receiptMatch || receipt.provider_id !== receiptMatch[1] || receipt.provider_id !== providerReceiptId(tenantId, checkpoint.eventRef, checkpoint.observedAt, checkpoint.artifactSha256)) invalid();
  if (receipt.observed_at != null && exactInstant(receipt.observed_at) !== checkpoint.observedAt || receipt.event_ref != null && receipt.event_ref !== checkpoint.eventRef || receipt.artifact_sha256 != null && receipt.artifact_sha256 !== checkpoint.artifactSha256) invalid();
  let bytes;
  try { bytes = await store.readArtifact(tenantId, checkpoint.artifactRef); } catch { invalid(); }
  if (!Buffer.isBuffer(bytes) || bytes.length < 5_000 || !bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE) || sha256(bytes) !== checkpoint.artifactSha256) invalid();
  return bytes;
}

async function captureProviderEvidence({ provider, providerName, page, candidate, providerStatus, tenantId, now, canonicalUrlSha256 }) {
  const observedAt = exactInstant(now());
  if (providerName === "peatix"
    ? typeof page.goto !== "function" || typeof page.url !== "function" || typeof page.evaluate !== "function"
    : typeof page.setContent !== "function") invalid();
  if (typeof page.screenshot !== "function") invalid();
  const receipt = receiptHtml(providerName, providerStatus, candidate.event_ref);
  if (providerName === "peatix") {
    try {
      await page.goto("about:blank", { waitUntil: "domcontentloaded", timeout: 30_000 });
      if (String(page.url()) !== "about:blank") invalid();
      const rendered = await page.evaluate((html) => { document.open(); document.write(html); document.close(); const root = document.querySelector("body > dl"); return root !== null && document.querySelectorAll("body > dl > dt").length === 3 && document.querySelectorAll("body > dl > dd").length === 3; }, receipt);
      if (rendered !== true) invalid();
    } catch { invalid(); }
  } else {
    try { await page.setContent(receipt); } catch { invalid(); }
  }
  const screenshot = await page.screenshot({ type: "png", fullPage: true });
  if (!Buffer.isBuffer(screenshot) || screenshot.length < 5_000 || !screenshot.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)) invalid();
  const artifactSha = sha256(screenshot);
  const evidence = await provider.store.record({ tenantId, eventRef: candidate.event_ref, observedAt, screenshot });
  const artifactMatch = ARTIFACT_REF.exec(String(evidence && evidence.artifact_ref || ""));
  const receiptRef = String(evidence && evidence.external_receipt_ref || ""); const receiptMatch = provider.receiptRef.exec(receiptRef);
  if (!receiptMatch || receiptMatch[1] !== providerReceiptId(tenantId, candidate.event_ref, observedAt, artifactSha) || !artifactMatch || artifactMatch[1] !== artifactSha) invalid();
  return { screenshot, checkpointValue: { schema_version: 1, stage: "evidence", provider: providerName, event_ref: candidate.event_ref, canonical_url_sha256: canonicalUrlSha256, provider_status: providerStatus, provider_receipt_ref: evidence.external_receipt_ref, artifact_ref: evidence.artifact_ref, artifact_sha256: artifactSha, observed_at: observedAt } };
}

function createMinimalEvidenceChain(options = {}) {
  const stateDir = privateStateDir(options.stateDir);
  const tenantId = text(options.tenantId, 128);
  const calendar = options.calendar;
  const calendarId = text(options.calendarId, 1_024);
  const telegramTarget = text(options.telegramTarget, 200);
  const lumaEvidenceStore = options.evidenceStore || createLumaEvidenceStore({
    dataDir: path.join(stateDir, "evidence"),
  });
  const peatixEvidenceStore = options.peatixEvidenceStore || createPeatixEvidenceStore({
    dataDir: path.join(stateDir, "evidence"),
  });
  const providers = {
    luma: { name: "luma", eventRef: EVENT_REF, receiptRef: RECEIPT_REF, url: lumaUrl, states: ["registered", "pending"], store: lumaEvidenceStore },
    peatix: { name: "peatix", eventRef: PEATIX_EVENT_REF, receiptRef: PEATIX_RECEIPT_REF, url: peatixUrl, states: ["registered"], store: peatixEvidenceStore },
  };
  const now = options.now || (() => new Date());
  const sendMessage = options.sendMessage || notifyOpenClawGateway;
  const sendPhoto = options.sendPhoto || notifyOpenClawPhoto;
  if (
    !calendar || typeof calendar.findConnectorEvents !== "function"
    || typeof calendar.createConnectorEvent !== "function"
    || !lumaEvidenceStore || typeof lumaEvidenceStore.record !== "function"
    || !peatixEvidenceStore || typeof peatixEvidenceStore.record !== "function"
    || typeof now !== "function" || typeof sendMessage !== "function" || typeof sendPhoto !== "function"
  ) invalid();

  return Object.freeze({
    async completeEvidence(input = {}) {
      const provider = providers[input.provider];
      if (
        !provider || !input.page || typeof input.page !== "object"
        || !input.providerState || !provider.states.includes(input.providerState.status)
      ) invalid();
      const candidate = input.candidate;
      if (!candidate || !provider.eventRef.test(String(candidate.event_ref || ""))) invalid();
      const eventUrl = provider.url(candidate.canonical_url, candidate.event_ref);
      const title = text(candidate.title, 500);
      const startsAt = exactInstant(candidate.starts_at);
      const endsAt = exactInstant(candidate.ends_at);
      if (Date.parse(endsAt) <= Date.parse(startsAt)) invalid();
      const venue = text(candidate.venue_address || candidate.venue_name || "See event page", 2_000);
      const identity = checkpointPath(stateDir, input.provider, candidate.event_ref, eventUrl);
      let checkpoint = readCheckpoint(stateDir, identity.file, provider, candidate, identity.canonicalUrlSha256);
      let screenshot;
      if (checkpoint) {
        if (checkpoint.status !== input.providerState.status) invalid();
        screenshot = await validateCheckpointEvidence(provider, checkpoint, tenantId);
      } else {
        const captured = await captureProviderEvidence({ provider, providerName: input.provider, page: input.page, candidate, providerStatus: input.providerState.status, tenantId, now, canonicalUrlSha256: identity.canonicalUrlSha256 });
        assertNoSymlinkPath(stateDir, identity.file);
        immutableJson(identity.file, captured.checkpointValue);
        checkpoint = readCheckpoint(stateDir, identity.file, provider, candidate, identity.canonicalUrlSha256);
        screenshot = captured.screenshot;
      }

      const idempotencyValue = identity.canonicalUrlSha256;
      const timeMin = new Date(Date.parse(startsAt) - 60_000).toISOString();
      const timeMax = new Date(Date.parse(endsAt) + 60_000).toISOString();
      const before = await calendar.findConnectorEvents({ calendarId, idempotencyValue, timeMin, timeMax });
      if (!Array.isArray(before) || before.length > 1) invalid();
      const expectedCalendar = before.length === 1
        ? calendarReceipt(before[0])
        : calendarReceipt(await calendar.createConnectorEvent({ calendarId, idempotencyValue, title, startAt: startsAt, endAt: endsAt, location: venue, canonicalUrl: eventUrl }));
      const after = await calendar.findConnectorEvents({ idempotencyValue, calendarId, timeMin, timeMax });
      if (!Array.isArray(after) || after.length !== 1) invalid();
      const verifiedCalendar = calendarReceipt(after[0]);
      if (verifiedCalendar.id !== expectedCalendar.id || verifiedCalendar.htmlLink !== expectedCalendar.htmlLink) invalid();
      const calendarReadbackAt = exactInstant(now());

      const status = input.providerState.status;
      const message = [
        "Connector::: イベント申込を確認しました",
        `provider: ${input.provider}`,
        `event: ${title}`,
        `status: ${status}`,
        `starts at: ${startsAt}`,
        `calendar event ID: ${verifiedCalendar.id}`,
      ].join("\n");
      const messageId = parseOpenClawMessageId(await sendMessage(message, {
        telegramTarget,
        idempotencyKey: `connector-evidence:${idempotencyValue}`,
      }));
      const photoId = parseOpenClawMessageId(await sendPhoto(screenshot, {
        telegramTarget,
        caption: input.provider === "luma" ? `Connector::: ${title} / ${status}` : `Connector::: ${input.provider} / ${title} / ${status}`,
      }));

      const core = Object.freeze({
        schema_version: 1,
        status: "applied_bundle",
        provider: input.provider,
        event_ref: candidate.event_ref,
        provider_status: status,
        provider_receipt_ref: checkpoint.receiptRef,
        artifact_ref: checkpoint.artifactRef,
        artifact_sha256: checkpoint.artifactSha256,
        calendar_event_id: verifiedCalendar.id,
        calendar_event_url: verifiedCalendar.htmlLink,
        calendar_readback_at: calendarReadbackAt,
        telegram_message_provider_id: messageId,
        telegram_photo_provider_id: photoId,
        created_at: checkpoint.observedAt,
      });
      const digest = createHash("sha256").update(stableJson(core)).digest("hex");
      const bundle = Object.freeze({ bundle_id: `applied-bundle:${digest}`, ...core });
      immutableJson(path.join(stateDir, "applied-bundles", `${digest}.json`), bundle);
      return bundle;
    },
  });
}

module.exports = { createMinimalEvidenceChain };
