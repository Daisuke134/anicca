#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const PRIVATE_QUERY_KEY = /([?&](?:access_?token|api_?key|token|secret|password|key)=)[^&\s"']+/gi;
const SECRET_ENV = /\b([A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*)=("[^"]*"|'[^']*'|[^\s]+)/g;
const BEARER = /\b(Bearer\s+)[A-Za-z0-9._~+/-]+=*/gi;
const EMAIL = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
const HOME_PATH = /\/Users\/[^/\s"'\\]+/g;
const TARGET_FLAG = /(\s--(?:target|chat(?:-id)?|phone|to)(?:=|\s+))("[^"]*"|'[^']*'|[^\s]+)/gi;
const ACCOUNT_FLAG = /(\s--(?:tt|ig|yt|account(?:-id)?|integration(?:-id)?)(?:=|\s+))("[^"]*"|'[^']*'|[^\s]+)/gi;
const CONNECTOR_ACCOUNT = /\bcm[a-z0-9]{18,}\b/gi;
const LONG_NUMBER = /\b\d{8,}\b/g;
const LETTER_HEX = "abcdefghijklmnop";

function fingerprint(value, length = 16) {
  return crypto.createHash("sha256")
    .update(String(value || ""))
    .digest("hex")
    .slice(0, length)
    .split("")
    .map((digit) => LETTER_HEX[Number.parseInt(digit, 16)])
    .join("");
}

function redactCommand(command) {
  return String(command || "")
    .replace(PRIVATE_QUERY_KEY, "$1[REDACTED_TOKEN]")
    .replace(SECRET_ENV, "$1=[REDACTED_TOKEN]")
    .replace(BEARER, "$1[REDACTED_TOKEN]")
    .replace(TARGET_FLAG, "$1[REDACTED_TARGET]")
    .replace(ACCOUNT_FLAG, "$1[REDACTED_ACCOUNT]")
    .replace(CONNECTOR_ACCOUNT, "[REDACTED_ACCOUNT]")
    .replace(EMAIL, "[REDACTED_EMAIL]")
    .replace(HOME_PATH, "$HOME")
    .replace(LONG_NUMBER, (value) => `[REDACTED_NUMBER_${fingerprint(value, 8)}]`);
}

function sourceBoundary(command) {
  const raw = String(command || "");
  if (/\/Projects\/life-manager-main(?:\/|$)/.test(raw)) return "canonical_life_manager";
  if (/\/\.openclaw(?:\/|$)/.test(raw)) return "openclaw";
  if (/\/profitable-claude(?:\/|$)/.test(raw)) return "profitable_claude";
  if (/\/anicca(?:\/|$)/.test(raw)) return "anicca_legacy";
  if (/life-manager-v0/.test(raw)) return "life_manager_v0";
  return "system_or_other";
}

function cronCadence(schedule) {
  const s = schedule && typeof schedule === "object" ? schedule : {};
  if (s.kind === "cron") return { kind: "cron", expr: s.expr || null, tz: s.tz || null };
  if (s.kind === "every") return { kind: "every", every_ms: Number(s.everyMs) || null };
  if (s.kind === "at") return { kind: "at", at: s.at || null };
  return { kind: s.kind || "unknown" };
}

function launchdCadence(plist) {
  if (plist.StartInterval !== undefined) {
    return { kind: "interval", every_seconds: Number(plist.StartInterval) || null };
  }
  if (plist.StartCalendarInterval !== undefined) {
    return { kind: "calendar", value: plist.StartCalendarInterval };
  }
  if (plist.KeepAlive) return { kind: "keep_alive" };
  if (plist.RunAtLoad) return { kind: "run_at_load" };
  return { kind: "manual_or_unknown" };
}

function cronReceipt(state) {
  const s = state && typeof state === "object" ? state : {};
  if (!s.lastRunAtMs && !s.lastStatus && s.lastDurationMs === undefined) return null;
  return {
    last_run_at_ms: Number(s.lastRunAtMs) || null,
    status: s.lastStatus || null,
    duration_ms: Number.isFinite(Number(s.lastDurationMs)) ? Number(s.lastDurationMs) : null,
    consecutive_errors: Number.isFinite(Number(s.consecutiveErrors)) ? Number(s.consecutiveErrors) : null,
  };
}

function launchdReceipt(loaded) {
  if (!loaded) return null;
  return {
    pid_present: Boolean(loaded.pid && loaded.pid !== "-"),
    status: loaded.lastExitStatus === undefined ? null : String(loaded.lastExitStatus),
  };
}

function migrationFields() {
  return {
    disposition: "unclassified",
    owner: null,
    target_adapter: null,
    effect_class: null,
    verify_command: null,
    rollback_action: null,
  };
}

function normalizeCron(row) {
  const rawCommand = row && row.payload && row.payload.message || "";
  const command = redactCommand(rawCommand);
  return {
    legacy_id: redactCommand(row && row.id || ""),
    display_name: redactCommand(row && row.name || ""),
    scheduler: "openclaw",
    command,
    command_fingerprint: fingerprint(command),
    source_boundary: sourceBoundary(rawCommand),
    cadence: cronCadence(row && row.schedule),
    enabled: Boolean(row && row.enabled),
    loaded: false,
    latest_receipt: cronReceipt(row && row.state),
    environment_keys: [],
    parse_error: null,
    ...migrationFields(),
  };
}

function normalizeLaunchAgent(plist, loadedLabels) {
  const p = plist && typeof plist === "object" ? plist : {};
  const label = String(p.Label || p.__fallbackLabel || "");
  const args = Array.isArray(p.ProgramArguments)
    ? p.ProgramArguments.map(String)
    : p.Program ? [String(p.Program)] : [];
  const rawCommand = args.join(" ");
  const command = redactCommand(rawCommand);
  const loaded = loadedLabels && loadedLabels[label];
  return {
    legacy_id: redactCommand(label),
    display_name: redactCommand(label),
    scheduler: "launchd",
    command,
    command_fingerprint: fingerprint(command),
    source_boundary: sourceBoundary(rawCommand),
    cadence: launchdCadence(p),
    enabled: p.Disabled !== true,
    loaded: Boolean(loaded),
    latest_receipt: launchdReceipt(loaded),
    environment_keys: Object.keys(p.EnvironmentVariables || {}).sort(),
    parse_error: p.__parseError || null,
    ...migrationFields(),
  };
}

function inventoryLegacyJobs({ cronRows = [], launchAgents = [], loadedLabels = {} } = {}) {
  const launchAgentLabels = new Set(
    launchAgents.map((row) => String(row && (row.Label || row.__fallbackLabel) || "")),
  );
  const loadedOnly = Object.keys(loadedLabels)
    .filter((label) => /^(?:ai\.(?:anicca|openclaw)|com\.anicca)(?:\.|$)/.test(label))
    .filter((label) => !launchAgentLabels.has(label))
    .map((label) => ({
      __fallbackLabel: label,
      __parseError: "loaded label has no user LaunchAgent plist",
      Disabled: false,
    }));
  const jobs = [
    ...cronRows.map(normalizeCron),
    ...launchAgents.concat(loadedOnly).map((row) => normalizeLaunchAgent(row, loadedLabels)),
  ].sort((a, b) => a.legacy_id.localeCompare(b.legacy_id) || a.scheduler.localeCompare(b.scheduler));

  const summary = {
    total: jobs.length,
    schedulers: { launchd: 0, openclaw: 0 },
    source_boundaries: {},
    enabled_or_loaded: 0,
    unclassified: 0,
    parse_errors: 0,
  };
  for (const job of jobs) {
    summary.schedulers[job.scheduler] = (summary.schedulers[job.scheduler] || 0) + 1;
    summary.source_boundaries[job.source_boundary] =
      (summary.source_boundaries[job.source_boundary] || 0) + 1;
    if (job.enabled || job.loaded) summary.enabled_or_loaded += 1;
    if (job.disposition === "unclassified") summary.unclassified += 1;
    if (job.parse_error) summary.parse_errors += 1;
  }
  return { jobs, summary };
}

function parseLaunchctlList(text) {
  const loaded = {};
  for (const line of String(text || "").split("\n")) {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 3 || parts[2] === "Label") continue;
    loaded[parts.slice(2).join(" ")] = { pid: parts[0], lastExitStatus: parts[1] };
  }
  return loaded;
}

function loadLaunchAgents(directory, spawnImpl = spawnSync) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory)
    .filter((name) => name.endsWith(".plist"))
    .sort()
    .map((name) => {
      const file = path.join(directory, name);
      const result = spawnImpl("plutil", ["-convert", "json", "-o", "-", file], {
        encoding: "utf8",
        timeout: 10000,
      });
      try {
        if (result.status !== 0) throw new Error((result.stderr || "plutil failed").trim());
        return JSON.parse(result.stdout);
      } catch (error) {
        return {
          __fallbackLabel: path.basename(name, ".plist"),
          __parseError: redactCommand(error.message),
          Disabled: false,
        };
      }
    });
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--cron-file") opts.cronFile = argv[++i];
    else if (argv[i] === "--launch-agents-dir") opts.launchAgentsDir = argv[++i];
    else if (argv[i] === "--output") opts.output = argv[++i];
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return opts;
}

function main(argv = process.argv.slice(2), env = process.env) {
  const opts = parseArgs(argv);
  const home = env.HOME;
  if (!home) throw new Error("HOME is required");
  const cronFile = opts.cronFile || path.join(home, ".openclaw", "cron", "jobs.json");
  const launchAgentsDir = opts.launchAgentsDir || path.join(home, "Library", "LaunchAgents");
  const cronStore = JSON.parse(fs.readFileSync(cronFile, "utf8"));
  const launchctl = spawnSync("launchctl", ["list"], { encoding: "utf8", timeout: 10000 });
  if (launchctl.status !== 0) throw new Error((launchctl.stderr || "launchctl list failed").trim());
  const inventory = inventoryLegacyJobs({
    cronRows: Array.isArray(cronStore) ? cronStore : cronStore.jobs || [],
    launchAgents: loadLaunchAgents(launchAgentsDir),
    loadedLabels: parseLaunchctlList(launchctl.stdout),
  });
  const document = {
    schema_version: 1,
    captured_at: new Date().toISOString(),
    capture_mode: "read_only",
    sources: ["openclaw_cron_store", "user_launch_agents", "launchctl_list"],
    ...inventory,
  };
  const json = `${JSON.stringify(document, null, 2)}\n`;
  if (opts.output) {
    fs.mkdirSync(path.dirname(path.resolve(opts.output)), { recursive: true });
    fs.writeFileSync(opts.output, json, { mode: 0o600 });
  } else {
    process.stdout.write(json);
  }
  return document;
}

module.exports = {
  inventoryLegacyJobs,
  loadLaunchAgents,
  main,
  parseLaunchctlList,
  redactCommand,
  sourceBoundary,
};

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(`[inventory] ${error.message}`);
    process.exitCode = 1;
  }
}
