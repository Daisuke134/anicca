#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { importContentObject } = require("../lib/content-object-store.js");

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!/^--[a-z-]+$/.test(String(flag || "")) || !value || String(value).startsWith("--")) {
      throw new Error("marketing import arguments must be --name value pairs");
    }
    args[flag.slice(2)] = value;
  }
  for (const name of [
    "data-dir",
    "tenant",
    "video",
    "caption",
    "approval",
    "instagram-accounts",
    "instagram-settings",
    "instagram-credentials",
  ]) {
    if (!args[name]) throw new Error(`--${name} is required`);
  }
  return args;
}

function safeTenant(value) {
  const tenant = String(value || "").trim();
  if (!/^[a-z0-9][a-z0-9._-]{0,127}$/i.test(tenant)) {
    throw new Error("marketing import tenant is invalid");
  }
  return tenant;
}

function copyPrivate(source, destination) {
  const stat = fs.statSync(source, { throwIfNoEntry: false });
  if (!stat?.isFile() || stat.size < 1) {
    throw new Error("marketing profile source must be a non-empty file");
  }
  fs.mkdirSync(path.dirname(destination), { recursive: true, mode: 0o700 });
  const temporary = `${destination}.tmp-${process.pid}`;
  fs.copyFileSync(source, temporary);
  fs.chmodSync(temporary, 0o600);
  fs.renameSync(temporary, destination);
}

function importMarketingDaily(argv) {
  const args = parseArgs(argv);
  const tenant = safeTenant(args.tenant);
  const dataDir = path.resolve(args["data-dir"]);
  if (!path.isAbsolute(dataDir) || dataDir === path.parse(dataDir).root) {
    throw new Error("marketing import data directory is invalid");
  }
  const objectDir = path.join(dataDir, "objects");
  const video = importContentObject(args.video, { objectDir });
  const caption = importContentObject(args.caption, { objectDir });
  const approval = importContentObject(args.approval, { objectDir });
  const profileDir = path.join(
    dataDir,
    "tenants",
    encodeURIComponent(tenant),
    "profiles",
    "instagram",
    "life-manager",
  );
  const accountsPath = path.join(profileDir, "accounts.json");
  const settingsPath = path.join(profileDir, "settings.json");
  const credentialsPath = path.join(profileDir, "credentials.json");
  const stateDir = path.join(profileDir, "state");
  copyPrivate(args["instagram-accounts"], accountsPath);
  copyPrivate(args["instagram-settings"], settingsPath);
  copyPrivate(args["instagram-credentials"], credentialsPath);
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });

  return {
    tenant_id: tenant,
    video_ref: video.ref,
    caption_ref: caption.ref,
    approval_ref: approval.ref,
    instagram_profile_ref: "profile://instagram/life-manager",
    profile_files: {
      accounts_path: accountsPath,
      settings_path: settingsPath,
      credentials_path: credentialsPath,
      state_dir: stateDir,
    },
  };
}

if (require.main === module) {
  try {
    process.stdout.write(`${JSON.stringify(importMarketingDaily(process.argv.slice(2)))}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { importMarketingDaily, parseArgs };
