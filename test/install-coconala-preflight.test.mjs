import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function executable(path, body) {
  writeFileSync(path, `#!/bin/sh\n${body}\n`, "utf8");
  chmodSync(path, 0o755);
}

function fixture({ browser = true } = {}) {
  const root = mkdtempSync(join(tmpdir(), "coconala-preflight-"));
  const home = join(root, "home");
  const bin = join(root, "bin");
  mkdirSync(home);
  mkdirSync(bin);
  executable(join(bin, "uname"), '[ "$1" = "-s" ] && echo Darwin || echo arm64');
  executable(join(bin, "python3"), "exit 0");
  executable(join(bin, "codex"), '[ "$1 $2" = "login status" ]');
  executable(join(bin, "df"), "printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\nmock 1 0 1048576 0%% /\\n'");
  if (browser) {
    const chromium = join(home, ".cloakbrowser", "chromium-999", "Chromium.app", "Contents", "MacOS", "Chromium");
    mkdirSync(dirname(chromium), { recursive: true });
    executable(chromium, "exit 0");
  }
  const result = spawnSync("bash", [join(REPO_ROOT, "install.sh"), "coconala", "preflight"], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    env: { ...process.env, HOME: home, PATH: `${bin}:${process.env.PATH}` },
    timeout: 10_000,
  });
  return { home, result };
}

test("ready machine passes side-effect-free Coconala preflight", () => {
  const { home, result } = fixture();
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), {
    status: "ready", darwin: true, arm64: true, python: true,
    codex_cli: true, codex_authenticated: true, cloakbrowser: true,
    disk_headroom: true,
  });
  assert.equal(existsSync(join(home, ".local")), false);
});

test("missing browser fails closed without writing HOME", () => {
  const { home, result } = fixture({ browser: false });
  assert.equal(result.status, 2);
  const receipt = JSON.parse(result.stdout);
  assert.equal(receipt.status, "blocked");
  assert.equal(receipt.cloakbrowser, false);
  assert.equal(existsSync(join(home, ".local")), false);
});
