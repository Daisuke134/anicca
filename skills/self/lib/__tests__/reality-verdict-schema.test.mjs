// VCSDD Phase 2a (RED): pure-core unit tests for reality-verdict-schema.mjs.
// Spec: .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-005/REQ-006/REQ-008.
// These must FAIL until skills/self/lib/reality-verdict-schema.mjs exists (Phase 2b).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  FINDING_CATEGORIES,
  isKnownCategory,
  normalizeLoopName,
  buildResultPath,
  validateVerdictShape,
} from "../reality-verdict-schema.mjs";

// ---------------------------------------------------------------------------
// REQ-005: finding category catalog
// ---------------------------------------------------------------------------

test("FINDING_CATEGORIES contains exactly the 7 REQ-005/REQ-004(reality-gate) categories", () => {
  // REQ-001/REQ-004 (reality-gate): "post_not_publicly_visible" added as the category the
  // provenance backstop attaches to its synthesized FAIL/CANNOT_VERIFY findings — the
  // catalog is an "open, growable set" per REQ-004's own EARS text; this length-7 test is
  // the deliberate, spec-sanctioned update of the prior length-6 test.
  assert.deepEqual(
    [...FINDING_CATEGORIES].sort(),
    [
      "internal_transfer_mislabeled",
      "mock_marker_in_success_path",
      "narrate_only_claim",
      "post_not_publicly_visible",
      "report_ledger_mismatch",
      "report_onchain_mismatch",
      "unhealthy_strategy",
    ].sort()
  );
});

test("isKnownCategory: true for every catalog member, false for unknown strings", () => {
  for (const category of FINDING_CATEGORIES) {
    assert.equal(isKnownCategory(category), true, `expected ${category} to be known`);
  }
  assert.equal(isKnownCategory("made_up_category"), false);
  assert.equal(isKnownCategory(""), false);
  assert.equal(isKnownCategory(undefined), false);
});

// ---------------------------------------------------------------------------
// normalizeLoopName / buildResultPath (REQ-008, mirrors self-fix.sh's -loop suffix rule)
// ---------------------------------------------------------------------------

test("normalizeLoopName appends -loop when missing", () => {
  assert.equal(normalizeLoopName("capafy"), "capafy-loop");
});

test("normalizeLoopName is a no-op when already suffixed", () => {
  assert.equal(normalizeLoopName("capafy-loop"), "capafy-loop");
});

test("normalizeLoopName('life-manager') and ('life-manager-loop') produce the identical name", () => {
  assert.equal(normalizeLoopName("life-manager"), normalizeLoopName("life-manager-loop"));
});

test("buildResultPath embeds the normalized loop name and the timestamp, under stateDir", () => {
  const p = buildResultPath("/tmp/state", "founder", 1752345678000);
  assert.match(p, /^\/tmp\/state\//);
  assert.match(p, /founder-loop/);
  assert.match(p, /1752345678000/);
});

test("buildResultPath is deterministic for identical inputs", () => {
  const a = buildResultPath("/tmp/state", "founder", 100);
  const b = buildResultPath("/tmp/state", "founder", 100);
  assert.equal(a, b);
});

test("buildResultPath differs for different timestamps (isolation across concurrent verify calls)", () => {
  const a = buildResultPath("/tmp/state", "founder", 100);
  const b = buildResultPath("/tmp/state", "founder", 200);
  assert.notEqual(a, b);
});

// ---------------------------------------------------------------------------
// REQ-006: validateVerdictShape — the anti-vague-PASS / evidence-required contract
// ---------------------------------------------------------------------------

const validFindingA = {
  category: "report_ledger_mismatch",
  severity: "critical",
  description: "Report claims $50 earned; ledger has no matching row.",
  evidence: { filePath: "/tmp/ledger.jsonl", lineRange: "1-3" },
};

test("valid FAIL verdict with one properly-evidenced finding is accepted", () => {
  const verdict = {
    role: "agentic-honesty-check",
    overallVerdict: "FAIL",
    findings: [validFindingA],
  };
  assert.deepEqual(validateVerdictShape(verdict), { ok: true });
});

test("valid PASS verdict with zero findings but evidenceReviewed is accepted", () => {
  const verdict = {
    role: "agentic-honesty-check",
    overallVerdict: "PASS",
    findings: [],
    evidenceReviewed: [
      { type: "ledger", location: "/tmp/ledger.jsonl", description: "checked all rows for loop founder" },
    ],
  };
  assert.deepEqual(validateVerdictShape(verdict), { ok: true });
});

test("REJECT: missing role field", () => {
  const verdict = { overallVerdict: "PASS", findings: [], evidenceReviewed: [{ type: "x", location: "y", description: "z" }] };
  const result = validateVerdictShape(verdict);
  assert.equal(result.ok, false);
  assert.match(result.reason, /role/);
});

test("REJECT: role is not exactly agentic-honesty-check (guards against confusion with DETERMINISTIC layer, REQ-003)", () => {
  const verdict = { role: "deterministic-gate", overallVerdict: "PASS", findings: [], evidenceReviewed: [{ type: "x", location: "y", description: "z" }] };
  assert.equal(validateVerdictShape(verdict).ok, false);
});

test("REJECT: overallVerdict outside PASS/FAIL", () => {
  const verdict = { role: "agentic-honesty-check", overallVerdict: "MAYBE", findings: [] };
  assert.equal(validateVerdictShape(verdict).ok, false);
});

test("REJECT: FAIL verdict with zero findings (a FAIL must always cite evidence)", () => {
  const verdict = { role: "agentic-honesty-check", overallVerdict: "FAIL", findings: [] };
  const result = validateVerdictShape(verdict);
  assert.equal(result.ok, false);
  assert.match(result.reason, /finding/i);
});

test("REJECT: PASS verdict with zero findings AND no evidenceReviewed (vague PASS)", () => {
  const verdict = { role: "agentic-honesty-check", overallVerdict: "PASS", findings: [] };
  const result = validateVerdictShape(verdict);
  assert.equal(result.ok, false);
  assert.match(result.reason, /vague|evidenceReviewed/i);
});

test("REJECT: finding with unknown category", () => {
  const verdict = {
    role: "agentic-honesty-check",
    overallVerdict: "FAIL",
    findings: [{ ...validFindingA, category: "totally_made_up" }],
  };
  assert.equal(validateVerdictShape(verdict).ok, false);
});

test("REJECT: finding with no citeable evidence (no filePath/txHash/domExcerpt)", () => {
  const verdict = {
    role: "agentic-honesty-check",
    overallVerdict: "FAIL",
    findings: [{ category: "report_ledger_mismatch", severity: "critical", description: "x", evidence: {} }],
  };
  const result = validateVerdictShape(verdict);
  assert.equal(result.ok, false);
  assert.match(result.reason, /evidence/i);
});

test("ACCEPT: finding evidenced by txHash instead of filePath (on-chain-cited finding)", () => {
  const verdict = {
    role: "agentic-honesty-check",
    overallVerdict: "FAIL",
    findings: [{
      category: "report_onchain_mismatch",
      severity: "critical",
      description: "Report claims inbound tx; on-chain shows none for this wallet in the window.",
      evidence: { txHash: "0xabc123", chain: "base" },
    }],
  };
  assert.deepEqual(validateVerdictShape(verdict), { ok: true });
});

test("REJECT: non-object input", () => {
  assert.equal(validateVerdictShape(null).ok, false);
  assert.equal(validateVerdictShape(undefined).ok, false);
  assert.equal(validateVerdictShape("PASS").ok, false);
});
