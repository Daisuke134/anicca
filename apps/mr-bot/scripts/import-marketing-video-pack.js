#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { importContentObject } = require("../lib/content-object-store.js");
const {
  normalizeMarketingVideoPack,
} = require("../lib/marketing-video-generation-adapter.js");

const REQUIRED = [
  "data-dir",
  "tenant",
  "product",
  "format",
  "form",
  "locale",
  "title",
  "hooks",
  "media-dir",
];
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (
      !/^--[a-z-]+$/.test(String(flag || ""))
      || !value
      || String(value).startsWith("--")
      || Object.hasOwn(args, String(flag).slice(2))
    ) {
      throw new Error("marketing video import arguments must be unique --name value pairs");
    }
    args[String(flag).slice(2)] = value;
  }
  for (const name of REQUIRED) {
    if (!args[name]) throw new Error(`--${name} is required`);
  }
  return args;
}

function canonicalInstant(value) {
  if (value == null || value === "") return null;
  const parsed = new Date(String(value));
  if (!Number.isFinite(parsed.getTime())) {
    throw new Error("marketing video hook lastUsed is invalid");
  }
  return parsed.toISOString();
}

function flattenHooks(value) {
  let raw;
  if (Array.isArray(value)) {
    raw = value;
  } else if (value && Array.isArray(value.hooks)) {
    raw = value.hooks;
  } else if (
    value
    && value.hooksByVideo
    && typeof value.hooksByVideo === "object"
    && !Array.isArray(value.hooksByVideo)
  ) {
    raw = Object.values(value.hooksByVideo).flat();
  } else {
    throw new Error("marketing video legacy hooks are invalid");
  }
  const hooks = raw.map((hook) => ({
    id: String(hook && hook.id || "").trim(),
    text: String(
      hook && hook.text
      || (Array.isArray(hook && hook.lines) ? hook.lines.join("\n") : ""),
    ).trim(),
    status: hook && hook.status == null ? "active" : String(hook.status),
    prior_used_at: canonicalInstant(hook && hook.lastUsed),
  })).sort((left, right) => left.id.localeCompare(right.id));
  if (new Set(hooks.map(({ id }) => id)).size !== hooks.length) {
    throw new Error("marketing video legacy hooks contain duplicate identities");
  }
  return hooks;
}

function isMp4(filePath) {
  const stat = fs.statSync(filePath, { throwIfNoEntry: false });
  if (!stat?.isFile() || stat.size < 12) return false;
  const handle = fs.openSync(filePath, "r");
  const header = Buffer.alloc(8);
  try {
    fs.readSync(handle, header, 0, header.length, 0);
  } finally {
    fs.closeSync(handle);
  }
  return header.subarray(4, 8).toString("ascii") === "ftyp";
}

function importMarketingVideoPack(argv) {
  const args = parseArgs(argv);
  for (const name of ["tenant", "product", "format", "form"]) {
    if (!IDENTIFIER.test(args[name])) {
      throw new Error(`marketing video import ${name} is invalid`);
    }
  }
  const dataDir = path.resolve(args["data-dir"]);
  if (dataDir === path.parse(dataDir).root) {
    throw new Error("marketing video import data directory is invalid");
  }
  const hooksPath = path.resolve(args.hooks);
  const mediaDir = path.resolve(args["media-dir"]);
  const mediaPaths = fs.readdirSync(mediaDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && /\.mp4$/i.test(entry.name))
    .map((entry) => path.join(mediaDir, entry.name))
    .sort();
  if (mediaPaths.length < 1 || mediaPaths.length > 20 || mediaPaths.some((file) => !isMp4(file))) {
    throw new Error("marketing video import requires valid MP4 media");
  }
  let legacy;
  try {
    legacy = JSON.parse(fs.readFileSync(hooksPath, "utf8"));
  } catch {
    throw new Error("marketing video legacy hooks are invalid");
  }
  const pack = {
    schema_version: 1,
    product_id: args.product,
    format_id: args.format,
    form: args.form,
    locale: args.locale,
    title: args.title,
    hashtags: String(args.hashtags || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    hooks: flattenHooks(legacy),
  };
  normalizeMarketingVideoPack(pack, {
    productId: args.product,
    formatId: args.format,
    locale: args.locale,
  });
  const importDir = path.join(
    dataDir,
    "tenants",
    args.tenant,
    "marketing",
    "imports",
  );
  fs.mkdirSync(importDir, { recursive: true, mode: 0o700 });
  const packPath = path.join(
    importDir,
    `${args.product}-${args.format}-${args.locale}.pack.json`,
  );
  fs.writeFileSync(packPath, `${JSON.stringify(pack)}\n`, { mode: 0o600 });
  fs.chmodSync(packPath, 0o600);
  const objectDir = path.join(dataDir, "objects");
  const importedPack = importContentObject(packPath, { objectDir });
  const mediaRefs = mediaPaths.map((source) => (
    importContentObject(source, { objectDir }).ref
  ));
  const result = {
    tenant_id: args.tenant,
    product_id: args.product,
    format_id: args.format,
    locale: args.locale,
    pack_ref: importedPack.ref,
    media_refs: mediaRefs,
  };
  const manifestPath = path.join(
    importDir,
    `${args.product}-${args.format}-${args.locale}.json`,
  );
  fs.writeFileSync(manifestPath, `${JSON.stringify(result)}\n`, { mode: 0o600 });
  fs.chmodSync(manifestPath, 0o600);
  return result;
}

if (require.main === module) {
  try {
    process.stdout.write(`${JSON.stringify(
      importMarketingVideoPack(process.argv.slice(2)),
    )}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  flattenHooks,
  importMarketingVideoPack,
  parseArgs,
};
