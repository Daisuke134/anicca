import assert from "node:assert/strict";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GIG = join(ROOT, "skills/earn/gig");
const SHELL_PATHS = join(GIG, "scripts/gig_paths.sh");
const PYTHON_PATHS = join(GIG, "scripts/gig_paths.py");
const FORBIDDEN = [
  "profitable-claude",
  "skills/gig-work",
  "/Users/anicca",
  "$HOME/anicca",
];

function filesBelow(root) {
  const found = [];
  for (const name of readdirSync(root)) {
    if (name === "__pycache__") continue;
    const path = join(root, name);
    const stat = statSync(path);
    if (stat.isDirectory()) found.push(...filesBelow(path));
    else if (stat.isFile()) found.push(path);
  }
  return found;
}

test("Gig non-document source has no developer or retired-repository path", () => {
  const violations = [];
  for (const path of filesBelow(GIG)) {
    if (extname(path) === ".md") continue;
    const content = readFileSync(path, "utf8");
    for (const token of FORBIDDEN) {
      if (content.includes(token)) {
        violations.push(`${path.slice(ROOT.length + 1)}:${token}`);
      }
    }
  }
  assert.deepEqual(violations, []);
});

test("shell path resolver is repository-relative in an isolated HOME", () => {
  const isolatedHome = mkdtempSync(join(tmpdir(), "gig-shell-home-"));
  const result = spawnSync(
    "bash",
    [
      "-c",
      `source "$1"; printf '%s\\n' "$LIFE_MANAGER_REPO" "$LIFE_MANAGER_HOME" "$GIG_DIR" "$GIG_RUNNER_DIR" "$GIG_BROWSER_DIR" "$GIG_STATE_DIR" "$GIG_HOST_STATE_DIR" "$GIG_LOG_DIR" "$GIG_ENV_FILE"`,
      "bash",
      SHELL_PATHS,
    ],
    { encoding: "utf8", env: { ...process.env, HOME: isolatedHome } },
  );

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(result.stdout.trim().split("\n"), [
    ROOT,
    join(isolatedHome, ".local/state/life-manager"),
    GIG,
    join(ROOT, "runtime/agent-runner"),
    join(ROOT, "skills/browser"),
    join(isolatedHome, "gig"),
    join(isolatedHome, ".local/state/life-manager/state"),
    join(isolatedHome, ".local/state/life-manager/logs"),
    join(isolatedHome, ".local/state/life-manager/.env"),
  ]);
});

test("Python path resolver matches the shell contract in an isolated HOME", () => {
  const isolatedHome = mkdtempSync(join(tmpdir(), "gig-python-home-"));
  const code = [
    "import importlib.util, json, sys",
    "spec=importlib.util.spec_from_file_location('gig_paths', sys.argv[1])",
    "module=importlib.util.module_from_spec(spec)",
    "spec.loader.exec_module(module)",
    "print(json.dumps([str(module.REPO_ROOT), str(module.LIFE_MANAGER_HOME), str(module.GIG_DIR), str(module.RUNNER_DIR), str(module.BROWSER_DIR), str(module.STATE_DIR), str(module.HOST_STATE_DIR), str(module.LOG_DIR), str(module.ENV_FILE)]))",
  ].join(";");
  const result = spawnSync("python3", ["-c", code, PYTHON_PATHS], {
    encoding: "utf8",
    env: { ...process.env, HOME: isolatedHome },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), [
    ROOT,
    join(isolatedHome, ".local/state/life-manager"),
    GIG,
    join(ROOT, "runtime/agent-runner"),
    join(ROOT, "skills/browser"),
    join(isolatedHome, "gig"),
    join(isolatedHome, ".local/state/life-manager/state"),
    join(isolatedHome, ".local/state/life-manager/logs"),
    join(isolatedHome, ".local/state/life-manager/.env"),
  ]);
});

test("Life Manager earn/gig bridge consumes the installed state contract", () => {
  const source = readFileSync(join(GIG, "run.sh"), "utf8");
  assert.equal(source.includes('source "$HERE/scripts/gig_paths.sh"'), true);
  assert.equal(source.includes('"$GIG_STATE_DIR"'), true);
  assert.equal(source.includes('expanduser("~/gig")'), false);
  assert.equal(source.includes("/opt/homebrew/bin/python3"), false);
});

test("immutable worker snapshot resolves paths through its exported canonical Gig root", () => {
  const isolatedHome = mkdtempSync(join(tmpdir(), "gig-snapshot-home-"));
  const snapshotDir = join(isolatedHome, "state", "snapshots");
  const snapshot = join(snapshotDir, "gig_pass.sh");
  mkdirSync(snapshotDir, { recursive: true });
  const source = readFileSync(join(GIG, "gig_pass.sh"), "utf8");
  const prelude = source.slice(0, source.indexOf('SCHEMA="$G/schemas/'));
  writeFileSync(
    snapshot,
    `${prelude}\nprintf '%s\\n' "$G" "$RUNNER" "$B"\n`,
    "utf8",
  );
  const result = spawnSync("bash", [snapshot], {
    encoding: "utf8",
    env: {
      ...process.env,
      HOME: isolatedHome,
      GIG_DIR: GIG,
      LIFE_MANAGER_REPO: ROOT,
      GIG_RUNNER_DIR: join(ROOT, "runtime/agent-runner"),
      GIG_BROWSER_DIR: join(ROOT, "skills/browser"),
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, "");
  assert.deepEqual(result.stdout.trim().split("\n"), [
    GIG,
    join(ROOT, "runtime/agent-runner", "agent_runner.py"),
    join(ROOT, "skills/browser", "scripts"),
  ]);
});
