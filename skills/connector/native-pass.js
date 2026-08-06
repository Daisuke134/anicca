#!/usr/bin/env node
"use strict";

const path = require("node:path");
const fs = require("node:fs");
const { createHash } = require("node:crypto");

const { runNativeConnectorPass } = require("../../apps/life-manager/lib/connector-native-runtime.js");
const { createGhIssueClient } = require("../../apps/life-manager/lib/feedback-to-issue.js");
const { recordContinuation } = require("./lib/native-state.js");
const { loadConnectorEnv } = require("./lib/load-connector-env.js");
const {
  notifyOpenClawPhoto,
  parseOpenClawMessageId,
} = require("../../apps/life-manager/lib/outbound-guardian.js");

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function unavailable() {
  throw new Error("Connector native pass unavailable");
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) unavailable();
  return directory;
}

function requiredToken(value) {
  const token = String(value == null ? "" : value).trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(token)) unavailable();
  return token;
}

function requiredText(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 2_000 || /[\x00-\x1f\x7f]/.test(text)) unavailable();
  return text;
}

function readDeliveryReceipts(stateDir) {
  const file = path.join(stateDir, "delivery-receipts.jsonl");
  let source;
  try {
    const stat = fs.statSync(file);
    if (stat.size > 1_000_000) unavailable();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return Object.freeze([]);
    throw error;
  }
  const rows = source.split(/\r?\n/).filter(Boolean).map((line) => {
    let value;
    try { value = JSON.parse(line); } catch { unavailable(); }
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || ![
        "calendar_event_ref,event_ref,telegram_provider_id",
        "artifact_sha256,calendar_event_ref,event_ref,telegram_photo_provider_id,telegram_provider_id",
      ].includes(Object.keys(value).sort().join(","))
      || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
      || !/^calendar-evidence:\/\/google\/event\/[0-9a-f]{64}$/.test(String(value.calendar_event_ref || ""))
      || !/^[^\x00-\x1f\x7f]{1,128}$/.test(String(value.telegram_provider_id || ""))
      || (Object.hasOwn(value, "telegram_photo_provider_id") && (
        !/^[^\x00-\x1f\x7f]{1,128}$/.test(String(value.telegram_photo_provider_id || ""))
        || !/^[0-9a-f]{64}$/.test(String(value.artifact_sha256 || ""))
      ))
    ) unavailable();
    return Object.freeze({ ...value });
  });
  if (rows.length > 100 || new Set(rows.map((row) => row.telegram_provider_id)).size !== rows.length) unavailable();
  return Object.freeze(rows);
}

function readPhotoDeliveredEvents(stateDir) {
  const file = path.join(stateDir, "photo-delivery-receipts.jsonl");
  let source = "";
  try {
    const stat = fs.statSync(file);
    if (stat.size > 1_000_000) unavailable();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  const events = new Set();
  for (const line of source.split(/\r?\n/).filter(Boolean)) {
    let value;
    try { value = JSON.parse(line); } catch { unavailable(); }
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== "artifact_sha256,event_ref,observed_at,telegram_photo_provider_id,telegram_provider_id"
      || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
      || !/^[0-9a-f]{64}$/.test(String(value.artifact_sha256 || ""))
      || !/^[^\x00-\x1f\x7f]{1,128}$/.test(String(value.telegram_provider_id || ""))
      || !/^[^\x00-\x1f\x7f]{1,128}$/.test(String(value.telegram_photo_provider_id || ""))
      || new Date(Date.parse(String(value.observed_at || ""))).toISOString() !== value.observed_at
    ) unavailable();
    events.add(value.event_ref);
  }
  return events;
}

async function backfillLegacyPhoto(options, stateDir, config) {
  const delivered = readDeliveryReceipts(stateDir);
  const alreadySent = readPhotoDeliveredEvents(stateDir);
  const legacy = delivered.find((row) => !row.telegram_photo_provider_id && !alreadySent.has(row.event_ref));
  if (!legacy) return;
  const tenant = String(config.tenantId || "");
  if (!/^[a-z0-9][a-z0-9._-]{0,127}$/i.test(tenant)) unavailable();
  if (!config.evidenceDir || !config.telegramTarget) return;
  const evidenceDir = absoluteDirectory(config.evidenceDir);
  const markerDir = path.join(evidenceDir, "tenants", tenant, "outbound", "luma", "artifacts");
  let names;
  try { names = fs.readdirSync(markerDir).sort(); } catch { return; }
  if (names.length > 100) unavailable();
  let artifact;
  for (const name of names) {
    if (!/^[0-9a-f]{64}\.json$/.test(name)) unavailable();
    let marker;
    try { marker = JSON.parse(fs.readFileSync(path.join(markerDir, name), "utf8")); } catch { unavailable(); }
    if (
      marker && marker.event_ref === legacy.event_ref
      && marker.sha256 === name.slice(0, -5)
    ) { artifact = marker; break; }
  }
  if (!artifact) return;
  const objectFile = path.join(evidenceDir, "objects", "sha256", artifact.sha256);
  let bytes;
  try { bytes = fs.readFileSync(objectFile); } catch { return; }
  if (
    bytes.length < 5_000 || !bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
    || createHash("sha256").update(bytes).digest("hex") !== artifact.sha256
  ) unavailable();
  const slug = legacy.event_ref.slice("luma-event://event/".length);
  const sendPhoto = typeof options.sendPhotoEvidence === "function"
    ? options.sendPhotoEvidence : notifyOpenClawPhoto;
  let response;
  try {
    response = await sendPhoto(bytes, {
      telegramTarget: requiredText(config.telegramTarget),
      caption: `✅ Connector登録済み証拠\nhttps://luma.com/${slug}`,
    });
  } catch {
    const error = new Error("Connector native photo send failed");
    error.code = "CONNECTOR_NATIVE_PHOTO_SEND_FAILED";
    throw error;
  }
  let photoProviderId;
  try { photoProviderId = parseOpenClawMessageId(JSON.stringify(response || {})); }
  catch {
    const error = new Error("Connector native photo receipt failed");
    error.code = "CONNECTOR_NATIVE_PHOTO_RECEIPT_FAILED";
    throw error;
  }
  const receipt = {
    event_ref: legacy.event_ref,
    telegram_provider_id: legacy.telegram_provider_id,
    telegram_photo_provider_id: photoProviderId,
    artifact_sha256: artifact.sha256,
    observed_at: new Date().toISOString(),
  };
  fs.appendFileSync(
    path.join(stateDir, "photo-delivery-receipts.jsonl"),
    `${JSON.stringify(receipt)}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

function readCandidateAttempts(stateDir) {
  const file = path.join(stateDir, "candidate-attempts.jsonl");
  let source;
  try {
    const stat = fs.statSync(file);
    if (stat.size > 10_000_000) unavailable();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return Object.freeze([]);
    throw error;
  }
  const rows = source.split(/\r?\n/).filter(Boolean).map((line) => {
    let value;
    try { value = JSON.parse(line); } catch { unavailable(); }
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || ![
        "event_ref,observed_at,outcome,retry_after,safe_reason",
        "capability_version,event_ref,observed_at,outcome,retry_after,safe_reason",
      ].includes(Object.keys(value).sort().join(","))
      || !(value.capability_version == null || /^[a-z0-9][a-z0-9._-]{0,63}$/.test(value.capability_version))
      || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
      || !["verified_success", "known_no_effect", "unknown_effect", "recovery_required"].includes(value.outcome)
      || !/^[A-Za-z0-9_:-]{1,100}$/.test(String(value.safe_reason || ""))
      || !Number.isFinite(Date.parse(String(value.observed_at || "")))
      || new Date(Date.parse(value.observed_at)).toISOString() !== value.observed_at
      || !(value.retry_after === null || (
        Number.isFinite(Date.parse(String(value.retry_after || "")))
        && new Date(Date.parse(value.retry_after)).toISOString() === value.retry_after
      ))
    ) unavailable();
    return Object.freeze({ ...value });
  });
  if (rows.length > 10_000) unavailable();
  return Object.freeze(rows);
}

function readCursor(stateDir) {
  const file = path.join(stateDir, "cursor.json");
  let value;
  try {
    const stat = fs.statSync(file);
    if (stat.size > 2_000) unavailable();
    value = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    if (error && error.code === "ENOENT") return null;
    unavailable();
  }
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "date,event_ref,observed_at,status"
    || value.status !== "resume_after"
    || !/^\d{4}-\d{2}-\d{2}$/.test(String(value.date || ""))
    || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
    || !Number.isFinite(Date.parse(String(value.observed_at || "")))
    || new Date(Date.parse(value.observed_at)).toISOString() !== value.observed_at
  ) unavailable();
  return Object.freeze({ ...value });
}

function runtimeConfig(options, stateDir) {
  if (options.config && typeof options.config === "object" && !Array.isArray(options.config)) {
    return options.config;
  }
  const suppliedEnv = options.env || process.env;
  const sharedFile = suppliedEnv.LM_CONNECTOR_SHARED_ENV_FILE
    || path.join(suppliedEnv.HOME || process.env.HOME || "", ".openclaw/.env");
  const env = { ...(fs.existsSync(sharedFile) ? loadConnectorEnv(sharedFile) : {}), ...suppliedEnv };
  const calendarAccount = String(
    env.LM_CONNECTOR_CALENDAR_ACCOUNT
      || env.GOG_ACCOUNT
      || env.DAIS_EMAIL
      || env.LM_CONNECTOR_LUMA_EMAIL
      || "",
  ).trim();
  if (!calendarAccount) unavailable();
  const evidenceDir = String(env.LM_CONNECTOR_EVIDENCE_DIR || path.join(stateDir, "evidence")).trim();
  const profilePath = path.resolve(String(
    env.LM_CONNECTOR_PROFILE_PATH
      || path.join(options.repoRoot, "apps/life-manager/config/connector/dais-local.json"),
  ));
  return Object.freeze({
    tenantId: String(env.LM_CONNECTOR_TENANT_ID || "dais-local").trim(),
    timeZone: String(env.LM_CONNECTOR_TIME_ZONE || "Asia/Tokyo").trim(),
    now: new Date().toISOString(),
    evidenceDir: absoluteDirectory(evidenceDir),
    calendarAccount,
    lumaEmail: requiredText(env.LM_CONNECTOR_LUMA_EMAIL || calendarAccount).toLowerCase(),
    lumaName: requiredText(env.LM_CONNECTOR_LUMA_NAME || "Dais"),
    gogBin: String(env.GOG_BIN || "").trim() || undefined,
    gogKeyring: requiredText(env.GOG_KEYRING_PASSWORD),
    profilePath,
    lumaFormProfilePath: path.join(path.dirname(stateDir), "private", "connector-luma-form-profile.json"),
    lunaEvidenceDir: absoluteDirectory(env.LM_CONNECTOR_LUNA_EVIDENCE_DIR || path.join(stateDir, "luna")),
    telegramTarget: requiredText(env.LM_CONNECTOR_TELEGRAM_TARGET),
    calendarId: requiredText(env.LM_CONNECTOR_CALENDAR_ID || "primary"),
    calendarCoverageUrl: requiredText(
      env.LM_CONNECTOR_CALENDAR_COVERAGE_URL || "https://calendar.google.com/calendar/u/0/r",
    ),
    homeLocation: requiredText(env.LIFE_HOME_ADDRESS),
    mapsKey: requiredText(env.GOOGLE_API_KEY_DIRECTIONS),
    repoRoot: absoluteDirectory(options.repoRoot),
    deliveredReceipts: readDeliveryReceipts(stateDir),
    candidateAttempts: readCandidateAttempts(stateDir),
    cursor: readCursor(stateDir),
    passCandidateBudget: Number(env.LM_CONNECTOR_PASS_CANDIDATE_BUDGET || 3),
    capabilityVersion: "luma-agentic-terra-v3",
  });
}

function boundedResult(result) {
  if (!result || typeof result !== "object" || Array.isArray(result)) unavailable();
  const status = String(result.status || "").trim();
  const counts = result.coverage && result.coverage.counts;
  const open = counts && counts.open;
  const continuation = result.continuation;
  if (
    !["complete", "incomplete"].includes(status)
    || !counts || !Number.isSafeInteger(open) || open < 0 || open > 21
    || !continuation || typeof continuation !== "object"
    || !["complete", "continue"].includes(String(continuation.status || ""))
  ) unavailable();
  const complete = status === "complete"
    && open === 0
    && continuation.status === "complete";
  if (status === "complete" && !complete) unavailable();
  if (status === "incomplete" && complete) unavailable();
  const rawWrite = result.write && typeof result.write === "object" && !Array.isArray(result.write)
    ? result.write : null;
  const receipt = rawWrite && rawWrite.registration_receipt;
  let evidence = {};
  if (receipt != null) {
    const artifactMatch = /^object:\/\/sha256\/([0-9a-f]{64})$/.exec(String(receipt.artifact_ref || ""));
    let canonical;
    try { canonical = new URL(String(receipt.canonical_url || "")); } catch { unavailable(); }
    const photoProviderId = String(rawWrite.telegram && rawWrite.telegram.photo_provider_id || "");
    const confirmationRef = String(rawWrite.confirmation && rawWrite.confirmation.external_receipt_ref || "");
    const ticketReceiptRef = String(rawWrite.ticket && rawWrite.ticket.ticket_receipt_ref || "");
    const ticketArtifactRef = String(rawWrite.ticket && rawWrite.ticket.artifact_ref || "");
    const ticketTelegramProviderId = String(rawWrite.ticket && rawWrite.ticket.telegram_provider_id || "");
    const hasTicketChain = Boolean(
      confirmationRef || ticketReceiptRef || ticketArtifactRef || ticketTelegramProviderId,
    );
    if (
      !artifactMatch || receipt.artifact_sha256 !== artifactMatch[1]
      || canonical.protocol !== "https:" || canonical.hostname !== "luma.com"
      || new Date(Date.parse(String(receipt.evidence_observed_at || ""))).toISOString() !== receipt.evidence_observed_at
      || !/^[^\x00-\x1f\x7f]{1,128}$/.test(photoProviderId)
      || rawWrite.telegram.artifact_sha256 !== receipt.artifact_sha256
      || (hasTicketChain && (
        !/^gmail-message:\/\/[a-z0-9._-]+\/[0-9a-f]{64}$/i.test(confirmationRef)
        || !/^ticket:\/\/[a-z0-9._-]+\/[0-9a-f]{64}$/i.test(ticketReceiptRef)
        || !/^object:\/\/sha256\/[0-9a-f]{64}$/.test(ticketArtifactRef)
        || !/^[^\x00-\x1f\x7f]{1,128}$/.test(ticketTelegramProviderId)
      ))
    ) unavailable();
    evidence = {
      canonical_url: canonical.toString(),
      evidence_observed_at: receipt.evidence_observed_at,
      artifact_ref: receipt.artifact_ref,
      artifact_sha256: receipt.artifact_sha256,
      telegram_photo_provider_id: photoProviderId,
      ...(hasTicketChain ? {
        confirmation_receipt_ref: confirmationRef,
        ticket_receipt_ref: ticketReceiptRef,
        ticket_artifact_ref: ticketArtifactRef,
        ticket_telegram_provider_id: ticketTelegramProviderId,
      } : {}),
    };
  }
  const write = rawWrite
    ? {
      status: String(result.write.status || ""),
      outcome: String(result.write.outcome || ""),
      ...(/^[A-Z][A-Z0-9_:-]{0,99}$/.test(String(result.write.error_code || ""))
        ? { error_code: String(result.write.error_code) }
        : {}),
      event_ref: String(result.write.event_ref || ""),
      ...evidence,
      calendar_event_ref: String(result.write.calendar_sync && result.write.calendar_sync.calendar_event_ref || ""),
      telegram_provider_id: String(result.write.telegram && result.write.telegram.provider_id || ""),
    }
    : null;
  const coverageCounts = Object.freeze({
    open,
    covered_existing: Number(counts.covered_existing || 0),
    covered_new: Number(counts.covered_new || 0),
    unavailable: Number(counts.unavailable || 0),
  });
  if (Object.values(coverageCounts).some((value) => !Number.isSafeInteger(value) || value < 0)) unavailable();
  let selection = null;
  if (result.selection != null) {
    const value = result.selection;
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== [
        "calendar_eligible_count", "calendar_gate_event_count", "inventory_event_count",
        "luna_ranked_count", "spend_ordered_count", "unsuppressed_count", "write_attempt_count",
      ].sort().join(",")
      || Object.values(value).some((count) => !Number.isSafeInteger(count) || count < 0 || count > 10_000)
      || value.calendar_gate_event_count > value.inventory_event_count
      || value.calendar_eligible_count > value.calendar_gate_event_count
      || value.spend_ordered_count > value.calendar_eligible_count
      || value.unsuppressed_count > value.spend_ordered_count
      || value.write_attempt_count > value.unsuppressed_count
    ) unavailable();
    selection = Object.freeze({ ...value });
  }
  const candidateAttempts = Array.isArray(result.candidate_attempts)
    ? result.candidate_attempts.map((attempt) => {
      if (
        !attempt || typeof attempt !== "object" || Array.isArray(attempt)
        || ![
          "event_ref,observed_at,outcome,retry_after,safe_reason",
          "capability_version,event_ref,observed_at,outcome,retry_after,safe_reason",
        ].includes(Object.keys(attempt).sort().join(","))
        || !(attempt.capability_version == null || /^[a-z0-9][a-z0-9._-]{0,63}$/.test(attempt.capability_version))
        || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(attempt.event_ref || ""))
        || !["verified_success", "known_no_effect", "unknown_effect", "recovery_required"].includes(attempt.outcome)
        || !/^[A-Za-z0-9_:-]{1,100}$/.test(String(attempt.safe_reason || ""))
        || new Date(Date.parse(String(attempt.observed_at || ""))).toISOString() !== attempt.observed_at
        || !(attempt.retry_after === null
          || new Date(Date.parse(String(attempt.retry_after || ""))).toISOString() === attempt.retry_after)
      ) unavailable();
      return Object.freeze({ ...attempt });
    })
    : [];
  if (candidateAttempts.length > 100) unavailable();
  const cursor = result.cursor == null ? null : result.cursor;
  if (
    cursor !== null && (
      !cursor || typeof cursor !== "object" || Array.isArray(cursor)
      || Object.keys(cursor).sort().join(",") !== "date,event_ref,observed_at,status"
      || cursor.status !== "resume_after"
      || !/^\d{4}-\d{2}-\d{2}$/.test(String(cursor.date || ""))
      || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(cursor.event_ref || ""))
      || !Number.isFinite(Date.parse(String(cursor.observed_at || "")))
      || new Date(Date.parse(cursor.observed_at)).toISOString() !== cursor.observed_at
    )
  ) unavailable();
  return Object.freeze({
    status,
    complete,
    write,
    candidateAttempts: Object.freeze(candidateAttempts),
    cursor: cursor === null ? null : Object.freeze({ ...cursor }),
    coverageCounts,
    selection,
  });
}

function appendCandidateAttempts(stateDir, attempts) {
  if (!attempts.length) return;
  const historyFile = path.join(stateDir, "candidate-attempts.jsonl");
  try {
    const stat = fs.statSync(historyFile);
    if (stat.size > 10_000_000) unavailable();
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  fs.appendFileSync(
    historyFile,
    `${attempts.map((attempt) => JSON.stringify(attempt)).join("\n")}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

function recordSelfHealIncident(stateDir, bounded) {
  const selection = bounded.selection;
  if (
    !selection
    || selection.spend_ordered_count < 1
    || selection.unsuppressed_count !== 0
    || selection.write_attempt_count !== 0
  ) return;
  const formFailure = [...readCandidateAttempts(stateDir)].reverse().find((attempt) => (
    attempt.outcome === "known_no_effect"
    && attempt.safe_reason === "LUMA_FORM_INPUT_REQUIRED"
    && attempt.retry_after === null
  ));
  if (!formFailure) return;
  const incidentClass = "apply_blocked_by_suppression";
  const component = "connector-native";
  const fingerprint = `sha256:${createHash("sha256").update(
    `${component}:${incidentClass}:${formFailure.safe_reason}`,
  ).digest("hex")}`;
  const file = path.join(stateDir, "self-heal-incidents.jsonl");
  let existing = "";
  try {
    const stat = fs.statSync(file);
    if (stat.size > 1_000_000) unavailable();
    existing = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  const duplicate = existing.split(/\r?\n/).filter(Boolean).some((line) => {
    try { return JSON.parse(line).fingerprint === fingerprint; }
    catch { unavailable(); }
  });
  if (duplicate) return;
  const incident = {
    schema_version: 1,
    fingerprint,
    component,
    incident_class: incidentClass,
    safe_reason: formFailure.safe_reason,
    observed_at: formFailure.observed_at,
    selection,
  };
  fs.appendFileSync(file, `${JSON.stringify(incident)}\n`, { encoding: "utf8", mode: 0o600 });
}

async function deliverPendingSelfHealIncident(options, stateDir) {
  const incidentFile = path.join(stateDir, "self-heal-incidents.jsonl");
  const receiptFile = path.join(stateDir, "self-heal-issue-receipts.jsonl");
  let incidents = "";
  let receipts = "";
  try { incidents = fs.readFileSync(incidentFile, "utf8"); }
  catch (error) { if (!error || error.code !== "ENOENT") throw error; }
  try { receipts = fs.readFileSync(receiptFile, "utf8"); }
  catch (error) { if (!error || error.code !== "ENOENT") throw error; }
  if (incidents.length > 1_000_000 || receipts.length > 1_000_000) unavailable();
  const delivered = new Set(receipts.split(/\r?\n/).filter(Boolean).map((line) => {
    try { return JSON.parse(line).fingerprint; } catch { unavailable(); }
  }));
  let incident = null;
  for (const line of incidents.split(/\r?\n/).filter(Boolean)) {
    let value;
    try { value = JSON.parse(line); } catch { unavailable(); }
    if (!delivered.has(value.fingerprint)) { incident = value; break; }
  }
  if (!incident) return;
  if (
    incident.schema_version !== 1
    || !/^sha256:[0-9a-f]{64}$/.test(String(incident.fingerprint || ""))
    || incident.component !== "connector-native"
    || incident.incident_class !== "apply_blocked_by_suppression"
    || incident.safe_reason !== "LUMA_FORM_INPUT_REQUIRED"
  ) unavailable();
  const marker = `lm-connector-incident:${incident.fingerprint}`;
  const issue = {
    title: "[error] Connector apply blocked by suppression",
    body: [
      "## Privacy-safe Connector incident",
      "",
      `Safe reason: ${incident.safe_reason}`,
      `Selection telemetry: ${JSON.stringify(incident.selection)}`,
      "",
      "## Acceptance",
      "",
      "- Add a failing regression test that reproduces Apply attempt count remaining zero.",
      "- Fix the smallest root cause and keep Connector tests green.",
      "- Verify the real Connector reaches Apply, submit, readback, and screenshot evidence.",
      "- Do not add raw event content, identity, contact, cookie, or secret data.",
      "",
      `<!-- ${marker} -->`,
    ].join("\n"),
    labels: ["lm:type:self-heal"],
  };
  const client = options.issueClient || createGhIssueClient();
  await client.ensureLabel("lm:type:self-heal");
  const existing = await client.findByMarker(marker);
  const resolved = existing || await client.create(issue);
  const issueUrl = String(resolved && resolved.url || "");
  if (!/^https:\/\/github\.com\/Daisuke134\/life-manager\/issues\/[1-9][0-9]*$/.test(issueUrl)) unavailable();
  fs.appendFileSync(receiptFile, `${JSON.stringify({
    schema_version: 1,
    fingerprint: incident.fingerprint,
    issue_url: issueUrl,
    observed_at: new Date().toISOString(),
  })}\n`, { encoding: "utf8", mode: 0o600 });
}

function appendDeliveryReceipt(stateDir, write) {
  if (write && write.telegram_provider_id && write.event_ref && write.calendar_event_ref) {
    const hasNewEvidence = Boolean(write.artifact_sha256 || write.telegram_photo_provider_id);
    if (hasNewEvidence && !(write.artifact_sha256 && write.telegram_photo_provider_id)) unavailable();
    const historyFile = path.join(stateDir, "delivery-receipts.jsonl");
    let existing = "";
    try {
      const stat = fs.statSync(historyFile);
      if (stat.size > 1_000_000) unavailable();
      existing = fs.readFileSync(historyFile, "utf8");
    } catch (error) {
      if (!error || error.code !== "ENOENT") throw error;
    }
    const receipt = {
      event_ref: write.event_ref,
      calendar_event_ref: write.calendar_event_ref,
      telegram_provider_id: write.telegram_provider_id,
      ...(hasNewEvidence ? {
        telegram_photo_provider_id: write.telegram_photo_provider_id,
        artifact_sha256: write.artifact_sha256,
      } : {}),
    };
    const duplicate = existing.split(/\r?\n/).filter(Boolean).some((line) => {
      try { return JSON.parse(line).telegram_provider_id === receipt.telegram_provider_id; }
      catch { unavailable(); }
    });
    if (!duplicate) fs.appendFileSync(historyFile, `${JSON.stringify(receipt)}\n`, { encoding: "utf8", mode: 0o600 });
  }
}

function recordCursor(stateDir, cursor) {
  const file = path.join(stateDir, "cursor.json");
  if (cursor === null) {
    try { fs.unlinkSync(file); }
    catch (error) { if (!error || error.code !== "ENOENT") throw error; }
    return;
  }
  fs.writeFileSync(file, `${JSON.stringify(cursor)}\n`, { encoding: "utf8", mode: 0o600 });
}

function recordLastResult(stateDir, bounded) {
  const file = path.join(stateDir, "last-result.json");
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(file, `${JSON.stringify({
    status: bounded.status, coverage_counts: bounded.coverageCounts,
    ...(bounded.selection ? { selection: bounded.selection } : {}),
    write: bounded.write,
  })}\n`, {
    encoding: "utf8", mode: 0o600,
  });
  appendDeliveryReceipt(stateDir, bounded.write);
  appendCandidateAttempts(stateDir, bounded.candidateAttempts);
  recordSelfHealIncident(stateDir, bounded);
  recordCursor(stateDir, bounded.cursor);
}

function migrateLastResult(stateDir) {
  const file = path.join(stateDir, "last-result.json");
  let value;
  try { value = JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) {
    if (error && error.code === "ENOENT") return;
    unavailable();
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) unavailable();
  appendDeliveryReceipt(stateDir, value.write);
}

async function runNativePass(options = {}) {
  absoluteDirectory(options.repoRoot);
  const stateDir = absoluteDirectory(options.stateDir);
  requiredToken(options.ownerToken);
  migrateLastResult(stateDir);

  const runtime = typeof options.runRuntime === "function"
    ? options.runRuntime
    : runNativeConnectorPass;
  try {
    const config = runtimeConfig(options, stateDir);
    await backfillLegacyPhoto(options, stateDir, config);
    const result = await runtime({
      config,
      deps: options.deps && typeof options.deps === "object" ? options.deps : {},
    });
    const bounded = boundedResult(result);
    recordLastResult(stateDir, bounded);
    await deliverPendingSelfHealIncident(options, stateDir);
    if (bounded.complete) {
      return Object.freeze({ exitCode: 0, status: "complete" });
    }
    recordContinuation({ stateDir, reason: "runtime_incomplete" });
    return Object.freeze({ exitCode: 1, status: "incomplete" });
  } catch (error) {
    const code = String(error && error.code || "");
    const reason = /^CONNECTOR_NATIVE_(?:CONFIG|AUTH|INVENTORY|CALENDAR_READ|PROFILE|LUNA|CALENDAR_GATE(?:_INPUT|_EXECUTION|_RESULT)?|SPEND_GATE|WRITE|PHOTO_SEND|PHOTO_RECEIPT)_FAILED$/.test(code)
      ? code.toLowerCase()
      : "runtime_failed";
    recordContinuation({ stateDir, reason });
    return Object.freeze({ exitCode: 1, status: "failed" });
  }
}

function cliArguments(argv = process.argv.slice(2)) {
  if (argv.length !== 6 || argv[0] !== "--repo-root" || argv[2] !== "--state-dir" || argv[4] !== "--owner-token") {
    unavailable();
  }
  return Object.freeze({ repoRoot: argv[1], stateDir: argv[3], ownerToken: argv[5], env: process.env });
}

if (require.main === module) {
  runNativePass(cliArguments())
    .then((result) => { process.exit(result.exitCode); })
    .catch(() => {
      process.stderr.write("Connector native pass unavailable\n", () => process.exit(2));
    });
}

module.exports = { runNativePass };
