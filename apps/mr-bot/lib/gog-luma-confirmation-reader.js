"use strict";

const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const { lumaConfirmationMessageFromGog } = require("./luma-confirmation-mail.js");
const { trustedLumaSender } = require("./gog-luma-code-reader.js");

const execFileAsync = promisify(execFile);
const DEFAULT_GOG = "/opt/homebrew/bin/gog";

function unavailable() {
  return new Error("Luma confirmation mail unavailable");
}

function parseJson(value) {
  try { return JSON.parse(String(value || "")); } catch { throw unavailable(); }
}

function addresses(value) {
  return (String(value || "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [])
    .map((address) => address.toLowerCase());
}

async function runGog(args, options) {
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

function createGogLumaConfirmationReader(options = {}) {
  const run = options.run || ((args) => runGog(args, options));
  const attempts = Number.isSafeInteger(options.attempts)
    ? options.attempts
    : (options.run ? 1 : 6);
  const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  if (typeof run !== "function" || typeof sleep !== "function" || attempts < 1 || attempts > 10) {
    throw unavailable();
  }

  return async function readConfirmation(input = {}) {
    const account = String(input.account || "").trim().toLowerCase();
    const afterMs = Number(input.afterMs);
    if (!/^[^@\s]+@[^@\s]+$/.test(account) || !Number.isSafeInteger(afterMs) || afterMs < 0) {
      throw unavailable();
    }
    const searchArgs = [
      "gmail", "messages", "search",
      `after:${Math.max(0, Math.floor((afterMs - 5_000) / 1_000))} (from:luma.com OR from:luma-mail.com)`,
      "--account", account,
      "--max", "10", "--json", "--results-only", "--no-input",
    ];
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const rows = parseJson(await run(searchArgs));
      if (!Array.isArray(rows) || rows.length > 10) throw unavailable();
      const candidates = [];
      for (const row of rows) {
        const id = String(row && row.id || "").trim();
        if (!id || id.length > 500) continue;
        const detail = parseJson(await run([
          "gmail", "get", id, "--account", account, "--json", "--no-input",
        ]));
        const headers = detail && detail.headers || {};
        const internalDate = Number(detail && detail.message && detail.message.internalDate);
        if (
          !Number.isSafeInteger(internalDate)
          || internalDate < afterMs - 5_000
          || !trustedLumaSender(headers.from)
          || !addresses(headers.to).includes(account)
          || !String(detail.body || "").trim()
        ) continue;
        candidates.push({ internalDate, message: lumaConfirmationMessageFromGog(detail) });
      }
      candidates.sort((a, b) => b.internalDate - a.internalDate);
      if (candidates[0]) return candidates[0].message;
      if (attempt + 1 < attempts) await sleep(5_000);
    }
    throw unavailable();
  };
}

module.exports = { createGogLumaConfirmationReader };
