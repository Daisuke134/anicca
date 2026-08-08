"use strict";

const { MobileError, nowIso, randomOpaque } = require("./mobile-utils.js");
const { projectSemanticMessage } = require("./mobile-localization.js");

const SEMANTIC_KEYS = new Set([
  "chat.welcome", "chat.route_ready", "chat.needs_information", "chat.no_upcoming_event",
  "chat.route_unavailable", "chat.failed",
]);

function encodeCursor(sequence) {
  const value = Number(sequence);
  if (!Number.isSafeInteger(value) || value < 0) throw new MobileError("invalid_cursor", "The chat cursor is invalid.", 400);
  return `cursor:v1:${Buffer.from(`seq:${value}`).toString("base64url")}`;
}

function decodeCursor(cursor) {
  if (cursor === null || cursor === undefined || cursor === "") return 0;
  const match = /^cursor:v1:([A-Za-z0-9_-]+)$/u.exec(String(cursor));
  if (!match) throw new MobileError("invalid_cursor", "The chat cursor is invalid.", 400);
  let decoded;
  try { decoded = Buffer.from(match[1], "base64url").toString("utf8"); } catch { throw new MobileError("invalid_cursor", "The chat cursor is invalid.", 400); }
  const value = /^seq:(\d+)$/u.exec(decoded);
  if (!value || !Number.isSafeInteger(Number(value[1]))) throw new MobileError("invalid_cursor", "The chat cursor is invalid.", 400);
  return Number(value[1]);
}

function semanticRow(row) {
  return {
    ...row,
    id: row.id,
    sequence: Number(row.sequence),
    key: row.key,
    args: row.args || {},
    userContent: row.userContent || row.user_content || { eventTitle: null, eventLocation: null },
    question: row.question || null,
    route: row.route || null,
    createdAt: row.createdAt || row.created_at,
  };
}

function projectMobileMessage(row, locale = "en") {
  const item = semanticRow(row);
  item.cursor = item.cursor || encodeCursor(item.sequence);
  return projectSemanticMessage(item, locale);
}

async function appendMobileMessage(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  if (!input.key || typeof input.key !== "string" || !SEMANTIC_KEYS.has(input.key)) throw new MobileError("message_key_invalid", "A supported semantic message key is required.");
  const store = deps.store;
  if (!store || typeof store.appendOutbox !== "function") throw new MobileError("outbox_unavailable", "Chat storage is unavailable.", 503, true);
  const row = {
    id: input.id || randomOpaque("message:v1:", deps), sequence: input.sequence,
    type: input.type || "system", key: input.key, args: input.args || {},
    userContent: input.userContent || { eventTitle: null, eventLocation: null }, question: input.question || null, route: input.route || null,
    createdAt: input.createdAt || nowIso(deps), mutationKey: input.mutationKey || null,
  };
  // Validate provider names and locale before persisting a route row. A projection failure must not
  // leave an unrenderable route in the durable outbox that a later retry would replay forever.
  projectSemanticMessage({ ...row, sequence: Number.isSafeInteger(row.sequence) ? row.sequence : 0 }, scope.productLocale || input.locale || "en");
  const stored = semanticRow(await store.appendOutbox(scope, row));
  if (!Number.isSafeInteger(stored.sequence)) throw new MobileError("outbox_sequence_missing", "Chat storage returned no monotonic sequence.", 503, true);
  stored.cursor = encodeCursor(stored.sequence);
  return projectMobileMessage(stored, scope.productLocale || input.locale || "en");
}

async function listMobileMessages(scope, cursor, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const store = deps.store;
  if (!store || typeof store.listOutbox !== "function") throw new MobileError("outbox_unavailable", "Chat storage is unavailable.", 503, true);
  const after = decodeCursor(cursor);
  const pageSize = Math.min(100, Math.max(1, Number(deps.pageSize || 50)));
  const rows = (await store.listOutbox(scope, after, pageSize + 1)).map(semanticRow).sort((a, b) => a.sequence - b.sequence);
  const hasMore = rows.length > pageSize;
  const pageRows = hasMore ? rows.slice(0, pageSize) : rows;
  const messages = pageRows.map((row) => projectMobileMessage(row, scope.productLocale || "en"));
  const nextSequence = pageRows.length ? pageRows[pageRows.length - 1].sequence : after;
  return { messages, nextCursor: encodeCursor(nextSequence), hasMore };
}

module.exports = { SEMANTIC_KEYS, encodeCursor, decodeCursor, appendMobileMessage, listMobileMessages, projectMobileMessage, semanticRow };
