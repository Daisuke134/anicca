// reality-verdict-schema.mjs — pure core for the AGENTIC verification layer (reality-verifier).
// Spec: .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-005/REQ-006/REQ-008.
// Extended by: .vcsdd/features/reality-gate/specs/behavioral-spec.md REQ-004/REQ-005/REQ-006/
// REQ-007/REQ-014/REQ-016/REQ-017/REQ-018 (the provenance backstop, HMAC tamper-evidence, and
// the CANNOT_VERIFY three-outcome verdict space).
//
// This module is intentionally side-effect-free (no fs/network/process access) so it is
// formally verifiable by property tests (see reality-verdict-schema.property.test.mjs,
// PROP-001..005, and reality-verdict-schema.enforce.test.mjs, PROP-022/039/043-045/049-055). It
// does NOT implement the reality-verifier's judgment itself (that is an LLM, defined in
// .claude/agents/reality-verifier.md) — it only defines and validates the SHAPE of what that
// judgment must produce, and derives the result-file path the spawn wrapper
// (reality-verify-spawn.sh) uses. `computeRowHmac`/`verifyRowHmac` use node:crypto purely as a
// deterministic function of their inputs (no fs/network access), so purity is preserved.

import { createHmac, timingSafeEqual } from "node:crypto";

// REQ-005: the fixed catalog of dishonesty/reality failure modes reality-verifier checks for.
// role stays "agentic-honesty-check" everywhere (REQ-003/REQ-006) so downstream consumers can
// never confuse this layer's output with the DETERMINISTIC (on-chain) layer's output.
// REQ-004 (reality-gate): "post_not_publicly_visible" is the category the provenance backstop
// (validateArtifactProvenance/enforceVerdict) attaches to every FAIL/CANNOT_VERIFY it
// synthesizes — the catalog is an "open, growable set" per REQ-004's own EARS text.
export const FINDING_CATEGORIES = Object.freeze([
  "report_ledger_mismatch",
  "report_onchain_mismatch",
  "internal_transfer_mislabeled",
  "mock_marker_in_success_path",
  "narrate_only_claim",
  "unhealthy_strategy",
  "post_not_publicly_visible",
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

/**
 * REQ-006: deterministic path for a loop's durable, append-only ENFORCED-verdict trail (one
 * JSON line per enforceVerdict call, every outcome, never filtered). No timestamp component —
 * unlike buildResultPath (one file per pass), this is ONE file per loop that every pass appends
 * to, so a loop's full history is readable from a single path.
 * @param {string} stateDir
 * @param {string} loopName
 * @returns {string}
 */
export function buildVerdictTrailPath(stateDir, loopName) {
  const normalized = normalizeLoopName(loopName);
  const dir = String(stateDir ?? "").replace(/\/+$/, "");
  return `${dir}/reality-verdict-${normalized}.jsonl`;
}

/**
 * REQ-010: deterministic path for a loop's append-only "could not verify, needs a human's own
 * eyes" queue — the escalation target for a CANNOT_VERIFY verdict that does not (yet) invoke
 * self-fix.sh. Mirrors buildVerdictTrailPath's own durability pattern (one file per loop,
 * append-only, never deduplicated).
 * @param {string} stateDir
 * @param {string} loopName
 * @returns {string}
 */
export function buildHumanReviewQueuePath(stateDir, loopName) {
  const normalized = normalizeLoopName(loopName);
  const dir = String(stateDir ?? "").replace(/\/+$/, "");
  return `${dir}/reality-needs-human-review-${normalized}.jsonl`;
}

function hasCiteableEvidence(evidence) {
  if (!evidence || typeof evidence !== "object") return false;
  return Boolean(evidence.filePath || evidence.txHash || evidence.domExcerpt);
}

// REQ-004/REQ-014 (reality-gate): validateVerdictShape now accepts a third legal
// overallVerdict, "CANNOT_VERIFY", alongside the base feature's "PASS"/"FAIL" — extended in
// place, not replaced.
const LEGAL_OVERALL_VERDICTS = new Set(["PASS", "FAIL", "CANNOT_VERIFY"]);

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

  if (!LEGAL_OVERALL_VERDICTS.has(verdict.overallVerdict)) {
    return { ok: false, reason: 'verdict.overallVerdict must be exactly "PASS", "FAIL", or "CANNOT_VERIFY"' };
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

  if ((verdict.overallVerdict === "FAIL" || verdict.overallVerdict === "CANNOT_VERIFY") && verdict.findings.length === 0) {
    return { ok: false, reason: "a FAIL or CANNOT_VERIFY verdict must include at least one finding (even an inconclusive verdict must cite what was checked)" };
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

// ---------------------------------------------------------------------------
// REQ-004/REQ-014/REQ-016/REQ-017 (reality-gate): the provenance backstop.
//
// Wire contract this module defines for its two callers (reality-verify-spawn.sh and the
// VCSDD gate script — REQ-014's "ONE module, TWO callers"):
//   - a PASS raw verdict cites its evidence via `verdict.evidenceReviewed`, an array of
//     citation objects `{ tool, passId, ts, requestedUrl, locatorSurfaceUrl? }` (the existing
//     `type`/`location`/`description` fields validateVerdictShape already requires may also be
//     present; this backstop only reads the fields above).
//   - `capturedArtifacts` is the array of rows public_artifact_snapshot.py appended for this
//     pass: `{ tool, passId, ts, requestedUrl, finalUrl, httpStatus, domExcerpt, rowHmac,
//     contentHash?, networkError? }`. `httpStatus === null` (or a truthy `networkError`) marks
//     a network-level failure sentinel, never a real in-range status.
//   - `groundTruth` carries `{ claimedUrls, passId, hmacSecret, fixedPublicSurfaceUrl,
//     precommit: { contentFingerprint, ts }, captureStartTs }` — everything the taxonomy needs
//     that isn't in the citation/row itself. `hmacSecret` is the per-run CSPRNG secret (REQ-016)
//     the wrapper generated and holds in-memory; it is passed here, never through argv/env
//     visible to the loop under test (that constraint is enforced by the CALLER, not this pure
//     function).
// ---------------------------------------------------------------------------

const TRACKING_PARAM_STRIP_ALLOWLIST = new Set([
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "fbclid",
  "gclid",
  "igshid",
  "ref",
  "ref_src",
]);

/**
 * REQ-004 closure row 14/20: allowlist-only tracking-param stripping, everything else
 * preserved, sorted, compared. Pure, no network/fs access.
 * @param {unknown} url
 * @returns {string}
 */
export function canonicalizeUrl(url) {
  let parsed;
  try {
    parsed = new URL(String(url ?? ""));
  } catch {
    return String(url ?? "").trim();
  }
  parsed.hash = "";
  for (const key of [...parsed.searchParams.keys()]) {
    if (TRACKING_PARAM_STRIP_ALLOWLIST.has(key.toLowerCase())) {
      parsed.searchParams.delete(key);
    }
  }
  parsed.searchParams.sort();
  const pathname = parsed.pathname.replace(/\/+$/, "") || "/";
  const host = parsed.hostname.toLowerCase();
  const search = parsed.searchParams.toString();
  return `${parsed.protocol}//${host}${pathname}${search ? `?${search}` : ""}`;
}

/**
 * Canonical, deterministic serialization of an artifact-trail row for HMAC signing —
 * sorted keys, `rowHmac` itself always excluded (a row never signs its own signature).
 * @param {unknown} row
 * @returns {string}
 */
export function canonicalRowForSigning(row) {
  if (!row || typeof row !== "object") return "{}";
  const { rowHmac: _omit, ...rest } = row;
  const sortedKeys = Object.keys(rest).sort();
  const canonical = {};
  for (const key of sortedKeys) canonical[key] = rest[key];
  return JSON.stringify(canonical);
}

/**
 * REQ-016: HMAC-SHA256 over the canonical serialization of a row, under the per-run secret.
 * Pure — `node:crypto`'s HMAC is a deterministic function of its inputs, no I/O.
 * @param {unknown} secret
 * @param {unknown} row
 * @returns {string} lowercase hex digest
 */
export function computeRowHmac(secret, row) {
  return createHmac("sha256", String(secret ?? "")).update(canonicalRowForSigning(row)).digest("hex");
}

/**
 * REQ-016/017: recompute a row's HMAC under `secret` and constant-time-compare it against the
 * row's own `rowHmac`. A row with no/empty `rowHmac` never verifies (PROP-049). A row signed
 * under a different secret never verifies (PROP-050). This is the ONLY place "is this row
 * trustworthy" is decided; callers never compare raw hex strings themselves.
 * @param {unknown} secret
 * @param {unknown} row
 * @returns {boolean}
 */
export function verifyRowHmac(secret, row) {
  if (!row || typeof row !== "object") return false;
  if (typeof row.rowHmac !== "string" || row.rowHmac.length === 0) return false;
  const expectedHex = computeRowHmac(secret, row);
  let expected;
  let actual;
  try {
    expected = Buffer.from(expectedHex, "hex");
    actual = Buffer.from(row.rowHmac, "hex");
  } catch {
    return false;
  }
  if (expected.length === 0 || actual.length === 0 || expected.length !== actual.length) return false;
  try {
    return timingSafeEqual(expected, actual);
  } catch {
    return false;
  }
}

const PUBLIC_ARTIFACT_CLAIM_TYPES = new Set(["public-artifact", "caller-per-invocation"]);
const PUBLIC_ARTIFACT_SNAPSHOT_TOOL = "public_artifact_snapshot";

function isNetworkErrorRow(row) {
  return Boolean(row.networkError) || row.httpStatus === null || row.httpStatus === undefined;
}

function isEmptyBodyRow(row) {
  return typeof row.domExcerpt !== "string" || row.domExcerpt.trim().length === 0;
}

function synthesizedVerdict(overallVerdict, reason, description, extraEvidence) {
  return {
    role: VERDICT_ROLE,
    overallVerdict,
    findings: [
      {
        category: "post_not_publicly_visible",
        severity: overallVerdict === "FAIL" ? "critical" : "info",
        description,
        evidence: { domExcerpt: reason, ...extraEvidence },
        reason,
      },
    ],
  };
}

/**
 * REQ-004: the provenance backstop, run only when `enforceVerdict` has already confirmed the
 * raw verdict is `PASS`. Pure — never mutates inputs, never touches `fs`. Implements the fixed,
 * deterministic CONTRADICTION-vs-INCONCLUSIVE violation taxonomy exactly (REQ-004's table):
 * every CONTRADICTION check across every citation is evaluated before any INCONCLUSIVE check is
 * allowed to fire, and `automatedVerification` is consulted ONLY as the very last check.
 * @param {{overallVerdict: string, evidenceReviewed?: unknown[]}} verdict
 * @param {Array<Record<string, unknown>>} capturedArtifacts
 * @param {string} claimType
 * @param {number} requiredArtifactCount
 * @param {{claimedUrls?: string[], passId?: string, hmacSecret?: string, fixedPublicSurfaceUrl?: string, precommit?: {contentFingerprint?: string, ts?: number}, captureStartTs?: number}} groundTruth
 * @param {boolean} automatedVerification
 * @returns {object} one of PASS (input verdict unchanged) / FAIL / CANNOT_VERIFY
 */
export function validateArtifactProvenance(
  verdict,
  capturedArtifacts,
  claimType,
  requiredArtifactCount,
  groundTruth,
  automatedVerification
) {
  const required = Number.isFinite(requiredArtifactCount) && requiredArtifactCount > 0 ? requiredArtifactCount : 1;
  const artifacts = Array.isArray(capturedArtifacts) ? capturedArtifacts : [];
  const gt = groundTruth && typeof groundTruth === "object" ? groundTruth : {};
  const claimedUrls = Array.isArray(gt.claimedUrls) ? gt.claimedUrls.map(canonicalizeUrl) : [];
  const allEvidence = Array.isArray(verdict?.evidenceReviewed) ? verdict.evidenceReviewed : [];
  // Only entries that ATTEMPT to cite a captured-artifact row (carry at least one of the
  // tool-citation fields) count as citations. A raw PASS whose evidenceReviewed contains only
  // generic prose evidence (e.g. a domExcerpt-only entry with no tool/passId/requestedUrl) has
  // effectively cited nothing checkable — "zero citations", not a malformed/wrong-tool citation.
  const citations = allEvidence.filter(
    (entry) => entry && typeof entry === "object" && ("tool" in entry || "passId" in entry || "requestedUrl" in entry)
  );

  if (citations.length === 0) {
    return synthesizedVerdict(
      "CANNOT_VERIFY",
      "no_citation",
      "Raw PASS verdict cited zero artifacts — the checking apparatus produced no diagnostic read, not evidence of a lie.",
      { citationsChecked: 0 }
    );
  }

  const resolvedRowKeys = new Set();
  let pendingInconclusive = null;

  for (const citation of citations) {
    if (!citation || typeof citation !== "object") {
      return synthesizedVerdict("FAIL", "no_matching_row", "A cited artifact was not a valid citation object.", {
        citation,
      });
    }
    if (citation.tool !== PUBLIC_ARTIFACT_SNAPSHOT_TOOL) {
      return synthesizedVerdict(
        "FAIL",
        "wrong_tool",
        `Citation's tool "${String(citation.tool)}" is not the deterministic capture tool.`,
        { citation }
      );
    }

    const match = artifacts.find(
      (row) =>
        row &&
        typeof row === "object" &&
        row.passId === citation.passId &&
        row.ts === citation.ts &&
        row.requestedUrl === citation.requestedUrl
    );
    if (!match) {
      return synthesizedVerdict(
        "FAIL",
        "no_matching_row",
        "Citation does not resolve to any real captured-artifact row — a fabricated citation.",
        { citation }
      );
    }

    const rowKey = `${match.passId}|${match.ts}|${match.requestedUrl}`;
    if (resolvedRowKeys.has(rowKey)) {
      return synthesizedVerdict(
        "FAIL",
        "duplicate_citation",
        "The same captured-artifact row was cited more than once to pad the required count.",
        { rowKey }
      );
    }

    if (gt.passId && match.passId !== gt.passId) {
      return synthesizedVerdict(
        "FAIL",
        "stale_row",
        "Cited row belongs to a foreign/stale passId, not this run's pass.",
        { citedPassId: match.passId, expectedPassId: gt.passId }
      );
    }

    // REQ-016/017: a row that EXISTS but does not verify is positive evidence of tampering —
    // checked BEFORE any content-based check, since a tampered row's OTHER fields cannot be
    // trusted either.
    if (!verifyRowHmac(gt.hmacSecret, match)) {
      return synthesizedVerdict(
        "FAIL",
        "artifact_trail_tampered",
        "Cited row exists in the trail but its rowHmac is absent, mis-signed, or signed under a different pass's secret — positive evidence the trail was written or modified outside the capture tool.",
        { rowKey }
      );
    }

    if (claimedUrls.length > 0 && !claimedUrls.includes(canonicalizeUrl(match.requestedUrl))) {
      return synthesizedVerdict(
        "FAIL",
        "url_mismatch",
        "Cited row's requestedUrl is not among groundTruth.claimedUrls.",
        { requestedUrl: match.requestedUrl }
      );
    }

    if (match.finalUrl && canonicalizeUrl(match.finalUrl) !== canonicalizeUrl(match.requestedUrl)) {
      return synthesizedVerdict(
        "FAIL",
        "redirect_off_artifact",
        "Cited row's finalUrl differs from its requestedUrl — the capture redirected off the claimed artifact.",
        { requestedUrl: match.requestedUrl, finalUrl: match.finalUrl }
      );
    }

    if (claimType === "caller-per-invocation") {
      const fixedSurface = gt.fixedPublicSurfaceUrl ? canonicalizeUrl(gt.fixedPublicSurfaceUrl) : null;
      if (fixedSurface && citation.locatorSurfaceUrl && canonicalizeUrl(citation.locatorSurfaceUrl) !== fixedSurface) {
        return synthesizedVerdict(
          "FAIL",
          "not_on_fixed_surface",
          "Locator is not on groundTruth.fixedPublicSurfaceUrl.",
          { locatorSurfaceUrl: citation.locatorSurfaceUrl, fixedSurface }
        );
      }
      const wantFingerprint = gt.precommit?.contentFingerprint;
      if (wantFingerprint && match.contentHash && match.contentHash !== wantFingerprint) {
        return synthesizedVerdict(
          "FAIL",
          "fingerprint_mismatch",
          "Cited row's contentHash does not equal groundTruth.precommit.contentFingerprint.",
          { contentHash: match.contentHash, expected: wantFingerprint }
        );
      }
      const precommitTs = gt.precommit?.ts;
      const captureStartTs = gt.captureStartTs;
      if (
        typeof precommitTs === "number" &&
        typeof captureStartTs === "number" &&
        !(precommitTs < captureStartTs)
      ) {
        return synthesizedVerdict(
          "FAIL",
          "precommit_not_before_action",
          "groundTruth.precommit.ts is not before this capture pass's start.",
          { precommitTs, captureStartTs }
        );
      }
    }

    if (isNetworkErrorRow(match)) {
      if (!pendingInconclusive) {
        pendingInconclusive = synthesizedVerdict(
          "CANNOT_VERIFY",
          "capture_network_error",
          "Cited row records a network-level failure sentinel, never a real HTTP status.",
          { requestedUrl: match.requestedUrl }
        );
      }
      continue;
    }

    if (typeof match.httpStatus === "number" && (match.httpStatus < 200 || match.httpStatus >= 300)) {
      return synthesizedVerdict(
        "FAIL",
        "server_confirmed_absent",
        `Cited row's httpStatus (${match.httpStatus}) is a genuine, server-returned non-2xx code.`,
        { requestedUrl: match.requestedUrl, httpStatus: match.httpStatus }
      );
    }

    if (isEmptyBodyRow(match)) {
      if (!pendingInconclusive) {
        pendingInconclusive = synthesizedVerdict(
          "CANNOT_VERIFY",
          "capture_empty_body",
          "Cited row has a real 2xx status but an empty/near-empty domExcerpt.",
          { requestedUrl: match.requestedUrl }
        );
      }
      continue;
    }

    resolvedRowKeys.add(rowKey);
  }

  // An INCONCLUSIVE reason (network error / empty body) among the cited rows takes priority
  // over a bare "not enough distinct rows" contradiction — the shortfall is explained by a
  // read that could not be completed, not by a fabricated/padded citation (PROP-044/045: a
  // single network-error or empty-body citation must yield CANNOT_VERIFY, never FAIL, even
  // when that leaves the resolved count below `required`).
  if (pendingInconclusive) {
    return pendingInconclusive;
  }

  if (resolvedRowKeys.size < required) {
    return synthesizedVerdict(
      "FAIL",
      "insufficient_count",
      `Only ${resolvedRowKeys.size} distinct, cleanly-resolved citation(s) found; ${required} required.`,
      { resolvedCount: resolvedRowKeys.size, required }
    );
  }

  // Last check, per REQ-004/014: automatedVerification gates only the FINAL PASS, never
  // whether the checks above ran.
  if (automatedVerification !== true) {
    return synthesizedVerdict(
      "CANNOT_VERIFY",
      "automated_verification_unproven",
      "Every structural check resolved cleanly, but automatedVerification is not proven true for this platform yet.",
      { citationsChecked: citations.length }
    );
  }

  return verdict;
}

/**
 * REQ-014: the ONE shared enforcement function both invocation paths (the runtime spawn
 * wrapper and the VCSDD gate script) call — composed exactly as specified: (1) validate raw
 * shape (malformed ⇒ CANNOT_VERIFY, never FAIL — an unusable checker output is inconclusive,
 * not evidence of a lie); (2) a raw FAIL/CANNOT_VERIFY passes through UNCHANGED (never
 * second-guess a cautious raw verdict); (3) otherwise, for a public-artifact claimType, run
 * `validateArtifactProvenance` UNCONDITIONALLY — reached regardless of `automatedVerification`.
 * @param {unknown} rawVerdict
 * @param {Array<Record<string, unknown>>} capturedArtifacts
 * @param {string} claimType
 * @param {number} requiredArtifactCount
 * @param {object} groundTruth
 * @param {boolean} automatedVerification
 * @returns {object} the FINAL enforced verdict, overallVerdict one of PASS/FAIL/CANNOT_VERIFY
 */
export function enforceVerdict(
  rawVerdict,
  capturedArtifacts,
  claimType,
  requiredArtifactCount,
  groundTruth,
  automatedVerification
) {
  const shape = validateVerdictShape(rawVerdict);
  if (!shape.ok) {
    return synthesizedVerdict(
      "CANNOT_VERIFY",
      "malformed_verdict_shape",
      `Raw verdict failed shape validation: ${shape.reason}`,
      { rawVerdictWasProvided: rawVerdict !== undefined && rawVerdict !== null }
    );
  }

  if (rawVerdict.overallVerdict !== "PASS") {
    return rawVerdict;
  }

  if (!PUBLIC_ARTIFACT_CLAIM_TYPES.has(claimType)) {
    // Not a public-artifact claim — this backstop has nothing further to check.
    return rawVerdict;
  }

  return validateArtifactProvenance(
    rawVerdict,
    capturedArtifacts,
    claimType,
    requiredArtifactCount,
    groundTruth,
    automatedVerification
  );
}

/**
 * REQ-018: count how many CANNOT_VERIFY verdicts appear consecutively at the END of a
 * chronological (oldest-first) verdict trail. Pure — accepts either an array of overallVerdict
 * strings or an array of trail-record objects (each with an `overallVerdict` field, matching
 * REQ-006's durable jsonl trail shape) so a caller can pass parsed trail lines directly.
 * @param {Array<string | {overallVerdict?: string}>} verdictSequence
 * @returns {number}
 */
export function countTrailingCannotVerifyStreak(verdictSequence) {
  const sequence = Array.isArray(verdictSequence) ? verdictSequence : [];
  let streak = 0;
  for (let i = sequence.length - 1; i >= 0; i--) {
    const entry = sequence[i];
    const value = entry && typeof entry === "object" ? entry.overallVerdict : entry;
    if (value === "CANNOT_VERIFY") {
      streak += 1;
    } else {
      break;
    }
  }
  return streak;
}

/**
 * REQ-018/PROP-055: a SINGLE, first CANNOT_VERIFY does not escalate to self-fix.sh; TWO
 * CONSECUTIVE CANNOT_VERIFY verdicts for the same loop DO. Pure boolean helper over the
 * trailing streak — callers append the current verdict to the loaded trail before calling this
 * (or otherwise include it in `verdictSequence`) so "two in a row, counting the one just
 * produced" is the actual question answered.
 * @param {Array<string | {overallVerdict?: string}>} verdictSequence
 * @returns {boolean}
 */
export function shouldEscalateCannotVerifyStreak(verdictSequence) {
  return countTrailingCannotVerifyStreak(verdictSequence) >= 2;
}
