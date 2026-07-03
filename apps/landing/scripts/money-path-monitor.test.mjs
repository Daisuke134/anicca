// money-path-monitor.test.mjs — FIND-103: a corrupt persisted-state file must NOT crash the monitor.
import { test } from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, rmSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadController } from "./money-path-monitor.mjs";

test("loadController: corrupt JSON state → fresh controller, no throw", () => {
  const dir = mkdtempSync(join(tmpdir(), "mon-"));
  const p = join(dir, "state.json");
  writeFileSync(p, "{ this is not json ");
  const rc = loadController(p); // must not throw
  assert.equal(rc.consecutiveFail, 0);
  assert.equal(rc.incidentOpen, false);
  assert.equal(rc.rollbackFired, false);
  rmSync(dir, { recursive: true, force: true });
});

test("loadController: valid state is restored", () => {
  const dir = mkdtempSync(join(tmpdir(), "mon-"));
  const p = join(dir, "state.json");
  writeFileSync(p, JSON.stringify({ consecutiveFail: 1, incidentOpen: true, rollbackFired: false }));
  const rc = loadController(p);
  assert.equal(rc.consecutiveFail, 1);
  assert.equal(rc.incidentOpen, true);
  rmSync(dir, { recursive: true, force: true });
});

test("loadController: missing file → fresh controller", () => {
  const rc = loadController("/nonexistent/xyz/state.json");
  assert.equal(rc.consecutiveFail, 0);
});
