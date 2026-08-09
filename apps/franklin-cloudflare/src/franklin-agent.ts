import { Agent } from "agents";
import type {
  FranklinAgentProps,
  FranklinEnv,
  FranklinMutation,
  FranklinState
} from "./contracts.js";

export class FranklinAgent extends Agent<FranklinEnv, FranklinState, FranklinAgentProps> {
  initialState: FranklinState = {
    franklinId: null,
    revision: 0,
    lastCommand: null,
    updatedAt: null
  };

  onStart(props?: FranklinAgentProps): void {
    if (this.state.franklinId !== null || props?.franklinId === undefined) return;

    this.setState({ ...this.state, franklinId: props.franklinId });
  }

  async onRequest(request: Request): Promise<Response> {
    const pathname = new URL(request.url).pathname;

    if (request.method === "GET" && pathname === "/status") {
      return Response.json({ franklinId: this.state.franklinId, state: this.state });
    }

    if (request.method === "POST" && pathname === "/state") {
      if (!isAuthorized(request, this.env)) return unauthorizedResponse();

      const mutation = await readMutation(request);
      if (mutation === null) {
        return Response.json({ error: "invalid_mutation" }, { status: 400 });
      }

      const nextState: FranklinState = {
        ...this.state,
        revision: this.state.revision + 1,
        lastCommand: mutation.command,
        updatedAt: Date.now()
      };
      this.setState(nextState);
      return Response.json({ franklinId: nextState.franklinId, state: nextState });
    }

    return new Response("Not found", { status: 404 });
  }
}

function isAuthorized(request: Request, env: FranklinEnv): boolean {
  const token = env.INTERNAL_API_TOKEN;
  return token !== undefined && request.headers.get("authorization") === `Bearer ${token}`;
}

function unauthorizedResponse(): Response {
  return Response.json({ error: "unauthorized" }, { status: 401 });
}

async function readMutation(request: Request): Promise<FranklinMutation | null> {
  try {
    const value: unknown = await request.json();
    if (
      typeof value !== "object" ||
      value === null ||
      !("command" in value) ||
      typeof value.command !== "string" ||
      value.command.length === 0 ||
      value.command.length > 256
    ) {
      return null;
    }

    return { command: value.command };
  } catch {
    return null;
  }
}
