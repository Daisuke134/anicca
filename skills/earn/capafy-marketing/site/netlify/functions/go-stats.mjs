import { getStore } from "@netlify/blobs";
import { readFileSync } from "node:fs";

const allowedAgents = JSON.parse(
  readFileSync(new URL("./allowed-agents.json", import.meta.url), "utf8"),
);

export default async (request) => {
  if (request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET" } });
  }

  const counts = Object.fromEntries(allowedAgents.map((agentId) => [agentId, 0]));
  const store = getStore("capafy-attribution-clicks");
  let cursor;
  do {
    const page = await store.list({ prefix: "clicks/", cursor });
    for (const blob of page.blobs) {
      const agentId = blob.key.split("/")[1];
      if (agentId) counts[agentId] = (counts[agentId] || 0) + 1;
    }
    cursor = page.cursor;
  } while (cursor);

  return Response.json(counts, { headers: { "cache-control": "no-store" } });
};
