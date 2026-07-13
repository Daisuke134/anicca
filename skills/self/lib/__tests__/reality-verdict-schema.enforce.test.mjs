// VCSDD Phase 2b: negative-test proof for the reality-gate provenance backstop.
// Spec: .vcsdd/features/reality-gate/specs/behavioral-spec.md REQ-004/REQ-005/REQ-006/REQ-007/
// REQ-014/REQ-016/REQ-017/REQ-018.
// REQ-007's own rule: "a gate that cannot fail is not a gate" — every fixture below that
// represents a FALSE or unprovable claim must produce a REAL, executed overallVerdict:"FAIL"
// or "CANNOT_VERIFY" in this test's actual stdout, not merely an asserted string.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  canonicalizeUrl,
  computeRowHmac,
  verifyRowHmac,
  validateArtifactProvenance,
  enforceVerdict,
  countTrailingCannotVerifyStreak,
  shouldEscalateCannotVerifyStreak,
  VERDICT_ROLE,
} from "../reality-verdict-schema.mjs";

const SECRET = "test-secret-do-not-use-in-prod";
const WRONG_SECRET = "a-different-secret-a-forger-might-guess-wrong";

function makeRow(overrides = {}) {
  const base = {
    tool: "public_artifact_snapshot",
    passId: "pass-abc123",
    ts: 1000,
    requestedUrl: "https://example.com/posts/1",
    finalUrl: "https://example.com/posts/1",
    httpStatus: 200,
    domExcerpt: "This is the real, visible post content.",
  };
  const row = { ...base, ...overrides };
  row.rowHmac = computeRowHmac(SECRET, row);
  return row;
}

function citationFor(row) {
  return { tool: row.tool, passId: row.passId, ts: row.ts, requestedUrl: row.requestedUrl };
}

function rawPass(evidenceReviewed) {
  return { role: VERDICT_ROLE, overallVerdict: "PASS", findings: [], evidenceReviewed };
}

const CLEAN_GROUND_TRUTH = {
  claimedUrls: ["https://example.com/posts/1"],
  passId: "pass-abc123",
  hmacSecret: SECRET,
};

// ---------------------------------------------------------------------------
// REQ-014/PROP-039: enforceVerdict's composition
// ---------------------------------------------------------------------------

test("enforceVerdict: malformed raw verdict (not even an object) -> CANNOT_VERIFY/malformed_verdict_shape, never FAIL", () => {
  const result = enforceVerdict(null, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, false);
  console.log("malformed-shape verdict:", JSON.stringify(result));
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "malformed_verdict_shape");
});

test("enforceVerdict: raw FAIL passes through UNCHANGED (never second-guessed)", () => {
  const raw = {
    role: VERDICT_ROLE,
    overallVerdict: "FAIL",
    findings: [{ category: "narrate_only_claim", severity: "critical", description: "x", evidence: { domExcerpt: "y" } }],
  };
  const result = enforceVerdict(raw, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.deepEqual(result, raw);
});

test("enforceVerdict: raw CANNOT_VERIFY passes through UNCHANGED", () => {
  const raw = {
    role: VERDICT_ROLE,
    overallVerdict: "CANNOT_VERIFY",
    findings: [{ category: "post_not_publicly_visible", severity: "info", description: "x", evidence: { domExcerpt: "y" } }],
  };
  const result = enforceVerdict(raw, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.deepEqual(result, raw);
});

test("enforceVerdict: non-public-artifact claimType passes a raw PASS through unchanged (backstop out of scope)", () => {
  const raw = rawPass([{ type: "ledger", location: "x", description: "y" }]);
  const result = enforceVerdict(raw, [], "none", 1, {}, false);
  assert.equal(result.overallVerdict, "PASS");
});

// ---------------------------------------------------------------------------
// REQ-007 / THE core negative test: a FABRICATED post claim must yield a REAL, executed FAIL.
// ---------------------------------------------------------------------------

test("REQ-007 negative test: a raw PASS citing a URL that was NEVER captured (fabricated claim) -> FAIL/no_matching_row, in actual executed output", () => {
  const fakeCitation = {
    tool: "public_artifact_snapshot",
    passId: "pass-abc123",
    ts: 9999,
    requestedUrl: "https://example.com/posts/this-was-never-actually-fetched",
  };
  const raw = rawPass([fakeCitation]);
  const result = enforceVerdict(raw, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  console.log("FABRICATED CLAIM negative-test result:", JSON.stringify(result));
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "no_matching_row");
});

// ---------------------------------------------------------------------------
// PROP-043: contradiction checked BEFORE, and takes priority over, automatedVerification
// ---------------------------------------------------------------------------

test("PROP-043(a): every structural check clean + automatedVerification:false -> CANNOT_VERIFY/automated_verification_unproven (proves checks actually ran)", () => {
  const row = makeRow();
  const raw = rawPass([citationFor(row)]);
  const result = enforceVerdict(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, false);
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "automated_verification_unproven");
});

test("PROP-043(b): companion fixture — same as (a) but ALSO a url_mismatch contradiction -> FAIL/url_mismatch, NOT CANNOT_VERIFY", () => {
  const row = makeRow({ requestedUrl: "https://example.com/posts/DIFFERENT-URL" });
  const raw = rawPass([citationFor(row)]);
  const result = enforceVerdict(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, false);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "url_mismatch");
});

test("clean + automatedVerification:true -> PASS (input verdict returned unchanged)", () => {
  const row = makeRow();
  const raw = rawPass([citationFor(row)]);
  const result = enforceVerdict(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "PASS");
  assert.equal(result, raw);
});

// ---------------------------------------------------------------------------
// PROP-022: zero citations -> CANNOT_VERIFY, not FAIL
// ---------------------------------------------------------------------------

test("PROP-022: a raw PASS whose evidenceReviewed is domExcerpt-only prose (no tool-citation fields) -> CANNOT_VERIFY/no_citation, not FAIL", () => {
  const raw = {
    role: VERDICT_ROLE,
    overallVerdict: "PASS",
    findings: [],
    evidenceReviewed: [{ type: "domExcerpt", location: "n/a", description: "I looked at the page and it seemed fine" }],
  };
  const result = enforceVerdict(raw, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  console.log("PROP-022 zero-citation result:", JSON.stringify(result));
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "no_citation");
});

// ---------------------------------------------------------------------------
// Wrong tool / stale passId / redirect / insufficient count / duplicate citation
// ---------------------------------------------------------------------------

test("wrong_tool: citation from a tool other than public_artifact_snapshot -> FAIL", () => {
  const row = makeRow();
  const citation = { ...citationFor(row), tool: "some_other_scraper" };
  const result = validateArtifactProvenance(rawPass([citation]), [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "wrong_tool");
});

test("ig_public_check is a trusted capture tool: a clean citation naming it -> PASS, not wrong_tool", () => {
  const row = makeRow({ tool: "ig_public_check" });
  const raw = rawPass([citationFor(row)]);
  const result = enforceVerdict(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "PASS");
});

test("tool allowlist still rejects anything outside {public_artifact_snapshot, ig_public_check} -> FAIL/wrong_tool", () => {
  const row = makeRow({ tool: "yet_another_untrusted_tool" });
  const citation = { ...citationFor(row), tool: "yet_another_untrusted_tool" };
  const result = validateArtifactProvenance(rawPass([citation]), [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "wrong_tool");
});

test("stale_row: cited row belongs to a foreign passId -> FAIL", () => {
  const row = makeRow({ passId: "pass-FOREIGN" });
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "stale_row");
});

test("redirect_off_artifact: finalUrl differs from requestedUrl -> FAIL", () => {
  const row = makeRow({ finalUrl: "https://example.com/redirected-elsewhere" });
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "redirect_off_artifact");
});

test("insufficient_count: fewer than requiredArtifactCount distinct resolved citations -> FAIL", () => {
  const row = makeRow();
  const raw = rawPass([citationFor(row)]);
  const gt = { ...CLEAN_GROUND_TRUTH };
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 2, gt, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "insufficient_count");
});

test("duplicate_citation: the same row cited twice to pad the count -> FAIL, not silently deduped to insufficient_count", () => {
  const row = makeRow();
  const raw = rawPass([citationFor(row), citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 2, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "duplicate_citation");
});

test("server_confirmed_absent: a genuine, real 404 status -> FAIL, regardless of automatedVerification", () => {
  const row = makeRow({ httpStatus: 404, domExcerpt: "Page not found" });
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, false);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "server_confirmed_absent");
});

// ---------------------------------------------------------------------------
// PROP-044/045 (FIND-O): network error / empty body -> CANNOT_VERIFY, never FAIL, never PASS
// ---------------------------------------------------------------------------

test("PROP-044: a row recording the network-error sentinel -> CANNOT_VERIFY/capture_network_error, never FAIL", () => {
  const row = makeRow({ httpStatus: null, networkError: "connection_refused", domExcerpt: undefined });
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "capture_network_error");
});

test("PROP-045: a real 2xx row with an empty domExcerpt -> CANNOT_VERIFY/capture_empty_body", () => {
  const row = makeRow({ httpStatus: 200, domExcerpt: "" });
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "capture_empty_body");
});

// ---------------------------------------------------------------------------
// PROP-049/050/052/053/054 (REQ-016/017): HMAC tamper-evidence
// ---------------------------------------------------------------------------

test("PROP-049: a cited row with NO rowHmac -> never a valid capture -> FAIL/artifact_trail_tampered", () => {
  const row = makeRow();
  delete row.rowHmac;
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "artifact_trail_tampered");
});

test("PROP-050: a cited row signed under a DIFFERENT secret (forger observed passId, not secret) -> never valid -> FAIL/artifact_trail_tampered", () => {
  const row = makeRow();
  row.rowHmac = computeRowHmac(WRONG_SECRET, row);
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "artifact_trail_tampered");
});

test("PROP-052: a VALID, correctly-signed row that CONTRADICTS the claim still yields FAIL (signing never launders a contradiction into CANNOT_VERIFY)", () => {
  const row = makeRow({ httpStatus: 404, domExcerpt: "not found" }); // correctly signed over ITS OWN real content
  const raw = rawPass([citationFor(row)]);
  const result = validateArtifactProvenance(raw, [row], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "server_confirmed_absent");
});

test("PROP-053: the exact FIND-U attack — honestly-captured real 404, then bytes corrupted with same-uid access AFTER signing -> FAIL/artifact_trail_tampered, MUST NOT be CANNOT_VERIFY", () => {
  const row = makeRow({ httpStatus: 404, domExcerpt: "not found" });
  assert.equal(verifyRowHmac(SECRET, row), true, "sanity: row verifies before tampering");
  // Same-uid file corruption: mutate a byte AFTER the row was signed. The signature was
  // computed over the ORIGINAL httpStatus/domExcerpt; changing them now must break verification.
  const tamperedRow = { ...row, domExcerpt: "not found (attacker edited this after signing)" };
  assert.equal(verifyRowHmac(SECRET, tamperedRow), false, "tampered row must fail HMAC verification");

  const raw = rawPass([citationFor(tamperedRow)]);
  const result = validateArtifactProvenance(raw, [tamperedRow], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  console.log("PROP-053 tampered-row result:", JSON.stringify(result));
  assert.equal(result.overallVerdict, "FAIL");
  assert.equal(result.findings[0].reason, "artifact_trail_tampered");
});

test("PROP-054: a trail with NO row at all (nothing captured, nothing cited) -> CANNOT_VERIFY — distinguishable from PROP-053's tampered-row FAIL", () => {
  const raw = rawPass([]); // the apparatus produced no read at all: no citation, no row
  const result = validateArtifactProvenance(raw, [], "public-artifact", 1, CLEAN_GROUND_TRUTH, true);
  assert.equal(result.overallVerdict, "CANNOT_VERIFY");
  assert.equal(result.findings[0].reason, "no_citation");
  // Distinctness proof: PROP-053 (a row EXISTS in the trail but fails HMAC verification) -> FAIL/
  // artifact_trail_tampered. PROP-054 (no row exists at all) -> CANNOT_VERIFY/no_citation. A
  // citation pointing at a row that was never captured (row absent, but SOMETHING was cited) is
  // a THIRD, distinct case: a fabricated citation -> FAIL/no_matching_row (see the REQ-007
  // fabricated-claim negative test above) — absence-of-any-read and fabrication-of-a-read are
  // both distinct from tampering-of-a-real-read, and this suite exercises all three.
});

// ---------------------------------------------------------------------------
// canonicalizeUrl / HMAC unit behavior
// ---------------------------------------------------------------------------

test("canonicalizeUrl strips allowlisted tracking params, preserves everything else, sorts remaining params", () => {
  const a = canonicalizeUrl("https://Example.com/posts/1/?utm_source=x&b=2&a=1#frag");
  const b = canonicalizeUrl("https://example.com/posts/1?a=1&b=2");
  assert.equal(a, b);
});

test("verifyRowHmac: a row with a syntactically-valid but wrong-length rowHmac never verifies (no crash)", () => {
  const row = makeRow();
  row.rowHmac = "deadbeef";
  assert.equal(verifyRowHmac(SECRET, row), false);
});

test("computeRowHmac/verifyRowHmac: signing then verifying under the same secret succeeds", () => {
  const row = makeRow();
  assert.equal(verifyRowHmac(SECRET, row), true);
});

// ---------------------------------------------------------------------------
// REQ-018/PROP-055: CANNOT_VERIFY streak escalation helper
// ---------------------------------------------------------------------------

test("PROP-055: a single, first CANNOT_VERIFY does NOT escalate", () => {
  const trail = ["PASS", "FAIL", "CANNOT_VERIFY"];
  assert.equal(countTrailingCannotVerifyStreak(trail), 1);
  assert.equal(shouldEscalateCannotVerifyStreak(trail), false);
});

test("PROP-055: two CONSECUTIVE CANNOT_VERIFY verdicts DO escalate", () => {
  const trail = ["PASS", "CANNOT_VERIFY", "CANNOT_VERIFY"];
  assert.equal(countTrailingCannotVerifyStreak(trail), 2);
  assert.equal(shouldEscalateCannotVerifyStreak(trail), true);
});

test("streak resets: a PASS or FAIL after CANNOT_VERIFY resets the trailing streak to 0", () => {
  const trail = ["CANNOT_VERIFY", "CANNOT_VERIFY", "FAIL"];
  assert.equal(countTrailingCannotVerifyStreak(trail), 0);
  assert.equal(shouldEscalateCannotVerifyStreak(trail), false);
});

test("streak helper accepts durable-trail-shaped objects ({overallVerdict}) identically to bare strings", () => {
  const trail = [{ overallVerdict: "PASS" }, { overallVerdict: "CANNOT_VERIFY" }, { overallVerdict: "CANNOT_VERIFY" }];
  assert.equal(shouldEscalateCannotVerifyStreak(trail), true);
});
