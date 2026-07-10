// VCSDD RED->GREEN: SOL pre-gate trace recording (franklin-sol-evolvable-edge, REQ-011/012).
// Fail-soft: a trace-file write failure must never crash the calling pass.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { appendGateTrace, appendGenomeLinkTrace } from "../sol-trace.mjs";
import { SAFE_DEFAULT_GENOME, genomeId } from "../sol-genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function readJsonl(filePath) {
  return fs
    .readFileSync(filePath, "utf8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

// --- PROP-011 --------------------------------------------------------------------------------
test("PROP-011: appendGateTrace writes exactly one line with all required fields", () => {
  const dir = tmpDir("sol-trace-gate-");
  const tracePath = path.join(dir, "sol-gate.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  const id = genomeId(genome);
  appendGateTrace(tracePath, {
    genome_id: id,
    genome,
    mode: "paper",
    decision: "skip",
    wouldEngage: false,
    conviction: 3,
    momentumPct: 1,
    liquidityUsd: 500000,
    mint: "So1111",
  });
  const lines = readJsonl(tracePath);
  assert.equal(lines.length, 1);
  const line = lines[0];
  for (const field of [
    "ts",
    "genome_id",
    "genome",
    "mode",
    "decision",
    "wouldEngage",
    "conviction",
    "momentumPct",
    "liquidityUsd",
    "mint",
  ]) {
    assert.ok(field in line, `missing field ${field}`);
  }
  assert.equal(line.genome_id, id);
  assert.deepEqual(line.genome, genome);
  assert.ok(line.mode === "paper" || line.mode === "live");
  assert.ok(line.decision === "engage" || line.decision === "skip");
});

test("PROP-011: every pass (paper+skip, live+engage) produces exactly one gate trace line", () => {
  const dir = tmpDir("sol-trace-gate-multi-");
  const tracePath = path.join(dir, "sol-gate.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  appendGateTrace(tracePath, {
    genome_id: genomeId(genome),
    genome,
    mode: "paper",
    decision: "skip",
    wouldEngage: false,
    conviction: 0,
    momentumPct: 0,
    liquidityUsd: 0,
    mint: "M1",
  });
  appendGateTrace(tracePath, {
    genome_id: genomeId(genome),
    genome,
    mode: "live",
    decision: "engage",
    wouldEngage: true,
    conviction: 8,
    momentumPct: 3,
    liquidityUsd: 2000000,
    mint: "M1",
  });
  assert.equal(readJsonl(tracePath).length, 2);
});

test("PROP-011 edge case: no-market-data pass records decision:skip reason:no-signal", () => {
  const dir = tmpDir("sol-trace-nosignal-");
  const tracePath = path.join(dir, "sol-gate.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  appendGateTrace(tracePath, {
    genome_id: genomeId(genome),
    genome,
    mode: "paper",
    decision: "skip",
    reason: "no-signal",
    wouldEngage: false,
    conviction: 0,
    momentumPct: null,
    liquidityUsd: null,
    mint: "M1",
  });
  const line = readJsonl(tracePath)[0];
  assert.equal(line.decision, "skip");
  assert.equal(line.reason, "no-signal");
});

test("PROP-011 edge case: trace-file write failure never throws (fail-soft)", () => {
  const dir = tmpDir("sol-trace-failsoft-");
  const notADir = path.join(dir, "not-a-dir-but-a-file");
  fs.writeFileSync(notADir, "x");
  const tracePath = path.join(notADir, "sol-gate.trace.jsonl"); // parent path segment is a FILE
  assert.doesNotThrow(() => {
    appendGateTrace(tracePath, {
      genome_id: "abc",
      genome: SAFE_DEFAULT_GENOME,
      mode: "paper",
      decision: "skip",
      wouldEngage: false,
      conviction: 0,
      momentumPct: 0,
      liquidityUsd: 0,
      mint: "M1",
    });
  });
});

// --- PROP-012 --------------------------------------------------------------------------------
test("PROP-012: engage===true pass's genome-link line has ts <= its later live-pass line's ts", () => {
  const dir = tmpDir("sol-trace-link-");
  const tracePath = path.join(dir, "sol-trade.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  const id = genomeId(genome);
  appendGenomeLinkTrace(tracePath, { genome_id: id, genome });
  const linkTs = readJsonl(tracePath)[0].ts;

  fs.appendFileSync(
    tracePath,
    JSON.stringify({ ts: new Date().toISOString(), slot: "earn/sol-trade", action: "live-pass", exit: 0 }) + "\n",
  );
  const lines = readJsonl(tracePath);
  const livePassLine = lines.find((l) => l.action === "live-pass");
  assert.ok(Date.parse(linkTs) <= Date.parse(livePassLine.ts));
});

test("PROP-012: genome-link line has action='genome' shape with genome_id + genome present", () => {
  const dir = tmpDir("sol-trace-link-shape-");
  const tracePath = path.join(dir, "sol-trade.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  const id = genomeId(genome);
  appendGenomeLinkTrace(tracePath, { genome_id: id, genome });
  const line = readJsonl(tracePath)[0];
  assert.equal(line.action, "genome");
  assert.equal(line.genome_id, id);
  assert.deepEqual(line.genome, genome);
});

test("PROP-012 edge case: a WAIT/no-fill pass still leaves the genome_id linkage line intact (no join yet)", () => {
  const dir = tmpDir("sol-trace-nofill-");
  const tracePath = path.join(dir, "sol-trade.trace.jsonl");
  const genome = SAFE_DEFAULT_GENOME;
  const id = genomeId(genome);
  appendGenomeLinkTrace(tracePath, { genome_id: id, genome });
  fs.appendFileSync(
    tracePath,
    JSON.stringify({ ts: new Date().toISOString(), slot: "earn/sol-trade", action: "live-pass", exit: 0, note: "WAIT" }) + "\n",
  );
  const lines = readJsonl(tracePath);
  assert.equal(lines.filter((l) => l.action === "genome").length, 1);
});

test("PROP-012 edge case: genome-link trace write failure never throws (fail-soft)", () => {
  const dir = tmpDir("sol-trace-link-failsoft-");
  const notADir = path.join(dir, "not-a-dir-but-a-file");
  fs.writeFileSync(notADir, "x");
  const tracePath = path.join(notADir, "sol-trade.trace.jsonl");
  assert.doesNotThrow(() => {
    appendGenomeLinkTrace(tracePath, { genome_id: "abc", genome: SAFE_DEFAULT_GENOME });
  });
});
