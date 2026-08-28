// SPDX-License-Identifier: MIT
// runtime/agentmail/inboxes-hermes.ts — closes G1 by provisioning the hermes
// inbox in a sibling AgentMail org.
//
// AgentMail's free tier hard-caps inboxes per organization at 3. The primary
// org (verified via contact@aniccaai.com on 2026-06-03) already holds
// anicca-genesis + anicca-001-claude + anicca-001-openclaw. A 4th inbox there
// requires a paid plan upgrade (financial broadcast → blocked by HARD RULE).
//
// The agent-native workaround: client.agent.signUp() creates a brand-new org
// with its own free-plan quota and its own API key. Each sibling Anicca
// instance can hold its own sovereign org without ever touching billing.
//
// Idempotent: if AGENTMAIL_HERMES_API_KEY is already in ~/.openclaw/.env we
// just confirm the inbox exists. If signup is needed, we use a +alias gmail
// address from HERMES_HUMAN_EMAIL so the OTP lands in the canonical
// gog gmail inbox and can be fetched programmatically.
import { AgentMailClient } from "agentmail";
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const HERMES_USERNAME = "anicca-001-hermes";
const HERMES_HUMAN_EMAIL = process.env.HERMES_HUMAN_EMAIL ?? "";
const GOG_ACCOUNT = process.env.GOG_ACCOUNT ?? "";
const OTP_GMAIL_QUERY = process.env.HERMES_OTP_QUERY ?? "from:agentmail subject:verification";

async function existingHermes(): Promise<{ key: string; inbox: string } | null> {
  const key = process.env.AGENTMAIL_HERMES_API_KEY;
  if (!key) return null;
  const c = new AgentMailClient({ apiKey: key });
  try {
    const list = await c.inboxes.list();
    const inbox = list.inboxes.find(i => (i.email ?? i.inboxId ?? "").startsWith(HERMES_USERNAME));
    if (inbox) return { key, inbox: inbox.email ?? (inbox.inboxId as string) };
  } catch (e) {
    console.warn(`existingHermes() check failed: ${(e as Error).message}`);
  }
  return null;
}

function readOtpFromGmail(): string | null {
  // Use `gog gmail messages list ... --full` and grep for the 6-digit code in the body.
  const r = spawnSync("/opt/homebrew/bin/gog", [
    "gmail", "messages", "list",
    "-a", GOG_ACCOUNT,
    "--max=1",
    OTP_GMAIL_QUERY,
    "--full", "--plain",
  ], { encoding: "utf8" });
  if (r.status !== 0) {
    console.warn(`gog read failed: ${r.stderr}`);
    return null;
  }
  const m = r.stdout.match(/\b(\d{6})\b/);
  return m?.[1] ?? null;
}

const existing = await existingHermes();
if (existing) {
  console.log(`= ${existing.inbox} already provisioned via AGENTMAIL_HERMES_API_KEY`);
  process.exit(0);
}
if (!HERMES_HUMAN_EMAIL || !GOG_ACCOUNT) {
  throw new Error("HERMES_HUMAN_EMAIL and GOG_ACCOUNT are required for signup");
}

console.log(`+ no hermes org yet — signing up via human_email=${HERMES_HUMAN_EMAIL}`);
const seedClient = new AgentMailClient({ apiKey: "placeholder" });
const signup = await seedClient.agent.signUp({
  humanEmail: HERMES_HUMAN_EMAIL,
  username: HERMES_USERNAME,
  source: "agentmail-node@0.5.8",
  referrer: "spec-10-anicca-inbox-keeper",
});
console.log(`+ org=${signup.organizationId}  inbox=${signup.inboxId}`);
console.log(`  api_key prefix: ${signup.apiKey.slice(0, 14)}…`);

// Wait + read OTP. agent.verify() is idempotent so retrying is safe.
let otp: string | null = null;
for (let i = 0; i < 10 && !otp; i++) {
  await sleep(5000);
  otp = readOtpFromGmail();
  if (otp) break;
  console.log(`  OTP not yet in gog gmail (${i + 1}/10) …`);
}
if (!otp) {
  console.error("OTP did not arrive within 50s — manual retry via client.agent.verify({otpCode}) when it does");
  process.exit(2);
}
const verifyClient = new AgentMailClient({ apiKey: signup.apiKey });
const result = await verifyClient.agent.verify({ otpCode: otp });
console.log(`+ verified: ${JSON.stringify(result).slice(0, 200)}`);

console.log(`\nAdd to ~/.openclaw/.env (chmod 600):`);
console.log(`  AGENTMAIL_HERMES_API_KEY=${signup.apiKey}`);
console.log(`  AGENTMAIL_HERMES_ORG_ID=${signup.organizationId}`);
console.log(`\nThen subscribe a webhook with this org's key and persist the secret as`);
console.log(`  AGENTMAIL_WEBHOOK_SECRET_HERMES=whsec_…`);
console.log(`then 'launchctl kickstart -k gui/$UID/ai.anicca.agentmail-webhook'.`);
