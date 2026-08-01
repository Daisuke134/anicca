"use strict";

const { createHash } = require("node:crypto");
const { notifyOpenClaw, parseOpenClawMessageId } = require("./outbound-guardian.js");
const { hashChatId } = require("./telegram.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const RECEIPT = /^provider-receipt:\/\/(luma|connpass)\/([A-Za-z0-9._:~-]+)$/;
const STATUSES = new Set(["covered_existing", "covered_new", "unavailable", "open"]);
const PLACEHOLDER = /\{\{|\}\}|TODO|TBD|<placeholder>/i;

function addDays(date, count) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + count)).toISOString().slice(0, 10);
}

function safeText(value, label, max) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!result || result.length > max || PLACEHOLDER.test(result)) throw new Error(`coverage Telegram ${label} invalid`);
  return result;
}

function validateCoverage(coverage) {
  if (!coverage || coverage.schema_version !== 1 || !Array.isArray(coverage.days) || coverage.days.length !== 21) {
    throw new Error("coverage Telegram coverage invalid");
  }
  const counts = { covered_existing: 0, covered_new: 0, unavailable: 0, open: 0 };
  for (let index = 0; index < 21; index += 1) {
    const day = coverage.days[index];
    if (!day || !DATE.test(String(day.date || "")) || (index > 0 && day.date !== addDays(coverage.days[index - 1].date, 1)) || !STATUSES.has(day.status)) {
      throw new Error("coverage Telegram day invalid");
    }
    if (day.status === "open" ? day.evidence_ref != null : typeof day.evidence_ref !== "string") {
      throw new Error("coverage Telegram evidence invalid");
    }
    counts[day.status] += 1;
  }
  if (
    coverage.window_start !== coverage.days[0].date
    || coverage.window_end !== coverage.days.at(-1).date
    || coverage.open_count !== counts.open
    || coverage.complete !== (counts.open === 0)
    || !coverage.counts
    || Object.keys(counts).some((key) => coverage.counts[key] !== counts[key])
  ) throw new Error("coverage Telegram counts invalid");
  return counts;
}

function reservationMap(reservations, coverage) {
  if (!Array.isArray(reservations)) throw new Error("coverage Telegram reservation invalid");
  const map = new Map();
  for (const reservation of reservations) {
    const date = String(reservation && reservation.date || "");
    const receipt = RECEIPT.exec(String(reservation && reservation.receipt_ref || ""));
    if (!DATE.test(date) || map.has(date) || !receipt) throw new Error("coverage Telegram reservation receipt invalid");
    map.set(date, Object.freeze({
      title: safeText(reservation.event_title, "event title", 100),
      reason: safeText(reservation.selection_reason, "selection reason", 300),
      provider: receipt[1],
      receipt_token: receipt[2],
    }));
  }
  const required = coverage.days.filter(({ status }) => status === "covered_new").map(({ date }) => date);
  if (map.size !== required.length || required.some((date) => !map.has(date))) {
    throw new Error("coverage Telegram reservation mismatch");
  }
  return map;
}

function compact(value, max) {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function buildEventCoverageMessage(input = {}) {
  const coverage = input.coverage;
  const counts = validateCoverage(coverage);
  const reservations = reservationMap(input.reservations, coverage);
  const lines = [
    "📅 Life Manager イベント21日レポート",
    `期間: ${coverage.window_start.replaceAll("-", "/")}〜${coverage.window_end.replaceAll("-", "/")}`,
    `既存 ${counts.covered_existing}｜新規 ${counts.covered_new}｜参加不可 ${counts.unavailable}｜残り ${counts.open}`,
    "",
  ];
  for (const day of coverage.days) {
    const label = `${Number(day.date.slice(5, 7))}/${day.date.slice(8, 10)}`;
    if (day.status === "covered_existing") lines.push(`✅ ${label} 既存の参加予定あり`);
    else if (day.status === "unavailable") lines.push(`⛔ ${label} 固定予定と移動時間により参加枠なし`);
    else if (day.status === "open") lines.push(`🔎 ${label} 未確保（次のrunで探索継続）`);
    else {
      const row = reservations.get(day.date);
      const provider = row.provider === "luma" ? "Luma" : "connpass";
      lines.push(`🎟️ ${label} ${compact(row.title, 40)}｜証拠 ${provider}:${compact(row.receipt_token, 32)}｜理由 ${compact(row.reason, 60)}`);
    }
  }
  lines.push("", counts.open === 0 ? "✅ 21日分の処理が完了しています。" : `🔄 残り${counts.open}日は自動探索を継続します。`);
  const message = lines.join("\n");
  if (message.length > 4096) throw new Error("coverage Telegram message too long");
  return message;
}

async function deliverEventCoverageSummary(input = {}, dependencies = {}) {
  const tenant = String(input.tenantId || "").trim();
  const target = String(input.telegramTarget || "").trim();
  if (!TENANT.test(tenant) || !target || target.length > 200) throw new Error("coverage Telegram delivery invalid");
  const message = buildEventCoverageMessage(input);
  const send = dependencies.send || notifyOpenClaw;
  const response = await send(message, { telegramTarget: target });
  let messageId;
  try { messageId = parseOpenClawMessageId(response); } catch {
    throw new Error("Telegram delivery needs a positive message ID");
  }
  const observedRaw = (dependencies.observedAt || (() => new Date().toISOString()))();
  const observedMs = Date.parse(String(observedRaw || ""));
  if (!Number.isFinite(observedMs)) throw new Error("coverage Telegram observed time invalid");
  const counts = validateCoverage(input.coverage);
  return Object.freeze({
    kind: "event_coverage_telegram_delivery",
    provider_id: messageId,
    observed_at: new Date(observedMs).toISOString(),
    tenant_id: tenant,
    chat_id_sha256: hashChatId(target),
    summary_sha256: createHash("sha256").update(message, "utf8").digest("hex"),
    window_start: input.coverage.window_start,
    window_end: input.coverage.window_end,
    counts: Object.freeze({ ...counts }),
  });
}

module.exports = { buildEventCoverageMessage, deliverEventCoverageSummary };
