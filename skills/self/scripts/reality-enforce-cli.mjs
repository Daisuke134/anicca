#!/usr/bin/env node
// reality-enforce-cli.mjs — thin, side-effecting CLI adapter around the PURE
// skills/self/lib/reality-verdict-schema.mjs core. Spec: .vcsdd/features/reality-gate/specs/
// behavioral-spec.md REQ-005/REQ-006/REQ-010/REQ-018.
//
// This file owns NO judgment logic of its own — it never redefines enforceVerdict,
// validateArtifactProvenance, canonicalizeUrl, computeRowHmac/verifyRowHmac, or the
// httpStatus-range comparison; it only IMPORTS them. Its own job is strictly effectful:
// (a) read the raw verdict + captured-artifact trail from disk, (b) call the imported pure
// functions, (c) perform the two required durable-trail appends (REQ-006's verdict trail,
// REQ-010's human-review queue), and (d) print ONE decision JSON line to stdout so the bash
// wrapper (reality-verify-spawn.sh) can branch on it without re-deriving anything itself.
//
// Usage (all effectful I/O, called by reality-verify-spawn.sh only):
//   printf '%s' "<hmac-secret>" | node reality-enforce-cli.mjs \
//     --loop <name> --state-dir <dir> --raw-verdict-file <path> --pass-id <id> \
//     [--claim-type <type>] [--required-count <n>] [--claimed-urls <comma,list>] \
//     [--fixed-surface-url <url>] [--content-fingerprint <hash>] [--precommit-ts <ms>] \
//     [--capture-start-ts <ms>] [--artifacts-file <path>] [--automated-verification true|false]
import { readFileSync, appendFileSync, mkdirSync, existsSync, writeFileSync, chmodSync } from "node:fs";
import { dirname } from "node:path";
import { randomBytes } from "node:crypto";
import {
  enforceVerdict,
  buildVerdictTrailPath,
  buildHumanReviewQueuePath,
  shouldEscalateCannotVerifyStreak,
  computeRowHmac,
  verifyRowHmac,
} from "../lib/reality-verdict-schema.mjs";

// REQ-006/017 follow-on (adversary-found FIND): the durable verdict trail itself must be
// tamper-evident, or a loop can defeat the CANNOT_VERIFY escalation streak (REQ-018) by
// appending a forged row directly to the trail file to reset it. Every trail row this CLI
// writes is HMAC-signed under a PERSISTENT per-state-dir key (distinct from the per-pass
// capture secret piped in on stdin, which does not survive between passes) so a later read
// can detect a row that was appended or edited by anything other than this CLI.
// Honest limit: this key lives on the same host/uid as the loop it verifies, so a fully
// compromised loop could read it too — this raises the bar, it is not a hard wall; the real
// fix is running the verifier under a separate user/host (tracked separately, not here).
function loadOrCreateTrailKey(stateDir) {
  const dir = String(stateDir ?? "").replace(/\/+$/, "");
  const keyPath = `${dir}/.reality-trail-key`;
  if (existsSync(keyPath)) {
    const existing = readFileSync(keyPath, "utf8").trim();
    if (existing) return existing;
  }
  mkdirSync(dir, { recursive: true });
  const key = randomBytes(32).toString("hex");
  writeFileSync(keyPath, key, { mode: 0o600 });
  try {
    chmodSync(keyPath, 0o600);
  } catch {
    // best-effort on platforms where chmod after write is redundant/unsupported
  }
  return key;
}

function tamperedTrailFinding() {
  return {
    category: "post_not_publicly_visible",
    severity: "critical",
    description:
      "The durable verdict trail for this loop contains a row that does not verify under the trail's own persistent HMAC key — positive evidence the trail file was appended to or modified by something other than reality-enforce-cli.mjs.",
    evidence: { domExcerpt: "artifact_trail_tampered" },
    reason: "artifact_trail_tampered",
  };
}

function readArg(name, argv) {
  const idx = argv.indexOf(name);
  return idx === -1 ? undefined : argv[idx + 1];
}

function readJsonlRows(path) {
  if (!path || !existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function readStdinSecret() {
  try {
    return readFileSync(0, "utf8").replace(/\n$/, "");
  } catch {
    return "";
  }
}

function main() {
  const argv = process.argv.slice(2);
  const loopName = readArg("--loop", argv);
  const stateDir = readArg("--state-dir", argv);
  const rawVerdictFile = readArg("--raw-verdict-file", argv);
  const passId = readArg("--pass-id", argv);
  const claimType = readArg("--claim-type", argv) || "none";
  const requiredCount = Number(readArg("--required-count", argv) || "1");
  const claimedUrlsRaw = readArg("--claimed-urls", argv) || "";
  const claimedUrls = claimedUrlsRaw
    ? claimedUrlsRaw.split(",").map((s) => s.trim()).filter(Boolean)
    : [];
  const fixedPublicSurfaceUrl = readArg("--fixed-surface-url", argv) || undefined;
  const contentFingerprint = readArg("--content-fingerprint", argv) || undefined;
  const precommitTsRaw = readArg("--precommit-ts", argv);
  const captureStartTsRaw = readArg("--capture-start-ts", argv);
  const artifactsFile = readArg("--artifacts-file", argv);
  const automatedVerification = readArg("--automated-verification", argv) === "true";

  if (!loopName || !stateDir || !rawVerdictFile) {
    process.stderr.write(
      "reality-enforce-cli.mjs: missing required --loop/--state-dir/--raw-verdict-file\n"
    );
    process.exit(1);
  }

  // REQ-016/017: the HMAC secret is read ONLY from stdin — never argv, never an env var.
  const hmacSecret = readStdinSecret();

  let rawVerdict = null;
  try {
    rawVerdict = JSON.parse(readFileSync(rawVerdictFile, "utf8"));
  } catch {
    // Missing/malformed raw verdict file: leave rawVerdict null. enforceVerdict's own
    // validateVerdictShape step turns this into CANNOT_VERIFY/malformed_verdict_shape — this
    // CLI never second-guesses that classification itself.
    rawVerdict = null;
  }

  const capturedArtifacts = readJsonlRows(artifactsFile);

  const hasPrecommit = Boolean(contentFingerprint) || Boolean(precommitTsRaw);
  const groundTruth = {
    claimedUrls,
    passId,
    hmacSecret,
    fixedPublicSurfaceUrl,
    precommit: hasPrecommit
      ? {
          contentFingerprint,
          ts: precommitTsRaw !== undefined ? Number(precommitTsRaw) : undefined,
        }
      : undefined,
    captureStartTs: captureStartTsRaw !== undefined ? Number(captureStartTsRaw) : undefined,
  };

  const enforced = enforceVerdict(
    rawVerdict,
    capturedArtifacts,
    claimType,
    requiredCount,
    groundTruth,
    automatedVerification
  );

  // REQ-006: durable per-loop verdict trail — appended unconditionally, every outcome,
  // never filtered to only "interesting" ones.
  const trailPath = buildVerdictTrailPath(stateDir, loopName);
  mkdirSync(dirname(trailPath), { recursive: true });

  // Tamper check: read the EXISTING trail (before this pass's own row is appended) and verify
  // every row's rowHmac under the persistent trail key. Any row that doesn't verify — forged,
  // edited, or written by something other than this CLI — is positive evidence of tampering,
  // and overrides THIS pass's own outcome to FAIL (never silently trusted, never used to reset
  // the CANNOT_VERIFY streak in the caller's favor).
  const trailKey = loadOrCreateTrailKey(stateDir);
  const existingTrailRows = readJsonlRows(trailPath);
  const trailTampered = existingTrailRows.some((row) => !verifyRowHmac(trailKey, row));

  const effectiveVerdict = trailTampered ? "FAIL" : enforced.overallVerdict;
  const effectiveFindings = trailTampered ? [tamperedTrailFinding()] : enforced.findings || [];

  const trailRow = {
    ts: Date.now(),
    loopName,
    passId,
    overallVerdict: effectiveVerdict,
    findings: effectiveFindings,
    RESULT: rawVerdictFile,
  };
  trailRow.rowHmac = computeRowHmac(trailKey, trailRow);
  appendFileSync(trailPath, JSON.stringify(trailRow) + "\n");

  // REQ-010/REQ-018 routing: FAIL always escalates to self-fix.sh (a code/behavior bug — or a
  // tampered trail — the caller must investigate). CANNOT_VERIFY escalates to self-fix.sh only
  // on the SECOND CONSECUTIVE occurrence for this loop (PROP-055) — the first goes to the
  // human-review queue only. shouldEscalateCannotVerifyStreak is IMPORTED, never re-derived here.
  let escalateSelfFix = false;
  let humanReviewAppended = false;
  if (effectiveVerdict === "FAIL") {
    escalateSelfFix = true;
  } else if (effectiveVerdict === "CANNOT_VERIFY") {
    const trailSoFar = [...existingTrailRows, trailRow]; // both halves already HMAC-verified above
    escalateSelfFix = shouldEscalateCannotVerifyStreak(trailSoFar);
    const queuePath = buildHumanReviewQueuePath(stateDir, loopName);
    mkdirSync(dirname(queuePath), { recursive: true });
    const firstFinding = effectiveFindings[0] || {};
    appendFileSync(
      queuePath,
      JSON.stringify({
        ts: Date.now(),
        loopName,
        passId,
        reason: firstFinding.reason || "cannot_verify",
        claimSummary: firstFinding.description || "",
      }) + "\n"
    );
    humanReviewAppended = true;
  }

  process.stdout.write(
    JSON.stringify({
      overallVerdict: effectiveVerdict,
      escalateSelfFix,
      humanReviewAppended,
      trailPath,
      findings: effectiveFindings,
    }) + "\n"
  );
}

main();
