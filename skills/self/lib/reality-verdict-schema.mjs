// reality-verdict-schema.mjs — pure core for the AGENTIC verification layer (reality-verifier).
// Spec: .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-005/REQ-006/REQ-008.
//
// This module is intentionally side-effect-free (no fs/network/process access) so it is
// formally verifiable by property tests (see reality-verdict-schema.property.test.mjs,
// PROP-001..005). It does NOT implement the reality-verifier's judgment itself (that is an
// LLM, defined in .claude/agents/reality-verifier.md) — it only defines and validates the
// SHAPE of what that judgment must produce, and derives the result-file path the spawn
// wrapper (reality-verify-spawn.sh) uses.

// REQ-005: the fixed catalog of dishonesty/reality failure modes reality-verifier checks for.
// role stays "agentic-honesty-check" everywhere (REQ-003/REQ-006) so downstream consumers can
// never confuse this layer's output with the DETERMINISTIC (on-chain) layer's output.
export const FINDING_CATEGORIES = Object.freeze([
  "report_ledger_mismatch",
  "report_onchain_mismatch",
  "internal_transfer_mislabeled",
  "mock_marker_in_success_path",
  "narrate_only_claim",
  "unhealthy_strategy",
]);

export const VERDICT_ROLE = "agentic-honesty-check";

/**
 * REQ-005 acceptance: pure lookup against the fixed catalog.
 * @param {unknown} category
 * @returns {boolean}
 */
export function isKnownCategory(category) {
  return typeof category === "string" && FINDING_CATEGORIES.includes(category);
}

/**
 * REQ-008 edge case: normalize "capafy" and "capafy-loop" to the identical "capafy-loop"
 * form, mirroring self-fix.sh's LOOP="${1:?loop name}"; LOOP="${LOOP%-loop}-loop" rule, so a
 * verify result for a loop is never split across two spellings.
 * @param {string} loopName
 * @returns {string}
 */
export function normalizeLoopName(loopName) {
  const trimmed = String(loopName ?? "").trim();
  const withoutSuffix = trimmed.endsWith("-loop") ? trimmed.slice(0, -"-loop".length) : trimmed;
  return `${withoutSuffix}-loop`;
}

/**
 * REQ-008: deterministic, isolated result-file path for a given loop + timestamp so
 * concurrent verify calls for different loops (or repeated calls for the same loop) never
 * collide or get silently overwritten.
 * @param {string} stateDir
 * @param {string} loopName
 * @param {number} timestampMs
 * @returns {string}
 */
export function buildResultPath(stateDir, loopName, timestampMs) {
  const normalized = normalizeLoopName(loopName);
  const dir = String(stateDir ?? "").replace(/\/+$/, "");
  return `${dir}/.reality-verify-${normalized}-${timestampMs}.json`;
}

function hasCiteableEvidence(evidence) {
  if (!evidence || typeof evidence !== "object") return false;
  return Boolean(evidence.filePath || evidence.txHash || evidence.domExcerpt);
}

/**
 * REQ-006: validate the SHAPE of a reality-verifier verdict object. This is a pure
 * structural/semantic check — it does not (and cannot) judge whether the verdict's
 * CONTENT is factually correct; that is the LLM's job, checked only by own-eyes review
 * (see verification-architecture.md "What this architecture explicitly does NOT verify").
 * @param {unknown} verdict
 * @returns {{ok: true} | {ok: false, reason: string}}
 */
export function validateVerdictShape(verdict) {
  if (!verdict || typeof verdict !== "object" || Array.isArray(verdict)) {
    return { ok: false, reason: "verdict must be a non-array object" };
  }

  if (verdict.role !== VERDICT_ROLE) {
    return {
      ok: false,
      reason: `verdict.role must be "${VERDICT_ROLE}" (boundary marker vs the DETERMINISTIC layer, REQ-003)`,
    };
  }

  if (verdict.overallVerdict !== "PASS" && verdict.overallVerdict !== "FAIL") {
    return { ok: false, reason: 'verdict.overallVerdict must be exactly "PASS" or "FAIL"' };
  }

  if (!Array.isArray(verdict.findings)) {
    return { ok: false, reason: "verdict.findings must be an array" };
  }

  for (const finding of verdict.findings) {
    if (!finding || typeof finding !== "object") {
      return { ok: false, reason: "each finding must be an object" };
    }
    if (!isKnownCategory(finding.category)) {
      return {
        ok: false,
        reason: `unknown finding category: ${String(finding.category)} (must be one of ${FINDING_CATEGORIES.join(", ")})`,
      };
    }
    if (!hasCiteableEvidence(finding.evidence)) {
      return {
        ok: false,
        reason: "finding.evidence must cite filePath, txHash, or domExcerpt (uncited findings are a process failure)",
      };
    }
  }

  if (verdict.overallVerdict === "FAIL" && verdict.findings.length === 0) {
    return { ok: false, reason: "a FAIL verdict must include at least one finding" };
  }

  if (verdict.overallVerdict === "PASS" && verdict.findings.length === 0) {
    const evidenceReviewed = verdict.evidenceReviewed;
    if (!Array.isArray(evidenceReviewed) || evidenceReviewed.length === 0) {
      return {
        ok: false,
        reason: "a PASS with zero findings must cite evidenceReviewed (what/where was checked) — vague PASS is invalid",
      };
    }
  }

  return { ok: true };
}
