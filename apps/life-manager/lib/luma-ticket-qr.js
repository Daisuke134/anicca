"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const jsQR = require("jsqr");
const { PNG } = require("pngjs");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const JOB_ID = /^outbound-event:[0-9a-f]{64}$/;
const MESSAGE_ID = /^[a-zA-Z0-9._:-]{1,500}$/;
const GUEST_KEY = /^g-[A-Za-z0-9_-]{8,200}$/;
const EVENT_PATH = /^\/([A-Za-z0-9_-]+)\/?$/;
const TICKET_PATH = /^\/e\/ticket\/([A-Za-z0-9_-]+)\/?$/;
const CHECK_IN_PATH = /^\/check-in\/[A-Za-z0-9_-]+\/?$/;
const URL_TOKEN = /https:\/\/[^\s<>"'`]+/gi;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const ARTIFACT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const TICKET_REF = /^ticket:\/\/([a-z0-9][a-z0-9._-]{0,127})\/([0-9a-f]{64})$/i;
const BINDING_SECRETS = new WeakMap();
const VERIFIED_QR = new WeakMap();

function validTenant(value) {
  const text = String(value == null ? "" : value).trim();
  if (!TENANT.test(text)) throw new Error("Luma ticket tenant invalid");
  return text;
}

function validJob(value) {
  const text = String(value == null ? "" : value).trim();
  if (!JOB_ID.test(text)) throw new Error("Luma ticket job invalid");
  return text;
}

function validInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) {
    throw new Error("Luma ticket observed time invalid");
  }
  return new Date(parsed).toISOString();
}

function parseLumaUrl(value) {
  let url;
  try { url = new URL(String(value || "").replace(/&amp;/gi, "&")); } catch { return null; }
  if (
    url.protocol !== "https:"
    || !/^(?:www\.)?(?:luma\.com|lu\.ma)$/i.test(url.hostname)
    || url.username
    || url.password
  ) return null;
  return url;
}

function canonicalEvent(value) {
  const url = parseLumaUrl(value);
  const match = url && EVENT_PATH.exec(url.pathname);
  if (!url || !match) throw new Error("Luma ticket event URL invalid");
  return { url: `https://${url.hostname.toLowerCase()}/${match[1]}`, slug: match[1] };
}

function urlsFromBody(value) {
  return (String(value || "").replace(/&amp;/gi, "&").match(URL_TOKEN) || [])
    .map((token) => parseLumaUrl(token.replace(/[),.;!?]+$/, "")))
    .filter(Boolean);
}

function createLumaGuestBinding(input = {}) {
  const tenant = validTenant(input.tenantId);
  const job = validJob(input.jobId);
  const expected = canonicalEvent(input.eventUrl);
  const providerMessageId = String(input.providerMessageId || "").trim();
  if (!MESSAGE_ID.test(providerMessageId)) throw new Error("Luma ticket message ID invalid");
  const urls = urlsFromBody(input.body);
  const eventCandidates = urls.filter((url) => {
    const match = EVENT_PATH.exec(url.pathname);
    return match && match[1] === expected.slug && GUEST_KEY.test(url.searchParams.get("pk") || "");
  });
  const ticketCandidates = urls.filter((url) => (
    TICKET_PATH.test(url.pathname) && GUEST_KEY.test(url.searchParams.get("pk") || "")
  ));
  if (eventCandidates.length !== 1) throw new Error("Luma ticket event guest key unavailable");
  if (ticketCandidates.length !== 1) throw new Error("Luma ticket guest key unavailable");
  const guestKey = eventCandidates[0].searchParams.get("pk");
  if (ticketCandidates[0].searchParams.get("pk") !== guestKey) {
    throw new Error("Luma ticket guest key mismatch");
  }
  const guestKeyHash = createHash("sha256").update(guestKey, "utf8").digest("hex");
  const binding = Object.freeze({
    tenant_id: tenant,
    job_id: job,
    event_url: expected.url,
    provider_message_id: providerMessageId,
    guest_key_sha256: guestKeyHash,
  });
  BINDING_SECRETS.set(binding, Object.freeze({
    guestKey,
    eventSlug: expected.slug,
  }));
  return binding;
}

function decodeQrPng(bytes) {
  if (!Buffer.isBuffer(bytes)) return null;
  try {
    const png = PNG.sync.read(bytes);
    const decoded = jsQR(
      new Uint8ClampedArray(png.data.buffer, png.data.byteOffset, png.data.byteLength),
      png.width,
      png.height,
      { inversionAttempts: "attemptBoth" },
    );
    return decoded && typeof decoded.data === "string" ? decoded.data : null;
  } catch {
    return null;
  }
}

function matchingPayload(value, binding) {
  const secret = BINDING_SECRETS.get(binding);
  if (!secret) return false;
  const url = parseLumaUrl(value);
  const eventMatch = url && EVENT_PATH.exec(url.pathname);
  return Boolean(
    url
    && (
      (eventMatch && eventMatch[1] === secret.eventSlug)
      || CHECK_IN_PATH.test(url.pathname)
    )
    && url.searchParams.get("pk") === secret.guestKey
  );
}

async function clickTicketControl(page) {
  if (typeof page.clickExactTicketControl === "function") {
    return page.clickExactTicketControl();
  }
  if (typeof page.evaluate !== "function") return false;
  return page.evaluate(() => {
    for (const element of document.querySelectorAll(
      'button, a[role="button"], input[type="submit"]',
    )) {
      const label = (element.innerText || element.value || element.getAttribute("aria-label") || "")
        .replace(/\s+/g, " ").trim().toLowerCase();
      if (label === "マイチケット" || label === "my ticket") {
        element.click();
        return true;
      }
    }
    return false;
  });
}

async function candidatePngs(page) {
  if (typeof page.qrCandidates === "function") return page.qrCandidates();
  if (typeof page.waitForTimeout !== "function" || typeof page.locator !== "function") return [];
  await page.waitForTimeout(1_500);
  const svgs = page.locator("svg");
  const values = [];
  for (let index = 0; index < await svgs.count(); index += 1) {
    const element = svgs.nth(index);
    const box = await element.boundingBox();
    if (!box || box.width < 120 || box.height < 120 || box.width > 800 || box.height > 800) continue;
    values.push(await element.screenshot({ type: "png" }));
  }
  return values;
}

async function captureOfficialLumaTicketQr(page, binding, options = {}) {
  if (!BINDING_SECRETS.has(binding)) throw new Error("Luma guest binding provenance missing");
  if (!await clickTicketControl(page)) throw new Error("Luma ticket control unavailable");
  const decode = options.decodeQr || (async (bytes) => decodeQrPng(bytes));
  const candidates = await candidatePngs(page);
  const matches = [];
  for (const bytes of candidates) {
    if (
      !Buffer.isBuffer(bytes)
      || bytes.length < 5_000
      || !bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
    ) continue;
    let decoded;
    try { decoded = await decode(bytes); } catch { decoded = null; }
    if (matchingPayload(decoded, binding)) matches.push(bytes);
  }
  if (matches.length !== 1) throw new Error("Luma matching official QR unavailable");
  const bytes = matches[0];
  const pngHash = createHash("sha256").update(bytes).digest("hex");
  const observedAt = validInstant((options.observedAt || (() => new Date().toISOString()))());
  const verified = Object.freeze({
    kind: "ticket",
    tenant_id: binding.tenant_id,
    job_id: binding.job_id,
    event_url: binding.event_url,
    provider_message_id: binding.provider_message_id,
    guest_key_sha256: binding.guest_key_sha256,
    observed_at: observedAt,
    png_sha256: pngHash,
    png_size_bytes: bytes.length,
  });
  VERIFIED_QR.set(verified, bytes);
  return verified;
}

function dataRoot(value) {
  const root = path.resolve(String(value || ""));
  if (!path.isAbsolute(root) || root === path.parse(root).root) {
    throw new Error("Luma ticket data directory invalid");
  }
  return root;
}

function atomicWrite(file, bytes) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) throw new Error("Luma ticket immutable object collision");
    return;
  }
  const temporary = `${file}.tmp-${process.pid}-${randomUUID()}`;
  fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
  fs.renameSync(temporary, file);
}

function createLumaTicketQrStore(options = {}) {
  const root = dataRoot(options.dataDir);
  const tenantRoot = (tenant) => path.join(root, "tenants", validTenant(tenant), "outbound", "luma");
  return Object.freeze({
    async record(verified = {}) {
      const bytes = VERIFIED_QR.get(verified);
      if (!bytes) throw new Error("Luma verified QR required");
      const tenant = validTenant(verified.tenant_id);
      const receipt = {
        kind: "ticket",
        provider_id: verified.png_sha256,
        observed_at: validInstant(verified.observed_at),
        job_id: validJob(verified.job_id),
        event_url: canonicalEvent(verified.event_url).url,
        artifact_sha256: verified.png_sha256,
        guest_key_sha256: verified.guest_key_sha256,
      };
      const receiptBytes = Buffer.from(`${JSON.stringify(receipt)}\n`, "utf8");
      const receiptHash = createHash("sha256").update(receiptBytes).digest("hex");
      atomicWrite(path.join(root, "objects", "sha256", verified.png_sha256), bytes);
      atomicWrite(
        path.join(tenantRoot(tenant), "ticket-artifacts", `${verified.png_sha256}.json`),
        Buffer.from(`${JSON.stringify({ sha256: verified.png_sha256, job_id: verified.job_id })}\n`, "utf8"),
      );
      atomicWrite(path.join(tenantRoot(tenant), "ticket-receipts", `${receiptHash}.json`), receiptBytes);
      return Object.freeze({
        ticket_receipt_ref: `ticket://${tenant}/${receiptHash}`,
        artifact_ref: `object://sha256/${verified.png_sha256}`,
      });
    },

    async readArtifact(requestTenant, ref) {
      const tenant = validTenant(requestTenant);
      const match = ARTIFACT_REF.exec(String(ref || ""));
      if (!match) throw new Error("Luma ticket artifact unavailable");
      try {
        const marker = JSON.parse(fs.readFileSync(
          path.join(tenantRoot(tenant), "ticket-artifacts", `${match[1]}.json`),
          "utf8",
        ));
        const bytes = fs.readFileSync(path.join(root, "objects", "sha256", match[1]));
        if (
          marker.sha256 !== match[1]
          || !JOB_ID.test(String(marker.job_id || ""))
          || createHash("sha256").update(bytes).digest("hex") !== match[1]
        ) throw new Error("integrity mismatch");
        return bytes;
      } catch {
        throw new Error("Luma ticket artifact unavailable");
      }
    },

    async readTicketReceipt(requestTenant, ref) {
      const tenant = validTenant(requestTenant);
      const match = TICKET_REF.exec(String(ref || ""));
      if (!match || match[1] !== tenant) throw new Error("Luma ticket receipt unavailable");
      try {
        const bytes = fs.readFileSync(path.join(tenantRoot(tenant), "ticket-receipts", `${match[2]}.json`));
        if (createHash("sha256").update(bytes).digest("hex") !== match[2]) throw new Error("integrity mismatch");
        const receipt = JSON.parse(bytes.toString("utf8"));
        if (receipt.kind !== "ticket" || !/^[0-9a-f]{64}$/.test(receipt.provider_id)) {
          throw new Error("invalid receipt");
        }
        return Object.freeze({
          kind: "ticket",
          provider_id: receipt.provider_id,
          observed_at: validInstant(receipt.observed_at),
        });
      } catch {
        throw new Error("Luma ticket receipt unavailable");
      }
    },
  });
}

module.exports = {
  captureOfficialLumaTicketQr,
  createLumaGuestBinding,
  createLumaTicketQrStore,
  decodeQrPng,
};
