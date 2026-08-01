"use strict";

const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const { extractLumaCode } = require("../scripts/browser-auth-luma-bootstrap.js");

const execFileAsync = promisify(execFile);
const DEFAULT_GOG = "/opt/homebrew/bin/gog";

function unavailable() {
  return new Error("Luma authentication mail unavailable");
}

function required(value, max = 500) {
  const text = String(value == null ? "" : value).trim();
  return text && text.length <= max ? text : "";
}

function parseJson(value) {
  try {
    return JSON.parse(String(value || ""));
  } catch {
    throw unavailable();
  }
}

function emailAddresses(value) {
  return (String(value || "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [])
    .map((item) => item.toLowerCase());
}

function trustedLumaSender(value) {
  return emailAddresses(value).some((address) => {
    const domain = address.split("@").pop();
    return domain === "luma.com" || domain.endsWith(".luma-mail.com");
  });
}

async function runGog(args, options = {}) {
  try {
    const result = await execFileAsync(options.gogPath || DEFAULT_GOG, args, {
      env: options.env || process.env,
      encoding: "utf8",
      maxBuffer: 4 * 1024 * 1024,
      timeout: 30_000,
    });
    return result.stdout;
  } catch {
    throw unavailable();
  }
}

function createGogLumaCodeReader(options = {}) {
  const run = options.run || ((args) => runGog(args, options));
  if (typeof run !== "function") throw unavailable();

  return async function readLoginCode(input = {}) {
    const afterMs = Number(input.afterMs);
    const account = required(input.account, 320).toLowerCase();
    if (
      !Number.isSafeInteger(afterMs)
      || afterMs < 0
      || !/^[^@\s]+@[^@\s]+$/.test(account)
    ) throw unavailable();

    const afterSeconds = Math.max(0, Math.floor((afterMs - 5_000) / 1_000));
    const searchArgs = [
      "gmail", "messages", "search",
      `after:${afterSeconds} (from:luma.com OR from:luma-mail.com)`,
      "--account", account,
      "--max", "10", "--json", "--results-only", "--no-input",
    ];
    const found = parseJson(await run(searchArgs));
    if (!Array.isArray(found) || found.length > 10) throw unavailable();

    const valid = [];
    for (const row of found) {
      const id = required(row && row.id, 300);
      if (!id) continue;
      const detail = parseJson(await run([
        "gmail", "get", id,
        "--account", account,
        "--json", "--no-input",
      ]));
      const headers = detail && detail.headers || {};
      const internalDate = Number(detail && detail.message && detail.message.internalDate);
      const body = required(detail && detail.body, 2_000_000);
      if (
        !Number.isSafeInteger(internalDate)
        || internalDate < afterMs - 5_000
        || !trustedLumaSender(headers.from)
        || !emailAddresses(headers.to).includes(account)
        || !body
      ) continue;
      const code = extractLumaCode({
        from: headers.from,
        subject: headers.subject,
        text: body,
      });
      if (/^\d{6}$/.test(String(code || ""))) valid.push({ internalDate, code });
    }
    valid.sort((a, b) => b.internalDate - a.internalDate);
    if (!valid[0]) throw unavailable();
    return valid[0].code;
  };
}

module.exports = {
  createGogLumaCodeReader,
  trustedLumaSender,
};
