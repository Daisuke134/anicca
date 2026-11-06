import { getStore } from "@netlify/blobs";
import { readFileSync } from "node:fs";

const allowedAgents = JSON.parse(
  readFileSync(new URL("./allowed-agents.json", import.meta.url), "utf8"),
);

// Keys: clicks/<agent>/<ts>-<uuid> (legacy) or clicks/<agent>/<platform>/<post>/<ts>-<uuid>.
export const summarize = (keys, agents = allowedAgents, bodies) => {
  const attribution = { recorded: 0, unavailable: 0, agents: {} };
  const counts = Object.fromEntries(agents.map((agentId) => [agentId, 0]));
  const byAgent = Object.fromEntries(
    agents.map((agentId) => [agentId, { total: 0, platforms: {}, posts: {} }]),
  );
  const platforms = {};
  let total = 0;
  const excluded_synthetic = { total: 0, posts: {} };
  for (const key of keys) {
    const parts = key.split("/");
    const agentId = parts[1];
    if (!agentId) continue;
    const platform = parts.length >= 5 ? parts[2] : "legacy";
    const post = parts.length >= 5 ? `${parts[2]}/${parts[3]}` : null;
    // Exact probe documented by official readback; preserve every raw blob.
    // Do not infer synthetic traffic from a generic test-looking name.
    if (post === "x/test_hq_4a481d") {
      excluded_synthetic.total += 1;
      excluded_synthetic.posts[post] = (excluded_synthetic.posts[post] || 0) + 1;
      continue;
    }
    if (bodies) {
      const body = bodies.get(key);
      const token = (value) => typeof value === "string" && /^(?:[A-Za-z0-9_-]{1,80})?$/.test(value);
      if (body?.schema_version === 1 && body.agentId === agentId &&
          [body.platform, body.post, body.ct].every(token) &&
          body.platform === (parts.length >= 5 ? parts[2] : "") &&
          (body.platform ? (body.post || "_") === parts[3] : body.post === "")) {
        attribution.recorded += 1;
        if (body.ct) {
          const row = (attribution.agents[agentId] ||= Object.create(null));
          row[body.ct] = (row[body.ct] || 0) + 1;
        }
      } else attribution.unavailable += 1;
    }
    counts[agentId] = (counts[agentId] || 0) + 1;
    const row = (byAgent[agentId] ||= { total: 0, platforms: {}, posts: {} });
    row.total += 1;
    row.platforms[platform] = (row.platforms[platform] || 0) + 1;
    if (post) row.posts[post] = (row.posts[post] || 0) + 1;
    platforms[platform] = (platforms[platform] || 0) + 1;
    total += 1;
  }
  return { counts, detail: { total, platforms, agents: byAgent, excluded_synthetic, ...(bodies ? { attribution } : {}) } };
};

export default async (request) => {
  if (request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET" } });
  }
  const keys = [];
  const store = getStore("capafy-attribution-clicks");
  let cursor;
  do {
    const page = await store.list({ prefix: "clicks/", cursor });
    for (const blob of page.blobs) keys.push(blob.key);
    cursor = page.cursor;
  } while (cursor);

  const params = new URL(request.url).searchParams;
  const detailed = params.get("detail") === "1";
  let bodies;
  if (detailed && params.get("attribution") === "1") {
    bodies = new Map();
    for (const key of keys) {
      const text = await store.get(key);
      try { bodies.set(key, JSON.parse(text)); }
      catch { bodies.set(key, null); }
    }
  }
  const { counts, detail } = summarize(keys, allowedAgents, bodies);
  // Default body stays the flat {agent_id: clicks} map for existing readers.
  const body = detailed ? detail : counts;
  return Response.json(body, { headers: { "cache-control": "no-store" } });
};
