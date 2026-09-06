"use strict";

const path = require("node:path");
const fs = require("node:fs");
const { spawnSync } = require("node:child_process");
const { resolveDataRoot } = require("./runtime-paths.js");

const SAFE_WAKE_ID = /^[A-Za-z0-9][A-Za-z0-9:._-]{2,159}$/;
const REPORT_TARGET = /^-?[0-9]{5,20}$/;
const REPORT_FAILURE = "Telegram report delivery failed";
const PHOTO_FAILURE = "Telegram photo delivery failed";
const OPENCLAW_GATEWAY_TIMEOUT_MS = 65_000;

function parseOpenClawMessageId(output) {
  let value = output;
  if (typeof output === "string") {
    try { value = JSON.parse(output); } catch { value = null; }
  }
  const raw = value && value.messageId;
  const numeric = Number(raw);
  if (!Number.isSafeInteger(numeric) || numeric <= 0) {
    throw new Error("Telegram delivery needs a positive message ID");
  }
  return String(numeric);
}

async function notifyOpenClaw(message, options = {}) {
  const target = String(options.telegramTarget || "").trim();
  if (!target) throw new Error("Telegram target is required");
  const spawn = options.spawnSync || spawnSync;
  const result = spawn("openclaw", [
    "message", "send", "--channel", "telegram", "--target", target,
    "--message", message, "--json",
  ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  if (!result || result.status !== 0) {
    throw new Error(String(result && result.stderr || "Telegram delivery failed").trim());
  }
  return { messageId: parseOpenClawMessageId(String(result.stdout || "")) };
}

async function notifyOpenClawGateway(message, options = {}) {
  try {
    const target = options.telegramTarget;
    const idempotencyKey = options.idempotencyKey;
    if (
      typeof message !== "string" || !message || message.length > 4_096
      || typeof target !== "string" || !REPORT_TARGET.test(target)
      || typeof idempotencyKey !== "string" || !SAFE_WAKE_ID.test(idempotencyKey)
    ) throw new Error(REPORT_FAILURE);
    const spawn = options.spawnSync || spawnSync;
    const result = spawn("openclaw", [
      "gateway", "call", "send", "--timeout", "60000", "--params",
      JSON.stringify({ channel: "telegram", to: target, message, idempotencyKey }), "--json",
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: OPENCLAW_GATEWAY_TIMEOUT_MS });
    if (!result || result.status !== 0) throw new Error(REPORT_FAILURE);
    return { messageId: parseOpenClawMessageId(String(result.stdout || "")) };
  } catch {
    throw new Error(REPORT_FAILURE);
  }
}

async function notifyOpenClawPhoto(bytes, options = {}) {
  const target = options.telegramTarget;
  const idempotencyKey = options.idempotencyKey;
  if (
    !Buffer.isBuffer(bytes)
    || typeof target !== "string" || !REPORT_TARGET.test(target)
    || typeof idempotencyKey !== "string" || !SAFE_WAKE_ID.test(idempotencyKey)
  ) throw new Error("Telegram photo delivery invalid");
  const spawn = options.spawnSync || spawnSync;
  const remove = options.rmSync || fs.rmSync;
  let directory;
  try {
    const mediaRoot = path.join(resolveDataRoot(options.env || process.env), "media");
    fs.mkdirSync(mediaRoot, { recursive: true, mode: 0o700 });
    const rootStat = fs.lstatSync(mediaRoot);
    if (
      !rootStat.isDirectory() || rootStat.isSymbolicLink()
      || (typeof process.getuid === "function" && rootStat.uid !== process.getuid())
    ) throw new Error(PHOTO_FAILURE);
    fs.chmodSync(mediaRoot, 0o700);
    directory = fs.mkdtempSync(path.join(mediaRoot, "connector-telegram-photo-"));
    fs.chmodSync(directory, 0o700);
    const file = path.join(directory, "registered-page.png");
    fs.writeFileSync(file, bytes, { mode: 0o600, flag: "wx" });
    const result = spawn("openclaw", [
      "gateway", "call", "send", "--timeout", "60000", "--params",
      JSON.stringify({
        channel: "telegram",
        to: target,
        message: String(options.caption || ""),
        mediaUrl: file,
        forceDocument: true,
        idempotencyKey,
      }), "--json",
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    if (!result || result.status !== 0) throw new Error(PHOTO_FAILURE);
    return { messageId: parseOpenClawMessageId(String(result.stdout || "")) };
  } catch {
    throw new Error(PHOTO_FAILURE);
  } finally {
    if (directory) {
      try { remove(directory, { recursive: true, force: true }); }
      catch { throw new Error(PHOTO_FAILURE); }
    }
  }
}
module.exports = {
  parseOpenClawMessageId,
  notifyOpenClaw,
  notifyOpenClawGateway,
  notifyOpenClawPhoto,
};
