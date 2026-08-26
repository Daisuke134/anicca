import assert from "node:assert/strict";
import {
  chmodSync,
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readlinkSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const REPO_ROOT = new URL("../", import.meta.url).pathname;

function parsePlist(path) {
  const result = spawnSync("python3", ["-c", [
    "import json, plistlib, sys",
    "print(json.dumps(plistlib.loads(open(sys.argv[1], 'rb').read())))",
  ].join(";"), path], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("agent-economy launchd declaration uses the immutable release and continuous contract", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-plist-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const current = join(home, "loops", "current");
  const logs = join(home, "loops", "logs");

  try {
    const generated = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"),
      "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out,
      "--home", home,
      "--current", current,
      "--logs", logs,
      "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.equal(generated.status, 0, `${generated.stdout}\n${generated.stderr}`);

    const plist = parsePlist(join(out, "ai.anicca.agent-economy-loop.plist"));
    assert.deepEqual(plist.ProgramArguments, [
      "/bin/bash",
      join(current, "skills", "agent-economy", "launch.sh"),
    ]);
    assert.equal(plist.KeepAlive, true);
    assert.equal(plist.RunAtLoad, true);
    assert.equal(plist.StartInterval, undefined);
    assert.equal(plist.StartCalendarInterval, undefined);
    assert.equal(plist.EnvironmentVariables.ANICCA_REPO, current);
    assert.equal(plist.EnvironmentVariables.ANICCA_HOME, join(home, "loops", "agent-economy"));
    assert.deepEqual(plist.EnvironmentVariables.ANICCA_SLOT_ALLOWLIST.split(","), [
      "earn/taskmarket", "x402_sell", "report", "cook",
    ]);
    assert.equal(plist.EnvironmentVariables.ANICCA_ECONOMY_RECONCILE, "1");
    assert.equal(plist.EnvironmentVariables.ANICCA_ECONOMY_CREATE_EVM_WALLET, "1");
    assert.equal(plist.ProgramArguments.join(" ").includes(".worktrees"), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("release cutter installs locked dependencies in the release and records provenance before sealing", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-deps-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
  const loops = join(root, "loops");
  const stubBin = join(root, "stub-npm");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  writeFileSync(join(repo, "package.json"), JSON.stringify({ name: "release-fixture", type: "module" }));
  writeFileSync(join(repo, "package-lock.json"), JSON.stringify({ name: "release-fixture", lockfileVersion: 3, packages: { "": { name: "release-fixture" } } }));
  mkdirSync(join(repo, "runtime", "compute-proxy"), { recursive: true });
  writeFileSync(join(repo, "runtime", "compute-proxy", "viem-probe.mjs"), 'import { marker } from "viem";\nconsole.log(marker);\n');
  writeFileSync(stubBin, [
    "#!/bin/sh",
    'if [ "$1" = "--version" ]; then echo "9.9.9"; exit 0; fi',
    'if [ "$1" != "ci" ]; then echo "unexpected npm invocation" >&2; exit 97; fi',
    'printf "%s" "$PWD" > "$NPM_STUB_CWD"',
    'printf "%s" "$*" > "$NPM_STUB_ARGS"',
    'mkdir -p node_modules/viem',
    'printf "%s" \'{"name":"viem","type":"module","exports":"./index.mjs"}\' > node_modules/viem/package.json',
    'printf "%s" \'export const marker = "release-viem";\' > node_modules/viem/index.mjs',
    "exit 0",
    "",
  ].join("\n"));
  chmodSync(stubBin, 0o755);

  const git = (...args) => spawnSync("git", ["-C", repo, ...args], { encoding: "utf8" });
  try {
    assert.equal(spawnSync("git", ["init", "-q", repo], { encoding: "utf8" }).status, 0);
    assert.equal(git("config", "user.email", "fixture@example.invalid").status, 0);
    assert.equal(git("config", "user.name", "fixture").status, 0);
    assert.equal(git("add", ".").status, 0);
    assert.equal(git("commit", "-qm", "fixture").status, 0);
    assert.equal(spawnSync("git", ["init", "--bare", "-q", remote], { encoding: "utf8" }).status, 0);
    assert.equal(git("remote", "add", "origin", remote).status, 0);
    assert.equal(git("push", "-q", "origin", "HEAD:main").status, 0);

    const cut = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], {
      cwd: repo,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: root,
        LOOPS_ROOT: loops,
        LOOPS_KEEP_RELEASES: "1",
        LOOPS_NPM_BIN: stubBin,
        NPM_STUB_CWD: join(root, "npm-cwd"),
        NPM_STUB_ARGS: join(root, "npm-args"),
      },
    });
    assert.equal(cut.status, 0, `${cut.stdout}\n${cut.stderr}`);
    const release = readFileSync(join(loops, "current", "RELEASE.json"), "utf8");
    const metadata = JSON.parse(release);
    const releaseRoot = readlinkSync(join(loops, "current"));
    assert.equal(readFileSync(join(root, "npm-cwd"), "utf8"), releaseRoot);
    assert.match(readFileSync(join(root, "npm-args"), "utf8"), /^ci /u);
    assert.match(metadata.lockfile_sha256, /^[0-9a-f]{64}$/u);
    assert.match(metadata.dependency_sha256, /^[0-9a-f]{64}$/u);
    assert.deepEqual(metadata.runtime_versions.npm, "9.9.9");
    assert.match(metadata.runtime_versions.node, /^v\d+/u);
    assert.equal(existsSync(join(repo, "node_modules")), false, "fixture source has no dependency install");
    const probe = spawnSync(process.execPath, [join(releaseRoot, "runtime", "compute-proxy", "viem-probe.mjs")], {
      encoding: "utf8",
      cwd: repo,
    });
    assert.equal(probe.status, 0, probe.stderr);
    assert.equal(probe.stdout.trim(), "release-viem");
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});
