#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

function fail() { process.stderr.write("verification failed\n"); process.exit(1); }
const args = process.argv.slice(2);
const marker = args.indexOf("--exclude-historical-json");
if (args[0] !== "--paths" || marker < 2 || marker !== args.length - 2 || args.at(-1) !== "--allow-utc-timestamps") fail();
const supplied = args.slice(1, marker);
if (supplied.length === 0 || supplied.some(value => !existsSync(value))) fail();

function files(target, direct = true) {
  const info = statSync(target);
  if (info.isFile()) return [target];
  if (!info.isDirectory()) return [];
  const out = [];
  for (const entry of readdirSync(target, { withFileTypes: true })) {
    if (["node_modules", ".git"].includes(entry.name) || /test-support|\.test\./.test(entry.name)) continue;
    const child = path.join(target, entry.name);
    if (entry.isDirectory()) out.push(...files(child, false));
    else if (/\.(?:json|jsonl|log|tap|txt|md)$/i.test(entry.name) && entry.name !== "package-lock.json" &&
        !/^daily-preflight-\d{8}T\d{6}Z\.json$/.test(entry.name)) out.push(child);
  }
  return out;
}

const patterns = [
  /fixture-secret-value|\b(?:api[_-]?key|access[_-]?token|secret)\s*[:=]\s*["']?(?!env\.|process\.|\$\{)[A-Za-z0-9_./+-]{12,}/i,
  /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  /\+\d[\d ()-]{7,}\d/,
  /raw-correlation-value|["']?(?:rawCorrelation|runCorrelation)["']?\s*[:=]\s*["'][^"']+["']/i,
  /provider-id-value|["']?(?:providerId|messageId|sentId)["']?\s*[:=]\s*["'][^"']+["']/i,
];
const targets = [...new Set(supplied.flatMap(target => files(target)))];
if (targets.length === 0) fail();
for (const target of targets) {
  let value;
  try { value = readFileSync(target, "utf8"); } catch { fail(); }
  if (patterns.some(pattern => pattern.test(value))) fail();
}
process.stdout.write(`paths=${targets.length} secret=0 email=0 phone=0 rawCorrelation=0 providerId=0\n`);
