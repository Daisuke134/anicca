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
const RECEIPT_REF = /^provider-receipt:\/\/luma\/[0-9a-f]{64}$/;
const PEATIX_EVENT_REF = /^peatix-event:\/\/event\/([1-9][0-9]*)$/;
const PEATIX_RECEIPT_REF = /^provider-receipt:\/\/peatix\/[0-9a-f]{64}$/;
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
    luma: { eventRef: EVENT_REF, receiptRef: RECEIPT_REF, url: lumaUrl, states: ["registered", "pending"], store: lumaEvidenceStore },
    peatix: { eventRef: PEATIX_EVENT_REF, receiptRef: PEATIX_RECEIPT_REF, url: peatixUrl, states: ["registered"], store: peatixEvidenceStore },
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
        !provider || !input.page || (input.provider === "peatix"
          ? typeof input.page.goto !== "function" || typeof input.page.url !== "function" || typeof input.page.evaluate !== "function"
          : typeof input.page.setContent !== "function") || typeof input.page.screenshot !== "function"
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
      const observedAt = exactInstant(now());

      const receipt = receiptHtml(input.provider, input.providerState.status, candidate.event_ref);
      if (input.provider === "peatix") {
        try {
          await input.page.goto("about:blank", { waitUntil: "domcontentloaded", timeout: 30_000 });
          if (String(input.page.url()) !== "about:blank") invalid();
          const rendered = await input.page.evaluate((html) => {
            document.open(); document.write(html); document.close();
            const root = document.querySelector("body > dl");
            return root !== null && document.querySelectorAll("body > dl > dt").length === 3 && document.querySelectorAll("body > dl > dd").length === 3;
          }, receipt);
          if (rendered !== true) invalid();
        } catch { invalid(); }
      } else {
        try { await input.page.setContent(receipt); } catch { invalid(); }
      }
      const screenshot = await input.page.screenshot({ type: "png", fullPage: true });
      if (
        !Buffer.isBuffer(screenshot) || screenshot.length < 5_000
        || !screenshot.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
      ) invalid();
      const artifactSha = createHash("sha256").update(screenshot).digest("hex");
      const evidence = await provider.store.record({
        tenantId,
        eventRef: candidate.event_ref,
        observedAt,
        screenshot,
      });
      const artifactMatch = ARTIFACT_REF.exec(String(evidence && evidence.artifact_ref || ""));
      if (
        !provider.receiptRef.test(String(evidence && evidence.external_receipt_ref || ""))
        || !artifactMatch || artifactMatch[1] !== artifactSha
      ) invalid();

      const idempotencyValue = createHash("sha256").update(eventUrl).digest("hex");
      const timeMin = new Date(Date.parse(startsAt) - 60_000).toISOString();
      const timeMax = new Date(Date.parse(endsAt) + 60_000).toISOString();
      const before = await calendar.findConnectorEvents({ calendarId, idempotencyValue, timeMin, timeMax });
      if (!Array.isArray(before) || before.length > 1) invalid();
      const expectedCalendar = before.length === 1
        ? calendarReceipt(before[0])
        : calendarReceipt(await calendar.createConnectorEvent({
          calendarId,
          idempotencyValue,
          title,
          startAt: startsAt,
          endAt: endsAt,
          location: venue,
          canonicalUrl: eventUrl,
        }));
      const after = await calendar.findConnectorEvents({ calendarId, idempotencyValue, timeMin, timeMax });
      if (!Array.isArray(after) || after.length !== 1) invalid();
      const verifiedCalendar = calendarReceipt(after[0]);
      if (
        verifiedCalendar.id !== expectedCalendar.id
        || verifiedCalendar.htmlLink !== expectedCalendar.htmlLink
      ) invalid();

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
        provider_receipt_ref: evidence.external_receipt_ref,
        artifact_ref: evidence.artifact_ref,
        artifact_sha256: artifactSha,
        calendar_event_id: verifiedCalendar.id,
        calendar_event_url: verifiedCalendar.htmlLink,
        calendar_readback_at: observedAt,
        telegram_message_provider_id: messageId,
        telegram_photo_provider_id: photoId,
        created_at: observedAt,
      });
      const digest = createHash("sha256").update(stableJson(core)).digest("hex");
      const bundle = Object.freeze({ bundle_id: `applied-bundle:${digest}`, ...core });
      immutableJson(path.join(stateDir, "applied-bundles", `${digest}.json`), bundle);
      return bundle;
    },
  });
}

module.exports = { createMinimalEvidenceChain };
