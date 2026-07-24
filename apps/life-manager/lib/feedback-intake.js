"use strict";

const crypto = require("node:crypto");


const ACK = "Thanks — your privacy-safe feedback was recorded.";
const LABEL_RULES = Object.freeze([
  ["calendar", /\bcalendar\b|カレンダー/i],
  ["notification", /\bnotification\b|通知/i],
  ["call", /\bcall\b|電話|コール/i],
  ["panel", /\b(panel|dashboard|card)\b|パネル|ダッシュボード|カード/i],
  ["email", /\b(email|mail)\b|メール/i],
  ["location", /\b(location|travel)\b|位置|移動/i],
]);


function classifyFeedback(text) {
  const value = String(text || "").trim();
  const match = value.match(/^(?:feedback|フィードバック)\s*[:：]\s*(.+)$/is);
  if (!match || !match[1].trim()) return null;
  return { kind: "feedback", body: match[1].trim() };
}


function scrubFeedback(text) {
  let value = String(text || "");
  value = value.replace(/\bname\s*:\s*[^\s,;]+(?:\s+[^\s,;]+){0,3}/gi, "[name]");
  value = value.replace(/\b(?:api[_-]?key|access[_-]?token|auth(?:orization)?|password|secret)\s*[:=]\s*[^\s,;]+/gi, "[secret]");
  value = value.replace(/https?:\/\/[^\s]+/gi, "[url]");
  value = value.replace(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/gi, "[email]");
  value = value.replace(/(?:\+?\d[\d\s().-]{7,}\d)/g, "[phone]");
  value = value.replace(/〒?\s*\d{3}-\d{4}/g, "[address]");
  value = value.replace(/(^|\s)@[a-z0-9_]{2,32}\b/gi, "$1[handle]");
  return value.replace(/\s+/g, " ").trim().slice(0, 500);
}


function labelsFor(summary) {
  const labels = ["feedback"];
  for (const [label, pattern] of LABEL_RULES) {
    if (pattern.test(summary)) labels.push(label);
  }
  return labels;
}


function buildFeedbackIntake({ text, uid, chatId, messageId, provenanceKey }) {
  const classified = classifyFeedback(text);
  if (!classified) return null;
  if (!uid || !chatId || !messageId || !provenanceKey) throw new Error("feedback_provenance_required");
  const labels = labelsFor(classified.body);
  const summary = scrubFeedback(classified.body);
  if (!summary) throw new Error("feedback_empty_after_scrub");
  const digest = crypto
    .createHmac("sha256", String(provenanceKey))
    .update(`${uid}:${chatId}:${messageId}`)
    .digest("hex")
    .slice(0, 32);
  return Object.freeze({
    source_ref: `tg:sha256:${digest}`,
    summary,
    labels: Object.freeze(labels),
  });
}


function exactIntake(intake) {
  const keys = Object.keys(intake || {}).sort();
  if (keys.join(",") !== "labels,source_ref,summary") throw new Error("feedback_schema_invalid");
  if (!/^tg:sha256:[a-f0-9]{32}$/.test(intake.source_ref)) throw new Error("feedback_schema_invalid");
  if (typeof intake.summary !== "string" || !intake.summary || intake.summary.length > 500) throw new Error("feedback_schema_invalid");
  if (!Array.isArray(intake.labels) || intake.labels[0] !== "feedback" || intake.labels.some((item) => !/^[a-z-]+$/.test(item))) {
    throw new Error("feedback_schema_invalid");
  }
  return intake;
}


async function persistFeedback(intake, opts = {}) {
  exactIntake(intake);
  if (typeof opts.query === "function") {
    const result = await opts.query(
      `INSERT INTO public.lm_feedback_intake (source_ref, summary, labels)
       VALUES ($1, $2, $3)
       ON CONFLICT (source_ref) DO NOTHING
       RETURNING id`,
      [intake.source_ref, intake.summary, intake.labels],
    );
    const row = result && Array.isArray(result.rows) ? result.rows[0] : null;
    return { id: row && row.id ? String(row.id) : null, duplicate: !row };
  }
  const base = String(opts.supaUrl || "").replace(/\/$/, "");
  if (!base || !opts.supaKey) throw new Error("feedback_store_unavailable");
  const response = await (opts.fetchImpl || fetch)(
    `${base}/rest/v1/lm_feedback_intake?on_conflict=source_ref`,
    {
      method: "POST",
      headers: {
        apikey: opts.supaKey,
        Authorization: `Bearer ${opts.supaKey}`,
        "content-type": "application/json",
        Prefer: "resolution=ignore-duplicates,return=representation",
      },
      body: JSON.stringify(intake),
    },
  );
  if (!response.ok) throw new Error("feedback_store_failed");
  const rows = await response.json().catch(() => []);
  const row = Array.isArray(rows) ? rows[0] : null;
  return { id: row && row.id ? String(row.id) : null, duplicate: !row };
}


function createPostgresFeedbackStore(connectionString, deps = {}) {
  if (!connectionString) throw new Error("feedback_store_unavailable");
  const Pool = deps.Pool || require("pg").Pool;
  const pool = new Pool({ connectionString });
  return {
    persist: (intake) => persistFeedback(intake, { query: pool.query.bind(pool) }),
    close: () => pool.end(),
  };
}


async function handleFeedbackMessage(update, user, opts = {}) {
  const classified = classifyFeedback(update && update.text);
  if (!classified) return { handled: false };
  const send = opts.send;
  if (!user) {
    if (send) await send(opts.token, update.chatId, "Complete Life Manager setup with /start before sending feedback.");
    return { handled: true, recorded: false };
  }
  const intake = buildFeedbackIntake({
    text: update.text,
    uid: user.uid,
    chatId: update.chatId,
    messageId: update.messageId,
    provenanceKey: opts.provenanceKey,
  });
  const stored = await (opts.persist || ((value) => persistFeedback(value, opts)))(intake);
  if (send) await send(opts.token, update.chatId, ACK);
  return { handled: true, recorded: true, source_ref: intake.source_ref, duplicate: stored.duplicate };
}


module.exports = {
  ACK,
  classifyFeedback,
  scrubFeedback,
  buildFeedbackIntake,
  persistFeedback,
  createPostgresFeedbackStore,
  handleFeedbackMessage,
};
