// lib/transport/mail-gog.js — LOCAL mail transport (#74 slice4). BYOK: the user's own `gog` Gmail CLI.
// Same interface as mail-unipile.js (send(to,subject,body)→bool, listInbox({limit})→items[]). `run`
// injectable for tests. listInbox shapes items to {subject, body} so ask.js's m.body_plain||m.body||
// m.snippet read still works.
"use strict";

const { execFile, execFileSync } = require("node:child_process");
const path = require("node:path");
const { promisify } = require("node:util");

const execFileAsync = promisify(execFile);

function parseReceiptInterval(value) {
  const raw = String(value || "");
  const minute = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/.exec(raw);
  if (minute) {
    const parts = minute.slice(1).map(Number);
    const lowerMs = new Date(parts[0], parts[1] - 1, parts[2], parts[3], parts[4], 0, 0).getTime();
    const check = new Date(lowerMs);
    if (check.getFullYear() !== parts[0] || check.getMonth() !== parts[1] - 1 || check.getDate() !== parts[2] ||
        check.getHours() !== parts[3] || check.getMinutes() !== parts[4]) return null;
    return { lowerMs, upperMs: lowerMs + 59999 };
  }
  const exact = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.exec(raw);
  if (!exact) return null;
  const [year, month, day, hour, minuteValue, second] = exact.slice(1).map(Number);
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  if (month < 1 || month > 12 || day < 1 || day > daysInMonth || hour > 23 || minuteValue > 59 || second > 59) return null;
  const instantMs = Date.parse(raw);
  return Number.isFinite(instantMs) ? { lowerMs: instantMs, upperMs: instantMs } : null;
}

function makeGogMail({ bin, account, keyring, run, execFileSyncImpl = execFileSync } = {}) {
  const gogBin = bin || process.env.GOG_BIN || "gog";
  const acct = account || process.env.GOG_ACCOUNT || "";
  const keyringPwd = keyring != null ? keyring : (process.env.GOG_KEYRING_PASSWORD || "");
  const injected = run || (execFileSyncImpl !== execFileSync && ((args, timeout = 15000) =>
    execFileSyncImpl(gogBin, [...args, "--account", acct], {
      env: { ...process.env, GOG_KEYRING_PASSWORD: keyringPwd, GOG_ACCOUNT: acct },
      encoding: "utf8", timeout,
    })));
  const exec = injected
    ? async (args, timeout = 15000) => injected(args, timeout)
    : async (args, timeout = 15000, signal) => {
      const { stdout } = await execFileAsync(gogBin, [...args, "--account", acct], {
        env: { ...process.env, GOG_KEYRING_PASSWORD: keyringPwd, GOG_ACCOUNT: acct },
        encoding: "utf8", timeout, signal,
      });
      return stdout;
    };

  return {
    kind: "gog",
    ready: () => !!acct,
    async send(to, subject, body) {
      if (!acct || !to) return false;
      // glued --flag=value form so a leading "-" in any value can't be parsed by gog as a flag.
      try {
        const out = await exec(["gmail", "send", `--to=${to}`, `--subject=${subject || ""}`, `--body=${body || ""}`, "--json"]);
        const j = JSON.parse(out);
        return !!(j && (j.id || j.messageId));
      } catch { return false; }
    },
    // Recent inbox messages with bodies, newest first. Shaped for the ask.js reply loop.
    async listInbox({ limit = 15 } = {}) {
      if (!acct) return [];
      let hits = [];
      try {
        const d = JSON.parse(await exec(["gmail", "search", "newer_than:2d", "-j", `--max=${limit}`]));
        hits = (d.threads || d.messages || (Array.isArray(d) ? d : [])).map((t) => ({ id: t.id, subject: t.subject || "" }));
      } catch { return []; }
      const out = [];
      for (const h of hits) {
        if (!h.id || /^-/.test(String(h.id))) continue; // positional id can't be flag-like
        try {
          const m = JSON.parse(await exec(["gmail", "get", h.id, "-j"]));
          const subject = (m.headers && (m.headers.subject || m.headers.Subject)) || m.subject || h.subject || "";
          out.push({ subject, body: m.body || "" });
        } catch { out.push({ subject: h.subject, body: "" }); }
      }
      return out;
    },
    async findLatestGoogleCloudInvoice() {
      if (!acct) return null;
      try {
        const query = 'from:payments-noreply@google.com subject:"Google Cloud Platform & APIs:" has:attachment filename:pdf newer_than:400d';
        const d = JSON.parse(await exec(["gmail", "messages", "search", query, "-j", "--max=10", "--gmail-no-send"]));
        const hits = Array.isArray(d.messages) ? d.messages : Array.isArray(d.threads) ? d.threads : Array.isArray(d) ? d : [];
        const valid = hits.filter((h) => {
          const id = String(h.id || ""), from = String(h.from || ""), date = String(h.date || "");
          const address = (from.match(/^.*<([^>]+)>$/) || [])[1] || from;
          return /^[a-f0-9]+$/i.test(id) && address === "payments-noreply@google.com" &&
            String(h.subject || "").startsWith("Google Cloud Platform & APIs:") &&
            /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(date) && parseReceiptInterval(date);
        }).sort((a, b) => String(b.date).localeCompare(String(a.date)));
        const hit = valid[0];
        if (!hit) return null;
        const m = JSON.parse(await exec(["gmail", "get", hit.id, "-j", "--format=full", "--gmail-no-send"]));
        const attachments = Array.isArray(m.attachments) ? m.attachments : [];
        if (attachments.length !== 1) return null;
        const a = attachments[0], filename = String(a.filename || ""), attachmentId = String(a.attachmentId || "");
        if (a.mimeType !== "application/pdf" || !/^[A-Za-z0-9][A-Za-z0-9._ -]*\.pdf$/i.test(filename) ||
            !/^[A-Za-z0-9_-]+$/.test(attachmentId) || !Number.isSafeInteger(a.size) || a.size <= 0) return null;
        return Object.freeze({ messageId: hit.id, attachmentId, filename, size: a.size,
          receivedAtLocal: hit.date, source: "google_cloud_invoice_gmail" });
      } catch { return null; }
    },
    async downloadGoogleCloudInvoice(locator, outPath) {
      try {
        const messageId = locator && String(locator.messageId || ""), attachmentId = locator && String(locator.attachmentId || "");
        if (!acct || !locator || locator.source !== "google_cloud_invoice_gmail" || !/^[a-f0-9]+$/i.test(messageId) ||
            !/^[A-Za-z0-9_-]+$/.test(attachmentId) || typeof outPath !== "string" || !path.isAbsolute(outPath) ||
            !/\.pdf$/i.test(outPath) || /[\0\r\n]/.test(outPath)) return null;
        const result = JSON.parse(await exec(["gmail", "attachment", messageId, attachmentId, `--out=${outPath}`, "-j", "--gmail-no-send"]));
        if (!result || result.path !== outPath || !Number.isSafeInteger(result.bytes) || result.bytes <= 0 || typeof result.cached !== "boolean") return null;
        return Object.freeze({ bytes: result.bytes, cached: result.cached });
      } catch { return null; }
    },
    async readLatestAnthropicSubscriptionReceipt() {
      if (!acct) return null;
      try {
        const query = 'from:(mail.anthropic.com) subject:"Your receipt from Anthropic, PBC" newer_than:400d';
        const d = JSON.parse(await exec(["gmail", "messages", "search", query, "-j", "--max=10", "--gmail-no-send"]));
        const hits = Array.isArray(d.messages) ? d.messages : Array.isArray(d.threads) ? d.threads : Array.isArray(d) ? d : [];
        const valid = hits.filter((h) => {
          const id = String(h && h.id || ""), from = String(h && h.from || ""), date = String(h && h.date || ""), addresses = from.match(/[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+/ig) || [];
          return /^[a-f0-9]+$/i.test(id) && addresses.length === 1 && addresses[0].toLowerCase().endsWith("@mail.anthropic.com") &&
            /^Your receipt from Anthropic, PBC #\d{4}-\d{4}-\d{4}$/.test(String(h && h.subject || "")) &&
            /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(date) && parseReceiptInterval(date);
        }).sort((a, b) => String(b.date).localeCompare(String(a.date)));
        const hit = valid[0]; if (!hit) return null;
        const raw = JSON.parse(await exec(["gmail", "raw", hit.id, "-j", "--gmail-no-send"]));
        const headers = raw && raw.payload && Array.isArray(raw.payload.headers) ? raw.payload.headers : [];
        const auth = headers.filter((h) => /^authentication-results$/i.test(String(h && h.name || "")));
        if (auth.length !== 1 || typeof auth[0].value !== "string" || !/^mx\.google\.com;/i.test(auth[0].value)) return null;
        const clauses = auth[0].value.split(";").map((c) => c.trim().toLowerCase());
        if (!clauses.some((c) => /(^|\s)dkim=pass(?:\s|$)/.test(c) && (/(^|\s)header\.i=@mail\.anthropic\.com(?:\s|$)/.test(c) || /(^|\s)header\.d=mail\.anthropic\.com(?:\s|$)/.test(c))) ||
            !clauses.some((c) => /(^|\s)dmarc=pass(?:\s|$)/.test(c) && /(^|\s)header\.from=mail\.anthropic\.com(?:\s|$)/.test(c))) return null;
        const m = JSON.parse(await exec(["gmail", "get", hit.id, "-j", "--format=full", "--sanitize-content", "--gmail-no-send"]));
        if (!m || typeof m !== "object" || Array.isArray(m) || typeof m.body !== "string" || !m.body || m.body.length > 20000 ||
            !m.headers || m.headers.from !== hit.from || m.headers.subject !== hit.subject) return null;
        return Object.freeze({ source: "anthropic_subscription_receipt_gmail", receivedAtLocal: hit.date, body: m.body });
      } catch { return null; }
    },
    async findReceipt({ nonce, afterMs }) {
      if (!acct || !/^[a-f0-9]{16,64}$/i.test(String(nonce || ""))) return null;
      try {
        const signal = arguments[0] && arguments[0].signal;
        const query = `in:anywhere newer_than:1d \"${nonce}\"`;
        const d = JSON.parse(await exec(["gmail", "messages", "search", query, "-j", "--max=10", "--include-body"], 15000, signal));
        const messages = d.messages || (Array.isArray(d) ? d : []);
        for (const message of messages) {
          if (!message.id || /^-/.test(String(message.id))) continue;
          const subject = String(message.subject || "");
          const body = String(message.body || "");
          const interval = parseReceiptInterval(message.date);
          const sameRun = interval && interval.upperMs >= afterMs;
          if ((subject.includes(nonce) || body.includes(nonce)) && sameRun) {
            return { id: String(message.id), receivedAtLowerMs: interval.lowerMs,
              receivedAtUpperMs: interval.upperMs, matchedNonce: nonce };
          }
        }
      } catch {}
      return null;
    },
  };
}

module.exports = { makeGogMail };
