import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SCRIPTS = join(REPO_ROOT, "skills", "earn", "gig", "scripts");
const OWNERS = [
  "storefront_direct.py",
  "application_direct.py",
  "reply_detector.py",
  "paid_direct.py",
];

test("the four accepted revenue owners boot from canonical Life Manager source", () => {
  for (const owner of OWNERS) {
    const path = join(SCRIPTS, owner);
    const source = readFileSync(path, "utf8");
    assert.match(source, /gig_paths import/);
    assert.equal(source.includes("profitable-claude"), false);
    assert.equal(source.includes("skills/gig-work"), false);
    const result = spawnSync("python3", [path, "--help"], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: join(REPO_ROOT, ".test-home-not-created"),
        LIFE_MANAGER_HOME: join(REPO_ROOT, ".test-state-not-created"),
      },
      timeout: 15_000,
    });
    assert.equal(
      result.status,
      0,
      `${owner} failed to boot\nstdout=${result.stdout}\nstderr=${result.stderr}`,
    );
  }
});
