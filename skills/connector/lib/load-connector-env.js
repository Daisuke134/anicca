#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const ALLOWED = new Set([
  "DAIS_LEGAL_NAME_ROMAJI", "GOG_ACCOUNT", "GOG_BIN", "GOG_KEYRING_PASSWORD", "GOOGLE_API_KEY_DIRECTIONS",
  "GEMINI_API_KEY",
  "LIFE_HOME_ADDRESS", "LM_CONNECTOR_CALENDAR_COVERAGE_URL", "LM_CONNECTOR_CALENDAR_ID",
  "LM_CONNECTOR_EVIDENCE_DIR", "LM_CONNECTOR_LUNA_EVIDENCE_DIR", "LM_CONNECTOR_PROFILE_PATH",
  "LM_CONNECTOR_LUMA_EMAIL", "LM_CONNECTOR_LUMA_NAME",
  "LM_CONNECTOR_TELEGRAM_TARGET", "LM_CONNECTOR_TENANT_ID", "LM_CONNECTOR_TIME_ZONE",
]);

function invalid() { throw new Error("Connector env unavailable"); }

function loadConnectorEnv(file) {
  const target = path.resolve(String(file == null ? "" : file));
  if (!path.isAbsolute(target) || target === path.parse(target).root) invalid();
  let source;
  try {
    const stat = fs.statSync(target);
    if (!stat.isFile() || stat.size > 128 * 1024) invalid();
    source = fs.readFileSync(target, "utf8");
  } catch { invalid(); }
  const values = {};
  for (const line of source.split(/\r?\n/)) {
    const match = /^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)\s*$/.exec(line);
    if (!match || !ALLOWED.has(match[1])) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!value || /[\x00-\x1f\x7f]/.test(value)) invalid();
    values[match[1]] = value;
  }
  return Object.freeze(values);
}

if (require.main === module) {
  try { loadConnectorEnv(process.argv[2]); }
  catch { process.stderr.write("Connector env unavailable\n"); process.exitCode = 2; }
}

module.exports = { loadConnectorEnv };
