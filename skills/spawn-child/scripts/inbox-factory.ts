// SPDX-License-Identifier: MIT
// inbox-factory.ts — provision anicca-002@agentmail.to via AgentMail SDK.
//
// Mirrors spec 10's inboxes.ts but parametric on instance_id. Free tier cap = 3
// inboxes (already verified). If we hit the cap, fall back to auto-assigned
// address (= still owned by the same org_id so anicca-001 can read it).

import { AgentMailClient } from "agentmail";

const apiKey = process.env.AGENTMAIL_API_KEY;
if (!apiKey) {
  console.error("AGENTMAIL_API_KEY missing — set in ~/.openclaw/.env");
  process.exit(2);
}

const instanceId = process.env.ANICCA_INSTANCE_ID ?? "anicca-002";

const client = new AgentMailClient({ apiKey });

interface Out {
  ok: boolean;
  instance_id: string;
  inbox_email: string;
  inbox_id: string | null;
  custom_address_attempted: string;
  custom_address_succeeded: boolean;
  note: string;
}

async function main(): Promise<number> {
  const customAddress = `${instanceId}-claude`;
  let inboxEmail: string;
  let inboxId: string | null = null;
  let succeeded = false;
  let note: string;

  try {
    const inbox = await client.inboxes.create({ request: { address: customAddress } });
    inboxEmail = (inbox as any).email ?? `${customAddress}@agentmail.to`;
    inboxId = (inbox as any).inbox_id ?? null;
    succeeded = true;
    note = `provisioned custom address`;
  } catch (err: any) {
    const msg = String(err?.message ?? err);
    if (msg.includes("IsTakenError") || msg.includes("limit") || msg.includes("cap")) {
      // Fallback — let the platform assign an auto address
      const inbox = await client.inboxes.create({ request: {} });
      inboxEmail = (inbox as any).email ?? "<unknown>";
      inboxId = (inbox as any).inbox_id ?? null;
      note = `custom address taken or cap reached; assigned auto address: ${msg.slice(0, 80)}`;
    } else {
      throw err;
    }
  }

  const out: Out = {
    ok: true,
    instance_id: instanceId,
    inbox_email: inboxEmail,
    inbox_id: inboxId,
    custom_address_attempted: `${customAddress}@agentmail.to`,
    custom_address_succeeded: succeeded,
    note,
  };
  console.log(JSON.stringify(out, null, 2));
  return 0;
}

main().then((c) => process.exit(c)).catch((e) => {
  console.error("inbox-factory error:", e);
  process.exit(2);
});
