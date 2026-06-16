#!/usr/bin/env node
// ~/anicca/skills/life/travel/travel.js
// B-travel skill entrypoint — spec27 WF-B B-travel.
//
// Uses `gog` CLI (google cli) with GOG_KEYRING_PASSWORD to:
//   1. List today's events from GCal
//   2. Detect events missing a "[Travel] <title>" block
//   3. Get travel duration from Google Maps Directions API
//   4. Insert "[Travel]" blocks before each uncovered event
//
// Canonical trigger: openclaw cron "anicca-travel-fill" (daily 05:00 JST)
// Also callable manually: node travel.js [--dry-run] [--horizon <days>]
//
// Env (read from ~/.openclaw/.env):
//   GOG_KEYRING_PASSWORD       — required, unlocks gog's keyring
//   GOG_ACCOUNT                — Google account email (default: keiodaisuke@gmail.com)
//   GOOGLE_API_KEY_DIRECTIONS  — Google Maps Directions API key (optional; falls back to 20min)
//   TRAVEL_HORIZON_DAYS        — how many days ahead to scan (default: 1)
//   HOME_ADDRESS               — departure address (default: 新宿区南元町15-27)

"use strict";

const { execFileSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// ── Config ──────────────────────────────────────────────────────────────────

const TRAVEL_PREFIX = "[Travel] ";
const TRAVEL_COLOR_ID = "7"; // Peacock — visually distinct
const DEFAULT_TRAVEL_SEC = 20 * 60; // 20 min fallback
const GOG_BIN = "/opt/homebrew/bin/gog";

function loadEnv() {
  const envPath = path.join(process.env.HOME, ".openclaw", ".env");
  const raw = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8") : "";
  const out = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}

const ENV = loadEnv();
const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT || "keiodaisuke@gmail.com";
const GOG_KEYRING_PASSWORD = process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "";
const MAPS_KEY = process.env.GOOGLE_API_KEY_DIRECTIONS || ENV.GOOGLE_API_KEY_DIRECTIONS || "";
const HOME_ADDRESS = process.env.HOME_ADDRESS || ENV.HOME_ADDRESS || "新宿区南元町15-27";
const HORIZON_DAYS = parseInt(process.env.TRAVEL_HORIZON_DAYS || "1", 10);
const EVENT_TZ = process.env.TRAVEL_EVENT_TZ || ENV.TRAVEL_EVENT_TZ || "Asia/Tokyo";
const DRY_RUN = process.argv.includes("--dry-run");

// ── GCal via gog CLI ────────────────────────────────────────────────────────

function gogEnv() {
  return { ...process.env, GOG_KEYRING_PASSWORD, GOG_ACCOUNT };
}

/**
 * List events for the next HORIZON_DAYS days.
 * @returns {Array<object>} GCal event items
 */
function listEvents() {
  const to = new Date();
  to.setDate(to.getDate() + HORIZON_DAYS);
  const toStr = to.toISOString().slice(0, 10);

  // execFileSync — no shell, args array prevents injection
  const raw = execFileSync(GOG_BIN, [
    "calendar", "events", "list",
    "-j",
    "--account", GOG_ACCOUNT,
    "--from", "today",
    "--to", toStr,
    "--all-pages",
  ], { env: gogEnv(), timeout: 60000 }).toString();

  const d = JSON.parse(raw);
  return Array.isArray(d) ? d : (d.events || d.items || []);
}

/**
 * Insert a single GCal event via gog.
 * @param {object} opts
 * @param {string} opts.summary
 * @param {string} opts.startIso
 * @param {string} opts.endIso
 * @param {string} opts.description
 * @returns {string|null} created event id, or null on error
 */
function insertEvent({ summary, startIso, endIso, description }) {
  if (DRY_RUN) {
    console.log(`[dry-run] would insert: ${summary} ${startIso}–${endIso}`);
    return "dry-run-id";
  }
  try {
    // execFileSync — no shell, args array prevents injection
    const raw = execFileSync(GOG_BIN, [
      "calendar", "create", "primary",
      "-j",
      "--account", GOG_ACCOUNT,
      "--summary", summary,
      "--from", startIso,
      "--to", endIso,
      "--start-timezone", EVENT_TZ,
      "--end-timezone", EVENT_TZ,
      "--description", description,
      "--event-color", TRAVEL_COLOR_ID,
    ], { env: gogEnv(), timeout: 30000 }).toString();

    const d = JSON.parse(raw);
    return (d.event && d.event.id) || d.id || null;
  } catch (err) {
    console.error(`[travel] insert failed for "${summary}":`, err.message.slice(0, 200));
    return null;
  }
}

// ── Pure logic (mirrors travel-logic.js in the Netlify function) ───────────

/**
 * Returns true if an event summary is an auto-inserted travel block.
 * @param {string} summary
 * @returns {boolean}
 */
function isTravelBlock(summary) {
  return typeof summary === "string" && summary.startsWith(TRAVEL_PREFIX);
}

/**
 * Given a list of GCal event objects, return those that need a travel block.
 * @param {Array<object>} events - GCal event resource list
 * @returns {Array<object>} events missing a travel block
 */
function detectMissingTravelBlocks(events) {
  if (!Array.isArray(events)) return [];

  const coveredTitles = new Set(
    events
      .filter((e) => isTravelBlock(e.summary || ""))
      .map((e) => (e.summary || "").slice(TRAVEL_PREFIX.length).trim())
  );

  return events.filter((e) => {
    const summary = (e.summary || "").trim();
    if (!e.start || !e.start.dateTime) return false; // skip all-day events
    if (isTravelBlock(summary)) return false;
    if (coveredTitles.has(summary)) return false;
    // location≠home-only: an event with no explicit location can't be travelled to
    if (!(e.location && e.location.trim())) return false;
    return true;
  });
}

// ── Google Maps Directions ──────────────────────────────────────────────────

/**
 * Returns travel duration in seconds via Google Maps Directions API.
 * Falls back to DEFAULT_TRAVEL_SEC when no destination or no API key.
 * @param {string} origin
 * @param {string|null} destination
 * @returns {Promise<number>} duration in seconds
 */
async function getTravelDurationSec(origin, destination) {
  if (!destination || !MAPS_KEY) return DEFAULT_TRAVEL_SEC;

  for (const mode of ["transit", "driving"]) {
    const params = new URLSearchParams({ origin, destination, mode, key: MAPS_KEY });
    if (mode === "transit") params.set("departure_time", "now");
    try {
      const r = await fetch(`https://maps.googleapis.com/maps/api/directions/json?${params}`);
      if (!r.ok) continue;
      const body = await r.json();
      if (body.status !== "OK") continue;
      let sec = body?.routes?.[0]?.legs?.[0]?.duration?.value;
      if (!sec) continue;
      if (mode === "driving") sec = Math.round(sec * 1.4); // JP transit ≈ driving×1.4
      return sec;
    } catch { /* try next mode */ }
  }
  return DEFAULT_TRAVEL_SEC;
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  if (!GOG_KEYRING_PASSWORD) {
    console.error("[travel] GOG_KEYRING_PASSWORD not set — cannot authenticate with Google");
    process.exit(1);
  }

  console.log(`[travel] listing events (horizon: ${HORIZON_DAYS}d, account: ${GOG_ACCOUNT})`);
  const events = listEvents();
  console.log(`[travel] found ${events.length} events`);

  const missing = detectMissingTravelBlocks(events);
  console.log(`[travel] ${missing.length} events need travel blocks`);

  const results = [];

  for (const ev of missing) {
    const startMs = new Date(ev.start.dateTime).getTime();
    const destination = ev.location || null;

    const durationSec = await getTravelDurationSec(HOME_ADDRESS, destination);
    const startTravelMs = startMs - durationSec * 1000;

    const summary = `${TRAVEL_PREFIX}${(ev.summary || "").trim()}`;
    const description = `Auto-inserted by Anicca B-travel (spec27). Travel time to: ${ev.summary}`;
    const startIso = new Date(startTravelMs).toISOString();
    const endIso = new Date(startMs).toISOString();

    const id = insertEvent({ summary, startIso, endIso, description });
    results.push({
      for: ev.summary,
      durationMin: Math.round(durationSec / 60),
      id: id || "error",
    });
    console.log(`[travel] inserted "${summary}" (${Math.round(durationSec / 60)} min) → id=${id}`);
  }

  const errors = results.filter((r) => r.id === "error").length;
  const out = { ok: errors === 0, checked: events.length, inserted: results, errors };
  console.log(JSON.stringify(out, null, 2));
  if (errors > 0) process.exitCode = 1; // HARD RULE 0.24: broken run must not look clean
  return out;
}

// Run if invoked directly; export pure functions for testing
if (require.main === module) {
  main().catch((err) => {
    console.error("[travel] fatal:", err.message);
    process.exit(1);
  });
}

module.exports = {
  isTravelBlock,
  detectMissingTravelBlocks,
  getTravelDurationSec,
  TRAVEL_PREFIX,
  DEFAULT_TRAVEL_SEC,
};
