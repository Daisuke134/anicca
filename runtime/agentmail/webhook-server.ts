// SPDX-License-Identifier: MIT
// runtime/agentmail/webhook-server.ts — Express receiver for AgentMail webhooks.
//
// Spec 10 — microtask 10.T2 + 10.T5.
//
// Behaviour:
//   - POST /agentmail   : verify Svix HMAC, enqueue event JSON to inbox-queue.jsonl
//   - GET  /healthz     : liveness probe
//
// Anti-human-loop (HARD RULE #-2): on signature failure or malformed body we LOG
// and still return 200 so AgentMail's Svix retries do not pile up. The error is
// captured in the queue file with `status: "rejected"` so a downstream daemon
// (anicca-friction-fixer / Conway) can attribute it without a human prompt.
import express, { type Request, type Response } from "express";
import bodyParser from "body-parser";
import { Webhook, WebhookVerificationError } from "svix";
import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { homedir } from "node:os";

const PORT = Number.parseInt(process.env.AGENTMAIL_WEBHOOK_PORT ?? "8810", 10);
const QUEUE_PATH = process.env.AGENTMAIL_QUEUE_PATH
  ?? `${homedir()}/.openclaw/state/inbox-queue.jsonl`;
const SIGNING_SECRET = process.env.AGENTMAIL_WEBHOOK_SECRET ?? "";

mkdirSync(dirname(QUEUE_PATH), { recursive: true });

type QueueRecord = {
  received_at: string;
  status: "verified" | "rejected" | "unverified";
  reason?: string;
  svix_id?: string;
  svix_timestamp?: string;
  event_type?: string;
  payload: unknown;
};

function enqueue(record: QueueRecord): void {
  try {
    appendFileSync(QUEUE_PATH, JSON.stringify(record) + "\n", { encoding: "utf8" });
  } catch (err) {
    // Last resort: dump to stderr so launchd captures it; never throw to caller.
    process.stderr.write(`[agentmail-webhook] enqueue failed: ${(err as Error).message}\n`);
  }
}

const app = express();

app.get("/healthz", (_req, res) => {
  res.json({ ok: true, port: PORT, queue: QUEUE_PATH, signed: SIGNING_SECRET.length > 0 });
});

// Raw body required for Svix HMAC verification (express.json() would mutate it).
app.post(
  "/agentmail",
  bodyParser.raw({ type: "*/*", limit: "10mb" }),
  (req: Request, res: Response) => {
    const rawBuf: Buffer = Buffer.isBuffer(req.body) ? req.body : Buffer.from("");
    const rawStr = rawBuf.toString("utf8");

    const svixId = String(req.header("svix-id") ?? "");
    const svixTimestamp = String(req.header("svix-timestamp") ?? "");
    const svixSignature = String(req.header("svix-signature") ?? "");

    let verified: unknown;
    let status: QueueRecord["status"] = "unverified";
    let reason: string | undefined;

    if (SIGNING_SECRET) {
      try {
        const wh = new Webhook(SIGNING_SECRET);
        verified = wh.verify(rawStr, {
          "svix-id": svixId,
          "svix-timestamp": svixTimestamp,
          "svix-signature": svixSignature,
        });
        status = "verified";
      } catch (err) {
        status = "rejected";
        reason = err instanceof WebhookVerificationError
          ? `svix-verify: ${err.message}`
          : `verify-error: ${(err as Error).message}`;
        try { verified = JSON.parse(rawStr); } catch { verified = rawStr; }
      }
    } else {
      // No secret configured (local smoke test). Best-effort parse, mark unverified.
      reason = "AGENTMAIL_WEBHOOK_SECRET unset — skipping HMAC";
      try { verified = JSON.parse(rawStr); } catch { verified = rawStr; }
    }

    const payload = verified as { event_type?: string; type?: string } | string;
    const eventType = typeof payload === "object" && payload !== null
      ? (payload.event_type ?? payload.type)
      : undefined;

    const record: QueueRecord = {
      received_at: new Date().toISOString(),
      status,
      reason,
      svix_id: svixId || undefined,
      svix_timestamp: svixTimestamp || undefined,
      event_type: eventType,
      payload: verified,
    };
    enqueue(record);

    process.stdout.write(
      `[agentmail-webhook] ${status} event=${eventType ?? "?"} id=${svixId || "-"}\n`
    );

    // Always 200 — retry storms harm us more than silently dropping bad sigs.
    res.status(200).json({ ok: true, status });
  }
);

const server = app.listen(PORT, () => {
  process.stdout.write(`[agentmail-webhook] listening :${PORT} queue=${QUEUE_PATH}\n`);
});

function shutdown(signal: string): void {
  process.stdout.write(`[agentmail-webhook] ${signal} — shutting down\n`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 5000).unref();
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT",  () => shutdown("SIGINT"));
