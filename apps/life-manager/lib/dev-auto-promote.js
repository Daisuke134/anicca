"use strict";


const ALLOWED_PATHS = Object.freeze([
  /^apps\/life-manager\/(?:lib|test|scripts|eval)\/[A-Za-z0-9_./-]+\.(?:js|cjs|mjs|json|sh)$/,
  /^apps\/life-manager\/package\.json$/,
  /^docs\/evidence\/10e-[A-Za-z0-9_.-]+\.md$/,
  /^docs\/superpowers\/specs\/2026-07-19-anicca-one-repo-consolidation-spec\.md$/,
  /^execution-notes\.md$/,
]);

const BLOCKED_ACTION_PATTERNS = Object.freeze({
  outreach_send: /\b(?:sendUnsolicitedEmail|sendMail|makeCall|postToSocial|telegramSend)\b/i,
  provider_account_mutation: /connected_accounts[^\n]*(?:PATCH|DELETE)|\bdisconnectProvider\b/i,
  secret_change: /\brailway\s+variable\s+set\b|\b(?:api|secret|token)[_-]?key\s*=/i,
  wallet_transfer: /\b(?:sendTransaction|eth_sendRawTransaction|wallet\.transfer)\b/i,
});


function uniqueSorted(values) {
  return [...new Set(values)].sort();
}


function evaluatePromotion(candidate = {}) {
  const reasons = [];
  const closing = Array.isArray(candidate.closingIssueNumbers)
    ? candidate.closingIssueNumbers.map(Number)
    : [];
  if (closing.length !== 1 || closing[0] !== Number(candidate.issueNumber)) reasons.push("issue_count");
  if (candidate.openPrsForIssue !== 1) reasons.push("pr_count");
  if (candidate.issueIsPrivacySafeError !== true) reasons.push("issue_contract");
  if (candidate.baseRefName !== "main") reasons.push("base_branch");
  if (!/^[a-f0-9]{40}$/.test(String(candidate.headOid || ""))
      || candidate.localHeadOid !== candidate.headOid) reasons.push("head_drift");
  if (candidate.mergeable !== "MERGEABLE") reasons.push("mergeable");

  const paths = Array.isArray(candidate.changedFiles) ? candidate.changedFiles : [];
  if (!paths.length || paths.some((file) => !ALLOWED_PATHS.some((pattern) => pattern.test(file)))) {
    reasons.push("path_allowlist");
  }
  const blockedActions = [];
  if (paths.some((file) => /(^|\/)migrations?\//i.test(file))) blockedActions.push("migration");
  const added = (Array.isArray(candidate.addedLines) ? candidate.addedLines : [])
    .map((entry) => typeof entry === "string" ? { path: "", line: entry } : entry)
    .filter((entry) => !(
      entry
      && entry.path === "apps/life-manager/lib/dev-auto-promote.js"
      && /^\s*(?:outreach_send|provider_account_mutation|secret_change|wallet_transfer):\s*\//.test(entry.line)
    ))
    .map((entry) => String(entry && entry.line || ""))
    .join("\n");
  for (const [name, pattern] of Object.entries(BLOCKED_ACTION_PATTERNS)) {
    if (pattern.test(added)) blockedActions.push(name);
  }
  if (blockedActions.length) reasons.push("blocked_actions");

  const gates = candidate.gates || {};
  for (const gate of ["tests", "evals", "privacy", "adversary", "cleanWorktree"]) {
    if (gates[gate] !== true) reasons.push(gate);
  }
  return Object.freeze({
    allowed: reasons.length === 0,
    reasons: Object.freeze(uniqueSorted(reasons)),
    blockedActions: Object.freeze(uniqueSorted(blockedActions)),
  });
}


function decideDeploymentOutcome({
  exactCommit,
  deploymentStatus,
  healthOk,
  previousDeploymentHealthy,
} = {}) {
  if (!exactCommit) return { action: "wait" };
  if (deploymentStatus === "SUCCESS" && healthOk === true) return { action: "complete" };
  if (previousDeploymentHealthy !== true) return { action: "stop" };
  if (deploymentStatus === "FAILED" || (deploymentStatus === "SUCCESS" && healthOk === false)) {
    return { action: "rollback" };
  }
  return { action: "wait" };
}


module.exports = {
  ALLOWED_PATHS,
  BLOCKED_ACTION_PATTERNS,
  evaluatePromotion,
  decideDeploymentOutcome,
};
