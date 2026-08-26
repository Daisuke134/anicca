import assert from "node:assert/strict";
import {
  chmodSync,
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readlinkSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
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

function sha256File(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function dependencyDigest(root) {
  const entries = [];
  const walk = (directory, relative) => {
    for (const name of readdirSync(directory)) {
      const absolute = join(directory, name);
      const rel = `${relative}/${name}`;
      const stat = lstatSync(absolute);
      const mode = (stat.mode & 0o777 & (stat.isSymbolicLink() ? 0o777 : 0o555)).toString(8);
      if (stat.isSymbolicLink()) {
        entries.push(["symlink", rel, mode, "-", readlinkSync(absolute)]);
      } else if (stat.isFile()) {
        entries.push(["file", rel, mode, sha256File(absolute), "-"]);
      } else if (stat.isDirectory()) {
        walk(absolute, rel);
      }
    }
  };
  walk(join(root, "node_modules"), "node_modules");
  entries.sort((a, b) => a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0);
  return sha256FileFromText(`${entries.map((entry) => entry.join("\t")).join("\n")}\n`);
}

function sha256FileFromText(value) {
  return createHash("sha256").update(value).digest("hex");
}

function assertSealedRelease(root) {
  const walk = (directory) => {
    for (const name of readdirSync(directory)) {
      const absolute = join(directory, name);
      const relative = absolute.slice(root.length + 1);
      const stat = lstatSync(absolute);
      if (relative === "state" || relative.startsWith("state/")) continue;
      assert.equal(stat.mode & 0o222, 0, `release entry remains writable: ${relative}`);
      if (stat.isDirectory()) walk(absolute);
    }
  };
  walk(root);
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

test("compute proxies require the instance key and pass it to the SDK without env reinjection", () => {
  for (const file of ["runtime/compute-proxy/proxy.mjs", "runtime/compute-proxy/force-frontier-proxy.mjs"]) {
    const source = readFileSync(join(REPO_ROOT, file), "utf8");
    assert.match(source, /loadEvmKey\(\{ mode: ["']agent-economy["'] \}\)/u);
    assert.match(source, /AGENT_ECONOMY_INSTANCE_KEY_MISSING/u);
    assert.match(source, /error\.code = ["']AGENT_ECONOMY_INSTANCE_KEY_MISSING["']/u);
    assert.match(source, /new BlockrunClient\(\{ privateKey: pk \}\)/u);
    assert.doesNotMatch(source, /process\.env\.BASE_CHAIN_WALLET_KEY\s*=/u);
  }
});

test("contract-only: both proxies fail before SDK construction when the instance wallet is missing", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-proxy-missing-key-"));
  const fixtureCompute = join(root, "runtime", "compute-proxy");
  const fixtureIdentity = join(root, "skills", "earn", "lib");
  const sdk = join(root, "node_modules", "@blockrun", "llm");
  mkdirSync(fixtureCompute, { recursive: true });
  mkdirSync(fixtureIdentity, { recursive: true });
  mkdirSync(sdk, { recursive: true });
  cpSync(join(REPO_ROOT, "runtime", "compute-proxy", "proxy.mjs"), join(fixtureCompute, "proxy.mjs"));
  cpSync(join(REPO_ROOT, "runtime", "compute-proxy", "force-frontier-proxy.mjs"), join(fixtureCompute, "force-frontier-proxy.mjs"));
  cpSync(join(REPO_ROOT, "skills", "earn", "lib", "resolve-identity.mjs"), join(fixtureIdentity, "resolve-identity.mjs"));
  writeFileSync(join(root, "package.json"), JSON.stringify({ type: "module" }));
  writeFileSync(join(sdk, "package.json"), JSON.stringify({ name: "@blockrun/llm", type: "module", exports: "./index.mjs" }));
  writeFileSync(join(sdk, "index.mjs"), "export class BlockrunClient { constructor() { throw new Error('SDK_CONSTRUCTED'); } }\n");
  try {
    for (const name of ["proxy.mjs", "force-frontier-proxy.mjs"]) {
      const env = { ...process.env, HOME: root, ANICCA_HOME: join(root, "instance"), COMPUTE_PROXY_PORT: "0", PORT: "0" };
      for (const field of ["ANICCA_EVM_PRIVATE_KEY", "PKVAR", "BLOCKRUN_WALLET_KEY", "BASE_CHAIN_WALLET_KEY", "WALLET_FILE"]) delete env[field];
      const result = spawnSync(process.execPath, [join(fixtureCompute, name)], { cwd: root, env, encoding: "utf8" });
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /AGENT_ECONOMY_INSTANCE_KEY_MISSING/u);
      assert.doesNotMatch(result.stderr, /SDK_CONSTRUCTED/u);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("start-local exports ANICCA_HOME before launching the identity-bound proxy", () => {
  const source = readFileSync(join(REPO_ROOT, "runtime/compute-proxy/start-local.sh"), "utf8");
  const homeIndex = source.indexOf('export ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"');
  const launchIndex = source.indexOf('ANICCA_HOME="$ANICCA_HOME" node proxy.mjs');
  assert.ok(homeIndex >= 0, "start-local must derive ANICCA_HOME");
  assert.ok(launchIndex > homeIndex, "proxy must launch after ANICCA_HOME is exported");
});

test("release sealing is fatal and occurs before the current symlink move", () => {
  const source = readFileSync(join(REPO_ROOT, "bin/cut-loop-release.sh"), "utf8");
  assert.doesNotMatch(source, /LOOPS_NPM_BIN/u);
  assert.match(source, /verify_release_seal/u);
  assert.doesNotMatch(source, /chmod -R a-w [^\n]*\|\| true/u);
  assert.ok(source.indexOf("verify_release_seal") < source.indexOf("ln -sfn"));
});

// Contract-only fixture: npm and viem are stubs, so this is not a live dependency/install proof.
test("contract-only: release cutter installs locked dependencies in the release and records provenance before sealing", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-deps-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
  const loops = join(root, "loops");
  const stubBin = join(root, "npm");
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
        PATH: `${root}:${process.env.PATH}`,
        NPM_STUB_CWD: join(root, "npm-cwd"),
        NPM_STUB_ARGS: join(root, "npm-args"),
      },
    });
    assert.equal(cut.status, 0, `${cut.stdout}\n${cut.stderr}`);
    const release = readFileSync(join(loops, "current", "RELEASE.json"), "utf8");
    const metadata = JSON.parse(release);
    const releaseRoot = readlinkSync(join(loops, "current"));
    assert.equal(readFileSync(join(root, "npm-cwd"), "utf8"), releaseRoot);
    assert.equal(readFileSync(join(root, "npm-args"), "utf8"), "ci --ignore-scripts --no-audit --no-fund");
    assert.equal(metadata.lockfile_sha256, sha256File(join(releaseRoot, "package-lock.json")));
    assert.equal(metadata.dependency_manifest_sha256, sha256File(join(releaseRoot, "package.json")));
    assert.equal(metadata.dependency_sha256, dependencyDigest(releaseRoot));
    assert.deepEqual(metadata.runtime_versions.npm, "9.9.9");
    assert.match(metadata.runtime_versions.node, /^v\d+/u);
    assertSealedRelease(releaseRoot);
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

// Contract-only fixture: the npm stub deliberately creates an escaping link; no live release is cut.
test("contract-only: release cutter rejects a dependency symlink that escapes the release node_modules root", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-symlink-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
  const loops = join(root, "loops");
  const outside = join(root, "outside-secret-marker");
  const npm = join(root, "npm");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  writeFileSync(join(repo, "package.json"), JSON.stringify({ name: "release-symlink-fixture", type: "module" }));
  writeFileSync(join(repo, "package-lock.json"), JSON.stringify({ name: "release-symlink-fixture", lockfileVersion: 3, packages: { "": { name: "release-symlink-fixture" } } }));
  writeFileSync(outside, "outside\n");
  writeFileSync(npm, [
    "#!/bin/sh",
    'if [ "$1" = "--version" ]; then echo "9.9.9"; exit 0; fi',
    'mkdir -p node_modules/viem',
    'printf "%s" \'{"name":"viem","type":"module","exports":"./index.mjs"}\' > node_modules/viem/package.json',
    'printf "%s" \'export const marker = "release-viem";\' > node_modules/viem/index.mjs',
    'ln -s "$NPM_STUB_ESCAPE_TARGET" node_modules/escape',
    "",
  ].join("\n"));
  chmodSync(npm, 0o755);
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
        PATH: `${root}:${process.env.PATH}`,
        LOOPS_ROOT: loops,
        NPM_STUB_ESCAPE_TARGET: outside,
      },
    });
    assert.notEqual(cut.status, 0);
    assert.match(cut.stderr, /dependency symlink escapes release node_modules/u);
    assert.equal(existsSync(join(loops, "current")), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

// Contract-only fixture: chmod is stubbed to fail, proving sealing aborts before current moves.
test("contract-only: release cutter aborts before current when the release seal fails", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-seal-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
  const loops = join(root, "loops");
  const npm = join(root, "npm");
  const chmod = join(root, "chmod");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  writeFileSync(join(repo, "package.json"), JSON.stringify({ name: "release-seal-fixture", type: "module" }));
  writeFileSync(join(repo, "package-lock.json"), JSON.stringify({ name: "release-seal-fixture", lockfileVersion: 3, packages: { "": { name: "release-seal-fixture" } } }));
  writeFileSync(npm, [
    "#!/bin/sh",
    'if [ "$1" = "--version" ]; then echo "9.9.9"; exit 0; fi',
    'mkdir -p node_modules/viem',
    'printf "%s" \'{"name":"viem","type":"module","exports":"./index.mjs"}\' > node_modules/viem/package.json',
    'printf "%s" \'export const marker = "release-viem";\' > node_modules/viem/index.mjs',
    "",
  ].join("\n"));
  writeFileSync(chmod, "#!/bin/sh\nexit 1\n");
  chmodSync(npm, 0o755);
  chmodSync(chmod, 0o755);
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
        PATH: `${root}:${process.env.PATH}`,
        LOOPS_ROOT: loops,
      },
    });
    assert.notEqual(cut.status, 0);
    assert.match(cut.stderr, /could not seal release permissions/u);
    assert.equal(existsSync(join(loops, "current")), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});
