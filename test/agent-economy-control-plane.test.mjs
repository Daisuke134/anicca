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
  realpathSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const REPO_ROOT = new URL("../", import.meta.url).pathname;
const TRUSTED_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"];

function trustedTool(name) {
  for (const directory of TRUSTED_BIN_DIRS) {
    const candidate = join(directory, name);
    try {
      if (statSync(candidate).isFile() && (statSync(candidate).mode & 0o111) !== 0) return candidate;
    } catch { /* try next allowlisted directory */ }
  }
  return null;
}

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
      const mode = (stat.mode & 0o777 & 0o555).toString(8);
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
      if (stat.isSymbolicLink()) continue;
      assert.equal(stat.mode & 0o222, 0, `release entry remains writable: ${relative}`);
      if (stat.isDirectory()) walk(absolute);
    }
  };
  walk(root);
}

function writeSealedAgentEconomyRelease(root, {
  id = "20260827T000000-a1a1a1a1",
  sha = "a1".repeat(20),
} = {}) {
  const releaseRoot = join(root, "home", "loops", "life-manager");
  const release = join(releaseRoot, "releases", id);
  mkdirSync(join(release, "skills", "agent-economy"), { recursive: true });
  mkdirSync(join(release, "node_modules"), { recursive: true });
  const launchPath = join(release, "skills", "agent-economy", "launch.sh");
  const launchBody = "#!/bin/bash\n";
  writeFileSync(launchPath, launchBody);
  const readmeBody = "readme\n";
  writeFileSync(join(release, "skills", "agent-economy", "readme.txt"), readmeBody);
  symlinkSync("launch.sh", join(release, "skills", "agent-economy", "internal-link.sh"));
  symlinkSync("readme.txt", join(release, "skills", "agent-economy", "nonexec-link.sh"));
  // Match cutter's sorted-key compact JSON exactly.
  const sourceEntries = [
    { mode: "0555", path: "skills/agent-economy/launch.sh", sha256: createHash("sha256").update(launchBody).digest("hex") },
    { mode: "0555", path: "skills/agent-economy/internal-link.sh", sha256: createHash("sha256").update("launch.sh").digest("hex"), target: "launch.sh" },
    { mode: "0555", path: "skills/agent-economy/nonexec-link.sh", sha256: createHash("sha256").update("readme.txt").digest("hex"), target: "readme.txt" },
    { mode: "0444", path: "skills/agent-economy/readme.txt", sha256: createHash("sha256").update(readmeBody).digest("hex") },
  ].sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")));
  const sourceManifestBody = `${JSON.stringify({ entries: sourceEntries, version: 1 })}\n`;
  writeFileSync(join(release, "SOURCE-MANIFEST.json"), sourceManifestBody);
  writeFileSync(join(release, "DEPENDENCY-MANIFEST.tsv"), "");
  writeFileSync(join(release, "RELEASE.json"), JSON.stringify({
    sha, git_commit: sha,
    release_id: id,
    release_root: releaseRoot,
    namespace: "life-manager",
    current: join(releaseRoot, "current"),
    previous: join(releaseRoot, "previous"),
    source_manifest_sha256: createHash("sha256").update(sourceManifestBody).digest("hex"),
    dependency_tree_manifest_sha256: createHash("sha256").update("").digest("hex"),
  }) + "\n");
  chmodSync(release, 0o555);
  chmodSync(join(release, "RELEASE.json"), 0o444);
  chmodSync(join(release, "SOURCE-MANIFEST.json"), 0o444);
  chmodSync(join(release, "DEPENDENCY-MANIFEST.tsv"), 0o444);
  chmodSync(join(release, "node_modules"), 0o555);
  chmodSync(join(release, "skills"), 0o555);
  chmodSync(join(release, "skills", "agent-economy"), 0o555);
  chmodSync(join(release, "skills", "agent-economy", "launch.sh"), 0o555);
  chmodSync(join(release, "skills", "agent-economy", "readme.txt"), 0o444);
  mkdirSync(releaseRoot, { recursive: true });
  symlinkSync(release, join(releaseRoot, "current"));
  return { releaseRoot, release };
}

test("agent-economy launchd declaration uses the immutable release and continuous contract", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-plist-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const current = join(home, "loops", "life-manager", "current");
  const logs = join(home, "loops", "logs");
  writeSealedAgentEconomyRelease(root);

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
    const release = realpathSync(current);
    assert.deepEqual(plist.ProgramArguments, [
      "/bin/bash",
      join(release, "skills", "agent-economy", "launch.sh"),
    ]);
    assert.equal(plist.KeepAlive, true);
    assert.equal(plist.RunAtLoad, true);
    assert.equal(plist.StartInterval, undefined);
    assert.equal(plist.StartCalendarInterval, undefined);
    assert.equal(plist.EnvironmentVariables.ANICCA_REPO, release);
    assert.equal(plist.EnvironmentVariables.ANICCA_CODE_ROOT, release);
    assert.equal(plist.EnvironmentVariables.ANICCA_HOME, join(home, "loops", "agent-economy"));
    assert.equal(plist.EnvironmentVariables.ANICCA_RELEASE_ROOT, join(home, "loops", "life-manager"));
    assert.equal(plist.EnvironmentVariables.ANICCA_RELEASE_ID, "20260827T000000-a1a1a1a1");
    assert.equal(plist.EnvironmentVariables.ANICCA_RELEASE_SHA, "a1".repeat(20));
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

test("agent-economy plist generation rejects a worktree current before writing any plist", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-plist-worktree-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const current = join(root, ".worktrees", "feature", "current");
  try {
    const generated = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"),
      "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out,
      "--home", home,
      "--current", current,
      "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.notEqual(generated.status, 0, `${generated.stdout}\n${generated.stderr}`);
    assert.match(`${generated.stdout}\n${generated.stderr}`, /worktree/i);
    assert.equal(existsSync(out), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("agent-economy plist pins the resolved release and does not follow a later current move", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-plist-pinned-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const first = writeSealedAgentEconomyRelease(root);
  const secondId = "20260827T000001-b2b2b2b2";
  rmSync(join(first.releaseRoot, "current"), { force: true });
  const second = writeSealedAgentEconomyRelease(root, { id: secondId, sha: "b2".repeat(20) });
  rmSync(join(first.releaseRoot, "current"), { force: true });
  symlinkSync(first.release, join(first.releaseRoot, "current"));
  try {
    const generated = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"), "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out, "--home", home, "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.equal(generated.status, 0, `${generated.stdout}\n${generated.stderr}`);
    const plistPath = join(out, "ai.anicca.agent-economy-loop.plist");
    const before = parsePlist(plistPath);
    const firstResolved = realpathSync(first.release);
    assert.equal(before.ProgramArguments[1], join(firstResolved, "skills", "agent-economy", "launch.sh"));
    assert.equal(before.EnvironmentVariables.ANICCA_CODE_ROOT, firstResolved);
    rmSync(join(first.releaseRoot, "current"), { force: true });
    symlinkSync(second.release, join(first.releaseRoot, "current"));
    const after = parsePlist(plistPath);
    assert.deepEqual(after.ProgramArguments, before.ProgramArguments);
    assert.equal(after.EnvironmentVariables.ANICCA_CODE_ROOT, firstResolved);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("agent-economy plist rejects a modified source file despite a sealed mode", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-manifest-mismatch-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const { release } = writeSealedAgentEconomyRelease(root);
  try {
    const launch = join(release, "skills", "agent-economy", "launch.sh");
    chmodSync(launch, 0o644);
    writeFileSync(launch, "#!/bin/bash\nchanged\n");
    chmodSync(launch, 0o555);
    const generated = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"), "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out, "--home", home, "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.notEqual(generated.status, 0);
    assert.match(`${generated.stdout}\n${generated.stderr}`, /manifest/i);
    assert.equal(existsSync(out), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("strict release validation accepts internal source symlinks and rejects release escapes", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-symlink-"));
  const home = join(root, "home");
  const out = join(root, "launchagents");
  const { release, releaseRoot } = writeSealedAgentEconomyRelease(root);
  try {
    const internal = join(release, "skills", "agent-economy", "internal-link.sh");
    assert.equal(lstatSync(internal).isSymbolicLink(), true);
    const ok = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"), "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", out, "--home", home, "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.equal(ok.status, 0, `${ok.stdout}\n${ok.stderr}`);
    chmodSync(join(release, "skills", "agent-economy"), 0o755);
    rmSync(internal, { force: true });
    symlinkSync("/etc/passwd", internal);
    const manifestPath = join(release, "SOURCE-MANIFEST.json");
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    const entry = manifest.entries.find((item) => item.path === "skills/agent-economy/internal-link.sh");
    entry.target = "/etc/passwd";
    entry.sha256 = createHash("sha256").update("/etc/passwd").digest("hex");
    const body = `${JSON.stringify(manifest)}\n`;
    chmodSync(release, 0o755);
    chmodSync(manifestPath, 0o644);
    writeFileSync(manifestPath, body);
    const metadataPath = join(release, "RELEASE.json");
    const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
    metadata.source_manifest_sha256 = createHash("sha256").update(body).digest("hex");
    chmodSync(metadataPath, 0o644);
    writeFileSync(metadataPath, JSON.stringify(metadata) + "\n");
    chmodSync(manifestPath, 0o444);
    chmodSync(metadataPath, 0o444);
    chmodSync(release, 0o555);
    chmodSync(join(release, "skills", "agent-economy"), 0o555);
    const bad = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"), "--loops-dir", join(REPO_ROOT, "loops"),
      "--out-dir", join(root, "launchagents-bad"), "--home", home, "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.notEqual(bad.status, 0);
    assert.match(`${bad.stdout}\n${bad.stderr}`, /symlink|escap/i);
    assert.equal(readlinkSync(join(releaseRoot, "current")), release);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("rollback restoration attempts the second pointer after the first restoration fails", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-restore-both-"));
  const repo = join(root, "repo");
  const loops = join(root, "home", "loops", "life-manager");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  const first = writeSealedAgentEconomyRelease(root, { id: "20260827T000000-a1a1a1a1", sha: "a1".repeat(20) });
  rmSync(join(loops, "current"), { force: true });
  const second = writeSealedAgentEconomyRelease(root, { id: "20260827T000001-b2b2b2b2", sha: "b2".repeat(20) });
  rmSync(join(loops, "current"), { force: true });
  symlinkSync(first.release, join(loops, "current"));
  symlinkSync(second.release, join(loops, "previous"));
  try {
    const result = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: join(root, "home"),
        LOOPS_ROOT: loops,
        LOOPS_TEST_FAIL_ROLLBACK_READBACK: "1",
        LOOPS_TEST_FAIL_RESTORE_CURRENT: "1",
      },
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /rollback restoration failed/u);
    assert.equal(readlinkSync(join(loops, "current")), second.release);
    assert.equal(readlinkSync(join(loops, "previous")), second.release);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("launch validation-only preflight verifies byte-sorted dependency entries and rejects mutation", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-launch-preflight-"));
  const home = join(root, "home");
  const { release, releaseRoot } = writeSealedAgentEconomyRelease(root);
  const launchPath = join(release, "skills", "agent-economy", "launch.sh");
  try {
    chmodSync(join(release, "skills", "agent-economy"), 0o755);
    const launchBody = readFileSync(join(REPO_ROOT, "skills", "agent-economy", "launch.sh"), "utf8");
    chmodSync(launchPath, 0o644);
    writeFileSync(launchPath, launchBody);
    chmodSync(launchPath, 0o555);
    chmodSync(release, 0o755);
    const daemonPath = join(release, "runtime", "anicca-daemon.sh");
    mkdirSync(join(release, "runtime"), { recursive: true });
    const daemonBody = "#!/bin/bash\nexit 0\n";
    writeFileSync(daemonPath, daemonBody);
    chmodSync(daemonPath, 0o555);
    const sourceManifestPath = join(release, "SOURCE-MANIFEST.json");
    const sourceManifest = JSON.parse(readFileSync(sourceManifestPath, "utf8"));
    sourceManifest.entries.find((entry) => entry.path === "skills/agent-economy/launch.sh").sha256 = createHash("sha256").update(launchBody).digest("hex");
    sourceManifest.entries.push({ mode: "0555", path: "runtime/anicca-daemon.sh", sha256: createHash("sha256").update(daemonBody).digest("hex") });
    sourceManifest.entries.sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")));
    const sourceManifestBody = `${JSON.stringify(sourceManifest)}\n`;
    chmodSync(sourceManifestPath, 0o644);
    writeFileSync(sourceManifestPath, sourceManifestBody);

    const dependencyRoot = join(release, "node_modules");
    chmodSync(dependencyRoot, 0o755);
    const files = new Map([
      ["@Scope/child.js", "scope\n"],
      ["UPPER", "upper\n"],
      ["_pkg/child", "underscore\n"],
      ["a/child", "nested\n"],
      ["a.js", "dot\n"],
    ]);
    const dependencyEntries = [];
    for (const [relative, body] of files) {
      const absolute = join(dependencyRoot, relative);
      mkdirSync(join(absolute, ".."), { recursive: true });
      writeFileSync(absolute, body);
      chmodSync(absolute, 0o444);
      dependencyEntries.push({ kind: "file", path: `node_modules/${relative}`, mode: "444", sha256: createHash("sha256").update(body).digest("hex"), target: "-" });
    }
    symlinkSync("UPPER", join(dependencyRoot, "nonexec"));
    dependencyEntries.push({ kind: "symlink", path: "node_modules/nonexec", mode: "555", sha256: "-", target: "UPPER" });
    const dependencyBody = `${dependencyEntries
      .sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")))
      .map((entry) => `${entry.kind}\t${entry.path}\t${entry.mode}\t${entry.sha256}\t${entry.target}`)
      .join("\n")}\n`;
    const dependencyManifestPath = join(release, "DEPENDENCY-MANIFEST.tsv");
    chmodSync(dependencyManifestPath, 0o644);
    writeFileSync(dependencyManifestPath, dependencyBody);
    const metadataPath = join(release, "RELEASE.json");
    const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
    metadata.source_manifest_sha256 = createHash("sha256").update(sourceManifestBody).digest("hex");
    metadata.dependency_tree_manifest_sha256 = createHash("sha256").update(dependencyBody).digest("hex");
    chmodSync(metadataPath, 0o644);
    writeFileSync(metadataPath, JSON.stringify(metadata) + "\n");
    chmodSync(sourceManifestPath, 0o444);
    chmodSync(dependencyManifestPath, 0o444);
    chmodSync(metadataPath, 0o444);
    chmodSync(dependencyRoot, 0o555);
    chmodSync(join(release, "skills", "agent-economy"), 0o555);
    spawnSync("chmod", ["-R", "a-w", release], { encoding: "utf8" });
    const rewriteSourceManifest = () => {
      sourceManifest.entries.sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")));
      const nextBody = `${JSON.stringify(sourceManifest)}\n`;
      chmodSync(sourceManifestPath, 0o644);
      writeFileSync(sourceManifestPath, nextBody);
      metadata.source_manifest_sha256 = createHash("sha256").update(nextBody).digest("hex");
      chmodSync(metadataPath, 0o644);
      writeFileSync(metadataPath, JSON.stringify(metadata) + "\n");
      chmodSync(sourceManifestPath, 0o444);
      chmodSync(metadataPath, 0o444);
      spawnSync("chmod", ["-R", "a-w", release], { encoding: "utf8" });
    };
    const resolvedRelease = realpathSync(release);
    const env = { ...process.env, ANICCA_HOME: home, ANICCA_CODE_ROOT: resolvedRelease, ANICCA_REPO: resolvedRelease, ANICCA_RELEASE_ROOT: releaseRoot, ANICCA_VALIDATE_RELEASE_ONLY: "1" };
    const preflight = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
    assert.equal(preflight.status, 0, `${preflight.stdout}\n${preflight.stderr}`);
    assert.match(preflight.stdout, /sealed release validation passed/u);
    const expectWritableRejected = (path, writableMode, sealedMode) => {
      chmodSync(path, writableMode);
      const rejectedWritable = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
      assert.equal(rejectedWritable.status, 2, `${rejectedWritable.stdout}\n${rejectedWritable.stderr}`);
      assert.match(`${rejectedWritable.stdout}\n${rejectedWritable.stderr}`, /sealed release metadata is invalid/u);
      chmodSync(path, sealedMode);
    };
    expectWritableRejected(release, 0o755, 0o555);
    expectWritableRejected(launchPath, 0o755, 0o555);
    expectWritableRejected(join(dependencyRoot, "a.js"), 0o644, 0o444);
    const resealed = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
    assert.equal(resealed.status, 0, `${resealed.stdout}\n${resealed.stderr}`);
    chmodSync(join(release, "runtime"), 0o755);
    rmSync(daemonPath, { force: true });
    sourceManifest.entries = sourceManifest.entries.filter((entry) => entry.path !== "runtime/anicca-daemon.sh");
    chmodSync(join(release, "runtime"), 0o555);
    rewriteSourceManifest();
    const missingDaemon = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
    assert.equal(missingDaemon.status, 2);
    assert.match(`${missingDaemon.stdout}\n${missingDaemon.stderr}`, /missing daemon at/u);
    chmodSync(join(release, "runtime"), 0o755);
    writeFileSync(daemonPath, daemonBody);
    chmodSync(daemonPath, 0o444);
    sourceManifest.entries.push({ mode: "0444", path: "runtime/anicca-daemon.sh", sha256: createHash("sha256").update(daemonBody).digest("hex") });
    chmodSync(join(release, "runtime"), 0o555);
    rewriteSourceManifest();
    const nonExecutableDaemon = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
    assert.equal(nonExecutableDaemon.status, 2);
    assert.match(`${nonExecutableDaemon.stdout}\n${nonExecutableDaemon.stderr}`, /missing daemon at/u);
    chmodSync(daemonPath, 0o555);
    sourceManifest.entries.find((entry) => entry.path === "runtime/anicca-daemon.sh").mode = "0555";
    rewriteSourceManifest();
    const mutate = join(dependencyRoot, "a.js");
    chmodSync(mutate, 0o644);
    writeFileSync(mutate, "tampered\n");
    chmodSync(mutate, 0o444);
    const rejected = spawnSync("bash", [launchPath], { cwd: REPO_ROOT, env, encoding: "utf8" });
    assert.notEqual(rejected.status, 0);
    assert.match(`${rejected.stdout}\n${rejected.stderr}`, /metadata|dependenc|release/i);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("launch validation accepts UTF-8 byte-sorted source paths from the release cutter", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-launch-unicode-"));
  const home = join(root, "home");
  const { release, releaseRoot } = writeSealedAgentEconomyRelease(root);
  const agentDir = join(release, "skills", "agent-economy");
  const manifestPath = join(release, "SOURCE-MANIFEST.json");
  const metadataPath = join(release, "RELEASE.json");
  try {
    chmodSync(release, 0o755);
    chmodSync(join(release, "skills"), 0o755);
    chmodSync(agentDir, 0o755);
    const launchBody = readFileSync(join(REPO_ROOT, "skills", "agent-economy", "launch.sh"), "utf8");
    chmodSync(join(agentDir, "launch.sh"), 0o644);
    writeFileSync(join(agentDir, "launch.sh"), launchBody);
    chmodSync(join(agentDir, "launch.sh"), 0o555);
    const collisionFiles = [["test/collision.txt", "test\n"], ["test-support/collision.txt", "support\n"]];
    for (const [relative] of collisionFiles) mkdirSync(join(agentDir, relative, ".."), { recursive: true });
    const unicodeFiles = [...collisionFiles, ["あ.txt", "jp\n"], ["😀.txt", "emoji\n"]];
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    for (const [name, body] of unicodeFiles) {
      writeFileSync(join(agentDir, name), body);
      chmodSync(join(agentDir, name), 0o444);
      manifest.entries.push({ mode: "0444", path: `skills/agent-economy/${name}`, sha256: createHash("sha256").update(body).digest("hex") });
    }
    manifest.entries.find((entry) => entry.path === "skills/agent-economy/launch.sh").sha256 = createHash("sha256").update(launchBody).digest("hex");
    manifest.entries.sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")));
    const manifestBody = `${JSON.stringify(manifest)}\n`;
    chmodSync(manifestPath, 0o644);
    writeFileSync(manifestPath, manifestBody);
    const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
    metadata.source_manifest_sha256 = createHash("sha256").update(manifestBody).digest("hex");
    chmodSync(metadataPath, 0o644);
    writeFileSync(metadataPath, `${JSON.stringify(metadata)}\n`);
    const daemonPath = join(release, "runtime", "anicca-daemon.sh");
    mkdirSync(join(release, "runtime"), { recursive: true });
    const daemonBody = "#!/bin/sh\nexit 0\n";
    writeFileSync(daemonPath, daemonBody);
    chmodSync(daemonPath, 0o555);
    manifest.entries.push({ mode: "0555", path: "runtime/anicca-daemon.sh", sha256: createHash("sha256").update(daemonBody).digest("hex") });
    manifest.entries.sort((a, b) => Buffer.compare(Buffer.from(a.path, "utf8"), Buffer.from(b.path, "utf8")));
    const finalManifestBody = `${JSON.stringify(manifest)}\n`;
    chmodSync(manifestPath, 0o644);
    writeFileSync(manifestPath, finalManifestBody);
    metadata.source_manifest_sha256 = createHash("sha256").update(finalManifestBody).digest("hex");
    chmodSync(metadataPath, 0o644);
    writeFileSync(metadataPath, `${JSON.stringify(metadata)}\n`);
    spawnSync("chmod", ["-R", "a-w", release], { encoding: "utf8" });
    const collisionPaths = collisionFiles.map(([relative]) => `skills/agent-economy/${relative}`);
    const componentWise = [...collisionPaths].sort((left, right) => {
      const leftParts = left.split("/");
      const rightParts = right.split("/");
      for (let index = 0; index < Math.min(leftParts.length, rightParts.length); index += 1) {
        if (leftParts[index] < rightParts[index]) return -1;
        if (leftParts[index] > rightParts[index]) return 1;
      }
      return leftParts.length - rightParts.length;
    });
    const byteWise = [...collisionPaths].sort((left, right) => Buffer.compare(Buffer.from(left, "utf8"), Buffer.from(right, "utf8")));
    assert.notDeepEqual(componentWise, byteWise, "component-wise Path ordering must differ for prefix collisions");
    assert.deepEqual(manifest.entries.map((entry) => entry.path).filter((path) => collisionPaths.includes(path)), byteWise);
    const installed = spawnSync("bash", [join(REPO_ROOT, "install.sh"), "agent-economy"], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: root,
        LIFE_MANAGER_HOME: join(root, "installed-home"),
        LIFE_MANAGER_RELEASE_ROOT: releaseRoot,
        LIFE_MANAGER_INSTALL_DAEMON: "0",
        LIFE_MANAGER_INSTALL_DEPS: "0",
      },
    });
    assert.equal(installed.status, 0, `${installed.stdout}\n${installed.stderr}`);
    const result = spawnSync("bash", [join(agentDir, "launch.sh")], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: { ...process.env, ANICCA_HOME: home, ANICCA_CODE_ROOT: realpathSync(release), ANICCA_REPO: realpathSync(release), ANICCA_RELEASE_ROOT: releaseRoot, ANICCA_VALIDATE_RELEASE_ONLY: "1" },
    });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, /sealed release validation passed/u);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("pinned runtime paths are explicit: daemon skips mutable self-update/sync and plist writes atomically", () => {
  const daemon = readFileSync(join(REPO_ROOT, "runtime/anicca-daemon.sh"), "utf8");
  assert.match(daemon, /ANICCA_CODE_ROOT/u);
  assert.match(daemon, /BASH_SOURCE/u);
  assert.match(daemon, /PINNED_RELEASE/u);
  assert.match(daemon, /rsync/u);
  assert.match(daemon, /node_modules/u);
  assert.match(daemon, /PINNED_RELEASE/u);
  const runSkill = readFileSync(join(REPO_ROOT, "runtime/loop/run-skill.mjs"), "utf8");
  assert.match(runSkill, /ANICCA_CODE_ROOT/u);
  assert.match(runSkill, /path\.join\(root, ['"]skills['"]/u);
  const launch = readFileSync(join(REPO_ROOT, "skills/agent-economy/launch.sh"), "utf8");
  assert.match(launch, /dependencyLines\.sort.*Buffer\.compare/su);
  const plistgen = readFileSync(join(REPO_ROOT, "bin/plistgen.py"), "utf8");
  assert.match(plistgen, /os\.replace\(/u);
  assert.doesNotMatch(plistgen, /target\.write_bytes\(/u);
});

test("run-skill executes code from CODE_ROOT while the skill writes state under ANICCA_HOME", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-code-state-"));
  const codeRoot = join(root, "release");
  const home = join(root, "home");
  const skill = join(codeRoot, "skills", "probe", "run.sh");
  mkdirSync(join(codeRoot, "skills", "probe"), { recursive: true });
  writeFileSync(skill, "#!/bin/bash\nmkdir -p \"$ANICCA_HOME/skills/probe/state\"\nprintf '%s\\n' \"$ANICCA_CODE_ROOT\" > \"$ANICCA_HOME/skills/probe/state/result\"\n");
  chmodSync(skill, 0o755);
  try {
    const script = [
      "import { runSkill } from './runtime/loop/run-skill.mjs';",
      "const result = await runSkill('probe', {}, 'wake', { ANICCA_HOME: process.env.ANICCA_HOME, SKILL_TIMEOUT_S: 5 });",
      "console.log(JSON.stringify(result));",
    ].join("\n");
    const result = spawnSync(process.execPath, ["--input-type=module", "-e", script], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: { ...process.env, ANICCA_CODE_ROOT: codeRoot, ANICCA_HOME: home },
    });
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.equal(JSON.parse(result.stdout).exitCode, 0);
    assert.equal(readFileSync(join(home, "skills", "probe", "state", "result"), "utf8").trim(), codeRoot);
    assert.equal(existsSync(join(codeRoot, "skills", "probe", "state")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("whole sealed releases have no effective-cron writable carveout", () => {
  const cutter = readFileSync(join(REPO_ROOT, "bin/cut-loop-release.sh"), "utf8");
  assert.doesNotMatch(cutter, /state\/effective-cron.*continue/u);
  assert.doesNotMatch(cutter, /u\+w.*state\/effective-cron/u);
  const launch = readFileSync(join(REPO_ROOT, "skills/agent-economy/launch.sh"), "utf8");
  assert.doesNotMatch(launch, /state\/effective-cron.*continue/u);
  assert.doesNotMatch(launch, /find "\$RELEASE" -mindepth 1 -print0/u);
  assert.doesNotMatch(launch, /\bstat -[fc]/u);
  const registry = readFileSync(join(REPO_ROOT, "lib/registry-enforce.sh"), "utf8");
  assert.match(registry, /CEO_EFFECTIVE_CRON_DIR/u);
});

test("active x402 improve/register/review writers require explicit instance state in pinned mode", () => {
  for (const name of ["store-improve.mjs", "store-ensure-register.mjs", "store-review.mjs"]) {
    const source = readFileSync(join(REPO_ROOT, "skills/earn/x402-sell", name), "utf8");
    assert.match(source, name === "store-review.mjs" ? /ANICCA_HOME/u : /resolveInstanceStateDir/u);
    assert.match(source, name === "store-review.mjs" ? /ANICCA_X402_STATE_DIR/u : /stateFilePath|resolveInstanceStateDir/u);
    assert.doesNotMatch(source, /STATE_DIR\s*=\s*join\(HERE, ['"]state['"]\)/u);
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
  const launchIndex = source.indexOf('COMPUTE_PROXY_PORT="$PORT" ANICCA_HOME="$ANICCA_HOME"');
  assert.ok(homeIndex >= 0, "start-local must derive ANICCA_HOME");
  assert.ok(launchIndex > homeIndex, "proxy must launch after ANICCA_HOME is exported");
  assert.match(source, /ANICCA_INSTANCE_WALLET_FILE="\$WALLET"/u);
});

test("release sealing is fatal and occurs before the current symlink move", () => {
  const source = readFileSync(join(REPO_ROOT, "bin/cut-loop-release.sh"), "utf8");
  assert.doesNotMatch(source, /LOOPS_NPM_BIN/u);
  assert.match(source, /TRUSTED_BIN_DIRS=\(/u);
  assert.match(source, /resolve_trusted_tool/u);
  assert.match(source, /verify_release_seal/u);
  assert.doesNotMatch(source, /chmod -R a-w [^\n]*\|\| true/u);
  assert.ok(source.indexOf("verify_release_seal") < source.indexOf("ln -sfn"));
});

// Contract-only fixture: npm ci runs against a committed local tarball, with no network; this is
// not the primary live-repository release proof.
test("contract-only: release cutter installs locked dependencies in the release and records provenance before sealing", (t) => {
  const npm = trustedTool("npm");
  const node = trustedTool("node");
  if (!npm || !node) {
    t.skip("trusted npm/node executable is unavailable");
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-deps-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
    const loops = join(root, "loops", "life-manager");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  writeFileSync(join(repo, "package.json"), JSON.stringify({
    name: "release-fixture", version: "1.0.0", type: "module", dependencies: { viem: "file:viem-1.0.0.tgz" },
  }));
  mkdirSync(join(repo, "vendor", "viem", "bin"), { recursive: true });
  writeFileSync(join(repo, "vendor", "viem", "package.json"), JSON.stringify({
    name: "viem", version: "1.0.0", type: "module", exports: "./index.mjs", bin: { "viem-cli": "bin/cli.mjs" },
  }));
  writeFileSync(join(repo, "vendor", "viem", "index.mjs"), 'export const marker = "release-viem";\n');
  writeFileSync(join(repo, "vendor", "viem", "bin", "cli.mjs"), "#!/usr/bin/env node\n");
  const packed = spawnSync(npm, ["pack", "./vendor/viem", "--pack-destination", repo], {
    cwd: repo, encoding: "utf8",
  });
  assert.equal(packed.status, 0, `${packed.stdout}\n${packed.stderr}`);
  const lock = spawnSync(npm, ["install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--offline"], {
    cwd: repo, encoding: "utf8",
  });
  assert.equal(lock.status, 0, `${lock.stdout}\n${lock.stderr}`);
  mkdirSync(join(repo, "runtime", "compute-proxy"), { recursive: true });
  writeFileSync(join(repo, "runtime", "compute-proxy", "viem-probe.mjs"), 'import { marker } from "viem";\nconsole.log(marker);\n');
  for (const [relative, body] of [["test/collision.txt", "test\n"], ["test-support/collision.txt", "support\n"]]) {
    const absolute = join(repo, relative);
    mkdirSync(join(absolute, ".."), { recursive: true });
    writeFileSync(absolute, body);
  }
  mkdirSync(join(repo, "loops", "agent-economy"), { recursive: true });
  writeFileSync(join(repo, "loops", "agent-economy", "loop.toml"), [
    'name = "agent-economy"',
    'state_dir = "~/loops/agent-economy"',
    'release_root = "~/loops/life-manager"',
    '[env]',
    'ANICCA_REPO = "~/loops/life-manager/current"',
    'ANICCA_HOME = "~/loops/agent-economy"',
    '[jobs.daemon]',
    'program = "skills/agent-economy/launch.sh"',
    'label = "ai.anicca.agent-economy-loop"',
    'keep_alive = true',
    'run_at_load = true',
  ].join("\n") + "\n");
  mkdirSync(join(repo, "skills", "agent-economy"), { recursive: true });
  writeFileSync(join(repo, "skills", "agent-economy", "launch.sh"), "#!/bin/bash\nexit 0\n");

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
      },
    });
    assert.equal(cut.status, 0, `${cut.stdout}\n${cut.stderr}`);
    const release = readFileSync(join(loops, "current", "RELEASE.json"), "utf8");
    const metadata = JSON.parse(release);
    const releaseRoot = readlinkSync(join(loops, "current"));
    assert.equal(metadata.release_root, loops);
    assert.equal(metadata.release_id, releaseRoot.split("/").at(-1));
    assert.equal(readlinkSync(join(loops, "current")), releaseRoot);
    assert.equal(metadata.lockfile_sha256, sha256File(join(releaseRoot, "package-lock.json")));
    assert.equal(metadata.dependency_manifest_sha256, sha256File(join(releaseRoot, "package.json")));
    assert.equal(metadata.dependency_sha256, dependencyDigest(releaseRoot));
    assert.equal(metadata.source_manifest_sha256, sha256File(join(releaseRoot, "SOURCE-MANIFEST.json")));
    const sourceManifest = JSON.parse(readFileSync(join(releaseRoot, "SOURCE-MANIFEST.json"), "utf8"));
    assert.equal(sourceManifest.entries.some((entry) => entry.path.startsWith("node_modules/")), false);
    assert.equal(sourceManifest.entries.some((entry) => entry.path === "RELEASE.json" || entry.path === "SOURCE-MANIFEST.json"), false);
    assert.deepEqual(sourceManifest.entries.map((entry) => entry.path).filter((path) => path.endsWith("/collision.txt")), [
      "test-support/collision.txt",
      "test/collision.txt",
    ]);
    assert.equal(metadata.dependency_tree_manifest_sha256, sha256File(join(releaseRoot, "DEPENDENCY-MANIFEST.tsv")));
    assert.match(readFileSync(join(releaseRoot, "DEPENDENCY-MANIFEST.tsv"), "utf8"), /node_modules\/viem/u);
    assert.match(metadata.runtime_versions.npm, /^\d+(?:\.\d+){2}/u);
    assert.match(metadata.runtime_versions.node, /^v\d+/u);
    assertSealedRelease(releaseRoot);
    assert.equal(existsSync(join(repo, "node_modules")), false, "fixture source has no dependency install");
    const binLink = join(releaseRoot, "node_modules", ".bin", "viem-cli");
    assert.equal(lstatSync(binLink).isSymbolicLink(), true, "npm must create an internal .bin symlink");
    assert.match(readlinkSync(binLink), /\.\.\/viem\//u);
    const probe = spawnSync(node, [join(releaseRoot, "runtime", "compute-proxy", "viem-probe.mjs")], {
      encoding: "utf8",
      cwd: repo,
    });
    assert.equal(probe.status, 0, probe.stderr);
    assert.equal(probe.stdout.trim(), "release-viem");

    const dependencyFile = join(releaseRoot, "node_modules", "viem", "index.mjs");
    chmodSync(dependencyFile, 0o644);
    writeFileSync(dependencyFile, 'export const marker = "tampered";\n');
    chmodSync(dependencyFile, 0o444);
    const dependencyCheck = spawnSync("python3", [
      join(REPO_ROOT, "bin", "plistgen.py"), "--loops-dir", join(releaseRoot, "loops"),
      "--out-dir", join(root, "plist-dependency-mismatch"), "--home", root,
      "--only", "agent-economy",
    ], { cwd: REPO_ROOT, encoding: "utf8" });
    assert.notEqual(dependencyCheck.status, 0);
    assert.match(`${dependencyCheck.stdout}\n${dependencyCheck.stderr}`, /dependenc/i);

    const firstCurrent = readlinkSync(join(loops, "current"));
    rmSync(join(loops, "current"), { force: true });
    const failedCut = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], {
      cwd: repo,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: root,
        LOOPS_ROOT: loops,
        LOOPS_TEST_FAIL_POST_CURRENT_READBACK: "1",
      },
    });
    assert.notEqual(failedCut.status, 0);
    assert.equal(existsSync(join(loops, "current")), false);
    assert.equal(existsSync(join(loops, "previous")), false);
    symlinkSync(firstCurrent, join(loops, "current"));

    writeFileSync(join(repo, "release-marker.txt"), "second\n");
    assert.equal(git("add", "release-marker.txt").status, 0);
    assert.equal(git("commit", "-qm", "second fixture").status, 0);
    assert.equal(git("push", "-q", "origin", "HEAD:main").status, 0);
    const cutSecond = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], {
      cwd: repo,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: root,
        LOOPS_ROOT: loops,
        LOOPS_KEEP_RELEASES: "1",
      },
    });
    assert.equal(cutSecond.status, 0, `${cutSecond.stdout}\n${cutSecond.stderr}`);
    const secondCurrent = readlinkSync(join(loops, "current"));
    const previous = readlinkSync(join(loops, "previous"));
    assert.notEqual(secondCurrent, previous);
    assert.equal(previous, releaseRoot);
    const failedCurrentSwap = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops, LOOPS_TEST_FAIL_CURRENT_SWAP: "1" },
    });
    assert.notEqual(failedCurrentSwap.status, 0);
    assert.equal(readlinkSync(join(loops, "current")), secondCurrent);
    assert.equal(readlinkSync(join(loops, "previous")), previous);
    const failedPreviousSwap = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops, LOOPS_TEST_FAIL_ROLLBACK_PREVIOUS_SWAP: "1" },
    });
    assert.notEqual(failedPreviousSwap.status, 0);
    assert.equal(readlinkSync(join(loops, "current")), secondCurrent);
    assert.equal(readlinkSync(join(loops, "previous")), previous);
    const failedRollback = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops, LOOPS_TEST_FAIL_ROLLBACK_READBACK: "1" },
    });
    assert.notEqual(failedRollback.status, 0);
    assert.equal(readlinkSync(join(loops, "current")), secondCurrent);
    assert.equal(readlinkSync(join(loops, "previous")), previous);
    const rollback = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops },
    });
    assert.equal(rollback.status, 0, `${rollback.stdout}\n${rollback.stderr}`);
    assert.equal(readlinkSync(join(loops, "current")), releaseRoot);
    assert.equal(readlinkSync(join(loops, "previous")), secondCurrent);
    const rollbackAgain = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops },
    });
    assert.equal(rollbackAgain.status, 0, `${rollbackAgain.stdout}\n${rollbackAgain.stderr}`);
    assert.equal(readlinkSync(join(loops, "current")), secondCurrent);
    assert.equal(readlinkSync(join(loops, "previous")), releaseRoot);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("release rollback rejects an invalid previous target without moving current", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-invalid-previous-"));
  const repo = join(root, "repo");
  const loops = join(root, "loops", "life-manager");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  try {
    mkdirSync(join(loops, "releases", "20260827T000000-a1a1a1a1"), { recursive: true });
    const release = join(loops, "releases", "20260827T000000-a1a1a1a1");
    writeFileSync(join(release, "RELEASE.json"), JSON.stringify({
      sha: "a1".repeat(20), git_commit: "a1".repeat(20), release_id: "20260827T000000-a1a1a1a1",
      release_root: loops, namespace: "life-manager",
    }) + "\n");
    chmodSync(release, 0o555);
    chmodSync(join(release, "RELEASE.json"), 0o444);
    symlinkSync(release, join(loops, "current"));
    symlinkSync(join(root, "outside"), join(loops, "previous"));
    const rollback = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "--rollback"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, HOME: root, LOOPS_ROOT: loops },
    });
    assert.notEqual(rollback.status, 0);
    assert.equal(readlinkSync(join(loops, "current")), release);
    assert.equal(readlinkSync(join(loops, "previous")), join(root, "outside"));
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

// Contract-only failure fixture: the malformed lock is rejected before an unsealed release can move
// current. The success fixture above exercises npm's real internal .bin symlink and import.
test("contract-only: release cutter rejects a malformed lock before current moves", () => {
  const root = mkdtempSync(join(tmpdir(), "agent-economy-release-lock-"));
  const repo = join(root, "repo");
  const remote = join(root, "remote.git");
  const loops = join(root, "loops");
  mkdirSync(join(repo, "bin"), { recursive: true });
  cpSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), join(repo, "bin", "cut-loop-release.sh"));
  writeFileSync(join(repo, "package.json"), JSON.stringify({
    name: "release-lock-fixture", version: "1.0.0", dependencies: { "missing-package": "1.0.0" },
  }));
  writeFileSync(join(repo, "package-lock.json"), JSON.stringify({
    name: "release-lock-fixture", version: "1.0.0", lockfileVersion: 3, requires: true, packages: { "": { name: "release-lock-fixture", version: "1.0.0" } },
  }));
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
      cwd: repo, encoding: "utf8", env: { ...process.env, HOME: root, LOOPS_ROOT: loops },
    });
    assert.notEqual(cut.status, 0);
    assert.match(cut.stderr, /lockfile-fixed dependency install failed|package\.json and package-lock\.json.*sync|Missing/u);
    assert.equal(existsSync(join(loops, "current")), false);
  } finally {
    spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
    rmSync(root, { recursive: true, force: true });
  }
});

test("release cutter reuses only a fully verified current dependency tree before falling back to npm ci", (t) => {
  const npm = trustedTool("npm");
  const node = trustedTool("node");
  if (!npm || !node || process.platform !== "darwin") {
    t.skip("Darwin trusted npm/node executable is unavailable");
    return;
  }

  const runCase = (kind) => {
    const root = mkdtempSync(join(tmpdir(), `agent-economy-reuse-${kind}-`));
    const repo = join(root, "repo");
    const remote = join(root, "remote.git");
    const loops = join(root, "loops", "life-manager");
    const tools = join(root, "trusted-tools");
    const marker = join(root, "npm-shim-called");
    mkdirSync(join(repo, "bin"), { recursive: true });
    mkdirSync(tools, { recursive: true });
    symlinkSync(node, join(tools, "node"));
    symlinkSync(npm, join(tools, "npm"));
    const cutter = readFileSync(join(REPO_ROOT, "bin", "cut-loop-release.sh"), "utf8");
    const trusted = "TRUSTED_BIN_DIRS=(/opt/homebrew/bin /usr/local/bin /usr/bin /bin /usr/sbin /sbin)";
    assert.ok(cutter.includes(trusted), "fixture must retain the production trusted-tool contract");
    writeFileSync(join(repo, "bin", "cut-loop-release.sh"), cutter.replace(trusted, `TRUSTED_BIN_DIRS=(${tools})`));
    writeFileSync(join(repo, "package.json"), JSON.stringify({
      name: `reuse-${kind}`, version: "1.0.0", dependencies: { "reuse-dependency": "file:reuse-dependency-1.0.0.tgz" },
    }));
    mkdirSync(join(repo, "vendor", "reuse-dependency"), { recursive: true });
    writeFileSync(join(repo, "vendor", "reuse-dependency", "package.json"), JSON.stringify({ name: "reuse-dependency", version: "1.0.0" }));
    writeFileSync(join(repo, "vendor", "reuse-dependency", "index.js"), "module.exports = 'original';\n");
    const packed = spawnSync(npm, ["pack", "./vendor/reuse-dependency", "--pack-destination", repo], { cwd: repo, encoding: "utf8" });
    assert.equal(packed.status, 0, `${packed.stdout}\n${packed.stderr}`);
    const locked = spawnSync(npm, ["install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--offline"], { cwd: repo, encoding: "utf8" });
    assert.equal(locked.status, 0, `${locked.stdout}\n${locked.stderr}`);
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
      const env = { ...process.env, HOME: root, LOOPS_ROOT: loops, LOOPS_KEEP_RELEASES: "10", LOOPS_NPM_SHIM_MARKER: marker };
      const initial = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], { cwd: repo, encoding: "utf8", env });
      assert.equal(initial.status, 0, `${initial.stdout}\n${initial.stderr}`);
      const current = readlinkSync(join(loops, "current"));
      writeFileSync(join(repo, "release-marker.txt"), "same dependency lock\n");
      assert.equal(git("add", "release-marker.txt").status, 0);
      assert.equal(git("commit", "-qm", "new source with same dependency lock").status, 0);
      assert.equal(git("push", "-q", "origin", "HEAD:main").status, 0);
      rmSync(join(tools, "npm"));
      writeFileSync(join(tools, "npm"), `#!/bin/bash
if [ "$1" = "--version" ]; then exec "${npm}" "$@"; fi
printf 'called\\n' > "$LOOPS_NPM_SHIM_MARKER"
exit 97
`);
      chmodSync(join(tools, "npm"), 0o755);

      if (kind === "lock-mismatch") {
        writeFileSync(join(repo, "package-lock.json"), `${readFileSync(join(repo, "package-lock.json"), "utf8").trimEnd()}\n\n`);
        assert.equal(git("add", "package-lock.json").status, 0);
        assert.equal(git("commit", "-qm", "lock differs").status, 0);
        assert.equal(git("push", "-q", "origin", "HEAD:main").status, 0);
      } else if (kind === "package-manifest-mismatch") {
        writeFileSync(join(repo, "package.json"), `${readFileSync(join(repo, "package.json"), "utf8").trimEnd()}\n\n`);
        assert.equal(git("add", "package.json").status, 0);
        assert.equal(git("commit", "-qm", "package manifest differs").status, 0);
        assert.equal(git("push", "-q", "origin", "HEAD:main").status, 0);
      } else if (kind === "mutated-dependency") {
        const dependencyDir = join(current, "node_modules", "reuse-dependency");
        const dependency = join(dependencyDir, "index.js");
        chmodSync(dependencyDir, 0o755);
        chmodSync(dependency, 0o644);
        writeFileSync(dependency, "module.exports = 'tampered';\n");
        chmodSync(dependency, 0o444);
        chmodSync(dependencyDir, 0o555);
      } else if (kind === "invalid-manifest") {
        const manifest = join(current, "DEPENDENCY-MANIFEST.tsv");
        chmodSync(current, 0o755);
        chmodSync(manifest, 0o644);
        writeFileSync(manifest, "invalid\n");
        chmodSync(manifest, 0o444);
        chmodSync(current, 0o555);
      }

      const cut = spawnSync("bash", [join(repo, "bin", "cut-loop-release.sh"), "HEAD"], { cwd: repo, encoding: "utf8", env });
      if (kind === "identical") {
        assert.equal(cut.status, 0, `${cut.stdout}\n${cut.stderr}`);
        assert.equal(existsSync(marker), false, "verified clone must avoid the failing npm shim");
      } else {
        assert.notEqual(cut.status, 0, `${cut.stdout}\n${cut.stderr}`);
        assert.equal(existsSync(marker), true, `${kind} must fall back to npm ci`);
        assert.equal(readlinkSync(join(loops, "current")), current, `${kind} must not move current`);
      }
    } finally {
      spawnSync("chmod", ["-R", "u+w", root], { encoding: "utf8" });
      rmSync(root, { recursive: true, force: true });
    }
  };

  for (const kind of ["identical", "lock-mismatch", "package-manifest-mismatch", "mutated-dependency", "invalid-manifest"]) runCase(kind);
});
