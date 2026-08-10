"use strict";
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("node:fs"), os = require("node:os"), path = require("node:path"), crypto = require("node:crypto");
const { readLocalAgentUsageChain } = require("./cfo-local-agent-usage-chain.js"), { collectAndWriteLocalAgentUsageBatch } = require("./cfo-local-agent-usage-batch-store.js");
const source = "life_manager_agent_usage", at = "2026-08-10T01:02:03Z";
const row = (event_id, extra = {}) => ({ version: 1, event_id, timestamp: at, loop: "gig", task_label: "gig-daily", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 }, ...extra });
const lines = (...rows) => Buffer.from(`${rows.map(JSON.stringify).join("\n")}\n`), hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const files = dir => fs.readdirSync(dir).filter(name => name.endsWith(".json")), readRecord = (dir, name) => JSON.parse(fs.readFileSync(path.join(dir, name)));
function writeManual(dir, value, name = hash(Buffer.from(JSON.stringify(value)))) { const bytes = Buffer.from(JSON.stringify(value)); fs.writeFileSync(path.join(dir, `${name}.json`), bytes, { mode: 0o600 }); }
function chainFixture() {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-chain-")), root = path.join(parent, "state"), dir = path.join(root, "cfo/local-agent-usage", source), firstBytes = lines(row("a".repeat(24)));
  const first = collectAndWriteLocalAgentUsageBatch(root, at, source, firstBytes, null), firstRecord = readRecord(dir, `${first.record_id}.json`); collectAndWriteLocalAgentUsageBatch(root, "2026-08-10T01:03:03Z", source, firstBytes, null); const current = firstRecord.source_state;
  collectAndWriteLocalAgentUsageBatch(root, "2026-08-10T01:04:03Z", source, firstBytes, current); const childBytes = Buffer.concat([firstBytes, lines(row("a".repeat(24), { loop: "connector", task_label: "connector-send", measurement: "unavailable", tokens: { input: null, cached_input: null, cache_creation_input: null, output: null, reasoning_output: null, total: null } }))]), child = collectAndWriteLocalAgentUsageBatch(root, "2026-08-10T01:04:03Z", source, childBytes, current);
  const childRecord = readRecord(dir, `${child.record_id}.json`), clean = collectAndWriteLocalAgentUsageBatch(root, "2026-08-10T01:05:03Z", source, childBytes, childRecord.source_state); collectAndWriteLocalAgentUsageBatch(root, "2026-08-10T01:07:03Z", source, childBytes, childRecord.source_state); const defect = { ...readRecord(dir, `${clean.record_id}.json`), collected_at: "2026-08-10T01:06:03Z", coverage_exceptions: ["source_rewritten"] }, defectBytes = Buffer.from(JSON.stringify(defect)); fs.writeFileSync(path.join(dir, `${hash(defectBytes)}.json`), defectBytes, { mode: 0o600 }); fs.writeFileSync(path.join(dir, ".orphan.tmp"), "ignored"); return { parent, root, dir, firstRecord, childRecord };
}
test("follows one causal chain and recomputes exact cumulative evidence", () => {
  const f = chainFixture();
  try {
    const before = files(f.dir).sort(), got = readLocalAgentUsageChain(f.root, source);
    assert.equal(got.status, "ready"); assert.equal(got.record_count, 5); assert.deepEqual(got.source_state, f.childRecord.source_state);
    assert.deepEqual(got.events.map(event => event.source_event_id), [...got.events].sort((a, b) => a.source_event_id.localeCompare(b.source_event_id)).map(event => event.source_event_id));
    assert.deepEqual(Object.keys(got.events[0]).sort(), ["schema_version", "source_ledger", "source_event_id", "runner_event_id", "occurred_at", "provider", "provider_name", "request_model", "upstream_model", "run", "financial_unit_id", "attribution_status", "measurement", "token_value_basis", "tokens", "coverage_status"].sort());
    assert.deepEqual(Object.keys(got.events[0].run).sort(), ["attempt", "loop", "status", "task_label"]); assert.deepEqual(Object.keys(got.events[0].tokens).sort(), ["cache_creation_input", "cached_input", "input", "output", "reasoning_output", "total"]);
    assert.deepEqual(got.counts, { discovered_rows: 2, accepted_rows: 2, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 1, runner_collision_groups: 1, attributed_rows: 1, unattributed_rows: 1 });
    assert.deepEqual(got.coverage_exceptions, ["missing_usage", "runner_identity_collision", "source_rewritten", "unattributed_usage"]); assert.deepEqual(fs.readdirSync(f.dir).sort(), [...before, ".orphan.tmp"].sort()); assert.ok(Object.isFrozen(got) && Object.isFrozen(got.events[0]));
  } finally { fs.rmSync(f.parent, { recursive: true, force: true }); }
});
test("missing source is the exact frozen empty result", () => {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-chain-")), root = path.join(parent, "state");
  try { const expected = { status: "empty", source_state: null, record_count: 0, events: [], counts: { discovered_rows: 0, accepted_rows: 0, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: 0, attributed_rows: 0, unattributed_rows: 0 }, coverage_exceptions: [] }, result = readLocalAgentUsageChain(root, source); assert.deepEqual(result, expected); assert.ok(Object.isFrozen(result)); const dir = path.join(root, "cfo/local-agent-usage", source); fs.mkdirSync(dir, { recursive: true }); fs.writeFileSync(path.join(dir, ".only.tmp"), "ignored"); const tempOnly = readLocalAgentUsageChain(root, source); assert.deepEqual(tempOnly, expected); assert.ok(Object.isFrozen(tempOnly)); } finally { fs.rmSync(parent, { recursive: true, force: true }); }
});
test("all malformed storage failures are fixed and redacted", () => {
  const cases = ["unknown non-temp entry", "bad hash", "bad schema", "bad count algebra", "broken prior", "fork", "symlink", "mode", "final directory", "directory read failure", "wrong attribution", "impossible defect", "missing derived", "extra derived", "canonical mismatch", "repeated event identical", "repeated event changed", "extra prompt"]; for (const name of cases) {
    const f = chainFixture(), base = f.firstRecord, child = f.childRecord;
    try { for (const file of files(f.dir)) fs.unlinkSync(path.join(f.dir, file));
      if (name === "unknown non-temp entry") fs.writeFileSync(path.join(f.dir, "HOSTILE_SECRET"), "x");
      else if (name === "bad hash") writeManual(f.dir, base, "0".repeat(64));
      else if (name === "bad schema") writeManual(f.dir, { ...base, schema_version: 2 });
      else if (name === "bad count algebra") writeManual(f.dir, { ...base, delta_counts: { ...base.delta_counts, discovered_rows: 99 } });
      else if (name === "broken prior") writeManual(f.dir, { ...base, prior_source_state: { ...base.source_state, byte_offset: 0 } });
      else if (name === "fork") { writeManual(f.dir, base); writeManual(f.dir, { ...base, collected_at: "2026-08-10T01:05:03Z", source_state: { ...base.source_state, byte_offset: base.source_state.byte_offset + 1, observed_file_size: base.source_state.observed_file_size + 1 } }); }
      else if (name === "symlink") { const bytes = Buffer.from(JSON.stringify(base)), target = path.join(f.parent, "target"); fs.writeFileSync(target, bytes); fs.symlinkSync(target, path.join(f.dir, `${hash(bytes)}.json`)); } else if (name === "mode") { writeManual(f.dir, base); fs.chmodSync(path.join(f.dir, `${hash(Buffer.from(JSON.stringify(base)))}.json`), 0o644); }
      else if (name === "final directory") { const bytes = Buffer.from(JSON.stringify(base)); fs.mkdirSync(path.join(f.dir, `${hash(bytes)}.json`)); } else if (name === "directory read failure") { fs.rmSync(f.dir, { recursive: true }); fs.writeFileSync(f.dir, "x"); }
      else { const event = name === "extra prompt" ? { ...base.events[0], prompt: "HOSTILE_SECRET" } : name === "wrong attribution" ? { ...base.events[0], financial_unit_id: "evil_unit" } : name === "impossible defect" ? base.events[0] : name === "missing derived" ? base.events[0] : name === "extra derived" ? base.events[0] : name === "canonical mismatch" ? { ...base.events[0], coverage_status: "missing_usage" } : name === "repeated event changed" ? { ...base.events[0], provider: "evil" } : base.events[0]; if (name === "impossible defect") writeManual(f.dir, { ...base, coverage_exceptions: ["source_rewritten"] }); else if (name === "extra derived") writeManual(f.dir, { ...base, coverage_exceptions: ["missing_usage"] }); else if (name === "missing derived") writeManual(f.dir, { ...child, coverage_exceptions: [] }); else { writeManual(f.dir, base); writeManual(f.dir, { ...child, events: [event], delta_counts: { ...child.delta_counts, accepted_rows: 1, discovered_rows: 1, missing_usage_rows: 0, attributed_rows: 1, unattributed_rows: 0, runner_collision_groups: 0 }, coverage_exceptions: [] }); } }
      assert.throws(() => readLocalAgentUsageChain(f.root, source), error => error.message === "cfo_local_agent_usage_chain_invalid:read_failed" && !error.message.includes("HOSTILE_SECRET"));
    } finally { fs.rmSync(f.parent, { recursive: true, force: true }); } }
});
test("rejects invalid arguments without leaking sentinels", () => { assert.throws(() => readLocalAgentUsageChain("relative", source), /^Error: cfo_local_agent_usage_chain_invalid:invalid_state_root$/); assert.throws(() => readLocalAgentUsageChain("/tmp/x", "bad"), /^Error: cfo_local_agent_usage_chain_invalid:invalid_source$/); });
