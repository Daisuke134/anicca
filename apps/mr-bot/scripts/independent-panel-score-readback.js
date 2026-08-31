#!/usr/bin/env node
"use strict";

// Spec-derived production readback oracle. It deliberately shares no scorer code.
const fs = require("node:fs");

const ORGANS = ["daily", "physical", "mental", "financial"];
const KINDS = { daily: "rolling_7_days", physical: "rolling_30_days", mental: "rolling_7_days", financial: "calendar_month" };
const MAX = BigInt(Number.MAX_SAFE_INTEGER);

function safeZone(input) {
  const value = String(input || "UTC");
  try { new Intl.DateTimeFormat("en", { timeZone: value }).format(0); return value; } catch { return "UTC"; }
}

function localFields(ms, zone) {
  const values = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).formatToParts(new Date(ms)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return { year: +values.year, month: +values.month, day: +values.day, hour: +values.hour, minute: +values.minute, second: +values.second, millisecond: ((ms % 1000) + 1000) % 1000 };
}

function wallNumber(value) {
  return Date.UTC(value.year, value.month - 1, value.day, value.hour, value.minute, value.second, value.millisecond || 0);
}

function resolveIndependent(value, zone) {
  const wall = wallNumber(value);
  const offsets = new Set();
  for (let hour = -48; hour <= 48; hour += 2) {
    const probe = wall + hour * 3600000;
    offsets.add(wallNumber(localFields(probe, zone)) - probe);
  }
  const candidates = [...offsets].map((offset) => {
    const instant = wall - offset;
    const shown = localFields(instant, zone);
    const delta = wallNumber(shown) - wall;
    return { instant, delta };
  });
  const exact = candidates.filter((item) => item.delta === 0).map((item) => item.instant).sort((a, b) => a - b);
  if (exact.length) return exact[0];
  const gaps = candidates.filter((item) => item.delta > 0 && item.delta <= 180 * 60000).sort((a, b) => a.delta - b.delta || a.instant - b.instant);
  if (gaps.length) return gaps[0].instant;
  throw new Error("period_resolution_failed");
}

function shiftDaysIndependent(fields, count) {
  const shifted = new Date(Date.UTC(fields.year, fields.month - 1, fields.day + count, fields.hour, fields.minute, fields.second, fields.millisecond));
  return { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() + 1, day: shifted.getUTCDate(), hour: shifted.getUTCHours(), minute: shifted.getUTCMinutes(), second: shifted.getUTCSeconds(), millisecond: shifted.getUTCMilliseconds() };
}

function buildPeriodsIndependent(nowMs, requestedZone) {
  const timezone = safeZone(requestedZone);
  const now = localFields(nowMs, timezone);
  const end_at = new Date(nowMs).toISOString();
  const period = (kind, start) => ({ kind, start_at: new Date(start).toISOString(), end_at });
  const seven = resolveIndependent(shiftDaysIndependent(now, -7), timezone);
  return {
    timezone,
    daily: period(KINDS.daily, seven),
    physical: period(KINDS.physical, resolveIndependent(shiftDaysIndependent(now, -30), timezone)),
    mental: period(KINDS.mental, seven),
    financial: period(KINDS.financial, resolveIndependent({ year: now.year, month: now.month, day: 1, hour: 0, minute: 0, second: 0, millisecond: 0 }, timezone)),
  };
}

function textOrder(a, b) { return String(a || "").toLowerCase().localeCompare(String(b || "").toLowerCase(), "en"); }
function newest(a, b) { return Date.parse(a.recorded_at) - Date.parse(b.recorded_at) || textOrder(a.revision_key, b.revision_key) || textOrder(a.public_ref, b.public_ref); }
function refs(rows) { return [...new Set(rows.map((row) => `outcome:${String(row.public_ref).toLowerCase()}`))].sort(); }

function accepted(organ, row) {
  const key = `${row.outcome_kind}:${row.outcome_status}`;
  if (organ === "daily") return /^(daily_travel|daily_call|daily_late):(required_succeeded|required_failed|required_pending|context_unnecessary|optional)$/.test(key);
  if (organ === "physical") return /^physical_need:(detected|candidate|search|unconfirmed_request|confirmed_booking|confirmed_completion|unresolved)$/.test(key);
  if (organ === "mental") return /^mental_trigger:(delivered|suppression_honored|correction_persisted|cap_overflow|unresolved)$/.test(key);
  return /^(financial_external_income:verified|financial_realized_loss:realized|financial_fee:charged|financial_user_transfer:confirmed|financial_(self_funding|deposit|internal_move|unverified):excluded)$/.test(key);
}

function rowsFor(input, organ, period) {
  const unique = new Map();
  let unknown = 0;
  const start = Date.parse(period.start_at), end = Date.parse(period.end_at);
  for (const row of Array.isArray(input[organ]) ? input[organ] : []) {
    if (!row || String(row.uid) !== String(input.uid) || row.organ !== organ) continue;
    const at = Date.parse(row.occurred_at);
    if (!Number.isFinite(at) || at < start || at >= end) continue;
    if (!accepted(organ, row)) { unknown += 1; continue; }
    const idempotency = [row.uid, row.organ, row.entity_key, row.outcome_kind, row.revision_key].join("\u0000");
    if (!unique.has(idempotency) || newest(row, unique.get(idempotency)) > 0) unique.set(idempotency, row);
  }
  return { rows: [...unique.values()], unknown };
}

function winners(rows, key, compare = newest) {
  const result = new Map();
  for (const row of rows) if (!result.has(key(row)) || compare(row, result.get(key(row))) > 0) result.set(key(row), row);
  return [...result.values()];
}

function shell(period, timezone, unknown, components) {
  return { status: "insufficient_data", value: null, period, numerator: 0, denominator: 0, reason: "Insufficient outcome data for this period.", source_outcome_ids: [], components: { timezone, excluded_unknown_count: unknown, ...components } };
}

function ratio(base, numerator, denominator, reason) {
  return denominator === 0 ? { ...base, reason } : { ...base, status: "measured", value: Math.max(0, Math.min(100, Math.round(numerator / denominator * 100))), numerator, denominator, reason };
}

function dailyIndependent(prepared, period, timezone) {
  const selected = winners(prepared.rows, (row) => `${row.entity_key}\u0000${row.outcome_kind}`);
  const events = new Map();
  const c = { eligible_events: 0, resolved_events: 0, required_succeeded: 0, required_failed: 0, required_pending: 0, context_unnecessary: 0, optional_ignored: 0 };
  for (const row of selected) {
    if (!events.has(row.entity_key)) events.set(row.entity_key, []);
    events.get(row.entity_key).push(row);
    if (row.outcome_status === "optional") c.optional_ignored += 1; else c[row.outcome_status] += 1;
  }
  for (const eventRows of events.values()) {
    const required = eventRows.filter((row) => row.outcome_status !== "optional");
    if (!required.length) continue;
    c.eligible_events += 1;
    if (required.every((row) => ["required_succeeded", "context_unnecessary"].includes(row.outcome_status))) c.resolved_events += 1;
  }
  const base = shell(period, timezone, prepared.unknown, c); base.source_outcome_ids = refs(selected);
  return ratio(base, c.resolved_events, c.eligible_events, c.eligible_events ? `Resolved ${c.resolved_events} of ${c.eligible_events} eligible events from required handling outcomes.` : "No events required travel, call, or late handling in this period.");
}

function physicalIndependent(prepared, period, timezone) {
  const rank = { confirmed_completion: 2, confirmed_booking: 1 };
  const selected = winners(prepared.rows, (row) => row.entity_key, (a, b) => (rank[a.outcome_status] || 0) - (rank[b.outcome_status] || 0) || newest(a, b));
  const c = { detected_needs: selected.length, confirmed_booking: 0, confirmed_completion: 0, unresolved_needs: 0, search_candidate_unconfirmed: 0 };
  for (const row of selected) {
    if (row.outcome_status === "confirmed_booking") c.confirmed_booking += 1;
    else if (row.outcome_status === "confirmed_completion") c.confirmed_completion += 1;
    else { c.unresolved_needs += 1; if (["search", "candidate", "unconfirmed_request"].includes(row.outcome_status)) c.search_candidate_unconfirmed += 1; }
  }
  const n = c.confirmed_booking + c.confirmed_completion;
  const base = shell(period, timezone, prepared.unknown, c); base.source_outcome_ids = refs(selected);
  return ratio(base, n, c.detected_needs, c.detected_needs ? `Resolved ${n} of ${c.detected_needs} detected needs by confirmed booking or completion.` : "No overdue needs were detected in this period.");
}

function dayKey(ms, timezone) { const p = localFields(ms, timezone); return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`; }
function mentalIndependent(prepared, period, timezone) {
  const selected = winners(prepared.rows, (row) => row.entity_key);
  const c = { deduplicated_triggers: selected.length, delivered_within_cap: 0, suppression_honored: 0, correction_persisted: 0, cap_overflow: 0, unresolved_triggers: 0 };
  const deliveries = [], end = Date.parse(period.end_at);
  for (const row of selected) {
    const meta = row.components || {};
    if (row.outcome_status === "delivered") {
      const occurred = Date.parse(row.occurred_at), effective = row.resolved_at == null || row.resolved_at === "" ? occurred : Date.parse(row.resolved_at);
      if (meta.intervention_valid === true && Number.isFinite(effective) && effective >= occurred && effective < end) deliveries.push({ row, effective }); else c.unresolved_triggers += 1;
    } else if (row.outcome_status === "suppression_honored" && meta.send_count === 0) c.suppression_honored += 1;
    else if (row.outcome_status === "correction_persisted" && meta.context_persisted === true) c.correction_persisted += 1;
    else if (row.outcome_status === "cap_overflow") c.cap_overflow += 1; else c.unresolved_triggers += 1;
  }
  deliveries.sort((a, b) => a.effective - b.effective || textOrder(a.row.public_ref, b.row.public_ref));
  const days = new Map();
  for (const item of deliveries) { const key = dayKey(item.effective, timezone), count = days.get(key) || 0; if (count < 3) c.delivered_within_cap += 1; else c.cap_overflow += 1; days.set(key, count + 1); }
  const n = c.delivered_within_cap + c.suppression_honored + c.correction_persisted;
  const base = shell(period, timezone, prepared.unknown, c); base.source_outcome_ids = refs(selected);
  return ratio(base, n, c.deduplicated_triggers, c.deduplicated_triggers ? `Satisfied ${n} of ${c.deduplicated_triggers} deduplicated triggers within delivery, suppression, and correction rules.` : "No context triggers were recorded in this period.");
}

function integerAmount(value) {
  if (typeof value === "number") return Number.isSafeInteger(value) && value >= 0 ? BigInt(value) : null;
  if (typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)) { const result = BigInt(value); return result <= MAX ? result : null; }
  return null;
}

function invalidFinancial(base, selected, reason, excluded) {
  return { ...base, status: "invalid_data", value: null, numerator: null, denominator: null, reason, source_outcome_ids: refs(selected), components: { ...base.components, currency: null, gross_income_minor: null, realized_loss_minor: null, fee_minor: null, user_transfer_minor: null, excluded_rows: excluded, net_clamped: false } };
}

function financialIndependent(prepared, period, timezone) {
  const selected = winners(prepared.rows, (row) => row.entity_key);
  const excluded = selected.filter((row) => row.outcome_status === "excluded").length;
  const base = shell(period, timezone, prepared.unknown, { currency: null, gross_income_minor: 0, realized_loss_minor: 0, fee_minor: 0, user_transfer_minor: 0, excluded_rows: excluded, net_clamped: false });
  const counted = selected.filter((row) => row.outcome_status !== "excluded"), currencies = new Set(), values = new Map();
  for (const row of counted) { const amount = integerAmount(row.amount_minor); if (amount == null || !/^[A-Z]{3}$/.test(String(row.currency || ""))) return invalidFinancial(base, selected, "Financial outcome amount is outside the supported range.", excluded); values.set(row, amount); currencies.add(row.currency); }
  if (currencies.size > 1) return invalidFinancial(base, selected, "Financial outcomes use more than one currency.", excluded);
  let gross = 0n, loss = 0n, fee = 0n, transfer = 0n;
  for (const row of counted) { const amount = values.get(row); if (row.outcome_kind === "financial_external_income") gross += amount; else if (row.outcome_kind === "financial_realized_loss") loss += amount; else if (row.outcome_kind === "financial_fee") fee += amount; else transfer += amount; if ([gross, loss, fee, transfer].some((n) => n > MAX)) return invalidFinancial(base, selected, "Financial outcome amount is outside the supported range.", excluded); }
  const raw = gross - loss - fee, net = raw < 0n ? 0n : raw;
  base.components = { ...base.components, currency: currencies.size ? [...currencies][0] : null, gross_income_minor: Number(gross), realized_loss_minor: Number(loss), fee_minor: Number(fee), user_transfer_minor: Number(transfer), net_clamped: raw < 0n };
  base.source_outcome_ids = refs(selected);
  if (gross === 0n) { base.reason = `No verified external gross income was recorded; user transfers total ${transfer} minor units and remain separate.`; return base; }
  return { ...base, status: "measured", value: Math.max(0, Math.min(100, Number((net * 200n + gross) / (gross * 2n)))), numerator: Number(net), denominator: Number(gross), reason: `Net verified external income is ${net} of ${gross} minor units after realized loss ${loss} and fee ${fee}; user transfers ${transfer} are shown separately.` };
}

function recomputeIndependent(rowsByOrgan, periods, requestedZone) {
  const timezone = safeZone(periods.timezone || requestedZone);
  return {
    daily: dailyIndependent(rowsFor(rowsByOrgan, "daily", periods.daily), periods.daily, timezone),
    physical: physicalIndependent(rowsFor(rowsByOrgan, "physical", periods.physical), periods.physical, timezone),
    mental: mentalIndependent(rowsFor(rowsByOrgan, "mental", periods.mental), periods.mental, timezone),
    financial: financialIndependent(rowsFor(rowsByOrgan, "financial", periods.financial), periods.financial, timezone),
  };
}

if (require.main === module) {
  const input = process.argv[2] ? fs.readFileSync(process.argv[2], "utf8") : fs.readFileSync(0, "utf8");
  const payload = JSON.parse(input);
  const periods = payload.periods || buildPeriodsIndependent(Date.parse(payload.now), payload.timezone);
  process.stdout.write(`${JSON.stringify({ organs: recomputeIndependent(payload.rows_by_organ, periods, payload.timezone) })}\n`);
}

module.exports = { buildPeriodsIndependent, recomputeIndependent };
