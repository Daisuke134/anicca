"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { importMarketingDaily } = require("./import-marketing-daily.js");

test("one-time import copies content and private Instagram profile into Life Manager ownership", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-import-"));
  const source = path.join(root, "source");
  const dataDir = path.join(root, "runtime-data");
  fs.mkdirSync(source);
  for (const [name, value] of [
    ["video", "video-bytes"],
    ["caption", "caption"],
    ["approval", "{\"scope\":\"standing\"}\n"],
    ["accounts", "[{\"handle\":\"life_manager\"}]"],
    ["settings", "{\"cookies\":{}}"],
    ["credentials", "{\"username\":\"fixture\"}"],
  ]) {
    fs.writeFileSync(path.join(source, name), value, { mode: 0o600 });
  }

  const result = importMarketingDaily([
    "--data-dir", dataDir,
    "--tenant", "tenant-a",
    "--video", path.join(source, "video"),
    "--caption", path.join(source, "caption"),
    "--approval", path.join(source, "approval"),
    "--instagram-accounts", path.join(source, "accounts"),
    "--instagram-settings", path.join(source, "settings"),
    "--instagram-credentials", path.join(source, "credentials"),
  ]);

  assert.match(result.video_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.match(result.caption_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.match(result.approval_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.equal(result.instagram_profile_ref, "profile://instagram/life-manager");
  assert.equal(fs.statSync(result.profile_files.accounts_path).mode & 0o777, 0o600);
  assert.equal(fs.statSync(result.profile_files.settings_path).mode & 0o777, 0o600);
  assert.equal(fs.statSync(result.profile_files.credentials_path).mode & 0o777, 0o600);
  assert.equal(fs.statSync(result.profile_files.state_dir).mode & 0o777, 0o700);
  assert.doesNotMatch(JSON.stringify(result), /cookies|source/);
});
