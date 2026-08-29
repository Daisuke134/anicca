# Eliza Life Manager Plugin Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register exactly one Life Manager plugin in the existing Eliza runtime with one health action, one provider, and one stateless service.

**Architecture:** Copy the single-`Plugin` wiring shape from `plugins/plugin-companion`, but keep all three health components in one source file. Load it through the existing `packages/app/package.json` host-manifest path; do not touch core plugin lists or create a runtime, scheduler, adapter, schema, or database.

**Tech Stack:** TypeScript, Eliza `Plugin`/`Action`/`Provider`/`Service`, Vitest, Bun workspaces.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Global Constraints

- Implementation repository is `/Users/anicca/Projects/life-manager-eliza-migration` at parent `52eefdac597b70f3cb769b007cc4209f0f55cc34`.
- Plugin package/name is exactly `@elizaos/plugin-life-manager`.
- Register exactly one action `LIFE_MANAGER_HEALTH`, one provider `lifeManagerHealth`, and one service type `LIFE_MANAGER`.
- The service is stateless: no timer, loop, scheduler, adapter, schema, database, network, credential, marketplace, or external effect.
- Existing `AgentRuntime.registerPlugin` owns dedupe; registering the same plugin twice must still yield one plugin/action/provider/service.
- Host loading uses only `packages/app/package.json` dependency plus `elizaos.app.defaults.life-manager={enabled:true,requiredForReady:true}`.
- Do not edit agent/core runtime registration lists, optional-plugin generators, scheduling, SQL, personal-assistant, app-core runtime, or `plugins.json`.
- One focused plugin test, one existing resolver test, and typecheck only. No full suite or CI.

---

### Task 1: Add and host-load the exactly-one Life Manager plugin

**Files:**
- Create: `plugins/plugin-life-manager/package.json`
- Create: `plugins/plugin-life-manager/src/index.ts`
- Create: `plugins/plugin-life-manager/src/index.test.ts`
- Create: `plugins/plugin-life-manager/tsconfig.json`
- Create: `plugins/plugin-life-manager/tsconfig.build.json`
- Create: `plugins/plugin-life-manager/vitest.config.ts`
- Modify: `packages/app/package.json`
- Modify: `bun.lock`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-c/plugin-registration-receipt.json`

**Interfaces:**
- Produces `lifeManagerPlugin`, `LifeManagerService`, `lifeManagerHealthAction`, and `lifeManagerHealthProvider` from `@elizaos/plugin-life-manager`.
- ELZ-C02 consumes the same plugin and existing Eliza runtime; no second execution surface is introduced.

- [ ] **Step 1: Write the focused failing registration test**

Create `plugins/plugin-life-manager/src/index.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { AgentRuntime } from "@elizaos/core";
import { describe, expect, it } from "vitest";
import {
  LIFE_MANAGER_SERVICE_TYPE,
  lifeManagerHealthAction,
  lifeManagerHealthProvider,
  lifeManagerPlugin,
} from "./index";

describe("lifeManagerPlugin", () => {
  it("registers exactly one plugin/action/provider/service through the host manifest", async () => {
    const runtime = new AgentRuntime({ logLevel: "fatal" });
    await runtime.registerPlugin(lifeManagerPlugin);
    await runtime.registerPlugin(lifeManagerPlugin);

    expect(runtime.plugins.filter((plugin) => plugin.name === lifeManagerPlugin.name)).toHaveLength(1);
    expect(runtime.actions.filter((action) => action.name === lifeManagerHealthAction.name)).toHaveLength(1);
    expect(runtime.providers.filter((provider) => provider.name === lifeManagerHealthProvider.name)).toHaveLength(1);
    expect(runtime.getRegisteredServiceTypes()).toContain(LIFE_MANAGER_SERVICE_TYPE);

    const appPackage = JSON.parse(
      readFileSync(new URL("../../../packages/app/package.json", import.meta.url), "utf8"),
    );
    expect(appPackage.dependencies["@elizaos/plugin-life-manager"]).toBe("workspace:*");
    expect(appPackage.elizaos.app.defaults["life-manager"]).toEqual({
      enabled: true,
      requiredForReady: true,
    });
  });
});
```

Run `bunx vitest run plugins/plugin-life-manager/src/index.test.ts` and require failure because the plugin source is absent.

- [ ] **Step 2: Add the minimal package/config scaffold**

Copy `plugin-companion` package/config conventions, removing WebSocket dependencies. `package.json` must contain:

```json
{
  "name": "@elizaos/plugin-life-manager",
  "version": "2.0.3-beta.7",
  "type": "module",
  "description": "Life Manager general-agent capability plugin.",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    "./package.json": "./package.json",
    ".": {
      "types": "./dist/index.d.ts",
      "eliza-source": { "types": "./src/index.ts", "import": "./src/index.ts", "default": "./src/index.ts" },
      "import": "./dist/index.js",
      "default": "./dist/index.js"
    }
  },
  "scripts": {
    "build": "bun run build:js && bun run build:types",
    "build:js": "tsup --config ../tsup.plugin-packages.shared.ts",
    "build:types": "tsc6 --noCheck -p tsconfig.build.json",
    "test": "vitest run --config vitest.config.ts",
    "typecheck": "tsc --noEmit -p tsconfig.json"
  },
  "dependencies": { "@elizaos/core": "workspace:*" },
  "devDependencies": {
    "@types/node": "^25.0.3",
    "@typescript/native": "npm:typescript@^7.0.2",
    "tsup": "^8.5.1",
    "typescript": "^6.0.3",
    "vitest": "^4.1.10"
  },
  "files": ["dist"],
  "publishConfig": { "access": "public" }
}
```

Copy `plugins/plugin-companion/{tsconfig.json,tsconfig.build.json,vitest.config.ts}` byte-for-byte except remove the companion-specific Vitest comment.

- [ ] **Step 3: Implement the stateless plugin in one file**

Create `plugins/plugin-life-manager/src/index.ts`:

```ts
import {
  type Action, type ActionResult, type IAgentRuntime, type Plugin,
  type Provider, type ProviderResult, Service,
} from "@elizaos/core";

export const LIFE_MANAGER_SERVICE_TYPE = "LIFE_MANAGER" as const;

export class LifeManagerService extends Service {
  static serviceType = LIFE_MANAGER_SERVICE_TYPE;
  capabilityDescription = "Hosts Life Manager capabilities inside the existing Eliza runtime.";
  static async start(runtime: IAgentRuntime): Promise<LifeManagerService> {
    return new LifeManagerService(runtime);
  }
  async stop(): Promise<void> {}
}

export const lifeManagerHealthProvider: Provider = {
  name: "lifeManagerHealth",
  description: "Reports whether the Life Manager plugin is registered in this Eliza runtime.",
  descriptionCompressed: "Life Manager plugin health.",
  dynamic: true,
  get: async (runtime: IAgentRuntime): Promise<ProviderResult> => {
    const registered = runtime.plugins.some((plugin) => plugin.name === "@elizaos/plugin-life-manager");
    return {
      text: registered ? "Life Manager plugin: registered." : "Life Manager plugin: unavailable.",
      values: { lifeManagerRegistered: registered },
    };
  },
};

export const lifeManagerHealthAction: Action = {
  name: "LIFE_MANAGER_HEALTH",
  description: "Read the structural registration health of the Life Manager plugin.",
  descriptionCompressed: "Read Life Manager plugin health.",
  validate: async () => true,
  handler: async (runtime: IAgentRuntime): Promise<ActionResult> => {
    const registered = runtime.plugins.some((plugin) => plugin.name === "@elizaos/plugin-life-manager");
    return {
      success: registered,
      text: registered ? "Life Manager plugin is registered." : "Life Manager plugin is unavailable.",
      data: { lifeManagerRegistered: registered },
    };
  },
};

export const lifeManagerPlugin: Plugin = {
  name: "@elizaos/plugin-life-manager",
  description: "Life Manager general-agent capabilities hosted by the existing Eliza runtime.",
  services: [LifeManagerService],
  actions: [lifeManagerHealthAction],
  providers: [lifeManagerHealthProvider],
};

export default lifeManagerPlugin;
```

- [ ] **Step 4: Add the existing host-manifest registration**

In `packages/app/package.json`, add dependency `"@elizaos/plugin-life-manager": "workspace:*"` in sorted position and add `elizaos.app.defaults.life-manager` equal to `{ "enabled": true, "requiredForReady": true }`. Do not edit another registration surface.

- [ ] **Step 5: Update only the workspace lock and run focused checks**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
bun install --lockfile-only
bunx vitest run plugins/plugin-life-manager/src/index.test.ts
bunx vitest run --config packages/agent/vitest.config.ts packages/agent/src/runtime/plugin-resolver.test.ts -t "loads a host-manifest readiness plugin in blocking only"
bun run --cwd plugins/plugin-life-manager typecheck
```

Expected: the focused plugin test, existing resolver test, and typecheck pass; only the eight named repo files change.

- [ ] **Step 6: Write the private receipt**

After commit/push and remote readback, write mode-0600 `/Users/anicca/.local/state/life-manager/migration/elz-c/plugin-registration-receipt.json` with exact counts: plugin/action/provider/service `1`, required-for-ready true, second-runtime/scheduler/database/external-effects `0`, and matching local/remote branch SHA.

## Plan Self-Review

- Spec coverage: one plugin, one action/provider/service, host-ready registration, no second runtime/scheduler/DB.
- Ponytail: one production source file and one focused test; no future domain logic.
- Agent rule: no keyword/regex judgment, routing, marketplace logic, or hardcoded plan graph exists in C01.
- Scope: model transport, schema, provider bridge, goals, planning, effects, receipts, wake loop, and Lancers are excluded.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one Luna implementer, one focused primary verification, and one bounded adversarial review. No full suite or CI.
