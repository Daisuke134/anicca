"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const JOB_ID = /^outbound-event:[0-9a-f]{64}$/;
const MESSAGE_ID = /^[a-zA-Z0-9._:-]{1,500}$/;
const RECEIPT_REF = /^gmail-message:\/\/([a-z0-9][a-z0-9._-]{0,127})\/([0-9a-f]{64})$/i;
const URL_TOKEN = /https:\/\/[^\s<>"'`]+/gi;
const VERIFIED_MESSAGES = new WeakSet();

function tenantId(value) {
  const result = String(value == null ? "" : value).trim();
  if (!TENANT.test(result)) throw new Error("Luma confirmation tenant invalid");
  return result;
}

function jobId(value) {
  const result = String(value == null ? "" : value).trim();
  if (!JOB_ID.test(result)) throw new Error("Luma confirmation job invalid");
  return result;
}

function exactInstant(value, label) {
  const result = String(value == null ? "" : value).trim();
  const parsed = Date.parse(result);
  if (!Number.isFinite(parsed) || !/[zZ]|[+-]\d\d:\d\d$/.test(result)) {
    throw new Error(`Luma confirmation ${label} invalid`);
  }
  return { milliseconds: parsed, iso: new Date(parsed).toISOString() };
}

function receivedInterval(message = {}) {
  if (message.internalDate) {
    const exact = exactInstant(message.internalDate, "received time");
    return { lowerMs: exact.milliseconds, upperMs: exact.milliseconds };
  }
  const match = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/.exec(String(message.date || ""));
  if (!match) throw new Error("Luma confirmation received time invalid");
  const parts = match.slice(1).map(Number);
  const lowerMs = new Date(parts[0], parts[1] - 1, parts[2], parts[3], parts[4], 0, 0).getTime();
  const check = new Date(lowerMs);
  if (
    check.getFullYear() !== parts[0]
    || check.getMonth() !== parts[1] - 1
    || check.getDate() !== parts[2]
    || check.getHours() !== parts[3]
    || check.getMinutes() !== parts[4]
  ) {
    throw new Error("Luma confirmation received time invalid");
  }
  return { lowerMs, upperMs: lowerMs + 59_999 };
}

function canonicalLumaUrl(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value).trim());
  } catch {
    throw new Error("Luma confirmation event URL invalid");
  }
  if (
    url.protocol !== "https:"
    || !/^(?:www\.)?(?:luma\.com|lu\.ma)$/i.test(url.hostname)
    || !/^\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)
  ) {
    throw new Error("Luma confirmation event URL invalid");
  }
  return `https://${url.hostname.toLowerCase()}${url.pathname.replace(/\/$/, "")}`;
}

function senderDomain(value) {
  const match = /<?[^<>\s@]+@([^<>\s]+)>?\s*$/.exec(String(value || "").trim());
  return match ? match[1].toLowerCase() : "";
}

function hasExactEventUrl(body, expected) {
  for (const token of String(body || "").match(URL_TOKEN) || []) {
    try {
      if (canonicalLumaUrl(token.replace(/[),.;!?]+$/, "")) === expected) return true;
    } catch {}
  }
  return false;
}

function verifyLumaConfirmationMessage(input = {}) {
  const tenant = tenantId(input.tenantId);
  const job = jobId(input.jobId);
  const eventUrl = canonicalLumaUrl(input.eventUrl);
  const title = String(input.eventTitle == null ? "" : input.eventTitle).trim();
  if (!title || title.length > 300) throw new Error("Luma confirmation event title invalid");
  const started = exactInstant(input.registrationStartedAt, "registration start time");
  const completed = exactInstant(input.registrationCompletedAt, "registration time");
  if (completed.milliseconds < started.milliseconds) {
    throw new Error("Luma confirmation registration interval invalid");
  }
  const message = input.message || {};
  const providerId = String(message.id == null ? "" : message.id).trim();
  if (!MESSAGE_ID.test(providerId)) throw new Error("Luma confirmation message ID invalid");

  const interval = receivedInterval(message);
  if (
    interval.upperMs < started.milliseconds
    || interval.lowerMs > completed.milliseconds + 30 * 60 * 1000
  ) {
    throw new Error("Luma confirmation outside registration attempt");
  }
  const domain = senderDomain(message.from);
  if (domain !== "luma.com" && !domain.endsWith(".luma-mail.com")) {
    throw new Error("Luma confirmation sender invalid");
  }
  const subject = String(message.subject || "");
  const completedSubject = /(?:参加登録|登録).{0,20}(?:完了|確定)/u.test(subject)
    || /(?:registration|rsvp).{0,30}(?:complete|confirmed)/i.test(subject);
  if (!subject.includes(title) || !completedSubject) {
    throw new Error("Luma confirmation subject mismatch");
  }
  if (!hasExactEventUrl(message.body, eventUrl)) {
    throw new Error("Luma confirmation event URL mismatch");
  }

  const receipt = Object.freeze({
    kind: "confirmation_mail",
    provider_id: providerId,
    observed_at: new Date(interval.upperMs).toISOString(),
    tenant_id: tenant,
    job_id: job,
    event_url: eventUrl,
  });
  VERIFIED_MESSAGES.add(receipt);
  return receipt;
}

function lumaConfirmationMessageFromGog(value = {}) {
  const message = value.message || {};
  const headers = value.headers || {};
  const timestamp = Number(message.internalDate);
  if (!Number.isFinite(timestamp) || timestamp < 0) {
    throw new Error("Gmail confirmation internal date invalid");
  }
  return {
    id: String(message.id || ""),
    internalDate: new Date(timestamp).toISOString(),
    from: String(headers.from || ""),
    subject: String(headers.subject || ""),
    body: String(value.body || ""),
  };
}

function rootDir(value) {
  const root = path.resolve(String(value || ""));
  if (!path.isAbsolute(root) || root === path.parse(root).root) {
    throw new Error("Luma confirmation data directory invalid");
  }
  return root;
}

function atomicWrite(file, bytes) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) {
      throw new Error("Luma confirmation immutable receipt collision");
    }
    return;
  }
  const temporary = `${file}.tmp-${process.pid}-${randomUUID()}`;
  fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
  fs.renameSync(temporary, file);
}

function createLumaConfirmationMailStore(options = {}) {
  const dataDir = rootDir(options.dataDir);
  const receiptFile = (tenant, hash) => path.join(
    dataDir,
    "tenants",
    tenantId(tenant),
    "outbound",
    "luma",
    "confirmation-mails",
    `${hash}.json`,
  );

  return Object.freeze({
    async record(receipt = {}) {
      if (
        !VERIFIED_MESSAGES.has(receipt)
        ||
        receipt.kind !== "confirmation_mail"
        || !MESSAGE_ID.test(String(receipt.provider_id || ""))
      ) {
        throw new Error("Luma confirmation verified receipt required");
      }
      const tenant = tenantId(receipt.tenant_id);
      const job = jobId(receipt.job_id);
      const eventUrl = canonicalLumaUrl(receipt.event_url);
      const observedAt = exactInstant(receipt.observed_at, "observed time").iso;
      const safe = {
        kind: "confirmation_mail",
        provider_id: String(receipt.provider_id),
        observed_at: observedAt,
        tenant_id: tenant,
        job_id: job,
        event_url: eventUrl,
      };
      const bytes = Buffer.from(`${JSON.stringify(safe)}\n`, "utf8");
      const hash = createHash("sha256").update(bytes).digest("hex");
      atomicWrite(receiptFile(tenant, hash), bytes);
      return Object.freeze({ external_receipt_ref: `gmail-message://${tenant}/${hash}` });
    },

    async readExternalReceipt(requestTenantId, ref) {
      const tenant = tenantId(requestTenantId);
      const match = RECEIPT_REF.exec(String(ref || ""));
      if (!match || match[1] !== tenant) throw new Error("Luma confirmation mail unavailable");
      try {
        const bytes = fs.readFileSync(receiptFile(tenant, match[2]));
        if (createHash("sha256").update(bytes).digest("hex") !== match[2]) {
          throw new Error("integrity mismatch");
        }
        const receipt = JSON.parse(bytes.toString("utf8"));
        if (
          receipt.kind !== "confirmation_mail"
          || receipt.tenant_id !== tenant
          || !MESSAGE_ID.test(String(receipt.provider_id || ""))
          || !JOB_ID.test(String(receipt.job_id || ""))
        ) {
          throw new Error("invalid receipt");
        }
        return Object.freeze({
          kind: receipt.kind,
          provider_id: receipt.provider_id,
          observed_at: exactInstant(receipt.observed_at, "observed time").iso,
        });
      } catch {
        throw new Error("Luma confirmation mail unavailable");
      }
    },
  });
}

module.exports = {
  createLumaConfirmationMailStore,
  lumaConfirmationMessageFromGog,
  verifyLumaConfirmationMessage,
};
