import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync, cpSync, symlinkSync, readlinkSync, existsSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { createHash } from "node:crypto";

const REPO_ROOT = new URL("../", import.meta.url).pathname;

test("installer restores a writable runtime slot root when the source is an immutable release", () => {
  const root = mkdtempSync(join(tmpdir(), "life-manager-release-install-"));
  const fixture = join(root, "release");
  const home = join(root, "home");
  const runtime = join(root, "runtime");
  mkdirSync(join(fixture, "skills", "_shared"), { recursive: true });
  mkdirSync(join(fixture, "skills", "agent-economy"), { recursive: true });
  mkdirSync(join(fixture, "identity"), { recursive: true });
  cpSync(join(REPO_ROOT, "install.sh"), join(fixture, "install.sh"));
  writeFileSync(join(fixture, ".env.example"), "FUEL=fixture\n");
  writeFileSync(join(fixture, "identity", "genesis.md"), "fixture genesis\n");
  writeFileSync(join(fixture, "skills", "_shared", "README"), "shared\n");
  writeFileSync(join(fixture, "skills", "agent-economy", "run.sh"), "#!/bin/sh\n");
  writeFileSync(join(fixture, "skills", "registry.json"), JSON.stringify({ slots: {
    "agent-economy": { dir: "skills/agent-economy", entrypoint: "run.sh", status: "dormant" },
  }}));
  chmodSync(join(fixture, "skills", "agent-economy"), 0o555);

  const result = spawnSync("bash", [join(fixture, "install.sh")], {
    cwd: fixture,
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: home,
      LIFE_MANAGER_HOME: runtime,
      LIFE_MANAGER_INSTALL_DAEMON: "0",
      LIFE_MANAGER_INSTALL_DEPS: "0",
    },
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  const state = join(runtime, "skills", "agent-economy", "state");
  assert.equal(statSync(state).isDirectory(), true);
  assert.notEqual(statSync(join(runtime, "skills", "agent-economy")).mode & 0o200, 0);
  assert.equal(readFileSync(join(runtime, "skills", "agent-economy", "run.sh"), "utf8"), "#!/bin/sh\n");
});

test("agent-economy installer reads the sealed namespaced current release and preserves instance state", () => {
  const root = mkdtempSync(join(tmpdir(), "life-manager-agent-install-"));
  const source = join(root, "source");
  const releaseRoot = join(root, "home", "loops", "life-manager");
  const releaseId = "20260827T000000-a1a1a1a1";
  const release = join(releaseRoot, "releases", releaseId);
  const runtime = join(root, "runtime");
  mkdirSync(join(source, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "install.sh"), join(source, "install.sh"));
  mkdirSync(join(release, "skills"), { recursive: true });
  mkdirSync(join(release, "identity"), { recursive: true });
  cpSync(join(source, "install.sh"), join(release, "install.sh"));
  writeFileSync(join(release, ".env.example"), "FUEL=fixture\n");
  writeFileSync(join(release, "identity", "genesis.md"), "fixture genesis\n");
  writeFileSync(join(release, "skills", "registry.json"), JSON.stringify({ slots: {} }));
  const sourceEntries = [
    [".env.example", "FUEL=fixture\n"],
    ["identity/genesis.md", "fixture genesis\n"],
    ["install.sh", readFileSync(join(source, "install.sh"), "utf8")],
    ["skills/registry.json", JSON.stringify({ slots: {} })],
  ].map(([path, body]) => ({ mode: "0444", path, sha256: createHash("sha256").update(body).digest("hex") }));
  const sourceManifestBody = JSON.stringify({ entries: sourceEntries, version: 1 }) + "\n";
  writeFileSync(join(release, "SOURCE-MANIFEST.json"), sourceManifestBody);
  writeFileSync(join(release, "RELEASE.json"), JSON.stringify({
    sha: "a1".repeat(20), git_commit: "a1".repeat(20), release_id: releaseId, release_root: releaseRoot,
    namespace: "life-manager", current: join(releaseRoot, "current"), previous: join(releaseRoot, "previous"),
    source_manifest_sha256: createHash("sha256").update(sourceManifestBody).digest("hex"),
  }) + "\n");
  for (const path of [release, join(release, "skills"), join(release, "identity")]) chmodSync(path, 0o555);
  for (const path of [join(release, "install.sh"), join(release, ".env.example"), join(release, "identity", "genesis.md"), join(release, "skills", "registry.json"), join(release, "SOURCE-MANIFEST.json"), join(release, "RELEASE.json")]) chmodSync(path, 0o444);
  mkdirSync(releaseRoot, { recursive: true });
  symlinkSync(release, join(releaseRoot, "current"));
  try {
    const result = spawnSync("bash", [join(source, "install.sh"), "agent-economy"], {
      cwd: source,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: join(root, "home"),
        LIFE_MANAGER_RELEASE_ROOT: releaseRoot,
        LIFE_MANAGER_HOME: runtime,
        LIFE_MANAGER_INSTALL_DAEMON: "0",
        LIFE_MANAGER_INSTALL_DEPS: "0",
      },
    });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, new RegExp(releaseId));
    assert.equal(existsSync(join(runtime, ".env")), true);
    assert.equal(readFileSync(join(runtime, "identity", "genesis.md"), "utf8"), "fixture genesis\n");
    assert.equal(existsSync(join(runtime, "skills", "agent-economy", "run.sh")), false);
    assert.equal(existsSync(join(runtime, "node_modules")), false);
    assert.equal(readlinkSync(join(releaseRoot, "current")), release);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});
