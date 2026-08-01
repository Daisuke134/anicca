"use strict";

const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const execFileAsync = promisify(execFile);

const GMAIL_ID = /^[0-9a-f]{16,32}$/i;
const EMAIL = /^[^\s@]+@[^\s@]+$/;
const TRUSTED_THREADS = new WeakSet();

function fail() {
  throw new Error("funder gog thread reader invalid");
}

function makeFunderGogThreadReader(options = {}) {
  const bin = String(options.bin || process.env.GOG_BIN || "gog");
  const account = String(options.account || process.env.GOG_ACCOUNT || "").trim();
  const injected = options.run;
  if (!EMAIL.test(account) || (injected != null && typeof injected !== "function")) fail();
  const run = injected || (async (args) => {
    const { stdout } = await execFileAsync(bin, args, {
      encoding: "utf8", timeout: 60_000,
      env: { ...process.env, GOG_ACCOUNT: account },
    });
    return stdout;
  });
  return Object.freeze({
    kind: "gog_exact_thread_read_only",
    async getThread(threadId) {
      const id = String(threadId || "").toLowerCase();
      if (!GMAIL_ID.test(id)) fail();
      try {
        const text = await run([
          "--gmail-no-send", "--no-input", "gmail", "thread", "get",
          `--account=${account}`, "--json", "--wrap-untrusted", "--full",
          "--sanitize-content", id,
        ]);
        const value = JSON.parse(String(text));
        if (!value || !value.thread || String(value.thread.id || "").toLowerCase() !== id
          || !Array.isArray(value.thread.messages)) fail();
        TRUSTED_THREADS.add(value);
        return value;
      } catch (error) {
        if (error && error.message === "funder gog thread reader invalid") throw error;
        fail();
      }
    },
  });
}

function isTrustedFunderGogThread(value) {
  return !!(value && typeof value === "object" && TRUSTED_THREADS.has(value));
}

module.exports = { makeFunderGogThreadReader, isTrustedFunderGogThread };
