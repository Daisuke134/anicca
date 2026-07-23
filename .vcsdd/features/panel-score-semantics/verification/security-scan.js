"use strict";

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "../../../..");
const scopedFiles = [
  "apps/life-call/lib/panel-score-semantics.js",
  "apps/life-call/lib/panel-api.js",
  "apps/life-call/lib/panel-ui.js",
  "apps/life-call/migrations/2026-07-22-panel-score-outcomes.sql",
];

const secretRules = [
  {
    name: "hardcoded-secret-assignment",
    pattern: /\b(?:api[_-]?key|secret|password|bearer|token)\b\s*[:=]\s*(["'`])([^"'`\n]+)\1/gi,
    unsafe(match) {
      const value = match[2];
      return value.length >= 8 && !value.includes("${") && !/^(?:process\.env|opts\.|synthetic|example|test)/i.test(value);
    },
  },
  {
    name: "credential-shape",
    pattern: /\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b/g,
    unsafe() { return true; },
  },
];

const unsafeRules = [
  {
    name: "unsafe-output-key",
    files: new Set(["apps/life-call/lib/panel-score-semantics.js", "apps/life-call/lib/panel-ui.js"]),
    pattern: /(?:^|[,{]\s*)(?:id|uid|entity_key|revision_key|provider_id|provider_ref|raw_id|internal_id)\s*:/gm,
  },
  {
    name: "unsafe-render-access",
    files: new Set(["apps/life-call/lib/panel-ui.js"]),
    pattern: /(?:organ|row|outcome)\.(?:id|uid|entity_key|revision_key|provider_id|provider_ref|raw_id|internal_id)\b/g,
  },
];

const findings = [];
const counts = { "hardcoded-secret-assignment": 0, "credential-shape": 0, "unsafe-output-key": 0, "unsafe-render-access": 0 };
for (const relativePath of scopedFiles) {
  const text = fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
  for (const rule of secretRules) {
    rule.pattern.lastIndex = 0;
    for (const match of text.matchAll(rule.pattern)) {
      if (!rule.unsafe(match)) continue;
      counts[rule.name] += 1;
      findings.push({ file: relativePath, line: text.slice(0, match.index).split("\n").length, rule: rule.name });
    }
  }
  for (const rule of unsafeRules) {
    if (!rule.files.has(relativePath)) continue;
    rule.pattern.lastIndex = 0;
    for (const match of text.matchAll(rule.pattern)) {
      counts[rule.name] += 1;
      findings.push({ file: relativePath, line: text.slice(0, match.index).split("\n").length, rule: rule.name });
    }
  }
}

console.log(`security-scan scope_files=${scopedFiles.length}`);
console.log(`hardcoded_secret_findings=${counts["hardcoded-secret-assignment"]}`);
console.log(`credential_shape_findings=${counts["credential-shape"]}`);
console.log(`unsafe_output_key_findings=${counts["unsafe-output-key"]}`);
console.log(`unsafe_render_access_findings=${counts["unsafe-render-access"]}`);
for (const finding of findings) console.log(`finding file=${finding.file} line=${finding.line} rule=${finding.rule}`);
console.log(`result=${findings.length === 0 ? "PASS" : "FAIL"}`);
if (findings.length) process.exitCode = 1;
