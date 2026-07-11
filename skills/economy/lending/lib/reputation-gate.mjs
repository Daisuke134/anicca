// economy/lending/lib/reputation-gate.mjs — franklin-reputation-gasless G3: JS port of Azeth/UFX's
// ReputationGateHook.beforeAction (23 §11 部品3, docs/superpowers/specs/2026-07-12-franklin-reputation-
// gasless-design.md §1 G3). Reads ERC-8004 Reputation via `getSummaryFn` (dependency-injected -- defaults
// to the real gig/lib/reputation.mjs::getReputationSummary in production, same DI convention as
// gig.mjs's own `pay`/`verifyIdentityFn`/`ensureGasFn` parameters) and decides whether a borrower's
// on-chain track record clears the configured (minScore, minJobCount) bar.
//
// ★段階導入 / fail-open (spec §1 G3 MUST: "未設定（min=0）なら素通り = fail-open で段階導入")★:
//   - BOTH minScore<=0 AND minJobCount<=0 (the default) -> passthrough, getSummaryFn is never even
//     called. This lets the gate be adopted gradually per-lender without breaking existing borrowers.
//   - A configured gate that CANNOT be evaluated (no clientAddresses, or getSummaryFn itself fails, e.g.
//     RPC outage) also fail-opens (spec §4 MONEY-SAFETY: "reputation は fail-open" applies to reads too
//     -- an on-chain outage must never itself block lending).
//   - The ONLY fail-CLOSED case is a configured gate with no borrowerAgentId at all: that is not a
//     reputation-read failure, it is a caller bug (an agent with no on-chain identity cannot be
//     evaluated against an on-chain gate the lender explicitly asked for), so it is rejected rather than
//     silently passed through.
import { getReputationSummary as getReputationSummaryReal } from "../../gig/lib/reputation.mjs";

export async function passesOnchainReputationGate({
  borrowerAgentId,
  minScore = 0,
  minJobCount = 0,
  clientAddresses = [],
  tag1 = "",
  tag2 = "",
  getSummaryFn = getReputationSummaryReal,
} = {}) {
  const gateConfigured = minScore > 0 || minJobCount > 0;
  if (!gateConfigured) return { eligible: true, reason: "reputation_gate_unset" };

  if (!borrowerAgentId) return { eligible: false, reason: "no_borrower_agent_id" };
  if (!Array.isArray(clientAddresses) || clientAddresses.length === 0) {
    return { eligible: true, reason: "fail_open_no_client_addresses" };
  }

  const summary = await getSummaryFn({ agentId: borrowerAgentId, clientAddresses, tag1, tag2 });
  if (!summary || !summary.ok) {
    return { eligible: true, reason: "fail_open_reputation_read_failed" };
  }

  if (minJobCount > 0 && summary.count < minJobCount) {
    return { eligible: false, reason: "insufficient_job_count" };
  }
  if (minScore > 0 && summary.summaryValue < minScore) {
    return { eligible: false, reason: "insufficient_score" };
  }
  return { eligible: true, reason: "ok" };
}
