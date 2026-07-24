"use strict";

const DAY_MS = 86400000;
const MAX_SAFE_BIGINT = BigInt(Number.MAX_SAFE_INTEGER);
const ORGAN_NAMES = Object.freeze(["daily", "physical", "mental", "financial"]);
const PERIOD_KINDS = Object.freeze({ daily: "rolling_7_days", physical: "rolling_30_days", mental: "rolling_7_days", financial: "calendar_month" });

const VALID_PAIRS = Object.freeze({
  daily: new Set([
    "daily_travel:required_succeeded", "daily_travel:required_failed", "daily_travel:required_pending", "daily_travel:context_unnecessary", "daily_travel:optional",
    "daily_call:required_succeeded", "daily_call:required_failed", "daily_call:required_pending", "daily_call:context_unnecessary", "daily_call:optional",
    "daily_late:required_succeeded", "daily_late:required_failed", "daily_late:required_pending", "daily_late:context_unnecessary", "daily_late:optional",
  ]),
  physical: new Set(["detected", "candidate", "search", "unconfirmed_request", "confirmed_booking", "confirmed_completion", "unresolved"].map((status) => `physical_need:${status}`)),
  mental: new Set(["delivered", "suppression_honored", "correction_persisted", "cap_overflow", "unresolved"].map((status) => `mental_trigger:${status}`)),
  financial: new Set([
    "financial_external_income:verified", "financial_realized_loss:realized", "financial_fee:charged", "financial_user_transfer:confirmed",
    "financial_self_funding:excluded", "financial_deposit:excluded", "financial_internal_move:excluded", "financial_unverified:excluded",
  ]),
});

function configuredTimeZone(value) {
  const candidate = String(value || "UTC");
  try {
    new Intl.DateTimeFormat("en", { timeZone: candidate }).format(0);
    return candidate;
  } catch {
    return "UTC";
  }
}

const FORMATTERS = new Map();
function formatter(timeZone) {
  if (!FORMATTERS.has(timeZone)) {
    FORMATTERS.set(timeZone, new Intl.DateTimeFormat("en-CA", {
      timeZone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }));
  }
  return FORMATTERS.get(timeZone);
}

function zonedParts(ms, timeZone) {
  const values = Object.fromEntries(formatter(timeZone).formatToParts(new Date(ms)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return {
    year: Number(values.year), month: Number(values.month), day: Number(values.day),
    hour: Number(values.hour), minute: Number(values.minute), second: Number(values.second),
    millisecond: ((ms % 1000) + 1000) % 1000,
  };
}

function wallEpoch(parts) {
  return Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second, parts.millisecond || 0);
}

function sameWall(left, right) {
  return left.year === right.year && left.month === right.month && left.day === right.day && left.hour === right.hour && left.minute === right.minute && left.second === right.second && left.millisecond === (right.millisecond || 0);
}

function resolveWallClock(parts, timeZone) {
  const targetWall = wallEpoch(parts);
  const offsets = new Set();
  for (let hour = -48; hour <= 48; hour += 3) {
    const probe = targetWall + hour * 3600000;
    offsets.add(wallEpoch(zonedParts(probe, timeZone)) - probe);
  }
  const exact = [];
  const shifted = [];
  for (const offset of offsets) {
    const candidate = targetWall - offset;
    const represented = zonedParts(candidate, timeZone);
    if (sameWall(represented, parts)) exact.push(candidate);
    else {
      const delta = wallEpoch(represented) - targetWall;
      if (delta > 0 && delta <= 180 * 60000) shifted.push({ candidate, delta });
    }
  }
  if (exact.length) return Math.min(...exact);
  shifted.sort((left, right) => left.delta - right.delta || left.candidate - right.candidate);
  if (shifted.length) return shifted[0].candidate;
  const error = new Error("period_resolution_failed");
  error.code = "period_resolution_failed";
  throw error;
}

function shiftLocalDays(parts, days) {
  const shifted = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + days, parts.hour, parts.minute, parts.second, parts.millisecond || 0));
  return {
    year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() + 1, day: shifted.getUTCDate(),
    hour: shifted.getUTCHours(), minute: shifted.getUTCMinutes(), second: shifted.getUTCSeconds(), millisecond: shifted.getUTCMilliseconds(),
  };
}

function buildScorePeriods(nowMs, requestedTimeZone) {
  if (!Number.isFinite(nowMs)) {
    const error = new Error("period_resolution_failed");
    error.code = "period_resolution_failed";
    throw error;
  }
  const timezone = configuredTimeZone(requestedTimeZone);
  const now = zonedParts(nowMs, timezone);
  const endAt = new Date(nowMs).toISOString();
  const period = (kind, startMs) => ({ kind, start_at: new Date(startMs).toISOString(), end_at: endAt });
  const dailyStart = resolveWallClock(shiftLocalDays(now, -7), timezone);
  const physicalStart = resolveWallClock(shiftLocalDays(now, -30), timezone);
  const financialStart = resolveWallClock({ year: now.year, month: now.month, day: 1, hour: 0, minute: 0, second: 0, millisecond: 0 }, timezone);
  return {
    timezone,
    daily: period(PERIOD_KINDS.daily, dailyStart),
    physical: period(PERIOD_KINDS.physical, physicalStart),
    mental: period(PERIOD_KINDS.mental, dailyStart),
    financial: period(PERIOD_KINDS.financial, financialStart),
  };
}

function compareText(left, right) {
  return String(left || "").toLowerCase().localeCompare(String(right || "").toLowerCase(), "en");
}

function compareLatest(left, right) {
  const recorded = Date.parse(left.recorded_at) - Date.parse(right.recorded_at);
  if (recorded) return recorded;
  const revision = compareText(left.revision_key, right.revision_key);
  if (revision) return revision;
  return compareText(left.public_ref, right.public_ref);
}

function validPublicRef(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ""));
}

function sourceRefs(rows) {
  return [...new Set(rows.filter((row) => validPublicRef(row.public_ref)).map((row) => `outcome:${String(row.public_ref).toLowerCase()}`))].sort();
}

function prepareRows(rowsByOrgan, organ, period) {
  const tenant = rowsByOrgan && rowsByOrgan.uid == null ? null : String(rowsByOrgan.uid);
  const startMs = Date.parse(period.start_at);
  const endMs = Date.parse(period.end_at);
  const seen = new Map();
  let excludedUnknownCount = 0;
  for (const candidate of Array.isArray(rowsByOrgan && rowsByOrgan[organ]) ? rowsByOrgan[organ] : []) {
    if (!candidate || (tenant != null && String(candidate.uid) !== tenant) || String(candidate.organ) !== organ) continue;
    const occurredMs = Date.parse(candidate.occurred_at);
    if (!Number.isFinite(occurredMs) || occurredMs < startMs || occurredMs >= endMs) continue;
    const pair = `${candidate.outcome_kind}:${candidate.outcome_status}`;
    if (!VALID_PAIRS[organ].has(pair)) {
      excludedUnknownCount += 1;
      continue;
    }
    const key = [candidate.uid, candidate.organ, candidate.entity_key, candidate.outcome_kind, candidate.revision_key].map(String).join("\u0000");
    const current = seen.get(key);
    if (!current || compareLatest(candidate, current) > 0) seen.set(key, candidate);
  }
  return { rows: [...seen.values()], excludedUnknownCount };
}

function selectLatest(rows, keyOf, compare = compareLatest) {
  const winners = new Map();
  for (const row of rows) {
    const key = keyOf(row);
    const current = winners.get(key);
    if (!current || compare(row, current) > 0) winners.set(key, row);
  }
  return [...winners.values()];
}

function baseEnvelope(period, timezone, excludedUnknownCount, components) {
  return {
    status: "insufficient_data", value: null, period,
    numerator: 0, denominator: 0, reason: "Insufficient outcome data for this period.",
    source_outcome_ids: [], components: { timezone, excluded_unknown_count: excludedUnknownCount, ...components },
  };
}

function roundedScoreValue(numerator, denominator) {
  const numeratorBig = BigInt(numerator);
  const denominatorBig = BigInt(denominator);
  return Math.max(0, Math.min(100, Number((numeratorBig * 200n + denominatorBig) / (denominatorBig * 2n))));
}

function measured(envelope, numerator, denominator, reason) {
  if (denominator === 0) return { ...envelope, reason };
  const value = roundedScoreValue(numerator, denominator);
  return { ...envelope, status: "measured", value, numerator, denominator, reason };
}

function dailyScore(prepared, period, timezone) {
  const winners = selectLatest(prepared.rows, (row) => `${row.entity_key}\u0000${row.outcome_kind}`);
  const byEvent = new Map();
  for (const row of winners) {
    if (!byEvent.has(row.entity_key)) byEvent.set(row.entity_key, []);
    byEvent.get(row.entity_key).push(row);
  }
  const components = { eligible_events: 0, resolved_events: 0, required_succeeded: 0, required_failed: 0, required_pending: 0, context_unnecessary: 0, optional_ignored: 0 };
  for (const row of winners) {
    if (row.outcome_status === "optional") components.optional_ignored += 1;
    else if (Object.hasOwn(components, row.outcome_status)) components[row.outcome_status] += 1;
  }
  for (const eventRows of byEvent.values()) {
    const required = eventRows.filter((row) => row.outcome_status !== "optional");
    if (!required.length) continue;
    components.eligible_events += 1;
    if (required.every((row) => row.outcome_status === "required_succeeded" || row.outcome_status === "context_unnecessary")) components.resolved_events += 1;
  }
  const envelope = baseEnvelope(period, timezone, prepared.excludedUnknownCount, components);
  envelope.source_outcome_ids = sourceRefs(winners);
  return measured(envelope, components.resolved_events, components.eligible_events,
    components.eligible_events ? `Resolved ${components.resolved_events} of ${components.eligible_events} eligible events from required handling outcomes.` : "No events required travel, call, or late handling in this period.");
}

const PHYSICAL_RANK = Object.freeze({ confirmed_completion: 2, confirmed_booking: 1 });
function physicalScore(prepared, period, timezone) {
  const winners = selectLatest(prepared.rows, (row) => row.entity_key, (left, right) => {
    const rank = (PHYSICAL_RANK[left.outcome_status] || 0) - (PHYSICAL_RANK[right.outcome_status] || 0);
    return rank || compareLatest(left, right);
  });
  const components = { detected_needs: winners.length, confirmed_booking: 0, confirmed_completion: 0, unresolved_needs: 0, search_candidate_unconfirmed: 0 };
  for (const row of winners) {
    if (row.outcome_status === "confirmed_booking") components.confirmed_booking += 1;
    else if (row.outcome_status === "confirmed_completion") components.confirmed_completion += 1;
    else {
      components.unresolved_needs += 1;
      if (["search", "candidate", "unconfirmed_request"].includes(row.outcome_status)) components.search_candidate_unconfirmed += 1;
    }
  }
  const numerator = components.confirmed_booking + components.confirmed_completion;
  const envelope = baseEnvelope(period, timezone, prepared.excludedUnknownCount, components);
  envelope.source_outcome_ids = sourceRefs(winners);
  return measured(envelope, numerator, components.detected_needs,
    components.detected_needs ? `Resolved ${numerator} of ${components.detected_needs} detected needs by confirmed booking or completion.` : "No overdue needs were detected in this period.");
}

function localDateKey(ms, timeZone) {
  const parts = zonedParts(ms, timeZone);
  return `${String(parts.year).padStart(4, "0")}-${String(parts.month).padStart(2, "0")}-${String(parts.day).padStart(2, "0")}`;
}

function mentalScore(prepared, period, timezone) {
  const winners = selectLatest(prepared.rows, (row) => row.entity_key);
  const endMs = Date.parse(period.end_at);
  const validDeliveries = [];
  const components = { deduplicated_triggers: winners.length, delivered_within_cap: 0, suppression_honored: 0, correction_persisted: 0, cap_overflow: 0, unresolved_triggers: 0 };
  for (const row of winners) {
    const facts = row.components && typeof row.components === "object" ? row.components : {};
    if (row.outcome_status === "delivered") {
      const occurredMs = Date.parse(row.occurred_at);
      const resolvedPresent = row.resolved_at != null && row.resolved_at !== "";
      const effectiveMs = resolvedPresent ? Date.parse(row.resolved_at) : occurredMs;
      if (facts.intervention_valid === true && Number.isFinite(effectiveMs) && effectiveMs >= occurredMs && effectiveMs < endMs) validDeliveries.push({ row, effectiveMs });
      else components.unresolved_triggers += 1;
    } else if (row.outcome_status === "suppression_honored" && facts.send_count === 0) components.suppression_honored += 1;
    else if (row.outcome_status === "correction_persisted" && facts.context_persisted === true) components.correction_persisted += 1;
    else if (row.outcome_status === "cap_overflow") components.cap_overflow += 1;
    else components.unresolved_triggers += 1;
  }
  validDeliveries.sort((left, right) => left.effectiveMs - right.effectiveMs || compareText(left.row.public_ref, right.row.public_ref));
  const perDay = new Map();
  for (const delivery of validDeliveries) {
    const key = localDateKey(delivery.effectiveMs, timezone);
    const count = perDay.get(key) || 0;
    if (count < 3) components.delivered_within_cap += 1;
    else components.cap_overflow += 1;
    perDay.set(key, count + 1);
  }
  const numerator = components.delivered_within_cap + components.suppression_honored + components.correction_persisted;
  const envelope = baseEnvelope(period, timezone, prepared.excludedUnknownCount, components);
  envelope.source_outcome_ids = sourceRefs(winners);
  return measured(envelope, numerator, components.deduplicated_triggers,
    components.deduplicated_triggers ? `Satisfied ${numerator} of ${components.deduplicated_triggers} deduplicated triggers within delivery, suppression, and correction rules.` : "No context triggers were recorded in this period.");
}

function amountBigInt(value) {
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || value < 0) return null;
    return BigInt(value);
  }
  if (typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)) {
    const parsed = BigInt(value);
    return parsed <= MAX_SAFE_BIGINT ? parsed : null;
  }
  return null;
}

function invalidFinancial(envelope, rows, reason, excludedRows) {
  return {
    ...envelope, status: "invalid_data", value: null, numerator: null, denominator: null, reason,
    source_outcome_ids: sourceRefs(rows),
    components: { ...envelope.components, currency: null, gross_income_minor: null, realized_loss_minor: null, fee_minor: null, user_transfer_minor: null, excluded_rows: excludedRows, net_clamped: false },
  };
}

function financialScore(prepared, period, timezone) {
  const winners = selectLatest(prepared.rows, (row) => row.entity_key);
  const excludedRows = winners.filter((row) => row.outcome_status === "excluded").length;
  const baseComponents = { currency: null, gross_income_minor: 0, realized_loss_minor: 0, fee_minor: 0, user_transfer_minor: 0, excluded_rows: excludedRows, net_clamped: false };
  const envelope = baseEnvelope(period, timezone, prepared.excludedUnknownCount, baseComponents);
  const counted = winners.filter((row) => row.outcome_status !== "excluded");
  const currencies = new Set();
  const amounts = new Map();
  for (const row of counted) {
    const amount = amountBigInt(row.amount_minor);
    if (amount == null || !/^[A-Z]{3}$/.test(String(row.currency || ""))) return invalidFinancial(envelope, winners, "Financial outcome amount is outside the supported range.", excludedRows);
    amounts.set(row, amount);
    currencies.add(row.currency);
  }
  if (currencies.size > 1) return invalidFinancial(envelope, winners, "Financial outcomes use more than one currency.", excludedRows);
  let gross = 0n, loss = 0n, fee = 0n, transfer = 0n;
  for (const row of counted) {
    const amount = amounts.get(row);
    if (row.outcome_kind === "financial_external_income") gross += amount;
    else if (row.outcome_kind === "financial_realized_loss") loss += amount;
    else if (row.outcome_kind === "financial_fee") fee += amount;
    else if (row.outcome_kind === "financial_user_transfer") transfer += amount;
    if ([gross, loss, fee, transfer].some((value) => value > MAX_SAFE_BIGINT)) return invalidFinancial(envelope, winners, "Financial outcome amount is outside the supported range.", excludedRows);
  }
  const netRaw = gross - loss - fee;
  const net = netRaw < 0n ? 0n : netRaw;
  envelope.components = {
    ...envelope.components, currency: currencies.size ? [...currencies][0] : null,
    gross_income_minor: Number(gross), realized_loss_minor: Number(loss), fee_minor: Number(fee), user_transfer_minor: Number(transfer), net_clamped: netRaw < 0n,
  };
  envelope.source_outcome_ids = sourceRefs(winners);
  if (gross === 0n) {
    envelope.reason = `No verified external gross income was recorded; user transfers total ${transfer.toString()} minor units and remain separate.`;
    return envelope;
  }
  return {
    ...envelope, status: "measured", value: roundedScoreValue(net, gross), numerator: Number(net), denominator: Number(gross),
    reason: `Net verified external income is ${net.toString()} of ${gross.toString()} minor units after realized loss ${loss.toString()} and fee ${fee.toString()}; user transfers ${transfer.toString()} are shown separately.`,
  };
}

function computePanelScores(rowsByOrgan, periods, requestedTimeZone) {
  const timezone = configuredTimeZone((periods && periods.timezone) || requestedTimeZone);
  const scorers = { daily: dailyScore, physical: physicalScore, mental: mentalScore, financial: financialScore };
  const result = {};
  for (const organ of ORGAN_NAMES) {
    const period = periods && periods[organ];
    if (!period || PERIOD_KINDS[organ] !== period.kind) throw new Error("invalid score period");
    result[organ] = scorers[organ](prepareRows(rowsByOrgan, organ, period), period, timezone);
  }
  return result;
}

module.exports = { buildScorePeriods, computePanelScores, roundedScoreValue };
