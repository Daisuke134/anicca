// VCSDD Phase 5 hardening (written up-front per verification-architecture.md Tier 1):
// property tests for reality-verdict-schema.mjs's pure core, using fast-check (already a
// repo devDependency; see skills/economy/lending/lib/__tests__/lending-gate.property.test.mjs
// for the established pattern this file follows).
// Proof obligations covered: PROP-001..PROP-005 in
// .vcsdd/features/reality-verifier/specs/verification-architecture.md
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import {
  FINDING_CATEGORIES,
  normalizeLoopName,
  buildResultPath,
  validateVerdictShape,
} from "../reality-verdict-schema.mjs";

const nonEmptyName = fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0 && !s.includes("/"));
const timestampMs = fc.nat({ max: Number.MAX_SAFE_INTEGER });

// ---------------------------------------------------------------------------
// PROP-001: normalizeLoopName is idempotent
// ---------------------------------------------------------------------------
test("PROP-001 (property): normalizeLoopName is idempotent for any non-empty loop name", () => {
  fc.assert(
    fc.property(nonEmptyName, (name) => {
      const once = normalizeLoopName(name);
      const twice = normalizeLoopName(once);
      assert.equal(twice, once);
    })
  );
});

// ---------------------------------------------------------------------------
// PROP-002: buildResultPath determinism + timestamp-distinctness
// ---------------------------------------------------------------------------
test("PROP-002 (property): buildResultPath is deterministic for identical inputs", () => {
  fc.assert(
    fc.property(nonEmptyName, timestampMs, (name, ts) => {
      const a = buildResultPath("/tmp/state", name, ts);
      const b = buildResultPath("/tmp/state", name, ts);
      assert.equal(a, b);
    })
  );
});

test("PROP-002 (property): buildResultPath differs whenever timestampMs differs (fixed stateDir/loopName)", () => {
  fc.assert(
    fc.property(nonEmptyName, timestampMs, timestampMs, (name, t1, t2) => {
      fc.pre(t1 !== t2);
      const a = buildResultPath("/tmp/state", name, t1);
      const b = buildResultPath("/tmp/state", name, t2);
      assert.notEqual(a, b);
    })
  );
});

// ---------------------------------------------------------------------------
// PROP-003: validateVerdictShape rejects every FAIL-with-empty-findings shape
// ---------------------------------------------------------------------------
test("PROP-003 (property): FAIL verdict with empty findings is ALWAYS rejected, regardless of other fields", () => {
  fc.assert(
    fc.property(fc.dictionary(fc.string(), fc.anything()), (extraFields) => {
      const verdict = {
        ...extraFields,
        role: "agentic-honesty-check",
        overallVerdict: "FAIL",
        findings: [],
      };
      assert.equal(validateVerdictShape(verdict).ok, false);
    })
  );
});

// ---------------------------------------------------------------------------
// PROP-004: validateVerdictShape rejects any finding with an out-of-catalog category
// ---------------------------------------------------------------------------
test("PROP-004 (property): a finding with a category outside FINDING_CATEGORIES is ALWAYS rejected", () => {
  const bogusCategory = fc.string().filter((s) => !FINDING_CATEGORIES.includes(s));
  fc.assert(
    fc.property(bogusCategory, (category) => {
      const verdict = {
        role: "agentic-honesty-check",
        overallVerdict: "FAIL",
        findings: [{
          category,
          severity: "critical",
          description: "x",
          evidence: { filePath: "/tmp/x", lineRange: "1-1" },
        }],
      };
      assert.equal(validateVerdictShape(verdict).ok, false);
    })
  );
});

// ---------------------------------------------------------------------------
// PROP-005: anti-vague-PASS — PASS + empty findings + empty/missing evidenceReviewed always rejected
// ---------------------------------------------------------------------------
test("PROP-005 (property): PASS with empty findings and empty evidenceReviewed is ALWAYS rejected", () => {
  fc.assert(
    fc.property(fc.constantFrom(undefined, [], null), (evidenceReviewed) => {
      const verdict = {
        role: "agentic-honesty-check",
        overallVerdict: "PASS",
        findings: [],
        ...(evidenceReviewed === undefined ? {} : { evidenceReviewed }),
      };
      assert.equal(validateVerdictShape(verdict).ok, false);
    })
  );
});

test("PROP-005 (property): PASS with empty findings and a non-empty evidenceReviewed is ALWAYS accepted", () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({ type: fc.string({ minLength: 1 }), location: fc.string({ minLength: 1 }), description: fc.string({ minLength: 1 }) }),
        { minLength: 1, maxLength: 5 }
      ),
      (evidenceReviewed) => {
        const verdict = { role: "agentic-honesty-check", overallVerdict: "PASS", findings: [], evidenceReviewed };
        assert.equal(validateVerdictShape(verdict).ok, true);
      }
    )
  );
});
