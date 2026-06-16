#!/usr/bin/env node
// send-report — deliver a wake/daily report to the USER's own Gmail via Composio, when the
// user has an ACTIVE Composio gmail connection. Called from anicca-report.sh. If the user is
// NOT connected (or anything is missing), it exits non-zero so the shell falls back to the
// existing AgentMail path. Honest (HARD 0.24): a real Composio API call is made — no fakes.
//
// Env:
//   COMPOSIO_API_KEY            required — Composio project key
//   ANICCA_REPORT_USER_ID       required — the Composio connection owner (the user's user_id)
//   ANICCA_REPORT_TO            optional — recipient address (default: the connection owner's inbox)
//
// Usage: node send-report.mjs "<subject>" "<body>" [to]
//   exit 0 = sent via Composio Gmail; exit 2 = not connected (caller should fall back);
//   exit 1 = error.
import { hasGmailConnection, sendGmail } from "./composio-gmail.mjs";

async function main() {
  const [, , subject, body, toArg] = process.argv;
  const apiKey = process.env.COMPOSIO_API_KEY;
  const userId = process.env.ANICCA_REPORT_USER_ID;
  const to = toArg || process.env.ANICCA_REPORT_TO;
  if (!apiKey || !userId) {
    console.error("send-report: COMPOSIO_API_KEY + ANICCA_REPORT_USER_ID required — falling back");
    process.exit(2);
  }
  if (!subject || !body) {
    console.error("send-report: subject + body required");
    process.exit(1);
  }
  if (!to) {
    console.error("send-report: no recipient (ANICCA_REPORT_TO) — falling back");
    process.exit(2);
  }
  const conn = await hasGmailConnection({ userId, apiKey });
  if (!conn.connected) {
    console.error(`send-report: user ${userId} has no ACTIVE Composio gmail connection — falling back`);
    process.exit(2);
  }
  await sendGmail({
    to,
    subject,
    body,
    userId,
    connectedAccountId: conn.connectedAccountId,
    apiKey,
  });
  console.error(`send-report: sent to ${to} via Composio (account ${conn.connectedAccountId})`);
  process.exit(0);
}

main().catch((e) => {
  console.error(`send-report: ${e.message || e}`);
  process.exit(1);
});
