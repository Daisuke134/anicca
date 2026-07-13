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
import { readFileSync, appendFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";
import {
  enforceVerdict,
  buildVerdictTrailPath,
  buildHumanReviewQueuePath,
  shouldEscalateCannotVerifyStreak,
} from "../lib/reality-verdict-schema.mjs";

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
  const trailRow = {
    ts: Date.now(),
    loopName,
    passId,
    overallVerdict: enforced.overallVerdict,
    findings: enforced.findings || [],
    RESULT: rawVerdictFile,
  };
  appendFileSync(trailPath, JSON.stringify(trailRow) + "\n");

  // REQ-010/REQ-018 routing: FAIL always escalates to self-fix.sh (a code/behavior bug the
  // caller must investigate). CANNOT_VERIFY escalates to self-fix.sh only on the SECOND
  // CONSECUTIVE occurrence for this loop (PROP-055) — the first goes to the human-review
  // queue only. shouldEscalateCannotVerifyStreak is IMPORTED, never re-derived here.
  let escalateSelfFix = false;
  let humanReviewAppended = false;
  if (enforced.overallVerdict === "FAIL") {
    escalateSelfFix = true;
  } else if (enforced.overallVerdict === "CANNOT_VERIFY") {
    const trailSoFar = readJsonlRows(trailPath); // includes the row just appended (last line)
    escalateSelfFix = shouldEscalateCannotVerifyStreak(trailSoFar);
    const queuePath = buildHumanReviewQueuePath(stateDir, loopName);
    mkdirSync(dirname(queuePath), { recursive: true });
    const firstFinding = (enforced.findings || [])[0] || {};
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
      overallVerdict: enforced.overallVerdict,
      escalateSelfFix,
      humanReviewAppended,
      trailPath,
      findings: enforced.findings || [],
    }) + "\n"
  );
}

main();
