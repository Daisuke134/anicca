"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { notifyOpenClawGateway, parseOpenClawMessageId } = require("./outbound-guardian.js");

const EVENT_REF = /^connpass-event:\/\/event\/[1-9][0-9]*$/;
const URL = /^https:\/\/(?:[a-z0-9-]+\.)?connpass\.com\/event\/[1-9][0-9]*\/$/i;
const SLOT = new Set(["available", "waitlist", "closed"]);
const TALK = new Set(["unknown", "not_offered", "open", "submitted", "provider_verified", "closed"]);
const PRIORITY = new Set(["yc_hackathon", "open_talk", "ai", "crypto", "startup", "other"]);
const CREDENTIAL_VALUE = /(?:password|cookie|api[ _-]?key|secret|(?:access|auth|refresh)[ _-]?token)\s*[:=]\s*\S{8,}|\bbearer\s+\S{16,}/i;

function invalid() { throw new Error("Connpass action Telegram invalid"); }
function stageError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}
function safe(value, max) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!text || text.length > max || /[\x00-\x1f\x7f]|\{\{|\}\}/.test(text) || CREDENTIAL_VALUE.test(text)) invalid();
  return text;
}
function publicText(value, max) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!text || text.length > max || /[\x00-\x1f\x7f]|\{\{|\}\}/.test(text)) invalid();
  return text;
}
function integer(value) { return Number.isSafeInteger(value) && value >= 0 ? value : null; }
function normalize(candidate) {
  if (!candidate || candidate.provider !== "connpass" || !EVENT_REF.test(String(candidate.event_ref || ""))
    || !URL.test(String(candidate.canonical_url || "")) || !SLOT.has(candidate.participation_slot_status)
    || !TALK.has(candidate.lightning_talk_status) || !PRIORITY.has(candidate.priority_class)) invalid();
  const deadline = candidate.application_deadline_at == null ? null : String(candidate.application_deadline_at);
  if (deadline != null && (!Number.isFinite(Date.parse(deadline)) || new Date(Date.parse(deadline)).toISOString() !== deadline)) invalid();
  return Object.freeze({
    event_ref: candidate.event_ref,
    canonical_url: candidate.canonical_url,
    title: publicText(candidate.title, 500).slice(0, 160),
    participation_slot_status: candidate.participation_slot_status,
    lightning_talk_status: candidate.lightning_talk_status,
    participant_limit: integer(candidate.participant_limit),
    accepted_count: integer(candidate.accepted_count),
    waiting_count: integer(candidate.waiting_count),
    application_deadline_at: deadline,
    priority_class: candidate.priority_class,
    preference_reason: publicText(candidate.preference_reason, 500),
  });
}
function digest(value) { return createHash("sha256").update(JSON.stringify(value), "utf8").digest("hex"); }

function createConnpassActionTelegram(options = {}) {
  const stateDir = path.resolve(String(options.stateDir || ""));
  const wakeId = safe(options.wakeId, 160);
  const telegramTarget = safe(options.telegramTarget, 200);
  const now = options.now || (() => new Date());
  const send = options.send || notifyOpenClawGateway;
  if (!path.isAbsolute(stateDir) || stateDir === path.parse(stateDir).root || typeof now !== "function" || typeof send !== "function") invalid();
  const file = path.join(stateDir, "connpass-action-boundary-deliveries.jsonl");
  return Object.freeze({
    async report(input = {}) {
      if (!Array.isArray(input.candidates) || input.candidates.length < 1 || input.candidates.length > 10_000) invalid();
      const normalized = input.candidates.slice(0, 5).map(normalize);
      const lines = ["Connector::: connpass候補（手動action boundary）", "自動申込: 0件", ""];
      const candidates = [];
      for (const row of normalized) {
        const index = candidates.length;
        const block = [
          `${index + 1}. ${row.title}`,
          `優先度: ${row.priority_class}`,
          `理由: ${row.preference_reason}`,
          `参加枠: ${row.participation_slot_status} / 参加 ${row.accepted_count ?? "不明"}人 / 定員 ${row.participant_limit ?? "不明"}人`,
          `LT: ${row.lightning_talk_status} / 補欠: ${row.waiting_count ?? "不明"}人`,
          `締切: ${row.application_deadline_at ?? "provider未提供"}`,
          row.canonical_url,
          "",
        ];
        if ([...lines, ...block].join("\n").trim().length > 4_096) break;
        candidates.push(row);
        lines.push(...block);
      }
      if (candidates.length < 1) invalid();
      const snapshot = digest(candidates);
      if (fs.existsSync(file)) {
        const rows = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
        const existing = rows.find((row) => row.wake_id === wakeId && row.candidate_snapshot_sha256 === snapshot);
        if (existing && /^[1-9][0-9]*$/.test(existing.telegram_provider_id)) {
          return Object.freeze({ telegram_provider_id: existing.telegram_provider_id, completion_disposition: "reused" });
        }
      }
      const message = lines.join("\n").trim();
      let response;
      try {
        response = await send(message, { telegramTarget, idempotencyKey: `connpass-action-boundary:${wakeId}:${snapshot}` });
      } catch {
        throw stageError("CONNPASS_ACTION_BOUNDARY_SEND_FAILED");
      }
      let providerId;
      try { providerId = parseOpenClawMessageId(response); }
      catch { throw stageError("CONNPASS_ACTION_BOUNDARY_PROVIDER_ID_FAILED"); }
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
      const receipt = Object.freeze({ schema_version: 1, wake_id: wakeId, candidate_snapshot_sha256: snapshot, telegram_provider_id: providerId, observed_at: observed.toISOString() });
      fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
      fs.appendFileSync(file, `${JSON.stringify(receipt)}\n`, { encoding: "utf8", mode: 0o600 });
      fs.chmodSync(file, 0o600);
      return Object.freeze({ telegram_provider_id: providerId, completion_disposition: "created" });
    },
  });
}

module.exports = { createConnpassActionTelegram };
