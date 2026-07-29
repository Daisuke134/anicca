import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const VERIFIER = join(REPO_ROOT, "scripts", "verify-oss-self-contained.mjs");
const REQUIRED_SOURCES = [
  "life-manager",
  "anicca-products",
  "profitable-claude",
  "anicca-dais",
];

function git(root, ...args) {
  return execFileSync("git", args, {
    cwd: root,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
}

function write(root, relativePath, content = "") {
  const path = join(root, relativePath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
}

function createFixture() {
  const root = mkdtempSync(join(tmpdir(), "life-manager-oss-contract-"));
  git(root, "init", "-q");
  git(root, "config", "user.email", "fixture@example.com");
  git(root, "config", "user.name", "Fixture");
  write(root, "skills/agent-runner/agent_runner.py", "print('fixture')\n");
  write(
    root,
    "docs/manifests/oss-merge-1-sources.json",
    `${JSON.stringify({
      version: 1,
      sources: REQUIRED_SOURCES.map((id) => ({
        id,
        repository: `https://example.com/${id}.git`,
        commit: "0".repeat(40),
        disposition: id === "life-manager" ? "canonical" : "inspected",
      })),
    }, null, 2)}\n`,
  );
  write(root, "apps/life-manager/index.js", "export const portable = true;\n");
  write(root, "runtime/README.md", "Runtime source only.\n");
  git(root, "add", ".");
  git(root, "commit", "-qm", "fixture");
  return root;
}

function verify(root) {
  const result = spawnSync(process.execPath, [VERIFIER, "--root", root, "--json"], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  let payload = { ok: false, violations: [] };
  try {
    payload = JSON.parse(result.stdout);
  } catch {
    // The assertion below reports stderr/stdout without hiding the real failure.
  }
  return { ...result, payload };
}

test("a clean committed fixture passes the OSS self-contained contract", () => {
  const root = createFixture();
  const result = verify(root);

  assert.equal(
    result.status,
    0,
    `verifier failed\nstdout=${result.stdout}\nstderr=${result.stderr}`,
  );
  assert.deepEqual(result.payload, { ok: true, violations: [] });
});

test("gitlinks and symlinks escaping the checkout fail with closed codes", () => {
  const root = createFixture();
  const head = git(root, "rev-parse", "HEAD");
  git(root, "update-index", "--add", "--cacheinfo", `160000,${head},vendor/gitlink`);
  symlinkSync("../../outside", join(root, "skills", "escape"));
  git(root, "add", "skills/escape");

  const result = verify(root);

  assert.equal(result.status, 1);
  assert.deepEqual(
    result.payload.violations.map(({ code, path }) => [code, path]),
    [
      ["symlink_escape", "skills/escape"],
      ["gitlink", "vendor/gitlink"],
    ],
  );
});

test("active local-source paths and generated runtime copies fail without echoing contents", () => {
  const root = createFixture();
  const privateLiteral = "/Users/example/private-source-with-token-shaped-value";
  write(root, "apps/life-manager/private.js", `export const source = "${privateLiteral}";\n`);
  write(
    root,
    "apps/life-manager/legacy.js",
    'export const source = "$HOME/anicca/skills/legacy-runner.js";\n',
  );
  write(
    root,
    "apps/life-manager/fixed.js",
    'export const source = "/opt/life-manager/skills/fixed-runner.js";\n',
  );
  write(
    root,
    "runtime/wrapped.sh",
    'REPO="${LIFE_MANAGER_REPO:-$HOME/anicca}"\n',
  );
  write(
    root,
    "runtime/fixed-env.sh",
    'REPO="${LIFE_MANAGER_REPO:-/opt/life-manager}"\n',
  );
  write(root, "apps/life-manager/state/session.json", '{"runtime":true}\n');
  git(root, "add", ".");

  const result = verify(root);

  assert.equal(result.status, 1);
  assert.deepEqual(
    result.payload.violations.map(({ code, path }) => [code, path]),
    [
      ["forbidden_source_root", "apps/life-manager/fixed.js"],
      ["forbidden_source_root", "apps/life-manager/legacy.js"],
      ["forbidden_source_root", "apps/life-manager/private.js"],
      ["runtime_copy", "apps/life-manager/state/session.json"],
      ["forbidden_source_root", "runtime/fixed-env.sh"],
      ["forbidden_source_root", "runtime/wrapped.sh"],
    ],
  );
  assert.equal(result.stdout.includes(privateLiteral), false);
  assert.equal(result.stderr.includes(privateLiteral), false);
});

test("personal mail and messaging destinations fail closed without echoing their values", () => {
  const root = createFixture();
  const privateMail = "owner.person+alerts" + "@gmail.com";
  const privateChat = ["12345", "6789"].join("");
  write(
    root,
    "runtime/personal-defaults.sh",
    `MAIL_TO="${privateMail}"\nopenclaw message send --target ${privateChat} --message ok\n`,
  );
  git(root, "add", ".");

  const result = verify(root);

  assert.equal(result.status, 1);
  assert.deepEqual(
    result.payload.violations.map(({ code, path }) => [code, path]),
    [["personal_runtime_default", "runtime/personal-defaults.sh"]],
  );
  assert.equal(result.stdout.includes(privateMail), false);
  assert.equal(result.stderr.includes(privateMail), false);
  assert.equal(result.stdout.includes(privateChat), false);
  assert.equal(result.stderr.includes(privateChat), false);
});

test("source provenance is closed over all four inspected repositories", () => {
  const root = createFixture();
  write(
    root,
    "docs/manifests/oss-merge-1-sources.json",
    `${JSON.stringify({
      version: 1,
      sources: [{ id: "life-manager", repository: "https://example.com/life-manager.git",
        commit: "0".repeat(40), disposition: "canonical" }],
    })}\n`,
  );
  git(root, "add", ".");

  const result = verify(root);

  assert.equal(result.status, 1);
  assert.deepEqual(
    result.payload.violations.map(({ code, path }) => [code, path]),
    [
      ["manifest_source_missing", "anicca-dais"],
      ["manifest_source_missing", "anicca-products"],
      ["manifest_source_missing", "profitable-claude"],
    ],
  );
});

test("declared third-party runtime adapters may document their own runtime home", () => {
  const root = createFixture();
  write(
    root,
    "skills/capafy-autopublish/vendor/runtime-adapter.py",
    'OPENCLAW_HOME = "~/.openclaw"\n',
  );
  git(root, "add", ".");

  const result = verify(root);

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(result.payload, { ok: true, violations: [] });
});
