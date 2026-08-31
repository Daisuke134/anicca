#!/usr/bin/env node
"use strict";

const path = require("node:path");

const { importContentObject } = require("../lib/content-object-store.js");

const REQUIRED = [
  "data-dir",
  "tenant",
  "bank",
  "call-audio",
  "stock",
  "telegram-proof",
  "whisper-ass",
];

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!/^--[a-z-]+$/.test(String(flag || "")) || !value || String(value).startsWith("--")) {
      throw new Error("marketing generation import arguments must be --name value pairs");
    }
    args[flag.slice(2)] = value;
  }
  for (const name of REQUIRED) {
    if (!args[name]) throw new Error(`--${name} is required`);
  }
  return args;
}

function importMarketingGeneration(argv) {
  const args = parseArgs(argv);
  const tenant = String(args.tenant || "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(tenant)) {
    throw new Error("marketing generation import tenant is invalid");
  }
  const dataDir = path.resolve(args["data-dir"]);
  if (!path.isAbsolute(dataDir) || dataDir === path.parse(dataDir).root) {
    throw new Error("marketing generation import data directory is invalid");
  }
  const objectDir = path.join(dataDir, "objects");
  const result = { tenant_id: tenant };
  for (const [flag, output] of [
    ["bank", "bank_ref"],
    ["call-audio", "call_audio_ref"],
    ["stock", "stock_ref"],
    ["telegram-proof", "telegram_proof_ref"],
    ["whisper-ass", "whisper_ass_ref"],
  ]) {
    result[output] = importContentObject(args[flag], { objectDir }).ref;
  }
  return result;
}

if (require.main === module) {
  try {
    process.stdout.write(`${JSON.stringify(importMarketingGeneration(process.argv.slice(2)))}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { importMarketingGeneration, parseArgs };
