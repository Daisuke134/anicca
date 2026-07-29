#!/usr/bin/env node
"use strict";

// Order 2 (spec 2026-07-29 life-manager finance/marketing platform, section 12
// row 2): assign one disposition to every captured legacy scheduler row in
// docs/migrations/openclaw/runtime-inventory.json.
//
// Disposition vocabulary (includes the decided "retain-external" amendment for
// third-party/system services that are outside the migration scope):
//   migrate | replace | retire | retain-external
//
// Deterministic rule order:
//   1. protected rows (already classified in Order 1) are never touched
//   2. named special cases classified from read-only inspection
//   3. disabled AND unloaded OpenClaw store rows -> retire
//   4. launchd system_or_other rows without openclaw/legacy path references
//      -> retain-external
//   5. remaining enabled-or-loaded rows -> family table (first match wins)
//   6. default family for remaining personal/transport loops
//      -> life-manager-runtime

const fs = require("node:fs");
const path = require("node:path");

const PROTECTED_ROWS = Object.freeze({
  "ai.anicca.life-manager-daily": "marketing-life-manager-daily",
  "ai.anicca.life-manager-financial-report": "financial-report-telegram",
  "ai.anicca.reelclaw-honne-ja": "marketing-video-generation",
});

const RETIRE_OPENCLAW_ROLLBACK =
  "re-enable job in archived OpenClaw store from signed inventory";
const RETIRE_LAUNCHD_ROLLBACK =
  "restore legacy scheduler entry from signed inventory";
const MIGRATE_ROLLBACK =
  "restore legacy scheduler entry from signed inventory";
const RETAIN_EXTERNAL_ROLLBACK = "none (outside migration scope)";

// Adapter ids that exist today; only these get a real verify command.
function loadExistingAdapterIds(configPath) {
  const file = configPath
    || path.join(__dirname, "..", "config", "loop-adapters.json");
  const config = JSON.parse(fs.readFileSync(file, "utf8"));
  return new Set((config.adapters || []).map((adapter) => adapter.adapter_id));
}

const ADAPTER_VERIFY_COMMAND =
  "cd apps/life-manager && npm run test:runtime-adapters";

// Named special cases, classified per read-only inspection (2026-07-30).
const SPECIAL_CASES = {
  "ai.anicca.cfo-daily": {
    disposition: "migrate",
    owner: "life-manager",
    target_adapter: "financial-report-telegram",
    effect_class: "message",
    rollback_action: MIGRATE_ROLLBACK,
    classification_note:
      "plist is not plutil-parseable (unknown ampersand-escape at line 11) so "
      + "the captured command is empty; read-only text inspection shows a "
      + "daily 06:00 job running $HOME/."
      + "openclaw/skills/cfo-core/run-cfo.sh "
      + "(OpenClaw CFO financial daily); launchctl list shows the label "
      + "loaded with last exit status 0 at classification time",
  },
  "com.anicca.daemon": {
    disposition: "retire",
    owner: "life-manager-migration",
    target_adapter: null,
    effect_class: null,
    rollback_action: RETIRE_LAUNCHD_ROLLBACK,
    classification_note:
      "loaded-only residual at capture time: the active plist was renamed to "
      + ".disabled backups on 2026-07-12/13 (KeepAlive daemon for "
      + "$HOME/"
      + "anicca/runtime/anicca-daemon.sh) and launchctl no longer "
      + "reports the label at classification time",
  },
};

// Third-party/system services scheduled from launchd but owned outside the
// Life Manager migration (CI runner, OS/app updaters, host tooling).
const RETAIN_EXTERNAL_OVERRIDES = new Map([
  [/^actions\.runner\./,
    "self-hosted GitHub Actions runner service (CI infrastructure), not a "
    + "legacy loop"],
  [/^com\.google\./, "Google software updater, not a legacy loop"],
  [/^com\.token-optimizer\./,
    "token-usage dashboard tooling owned outside Life Manager"],
  [/^com\.vineyard\./,
    "Dais-owned dashboard-sync tooling owned outside Life Manager"],
  [/^ai\.anicca\.colima-autostart$/,
    "host container-runtime autostart (colima), host tooling rather than a "
    + "legacy loop"],
]);

// Family table for remaining enabled-or-loaded rows. First match wins; the
// match input is "<name> <legacy_id>" lower-cased.
const FAMILY_RULES = [
  // stale one-off probes
  { pattern: /probe-rollback/, disposition: "retire" },
  // OpenClaw core scheduler/interface itself is replaced by the Life Manager
  // scheduler and bot routing (Orders 7, 9, 14).
  {
    pattern: /\bai\.openclaw\.gateway\b|\bai\.openclaw\.anicca-ask\b|\banicca-heartbeat\b/,
    disposition: "replace",
    target: "life-manager-runtime",
  },
  // machine-maintenance/monitoring class (monkey/watchdog/janitor and other
  // healthcheck/backup/cleanup jobs) -> replace with Life Manager monitoring
  {
    pattern: new RegExp(
      [
        "monkey", "watchdog", "janitor", "healthcheck", "health-check",
        "silence-check", "diagnose", "remediate", "cron-doctor",
        "cron-auto-disable", "cron-harvester", "config-canary", "exec-guard",
        "watch-sweep", "earn-watch", "earning-health", "disk-sentinel",
        "disk-guard", "netmonitor", "phone-cleanup", "backup",
        "session-vault", "agents-skills-sync", "verify-loops-audit",
        "citizens-diff-monitor", "agentmemory-mcp-cleanup", "gcal-heal",
        "\\banicca-health\\b",
      ].join("|"),
    ),
    disposition: "replace",
    target: "life-manager-monitoring",
  },
  // capafy before any generic keyword (capafy-goal-monitor)
  { pattern: /capafy/, disposition: "migrate", target: "capafy-loop" },
  // finance/trading/x402 family
  {
    pattern: new RegExp(
      [
        "x402", "the402", "usdc", "autohedge", "\\bpm-decision", "\\bpm-live",
        "reinvest", "sol-funding", "ubi-watcher", "stripe-revenue",
        "wallet-balance", "credit-monitor", "fuel-broker", "agent-economy",
        "taskmarket",
      ].join("|"),
    ),
    disposition: "migrate",
    target: "finance-x402",
  },
  // CFO financial sync joins the financial report family
  {
    pattern: /\bcfo\b|cfo-sync/,
    disposition: "migrate",
    target: "financial-report-telegram",
  },
  // marketing observation/metrics family (existing adapter)
  {
    pattern: new RegExp(
      [
        "account-health", "postiz", "marketing-dashboard", "marketing-metrics",
        "connector-daily-report", "connector-fill-gaps", "app-reviews",
        "dashboard-refresh", "slack-metrics",
      ].join("|"),
    ),
    disposition: "migrate",
    target: "marketing-platform-observation",
  },
  // citizen loops (franklin/claude-p images and MCP sidecars)
  {
    pattern: /franklin|claude-p|citizen-refill/,
    disposition: "migrate",
    target: "franklin-loop",
  },
  // marketing content generation/posting family
  {
    pattern: new RegExp(
      [
        "larry", "reelclaw", "honne", "watercolor", "slideshow", "clip-loop",
        "warmup", "viral-format", "music", "yangmun",
        "fastlane-affirmation", "comedy-tiktok-cross-post",
        "comedy-live-schedule-publish", "\\bai\\.anicca\\.image-",
      ].join("|"),
    ),
    disposition: "migrate",
    target: "marketing-video-generation",
  },
  // writer/article/research family
  {
    pattern: /writer|article|craft-train|auto-research/,
    disposition: "migrate",
    target: "writer-loop",
  },
  // gig/bounty/hf income family
  {
    pattern: /\bhf-|gig|bounty|contra|job-search/,
    disposition: "migrate",
    target: "gig-loop",
  },
  // outbound/inbound mail family (before seo so corey cold email lands here)
  {
    pattern: /mail|cold-email|letter|recruit/,
    disposition: "migrate",
    target: "mail-loop",
  },
  // seo family
  { pattern: /seo|backlink|corey/, disposition: "migrate", target: "seo-loop" },
  // school/research administration family
  {
    pattern: /naist|school|homework|jsps/,
    disposition: "migrate",
    target: "school-loop",
  },
  // memory/knowledge upkeep family
  {
    pattern: /memory|factory-bp|pattern-promoter/,
    disposition: "migrate",
    target: "memory-maintenance",
  },
];

const DEFAULT_FAMILY = { disposition: "migrate", target: "life-manager-runtime" };

function effectClassFor(targetAdapter) {
  if (targetAdapter === "marketing-video-generation") return "publish";
  if (targetAdapter === "marketing-life-manager-daily") return "publish";
  if (targetAdapter === "mail-loop") return "message";
  if (targetAdapter === "financial-report-telegram") return "message";
  return "none";
}

function matchInput(job) {
  return `${job.display_name || ""} ${job.legacy_id || ""}`.toLowerCase();
}

function classifyJob(job, existingAdapterIds) {
  const id = job.legacy_id || "";
  if (Object.prototype.hasOwnProperty.call(PROTECTED_ROWS, id)) {
    return null; // never touched
  }
  if (Object.prototype.hasOwnProperty.call(SPECIAL_CASES, id)) {
    return { ...SPECIAL_CASES[id] };
  }
  for (const [pattern, note] of RETAIN_EXTERNAL_OVERRIDES) {
    if (pattern.test(id)) {
      return {
        disposition: "retain-external",
        owner: "system",
        target_adapter: null,
        effect_class: null,
        rollback_action: RETAIN_EXTERNAL_ROLLBACK,
        classification_note: note,
      };
    }
  }
  // rule: disabled AND unloaded OpenClaw store rows retire
  if (job.scheduler === "openclaw" && !job.enabled && !job.loaded) {
    return {
      disposition: "retire",
      owner: "life-manager-migration",
      target_adapter: null,
      effect_class: null,
      rollback_action: RETIRE_OPENCLAW_ROLLBACK,
    };
  }
  // rule: launchd system rows whose command references no openclaw/legacy
  // path (that is exactly what source_boundary === "system_or_other" means)
  if (job.source_boundary === "system_or_other" && job.scheduler === "launchd") {
    const result = {
      disposition: "retain-external",
      owner: "system",
      target_adapter: null,
      effect_class: null,
      rollback_action: RETAIN_EXTERNAL_ROLLBACK,
    };
    if (!id && !job.command) {
      result.classification_note =
        "plist captured without label or program arguments; no "
        + "openclaw/legacy reference observable";
    }
    return result;
  }
  const input = ` ${matchInput(job)} `;
  for (const rule of FAMILY_RULES) {
    if (rule.pattern.test(input)) {
      if (rule.disposition === "retire") {
        return {
          disposition: "retire",
          owner: "life-manager-migration",
          target_adapter: null,
          effect_class: null,
          rollback_action: job.scheduler === "openclaw"
            ? RETIRE_OPENCLAW_ROLLBACK
            : RETIRE_LAUNCHD_ROLLBACK,
        };
      }
      return {
        disposition: rule.disposition,
        owner: "life-manager",
        target_adapter: rule.target,
        effect_class: effectClassFor(rule.target),
        rollback_action: MIGRATE_ROLLBACK,
      };
    }
  }
  return {
    disposition: DEFAULT_FAMILY.disposition,
    owner: "life-manager",
    target_adapter: DEFAULT_FAMILY.target,
    effect_class: effectClassFor(DEFAULT_FAMILY.target),
    rollback_action: MIGRATE_ROLLBACK,
  };
}

function classifyInventory(document, existingAdapterIds) {
  const jobs = (document.jobs || []).map((job) => {
    const decision = classifyJob(job, existingAdapterIds);
    if (!decision) return job; // protected row stays byte-identical
    const next = { ...job, ...decision };
    next.verify_command =
      next.target_adapter && existingAdapterIds.has(next.target_adapter)
        ? ADAPTER_VERIFY_COMMAND
        : null;
    return next;
  });
  const summary = { ...document.summary };
  summary.unclassified =
    jobs.filter((job) => job.disposition === "unclassified").length;
  const dispositions = {};
  for (const job of jobs) {
    dispositions[job.disposition] = (dispositions[job.disposition] || 0) + 1;
  }
  summary.dispositions = dispositions;
  return { ...document, jobs, summary };
}

function main(argv = process.argv.slice(2)) {
  let inventoryPath = path.join(
    __dirname, "..", "..", "..",
    "docs", "migrations", "openclaw", "runtime-inventory.json",
  );
  let write = false;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--inventory") inventoryPath = argv[++i];
    else if (argv[i] === "--write") write = true;
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  const document = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));
  const classified = classifyInventory(document, loadExistingAdapterIds());
  const json = `${JSON.stringify(classified, null, 2)}\n`;
  if (write) {
    fs.writeFileSync(inventoryPath, json);
    console.error(
      `[classify] wrote ${inventoryPath}: `
      + JSON.stringify(classified.summary.dispositions),
    );
  } else {
    process.stdout.write(json);
  }
  return classified;
}

module.exports = {
  ADAPTER_VERIFY_COMMAND,
  PROTECTED_ROWS,
  classifyInventory,
  classifyJob,
  loadExistingAdapterIds,
  main,
};

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(`[classify] ${error.message}`);
    process.exitCode = 1;
  }
}
