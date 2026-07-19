import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { getStore } from "@netlify/blobs";

const CAMPAIGN =
  "utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing";
const allowedAgents = new Set(
  JSON.parse(readFileSync(new URL("./allowed-agents.json", import.meta.url), "utf8")),
);

const redirect = (location) =>
  new Response(null, { status: 302, headers: { location, "cache-control": "no-store" } });

export default async (request) => {
  if (request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET" } });
  }

  const segments = new URL(request.url).pathname.split("/").filter(Boolean);
  let agentId = "";
  try {
    agentId = decodeURIComponent(segments.at(-1) || "");
  } catch {
    return redirect("https://capafy.ai/");
  }
  if (!allowedAgents.has(agentId)) return redirect("https://capafy.ai/");

  const store = getStore("capafy-attribution-clicks");
  await store.set(`clicks/${agentId}/${Date.now()}-${randomUUID()}`, "1");
  return redirect(`https://capafy.ai/agent/${encodeURIComponent(agentId)}?${CAMPAIGN}`);
};
