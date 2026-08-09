import { getAgentByName } from "agents";
import { FranklinAgent } from "./franklin-agent.js";
import type { FranklinEnv } from "./contracts.js";
import { parseFranklinId, type FranklinId } from "./contracts.js";

export { FranklinAgent };

export default {
  async fetch(request: Request, env: FranklinEnv): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ service: "franklin-cloudflare", status: "ok" });
    }

    const statusMatch = /^\/api\/franklin\/([^/]+)\/status$/.exec(url.pathname);
    if (request.method === "GET" && statusMatch !== null) {
      const franklinId = parseFranklinId(statusMatch[1]);
      return franklinId === null
        ? Response.json({ error: "invalid_franklin_id" }, { status: 400 })
        : forwardToAgent(env, franklinId, "/status", request);
    }

    const mutationMatch = /^\/internal\/franklin\/([^/]+)\/state$/.exec(url.pathname);
    if (request.method === "POST" && mutationMatch !== null) {
      if (!isAuthorized(request, env)) return Response.json({ error: "unauthorized" }, { status: 401 });

      const franklinId = parseFranklinId(mutationMatch[1]);
      return franklinId === null
        ? Response.json({ error: "invalid_franklin_id" }, { status: 400 })
        : forwardToAgent(env, franklinId, "/state", request);
    }

    return new Response("Not found", { status: 404 });
  }
} satisfies ExportedHandler<FranklinEnv>;

async function forwardToAgent(
  env: FranklinEnv,
  franklinId: FranklinId,
  pathname: "/status" | "/state",
  request: Request
): Promise<Response> {
  const agent = await getAgentByName<FranklinEnv, FranklinAgent, { franklinId: FranklinId }>(env.FRANKLIN_AGENT, franklinId, {
    props: { franklinId }
  });
  return agent.fetch(new Request(`https://franklin-agent.internal${pathname}`, request));
}

function isAuthorized(request: Request, env: FranklinEnv): boolean {
  const token = env.INTERNAL_API_TOKEN;
  return token !== undefined && request.headers.get("authorization") === `Bearer ${token}`;
}
