// lib/transport/mail-gog.js — LOCAL mail transport (#74 slice4). BYOK: the user's own `gog` Gmail CLI.
// Same interface as mail-unipile.js (send(to,subject,body)→bool, listInbox({limit})→items[]). `run`
// injectable for tests. listInbox shapes items to {subject, body} so ask.js's m.body_plain||m.body||
// m.snippet read still works.
"use strict";

const { execFileSync } = require("node:child_process");

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
  const exec = run || ((args, timeout = 30000) =>
    execFileSyncImpl(gogBin, [...args, "--account", acct], {
      env: { ...process.env, GOG_KEYRING_PASSWORD: keyringPwd, GOG_ACCOUNT: acct },
      encoding: "utf8", timeout,
    }));

  return {
    kind: "gog",
    ready: () => !!acct,
    async send(to, subject, body) {
      if (!acct || !to) return false;
      // glued --flag=value form so a leading "-" in any value can't be parsed by gog as a flag.
      try {
        const out = exec(["gmail", "send", `--to=${to}`, `--subject=${subject || ""}`, `--body=${body || ""}`, "--json"]);
        const j = JSON.parse(out);
        return !!(j && (j.id || j.messageId));
      } catch { return false; }
    },
    // Recent inbox messages with bodies, newest first. Shaped for the ask.js reply loop.
    async listInbox({ limit = 15 } = {}) {
      if (!acct) return [];
      let hits = [];
      try {
        const d = JSON.parse(exec(["gmail", "search", "newer_than:2d", "-j", `--max=${limit}`]));
        hits = (d.threads || d.messages || (Array.isArray(d) ? d : [])).map((t) => ({ id: t.id, subject: t.subject || "" }));
      } catch { return []; }
      const out = [];
      for (const h of hits) {
        if (!h.id || /^-/.test(String(h.id))) continue; // positional id can't be flag-like
        try {
          const m = JSON.parse(exec(["gmail", "get", h.id, "-j"]));
          const subject = (m.headers && (m.headers.subject || m.headers.Subject)) || m.subject || h.subject || "";
          out.push({ subject, body: m.body || "" });
        } catch { out.push({ subject: h.subject, body: "" }); }
      }
      return out;
    },
    async findReceipt({ nonce, afterMs }) {
      if (!acct || !/^[a-f0-9]{16,64}$/i.test(String(nonce || ""))) return null;
      try {
        const query = `in:anywhere newer_than:1d \"${nonce}\"`;
        const d = JSON.parse(exec(["gmail", "messages", "search", query, "-j", "--max=10", "--include-body"]));
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
