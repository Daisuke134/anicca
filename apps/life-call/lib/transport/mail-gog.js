// lib/transport/mail-gog.js — LOCAL mail transport (#74 slice4). BYOK: the user's own `gog` Gmail CLI.
// Same interface as mail-unipile.js (send(to,subject,body)→bool, listInbox({limit})→items[]). `run`
// injectable for tests. listInbox shapes items to {subject, body} so ask.js's m.body_plain||m.body||
// m.snippet read still works.
"use strict";

const { execFileSync } = require("node:child_process");

function makeGogMail({ bin, account, keyring, run } = {}) {
  const gogBin = bin || process.env.GOG_BIN || "gog";
  const acct = account || process.env.GOG_ACCOUNT || "";
  const keyringPwd = keyring != null ? keyring : (process.env.GOG_KEYRING_PASSWORD || "");
  const exec = run || ((args, timeout = 30000) =>
    execFileSync(gogBin, [...args, "--account", acct], {
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
  };
}

module.exports = { makeGogMail };
