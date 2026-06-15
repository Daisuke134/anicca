#!/usr/bin/env node
// ~/anicca/skills/life/notify/notify.js
// B-notify skill entrypoint — spec27 WF-B B-notify (email-only approval gate).
//
// Two modes (selected by first CLI arg or NOTIFY_MODE env var):
//
//   node notify.js scan   (default)
//     1. List today's GCal events via `gog` CLI
//     2. detectLateRiskEvents — events with a started [Travel] block
//     3. For each at-risk event:
//        a. Build draft message body (buildAttendeeDraft)
//        b. Save draft to AgentMail Drafts (durable hold)
//        c. Send approval email to owner (buildApprovalEmail)
//     Exits 0 if OK (even when 0 late risks found).
//
//   node notify.js webhook --draftId <id> --reply <text>
//     1. extractApproval from reply text
//     2. If approved: fetch draft from AgentMail → send to attendees
//     Exits 0 on success, 1 on error.
//
// Env (read from ~/.openclaw/.env):
//   AGENTMAIL_API_KEY      — required (AgentMail bearer token)
//   AGENTMAIL_INBOX_ID     — required (e.g. anicca-genesis@agentmail.to)
//   OWNER_EMAIL            — required (recipient of approval email, e.g. keiodaisuke@gmail.com)
//   GOG_KEYRING_PASSWORD   — required for GCal via gog CLI
//   GOG_ACCOUNT            — Google account (default: keiodaisuke@gmail.com)
//   GCAL_ID                — Calendar ID (default: primary)
//
// This skill is the local Anicca body implementation; the matching Netlify
// function (apps/landing/netlify/functions/life-notify.js) runs the same
// business logic (notify-logic.js) in the cloud, triggered by heartbeat POSTs.
//
// Pattern mirrors ~/anicca/skills/life/travel/travel.js (proven WF-B template).

"use strict";

const { execFileSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// ── Config ──────────────────────────────────────────────────────────────────

const TRAVEL_PREFIX = "[Travel] ";
const GOG_BIN = "/opt/homebrew/bin/gog";
const AGENTMAIL_BASE = "https://api.agentmail.to/v0";

function loadEnv() {
  const envPath = path.join(process.env.HOME || "/root", ".openclaw", ".env");
  const raw = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8") : "";
  const out = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}

const ENV = loadEnv();
const AGENTMAIL_API_KEY = process.env.AGENTMAIL_API_KEY || ENV.AGENTMAIL_API_KEY || "";
const AGENTMAIL_INBOX_ID = process.env.AGENTMAIL_INBOX_ID || ENV.AGENTMAIL_INBOX_ID || "";
const OWNER_EMAIL = process.env.OWNER_EMAIL || ENV.OWNER_EMAIL || ENV.GOG_ACCOUNT || "keiodaisuke@gmail.com";
const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT || "keiodaisuke@gmail.com";
const GOG_KEYRING_PASSWORD = process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "";
const GCAL_ID = process.env.GCAL_ID || ENV.GCAL_ID || "primary";

// ── Pure logic (mirrors notify-logic.js in the Netlify function) ─────────────

/**
 * Returns true if a GCal event summary is an auto-inserted travel block.
 * @param {string} summary
 * @returns {boolean}
 */
function isTravelBlock(summary) {
  return typeof summary === "string" && summary.startsWith(TRAVEL_PREFIX);
}

/**
 * Returns true when a travel block has already started (late-risk).
 * @param {{ travelStartMs: number, nowMs: number }} opts
 * @returns {boolean}
 */
function isLateRisk({ travelStartMs, nowMs }) {
  return nowMs > travelStartMs;
}

/**
 * Given today's GCal events and current time, return late-risk events:
 * those with a matching [Travel] block that has already started.
 * @param {Array<object>} events
 * @param {number} nowMs
 * @returns {Array<{event: object, travelEvent: object, isLate: boolean}>}
 */
function detectLateRiskEvents(events, nowMs) {
  if (!Array.isArray(events)) return [];

  const travelBlocks = new Map();
  for (const e of events) {
    if (!e.start || !e.start.dateTime) continue;
    if (!isTravelBlock(e.summary || "")) continue;
    const dest = (e.summary || "").slice(TRAVEL_PREFIX.length).trim();
    travelBlocks.set(dest, e);
  }

  const risks = [];
  for (const e of events) {
    if (!e.start || !e.start.dateTime) continue;
    if (isTravelBlock(e.summary || "")) continue;

    const title = (e.summary || "").trim();
    const travelBlock = travelBlocks.get(title);
    if (!travelBlock) continue;

    const travelStartMs = new Date(travelBlock.start.dateTime).getTime();
    if (isLateRisk({ travelStartMs, nowMs })) {
      risks.push({ event: e, travelEvent: travelBlock, isLate: true });
    }
  }
  return risks;
}

/**
 * Estimate minutes late (clamped ≥5, rounded to nearest 5).
 * @param {{ travelStartMs: number, nowMs: number }} opts
 * @returns {number}
 */
function estimateMinutesLate({ travelStartMs, nowMs }) {
  const diff = Math.round((nowMs - travelStartMs) / 60_000);
  const clamped = Math.max(5, diff);
  return Math.round(clamped / 5) * 5;
}

/**
 * Build the short draft message to send to attendees.
 * @param {{ eventSummary: string, minutesLate: number }} opts
 * @returns {string}
 */
function buildAttendeeDraft({ eventSummary, minutesLate }) {
  return (
    `I'll be approximately ${minutesLate} minutes late to "${eventSummary}". ` +
    `Apologies for the short notice — I'm on my way.`
  );
}

/**
 * Build the approval email body for the calendar owner.
 * @param {{ ownerEmail, eventSummary, attendees, draftBody, draftId }} opts
 * @returns {{ to, subject, body }}
 */
function buildApprovalEmail({ ownerEmail, eventSummary, attendees, draftBody, draftId }) {
  const recipientList =
    attendees && attendees.length > 0
      ? attendees.map((a) => a.email).join(", ")
      : "(no attendees found — reply OK to dismiss)";

  const subject = `[Anicca] Late alert for "${eventSummary}" — reply OK to notify`;

  const body = [
    `You appear to be running late for: "${eventSummary}"`,
    ``,
    `Anicca will send the following to: ${recipientList}`,
    ``,
    `───────────────────────────────`,
    draftBody,
    `───────────────────────────────`,
    ``,
    `Reply "OK" to this email to approve and send.`,
    `Reply anything else (or ignore) to cancel.`,
    ``,
    `Draft ID: ${draftId}`,
    `Powered by Anicca B-notify (spec27)`,
  ].join("\n");

  return { to: ownerEmail, subject, body };
}

/**
 * Parse an inbound reply body to determine if the owner approved.
 * Accepts: "ok", "ok!", "ok,", "ok " (case-insensitive), "はい".
 * @param {string} replyBody
 * @returns {boolean}
 */
function extractApproval(replyBody) {
  if (typeof replyBody !== "string") return false;
  const trimmed = replyBody.trim();
  const lower = trimmed.toLowerCase();
  if (lower === "ok" || lower.startsWith("ok!") || lower.startsWith("ok,") || lower.startsWith("ok ")) {
    return true;
  }
  if (trimmed === "はい" || trimmed.startsWith("はい")) return true;
  return false;
}

// ── GCal via gog CLI ─────────────────────────────────────────────────────────

function gogEnv() {
  return { ...process.env, GOG_KEYRING_PASSWORD, GOG_ACCOUNT };
}

/**
 * List today's events from GCal via gog CLI.
 * @returns {Array<object>} GCal event items
 */
function listTodayEvents() {
  const today = new Date().toISOString().slice(0, 10);
  const raw = execFileSync(GOG_BIN, [
    "calendar", "events", "list",
    "-j",
    "--account", GOG_ACCOUNT,
    "--from", today,
    "--to", today,
    "--all-pages",
  ], { env: gogEnv(), timeout: 60000 }).toString();

  const d = JSON.parse(raw);
  return Array.isArray(d) ? d : (d.events || d.items || []);
}

// ── AgentMail REST helpers ─────────────────────────────────────────────────

/** Headers for all AgentMail REST calls */
function amHeaders() {
  return {
    Authorization: `Bearer ${AGENTMAIL_API_KEY}`,
    "Content-Type": "application/json",
  };
}

/**
 * Save a draft to AgentMail Drafts.
 * @param {{ to, subject, body }} draft
 * @returns {Promise<{ id: string }>}
 */
async function saveAgentMailDraft({ to, subject, body }) {
  const url = `${AGENTMAIL_BASE}/inboxes/${encodeURIComponent(AGENTMAIL_INBOX_ID)}/drafts`;
  const r = await fetch(url, {
    method: "POST",
    headers: amHeaders(),
    body: JSON.stringify({ to, subject, body }),
  });
  if (!r.ok) {
    const msg = await r.text();
    throw new Error(`AgentMail draft save ${r.status}: ${msg}`);
  }
  return r.json();
}

/**
 * Send a message directly via AgentMail.
 * @param {{ to, subject, body }} msg
 * @returns {Promise<{ id: string }>}
 */
async function sendAgentMailEmail({ to, subject, body }) {
  const url = `${AGENTMAIL_BASE}/inboxes/${encodeURIComponent(AGENTMAIL_INBOX_ID)}/messages/send`;
  const r = await fetch(url, {
    method: "POST",
    headers: amHeaders(),
    body: JSON.stringify({ to, subject, body }),
  });
  if (!r.ok) {
    const msg = await r.text();
    throw new Error(`AgentMail send ${r.status}: ${msg}`);
  }
  return r.json();
}

/**
 * Fetch a saved draft by ID.
 * @param {string} draftId
 * @returns {Promise<{ id, to, subject, body }>}
 */
async function getAgentMailDraft(draftId) {
  const url = `${AGENTMAIL_BASE}/inboxes/${encodeURIComponent(AGENTMAIL_INBOX_ID)}/drafts/${encodeURIComponent(draftId)}`;
  const r = await fetch(url, { headers: amHeaders() });
  if (!r.ok) {
    const msg = await r.text();
    throw new Error(`AgentMail draft get ${r.status}: ${msg}`);
  }
  return r.json();
}

// ── Scan mode ─────────────────────────────────────────────────────────────────

async function runScan() {
  // Validate required env
  if (!AGENTMAIL_API_KEY) throw new Error("AGENTMAIL_API_KEY is required");
  if (!AGENTMAIL_INBOX_ID) throw new Error("AGENTMAIL_INBOX_ID is required");
  if (!OWNER_EMAIL) throw new Error("OWNER_EMAIL is required");

  const events = listTodayEvents();
  const nowMs = Date.now();
  const risks = detectLateRiskEvents(events, nowMs);

  if (risks.length === 0) {
    console.log(JSON.stringify({ ok: true, scanned: events.length, lateRisks: 0, alerted: [] }));
    return;
  }

  const alerted = [];
  for (const { event: ev, travelEvent } of risks) {
    const travelStartMs = new Date(travelEvent.start.dateTime).getTime();
    const minutesLate = estimateMinutesLate({ travelStartMs, nowMs });
    const attendees = ev.attendees || [];
    const attendeeEmails = attendees.map((a) => a.email).filter(Boolean);
    const draftTo = attendeeEmails.length > 0 ? attendeeEmails.join(",") : OWNER_EMAIL;

    const draftBody = buildAttendeeDraft({ eventSummary: ev.summary, minutesLate });

    let draft;
    try {
      draft = await saveAgentMailDraft({
        to: draftTo,
        subject: `Late notice for "${ev.summary}"`,
        body: draftBody,
      });
    } catch (err) {
      console.error(`[notify] draft save failed for "${ev.summary}":`, err.message);
      alerted.push({ error: `draft_save: ${err.message}`, event: ev.summary });
      continue;
    }

    const approvalEmail = buildApprovalEmail({
      ownerEmail: OWNER_EMAIL,
      eventSummary: ev.summary,
      attendees,
      draftBody,
      draftId: draft.id,
    });

    try {
      await sendAgentMailEmail({
        to: approvalEmail.to,
        subject: approvalEmail.subject,
        body: approvalEmail.body,
      });
      alerted.push({ event: ev.summary, draftId: draft.id, minutesLate });
    } catch (err) {
      console.error(`[notify] approval email failed for "${ev.summary}":`, err.message);
      alerted.push({ error: `approval_send: ${err.message}`, event: ev.summary });
    }
  }

  const result = { ok: true, scanned: events.length, lateRisks: risks.length, alerted };
  console.log(JSON.stringify(result));
}

// ── Webhook mode ──────────────────────────────────────────────────────────────

async function runWebhook(args) {
  if (!AGENTMAIL_API_KEY) throw new Error("AGENTMAIL_API_KEY is required");
  if (!AGENTMAIL_INBOX_ID) throw new Error("AGENTMAIL_INBOX_ID is required");

  // Parse --draftId and --reply from CLI args
  const draftIdIdx = args.indexOf("--draftId");
  const replyIdx = args.indexOf("--reply");
  if (draftIdIdx === -1 || replyIdx === -1) {
    throw new Error("webhook mode requires --draftId <id> --reply <text>");
  }
  const draftId = args[draftIdIdx + 1];
  const replyBody = args[replyIdx + 1];

  if (!draftId || !replyBody) {
    throw new Error("--draftId and --reply must have non-empty values");
  }

  const approved = extractApproval(replyBody);
  if (!approved) {
    console.log(JSON.stringify({ ok: true, approved: false, sent: 0 }));
    return;
  }

  const draft = await getAgentMailDraft(draftId);
  const attendeeEmails = Array.isArray(draft.to) ? draft.to : [draft.to].filter(Boolean);

  let sentCount = 0;
  for (const to of attendeeEmails) {
    try {
      await sendAgentMailEmail({
        to,
        subject: draft.subject || "Update from Anicca",
        body: draft.body || "",
      });
      sentCount += 1;
    } catch (err) {
      console.error(`[notify] send failed to ${to}:`, err.message);
    }
  }

  console.log(JSON.stringify({ ok: true, approved: true, sent: sentCount }));
}

// ── Main ──────────────────────────────────────────────────────────────────────

const [, , mode = "scan", ...rest] = process.argv;

(async () => {
  try {
    if (mode === "webhook") {
      await runWebhook(rest);
    } else {
      await runScan();
    }
    process.exit(0);
  } catch (err) {
    console.error("[notify] fatal:", err.message);
    process.exit(1);
  }
})();

module.exports = {
  isTravelBlock,
  isLateRisk,
  detectLateRiskEvents,
  estimateMinutesLate,
  buildAttendeeDraft,
  buildApprovalEmail,
  extractApproval,
};
