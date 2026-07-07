// anicca-agent-economy REQ-301/302 (Phase 2a, RED phase) — Tier 0 structural checks.
//
// PROP-301a/b: `evidence/business-blockrun-ai-research.md` must exist and contain all five required
// items (a)-(e) from behavioral-spec.md REQ-301, each with at least one concrete piece of cited evidence
// (not a bare unsupported assertion). This file does NOT exist yet as of this Phase 2a commit —
// EVERY assertion in the first test below is EXPECTED TO FAIL (file-not-found), which is the intended
// RED signal: this is a research DELIVERABLE Phase 2b (or a dedicated research pass) must produce, not
// something this Phase 2a test harness fabricates.
//
// PROP-302a: no code/process change in this increment may introduce a dependency (code, gate, or
// sequencing rule) from the gig-board witness track (skills/economy/gig/WITNESS-RUNBOOK.md) onto
// REQ-301's research record. As of this Phase 2a commit, no such gating condition exists yet (the
// research record isn't even referenced in the witness runbook) — this second test is EXPECTED TO PASS
// immediately (a "coverage-retrofit" case, exactly like this increment's own precedent for this PROP:
// see behavioral-spec.md's PROP-302a description, "現状で通ってしまう可能性がある"). It remains valuable
// as a REGRESSION GUARD: it will start failing the moment a future edit introduces exactly the kind of
// gating dependency REQ-302 forbids.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FEATURE_ROOT = path.resolve(__dirname, "..");
const RESEARCH_RECORD_PATH = path.join(FEATURE_ROOT, "evidence", "business-blockrun-ai-research.md");
// Resolved against the actual anicca OSS checkout location (~/anicca/skills/economy/gig/), since this
// feature's test tree lives in a different repo (anicca-project) than the gig skill itself (anicca).
const WITNESS_RUNBOOK_ABS_PATH = path.join(os.homedir(), "anicca", "skills", "economy", "gig", "WITNESS-RUNBOOK.md");

const REQUIRED_ITEMS = {
  a: /\(a\)/, // seller/listing API existence claim
  b: /\(b\)/, // fee/take-rate structure
  c: /\(c\)/, // Coinbase CDP dependency / human-zero risk check
  d: /\(d\)/, // implementation-effort estimate
  e: /\(e\)/, // explicit recommendation vs. gig board's own witness status
};

test("★PROP-301a★ the research record exists under evidence/ and contains all five required items (a)-(e)", async () => {
  let content = null;
  try {
    content = await fs.readFile(RESEARCH_RECORD_PATH, "utf8");
  } catch (err) {
    assert.fail(`research record must exist at ${RESEARCH_RECORD_PATH} -- read failed: ${err.code || err.message}`);
  }
  assert.ok(content && content.length > 0, "research record must be non-empty");
  for (const [item, pattern] of Object.entries(REQUIRED_ITEMS)) {
    assert.ok(pattern.test(content), `research record must contain a distinct, labeled section for item (${item})`);
  }
});

test("PROP-301b: each of the five items in the research record cites at least one piece of concrete evidence (a URL, file path, quoted response, or an explicit 'checked X, not found' statement), not a bare assertion", async () => {
  let content = null;
  try {
    content = await fs.readFile(RESEARCH_RECORD_PATH, "utf8");
  } catch (err) {
    assert.fail(`research record must exist at ${RESEARCH_RECORD_PATH} -- read failed: ${err.code || err.message}`);
  }
  // Lightweight structural proxy for "cites concrete evidence": at least one URL/path/code-reference
  // marker somewhere in the document (a full semantic check of EACH item's citation quality is a Phase 3
  // adversary spot-check per verification-architecture.md, not something this Tier-0 test can fully
  // automate).
  const hasUrl = /https?:\/\//.test(content);
  const hasRepoRef = /BlockRunAI\/|PR ?#\d+|github\.com/i.test(content);
  assert.ok(hasUrl || hasRepoRef, "research record must cite at least one concrete, checkable source (a URL, a GitHub repo/PR reference)");
});

test("PROP-302a: the gig-board witness runbook introduces no new gating condition referencing REQ-301's research record", async () => {
  let content = null;
  try {
    content = await fs.readFile(WITNESS_RUNBOOK_ABS_PATH, "utf8");
  } catch (err) {
    assert.fail(`witness runbook must exist at ${WITNESS_RUNBOOK_ABS_PATH} to be checked -- read failed: ${err.code || err.message}`);
  }
  const referencesResearchRecord = /business-blockrun-ai-research|REQ-301/i.test(content);
  assert.equal(
    referencesResearchRecord,
    false,
    "the gig-board witness runbook must NOT reference REQ-301's research record or gate any step on its completion -- the two tracks proceed independently"
  );
});
