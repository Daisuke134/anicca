#!/usr/bin/env node
"use strict";

// scan-legacy-paths.js — Order 5 exit evidence: the Life Manager runtime must
// not depend on any legacy runtime root (the OpenClaw store, the retired
// private checkout, or the v0 tree; see PATTERNS below for the exact tokens).
//
// SCOPE (decided by what the Life Manager runtime actually loads):
//   - apps/life-manager        the runtime itself: server.js, scheduler.js,
//                              lib/, scripts/, inngest/, transport/, config/,
//                              skill-life-manager/, launchd/ templates, eval/
//   - skills/video/daily-lm-video   spawned by marketing-daily-generation-adapter.js
//   - skills/video/lm-distribution  spawned by marketing-daily-adapter.js and
//                                   marketing-video-publication-adapter.js
//   - skills/tools/telegram-user    spawned by daily-preflight-collectors.js
//   - skills/life-manager           launchd daily/self-build entrypoints
//   - runtime/                      the portable scheduler/worker runtime (spec section 8)
// The rest of skills/ (earn/self/report/economy loops and the vendored capafy
// publisher, whose product purpose is packaging OpenClaw workspaces) is not
// loaded by the Life Manager runtime and is out of scope here; the repo-level
// scripts/verify-oss-self-contained.mjs covers developer-local roots there.
//
// Test files and fixtures are excluded: tests legitimately fabricate legacy
// paths to prove rejection. Allowlisted lines are boundary/denial logic or
// migration tooling that reads the legacy store by design; each entry pins one
// file plus a required line substring, never a blanket file exclusion.

const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

const SCAN_ROOTS = [
  "apps/life-manager",
  "skills/video/daily-lm-video",
  "skills/video/lm-distribution",
  "skills/tools/telegram-user",
  "skills/life-manager",
  "runtime",
];

const SCAN_EXTENSIONS = new Set([
  ".js", ".mjs", ".cjs", ".py", ".sh", ".json", ".plist", ".template",
  ".toml", ".sql", ".yml", ".yaml",
]);

const EXCLUDED_DIRS = new Set([
  "node_modules", ".git", "test", "tests", "__tests__", "test-support",
  "fixtures", "migrations-archive",
]);

// Patterns and their ids are assembled from fragments so this scanner never
// matches its own source.
const OPENCLAW_TOKEN = "\\." + "open" + "claw";
const RETIRED_CHECKOUT_TOKEN = "profitable" + "-claude";
const V0_TREE_TOKEN = "life-manager" + "-v0";
const PATTERNS = [
  {
    id: "openclaw-path",
    regex: new RegExp("(?:^|[^A-Za-z0-9])" + OPENCLAW_TOKEN + "\\b"),
  },
  { id: RETIRED_CHECKOUT_TOKEN, regex: new RegExp(RETIRED_CHECKOUT_TOKEN) },
  { id: V0_TREE_TOKEN, regex: new RegExp(V0_TREE_TOKEN) },
];

// file: repo-relative path. lineIncludes: substring the matching line must
// contain for the hit to be allowed. reason: why the reference is legitimate.
const ALLOWLIST = [
  {
    file: "apps/life-manager/lib/runtime-paths.js",
    lineIncludes: "LEGACY_SEGMENT",
    reason: "denial regex rejecting legacy runtime roots",
  },
  {
    file: "apps/life-manager/lib/loop-adapter-registry.js",
    lineIncludes: "LEGACY_OR_ABSOLUTE",
    reason: "denial regex rejecting legacy adapter module refs",
  },
  {
    file: "apps/life-manager/scripts/classify-legacy-jobs.js",
    lineIncludes: "pattern:",
    reason: "Order 2 migration classifier matching legacy job identifiers",
  },
  {
    file: "apps/life-manager/scripts/classify-legacy-jobs.js",
    lineIncludes: "sourceBoundary",
    reason: "Order 2 migration classifier reading legacy source boundaries",
  },
  {
    file: "apps/life-manager/scripts/inventory-legacy-jobs.js",
    lineIncludes: "cronFile",
    reason: "Order 1 migration inventory reads the legacy cron store by design",
  },
  {
    file: "apps/life-manager/scripts/inventory-legacy-jobs.js",
    lineIncludes: 'return "openclaw"',
    reason: "Order 1 migration inventory classifies legacy source boundaries",
  },
  {
    file: "apps/life-manager/scripts/inventory-legacy-jobs.js",
    lineIncludes: 'return "profitable_claude"',
    reason: "Order 1 migration inventory classifies legacy source boundaries",
  },
  {
    file: "apps/life-manager/scripts/inventory-legacy-jobs.js",
    lineIncludes: 'return "life_manager_v0"',
    reason: "Order 1 migration inventory classifies legacy source boundaries",
  },
];

function isTestFile(filePath) {
  const base = path.basename(filePath);
  return /\.test\.[a-z]+$/.test(base)
    || /^test[_-]/.test(base)
    || /_test\.[a-z]+$/.test(base)
    || /\.integration\.sh$/.test(base);
}

function isScannableFile(filePath) {
  const base = path.basename(filePath);
  const extension = path.extname(base).toLowerCase();
  return SCAN_EXTENSIONS.has(extension) && !isTestFile(filePath);
}

function walk(absoluteDir, collected) {
  let entries;
  try {
    entries = fs.readdirSync(absoluteDir, { withFileTypes: true });
  } catch {
    return collected;
  }
  for (const entry of entries) {
    const absolute = path.join(absoluteDir, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) walk(absolute, collected);
    } else if (entry.isFile() && isScannableFile(absolute)) {
      collected.push(absolute);
    }
  }
  return collected;
}

function isAllowed(relativeFile, lineText) {
  return ALLOWLIST.some((entry) =>
    entry.file === relativeFile && lineText.includes(entry.lineIncludes));
}

function scanLegacyPaths(options = {}) {
  const root = path.resolve(options.root || REPO_ROOT);
  const roots = options.roots || SCAN_ROOTS;
  const files = [];
  for (const scanRoot of roots) {
    const absolute = path.join(root, scanRoot);
    let stat;
    try {
      stat = fs.statSync(absolute);
    } catch {
      continue;
    }
    if (stat.isDirectory()) walk(absolute, files);
    else if (stat.isFile() && isScannableFile(absolute)) files.push(absolute);
  }
  files.sort();

  const violations = [];
  for (const file of files) {
    const relativeFile = path.relative(root, file);
    const lines = fs.readFileSync(file, "utf8").split("\n");
    lines.forEach((lineText, index) => {
      for (const { id, regex } of PATTERNS) {
        if (!regex.test(lineText)) continue;
        if (isAllowed(relativeFile, lineText)) continue;
        violations.push({
          file: relativeFile,
          line: index + 1,
          pattern: id,
          text: lineText.trim().slice(0, 160),
        });
      }
    });
  }
  return { scannedFiles: files.length, violations };
}

function main() {
  const result = scanLegacyPaths();
  if (result.violations.length === 0) {
    process.stdout.write(
      `legacy-path scan: PASS (${result.scannedFiles} files scanned, 0 violations)\n`,
    );
    process.exitCode = 0;
    return;
  }
  process.stderr.write(
    `legacy-path scan: FAIL (${result.violations.length} violations in ${result.scannedFiles} files)\n`,
  );
  for (const violation of result.violations) {
    process.stderr.write(
      `${violation.file}:${violation.line}\t${violation.pattern}\t${violation.text}\n`,
    );
  }
  process.exitCode = 1;
}

module.exports = { scanLegacyPaths, SCAN_ROOTS, ALLOWLIST };

if (require.main === module) main();
