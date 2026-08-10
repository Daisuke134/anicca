"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const { writeLocalAgentUsageCheckpoint } = require("./cfo-local-agent-usage-checkpoint.js");
const SOURCE_ID = "life_manager_agent_usage";
const root = () => fs.mkdtempSync(path.join(os.tmpdir(), "cfo-local-agent-checkpoint-"));
const state = (discovered_rows = 1) => ({ source_id: SOURCE_ID, byte_offset: discovered_rows * 10, prefix_sha256: "1".repeat(64), discovered_rows });
const batch = (overrides = {}) => ({ events: [{ SECRET_SENTINEL: "raw-token" }], source_state: state(), mapping_id: "local_agent_usage_v1", counts: { discovered_rows: 1, accepted_rows: 1, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: 0, attributed_rows: 1, unattributed_rows: 0 }, coverage_exceptions: [], ...overrides });
const finalPath = (stateRoot) => path.join(stateRoot, "cfo", "local-agent-usage", `${SOURCE_ID}.json`);
test("atomically writes and replaces one redacted checkpoint with fixed modes", () => {
  const stateRoot = root(); const directory = path.dirname(finalPath(stateRoot)); fs.mkdirSync(directory, { recursive: true, mode: 0o755 }); fs.chmodSync(directory, 0o755);
  try {
    const first = writeLocalAgentUsageCheckpoint(stateRoot, "2026-08-10T01:02:03Z", batch());
    assert.deepEqual(first, { source_id: SOURCE_ID, byte_offset: 10, discovered_rows: 1, mapping_id: "local_agent_usage_v1" }); assert.ok(Object.isFrozen(first));
    assert.equal(fs.statSync(directory).mode & 0o777, 0o700); assert.equal(fs.statSync(finalPath(stateRoot)).mode & 0o777, 0o600);
    const firstBytes = fs.readFileSync(finalPath(stateRoot)); const stored = JSON.parse(firstBytes); assert.deepEqual(Object.keys(stored), ["schema_version", "collected_at", "mapping_id", "source_state", "counts", "coverage_exceptions"]); assert.equal(stored.schema_version, 1); assert.doesNotMatch(firstBytes.toString(), /SECRET_SENTINEL|raw-token|events|stateRoot|token/i);
    const second = writeLocalAgentUsageCheckpoint(stateRoot, "2026-08-10T01:03:03Z", batch({ events: [{}, {}], source_state: state(2), counts: { ...batch().counts, discovered_rows: 2, accepted_rows: 2, attributed_rows: 2 } }));
    assert.equal(second.byte_offset, 20); assert.notDeepEqual(fs.readFileSync(finalPath(stateRoot)), firstBytes); assert.deepEqual(fs.readdirSync(directory), [`${SOURCE_ID}.json`]);
  } finally { fs.rmSync(stateRoot, { recursive: true, force: true }); }
});
test("rolls back on fsync failure and rejects invalid state before mkdir", () => {
  const stateRoot = root();
  try {
    writeLocalAgentUsageCheckpoint(stateRoot, "2026-08-10T01:02:03Z", batch()); const before = fs.readFileSync(finalPath(stateRoot));
    assert.throws(() => writeLocalAgentUsageCheckpoint(stateRoot, "2026-08-10T01:04:03Z", batch(), { fsyncImpl: () => { throw new Error("SECRET"); } }), /^Error: cfo_local_agent_checkpoint_invalid:write_failed$/);
    assert.deepEqual(fs.readFileSync(finalPath(stateRoot)), before); assert.deepEqual(fs.readdirSync(path.dirname(finalPath(stateRoot))), [`${SOURCE_ID}.json`]); assert.throws(() => writeLocalAgentUsageCheckpoint(stateRoot, "2026-08-10T01:05:03Z", batch({ coverage_exceptions: ["source_rewritten"], events: [{ raw: "x" }] })), /^Error: cfo_local_agent_checkpoint_invalid:invalid_batch$/); assert.deepEqual(fs.readFileSync(finalPath(stateRoot)), before);
  } finally { fs.rmSync(stateRoot, { recursive: true, force: true }); }
  for (const [args, reason] of [
    [["relative", "2026-08-10T01:02:03Z", batch()], "invalid_state_root"], [[path.parse(stateRoot).root, "2026-08-10T01:02:03Z", batch()], "invalid_state_root"],
    [[stateRoot, "bad-date", batch()], "invalid_collected_at"],
    [[stateRoot, "2026-08-10T01:02:03Z", batch({ mapping_id: "bad" })], "invalid_batch"],
    [[stateRoot, "2026-08-10T01:02:03Z", batch({ coverage_exceptions: ["source_rewritten"], events: [{ raw: "x" }] })], "invalid_batch"],
    [[stateRoot, "2026-08-10T01:02:03Z", batch(), { extra: true }], "invalid_options"],
  ]) {
    assert.throws(() => writeLocalAgentUsageCheckpoint(...args), new RegExp(`^Error: cfo_local_agent_checkpoint_invalid:${reason}$`)); assert.equal(fs.existsSync(path.join(stateRoot, "cfo")), false);
  }
});
