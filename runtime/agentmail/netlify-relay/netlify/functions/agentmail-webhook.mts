// netlify/functions/agentmail-webhook.mts
//
// Stable public endpoint for AgentMail webhooks.
// Lives at https://anicca-agentmail-webhook.netlify.app/agentmail (via /agentmail redirect).
//
// Behaviour:
//   - GET  /healthz   → returns {ok:true, forward: <CLOUDFLARE_TUNNEL_URL>}
//   - POST /agentmail → verify Svix HMAC against AGENTMAIL_WEBHOOK_SECRET, then forward
//                       the raw body + svix-* headers to CLOUDFLARE_TUNNEL_URL/agentmail
//                       so the on-prem :8810 receiver can re-verify and enqueue.
//
// When the trycloudflare URL rotates, we update CLOUDFLARE_TUNNEL_URL via Netlify API
// (no AgentMail-side change needed → URL stays stable forever).
//
// Anti-human-loop: bad signatures still return 200 (matches on-prem behaviour, avoids
// Svix retry storms). Forward failures are surfaced via 502 so we see them in Netlify logs.
import type { Context } from "@netlify/functions";
import { Webhook, WebhookVerificationError } from "svix";

export default async (req: Request, _ctx: Context): Promise<Response> => {
  const url = new URL(req.url);

  if (req.method === "GET" || url.pathname.endsWith("/healthz")) {
    return Response.json({
      ok: true,
      tunnel: process.env.CLOUDFLARE_TUNNEL_URL ?? null,
      signed: Boolean(process.env.AGENTMAIL_WEBHOOK_SECRET),
      ts: new Date().toISOString(),
    });
  }

  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }

  const rawBody = await req.text();
  const secret = process.env.AGENTMAIL_WEBHOOK_SECRET ?? "";
  const svixId = req.headers.get("svix-id") ?? "";
  const svixTimestamp = req.headers.get("svix-timestamp") ?? "";
  const svixSignature = req.headers.get("svix-signature") ?? "";

  let verifyStatus: "verified" | "rejected" | "unsigned" = "unsigned";
  let verifyReason: string | undefined;

  if (secret) {
    try {
      const wh = new Webhook(secret);
      wh.verify(rawBody, {
        "svix-id": svixId,
        "svix-timestamp": svixTimestamp,
        "svix-signature": svixSignature,
      });
      verifyStatus = "verified";
    } catch (err) {
      verifyStatus = "rejected";
      verifyReason = err instanceof WebhookVerificationError
        ? `svix: ${err.message}`
        : `verify: ${(err as Error).message}`;
      // Log to Netlify Function logs but still return 200 to suppress retries.
      console.warn(`[agentmail-relay] rejected: ${verifyReason}`);
      return Response.json({ ok: true, status: "rejected", reason: verifyReason }, { status: 200 });
    }
  }

  const tunnel = process.env.CLOUDFLARE_TUNNEL_URL;
  if (!tunnel) {
    console.error("[agentmail-relay] CLOUDFLARE_TUNNEL_URL missing — dropping event");
    return Response.json({ ok: true, status: "no-forward" }, { status: 200 });
  }

  const forwardUrl = tunnel.replace(/\/+$/, "") + "/agentmail";

  try {
    const forwardResp = await fetch(forwardUrl, {
      method: "POST",
      headers: {
        "content-type": req.headers.get("content-type") ?? "application/json",
        "svix-id": svixId,
        "svix-timestamp": svixTimestamp,
        "svix-signature": svixSignature,
      },
      body: rawBody,
      signal: AbortSignal.timeout(8000),
    });

    const text = await forwardResp.text().catch(() => "");
    console.log(`[agentmail-relay] forwarded → ${forwardResp.status} (${verifyStatus}) id=${svixId}`);
    return Response.json({
      ok: true,
      status: verifyStatus,
      forwarded_code: forwardResp.status,
      forwarded_body: text.slice(0, 200),
    });
  } catch (err) {
    console.error(`[agentmail-relay] forward failed: ${(err as Error).message}`);
    // AgentMail will retry on 5xx; let it queue until tunnel recovers.
    return new Response(`forward error: ${(err as Error).message}`, { status: 502 });
  }
};

export const config = {
  path: ["/agentmail", "/healthz", "/.netlify/functions/agentmail-webhook"],
};
