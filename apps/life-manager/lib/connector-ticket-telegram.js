"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const { parseOpenClawMessageId } = require("./outbound-guardian.js");
const { hashChatId } = require("./telegram.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const ARTIFACT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const PLACEHOLDER = /\{\{|\}\}|<placeholder>|TODO|TBD/i;

function text(value, label, max = 500) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!result || result.length > max || PLACEHOLDER.test(result)) {
    throw new Error(`Connector Telegram ${label} placeholder or value invalid`);
  }
  return result;
}

function instant(value, label) {
  const raw = String(value == null ? "" : value).trim();
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed) || !/[zZ]|[+-]\d\d:\d\d$/.test(raw)) {
    throw new Error(`Connector Telegram ${label} time invalid`);
  }
  return parsed;
}

function parts(milliseconds) {
  const result = {};
  for (const part of new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(milliseconds))) {
    if (part.type !== "literal") result[part.type] = part.value;
  }
  return result;
}

function eventUrl(value) {
  let url;
  try { url = new URL(String(value || "")); } catch { throw new Error("Connector Telegram event URL invalid"); }
  if (
    url.protocol !== "https:"
    || !/^(?:www\.)?(?:luma\.com|lu\.ma)$/i.test(url.hostname)
    || !/^\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)
    || url.username
    || url.password
  ) throw new Error("Connector Telegram event URL invalid");
  url.hash = "";
  url.search = "";
  return `https://${url.hostname.toLowerCase()}${url.pathname.replace(/\/$/, "")}`;
}

function calendarUrl(value) {
  let url;
  try { url = new URL(String(value || "")); } catch { throw new Error("Connector Telegram Calendar URL invalid"); }
  if (
    url.protocol !== "https:"
    || !/^(?:www\.)?google\.com$/i.test(url.hostname)
    || url.pathname !== "/calendar/event"
    || !url.searchParams.get("eid")
    || url.username
    || url.password
  ) throw new Error("Connector Telegram Calendar URL invalid");
  return url.toString();
}

function buildConnectorTicketCaption(input = {}) {
  const title = text(input.eventTitle, "event title", 300);
  const venue = text(input.venue, "venue", 500);
  const identity = text(input.registrationIdentity, "registration identity", 100);
  const reason = text(input.selectionReason, "selection reason", 500);
  const startMs = instant(input.startsAt, "start");
  const endMs = instant(input.endsAt, "end");
  if (endMs <= startMs) throw new Error("Connector Telegram event time invalid");
  const start = parts(startMs);
  const end = parts(endMs);
  const date = `${start.year}年${Number(start.month)}月${Number(start.day)}日（${start.weekday}）`;
  const when = `${date}${start.hour}:${start.minute}〜${end.hour}:${end.minute}`;
  const event = eventUrl(input.eventUrl);
  const calendar = calendarUrl(input.calendarUrl);
  const caption = [
    "🎟️ イベント参加の申込みが完了しました。",
    "",
    `イベント: ${title}`,
    `日時: ${when}`,
    `場所: ${venue}`,
    `申込者: ${identity}`,
    "",
    "このイベントを選んだ理由:",
    reason,
    "",
    "✅ Lumaの確認メールを受信済み",
    "✅ Google Calendarへ登録済み",
    "📱 当日の公式QRを添付しました",
    "",
    "イベントページ:",
    event,
    "",
    "カレンダー:",
    calendar,
  ].join("\n");
  if (caption.length > 1024) throw new Error("Connector Telegram caption too long");
  return caption;
}

async function sendOpenClawMedia(targetValue, bytes, caption, options = {}) {
  const target = String(targetValue == null ? "" : targetValue).trim();
  if (!target || target.length > 200) throw new Error("Telegram target invalid");
  if (!Buffer.isBuffer(bytes) || bytes.length < 5_000) throw new Error("Telegram PNG invalid");
  const defaultMediaRoot = process.platform === "win32"
    ? path.join(os.tmpdir(), `openclaw-${typeof process.getuid === "function" ? process.getuid() : "user"}`)
    : "/tmp/openclaw";
  const mediaRoot = path.resolve(String(options.mediaRoot || defaultMediaRoot));
  if (mediaRoot === path.parse(mediaRoot).root) throw new Error("OpenClaw media root invalid");
  fs.mkdirSync(mediaRoot, { recursive: true, mode: 0o700 });
  const rootStat = fs.lstatSync(mediaRoot);
  const currentUid = typeof process.getuid === "function" ? process.getuid() : null;
  if (
    !rootStat.isDirectory()
    || rootStat.isSymbolicLink()
    || (rootStat.mode & 0o077) !== 0
    || (currentUid != null && rootStat.uid !== currentUid)
  ) throw new Error("OpenClaw media root unsafe");
  const temporaryRoot = fs.mkdtempSync(path.join(mediaRoot, "life-manager-telegram-"));
  const temporaryFile = path.join(temporaryRoot, "ticket.png");
  fs.writeFileSync(temporaryFile, bytes, { mode: 0o600, flag: "wx" });
  try {
    const spawn = options.spawnSync || spawnSync;
    const result = spawn("openclaw", [
      "message", "send",
      "--channel", "telegram",
      "--target", target,
      "--media", temporaryFile,
      "--message", caption,
      "--json",
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    if (!result || result.status !== 0) {
      throw new Error(String(result && result.stderr || "Telegram media delivery failed").trim());
    }
    return { messageId: parseOpenClawMessageId(String(result.stdout || "")) };
  } finally {
    try { fs.unlinkSync(temporaryFile); } catch {}
    try { fs.rmdirSync(temporaryRoot); } catch {}
  }
}

async function deliverConnectorTicket(input = {}, dependencies = {}) {
  const tenant = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (!TENANT.test(tenant)) throw new Error("Connector Telegram tenant invalid");
  const artifactRef = String(input.artifactRef == null ? "" : input.artifactRef).trim();
  if (!ARTIFACT_REF.test(artifactRef)) throw new Error("Connector Telegram artifact ref invalid");
  if (typeof dependencies.readArtifact !== "function") {
    throw new Error("Connector Telegram artifact reader unavailable");
  }
  const caption = buildConnectorTicketCaption(input);
  const bytes = await dependencies.readArtifact(tenant, artifactRef);
  if (
    !Buffer.isBuffer(bytes)
    || bytes.length < 5_000
    || !bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
  ) throw new Error("Connector Telegram PNG invalid");
  const send = dependencies.sendMedia || sendOpenClawMedia;
  const response = await send(input.telegramTarget, bytes, caption);
  let messageId;
  try { messageId = parseOpenClawMessageId(response); } catch {
    throw new Error("Telegram delivery needs a positive message ID");
  }
  const observedAt = new Date(Date.parse(
    (dependencies.observedAt || (() => new Date().toISOString()))(),
  )).toISOString();
  if (!Number.isFinite(Date.parse(observedAt))) throw new Error("Connector Telegram observed time invalid");
  return Object.freeze({
    kind: "telegram_delivery",
    provider_id: messageId,
    observed_at: observedAt,
    tenant_id: tenant,
    chat_id_sha256: hashChatId(input.telegramTarget),
    artifact_ref: artifactRef,
    event_url: eventUrl(input.eventUrl),
  });
}

module.exports = {
  buildConnectorTicketCaption,
  deliverConnectorTicket,
  sendOpenClawMedia,
};
