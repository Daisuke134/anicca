# Eliza Local Model Transport Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the real Eliza OpenAI plugin can make one bounded structured call through local ClawRouter port 8402 with zero spend and no provider credential.

**Architecture:** Make no repository change. Build an ephemeral RAM dependency closure for `@elizaos/plugin-openai` and `@elizaos/plugin-life-manager`, register both in one `AgentRuntime`, and call `TEXT_SMALL` with a free model and JSON-object response. Bind ClawRouter wallet/stats before/after and detach the RAM disk.

**Tech Stack:** Eliza AgentRuntime, `@elizaos/plugin-openai`, ClawRouter 0.12.211, Bun 1.3.14, Turbo prune, APFS RAM disk.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Global Constraints

- Canonical source is `/Users/anicca/Projects/life-manager-eliza-migration` at `bd24601e737ec2cc93ab8f5556f25330f75053a9`.
- Local endpoint is exactly `http://127.0.0.1:8402/v1`; proxy listener identity must remain unchanged.
- Model is exactly `free/gpt-oss-20b`; ClawRouter documents free models as $0 and current wallet balance is $0.00.
- `OPENAI_API_KEY=x402` is a non-secret proxy placeholder; no OpenAI/provider/Capafy credential is loaded.
- One runtime, one OpenAI plugin, one Life Manager plugin, one model call. No retry, tool call, marketplace action, scheduler, DB, source edit, full suite, or CI.
- Structured response must parse to `{ok:true, agent:"life-manager"}`.
- Wallet balance and total cost remain exactly zero; request count increases by at least one because unrelated proxy traffic may run concurrently.

---

### Task 1: Run and receipt the zero-spend structured call

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-c/c02/`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-c/model-provider-receipt.json`
- Create outside repo: `/Users/anicca/Projects/life-manager-main/.worktrees/elz-c02-plan/.superpowers/sdd/2026-08-30-eliza-local-model-transport-preflight/task-1-report.md`
- Repository files: none.

- [ ] **Step 1: Record proxy, wallet, and stats before the call**

```bash
set -e
STATE=/Users/anicca/.local/state/life-manager/migration/elz-c/c02
mkdir -p -m 700 "$STATE"
test -z "$(git -C /Users/anicca/Projects/life-manager-eliza-migration status --porcelain=v1)"
test "$(git -C /Users/anicca/Projects/life-manager-eliza-migration rev-parse HEAD)" = bd24601e737ec2cc93ab8f5556f25330f75053a9
PROXY_PID=$(lsof -nP -tiTCP:8402 -sTCP:LISTEN)
test -n "$PROXY_PID"
PROXY_START=$(ps -p "$PROXY_PID" -o lstart= | xargs)
PROXY_ARGV_SHA=$(ps -p "$PROXY_PID" -o command= | shasum -a 256 | awk '{print $1}')
printf '%s\n' "$PROXY_PID" > "$STATE/proxy-pid.txt"
printf '%s\n' "$PROXY_START" > "$STATE/proxy-start.txt"
printf '%s\n' "$PROXY_ARGV_SHA" > "$STATE/proxy-argv-sha.txt"
/usr/bin/curl -fsS http://127.0.0.1:8402/health > "$STATE/health-before.json"
/usr/bin/curl -fsS http://127.0.0.1:8402/v1/models > "$STATE/models-before.json"
jq -e '.status=="ok" and .paymentChain=="base"' "$STATE/health-before.json"
jq -e '[.data[].id] | index("free/gpt-oss-20b") != null' "$STATE/models-before.json"
NO_COLOR=1 clawrouter wallet > "$STATE/wallet-before.txt"
NO_COLOR=1 clawrouter stats --days 1 > "$STATE/stats-before.txt"
BALANCE_BEFORE=$(awk '/Balance:/ {print $2; exit}' "$STATE/wallet-before.txt")
REQUESTS_BEFORE=$(awk '/Requests:/ {print $2; exit}' "$STATE/stats-before.txt")
COST_BEFORE=$(awk '/Cost:/ {print $2; exit}' "$STATE/stats-before.txt")
test "$BALANCE_BEFORE" = '$0.00'
test "$COST_BEFORE" = '$0.0000'
test "$REQUESTS_BEFORE" -ge 0
printf '%s\n' "$BALANCE_BEFORE" > "$STATE/balance-before.txt"
printf '%s\n' "$REQUESTS_BEFORE" > "$STATE/requests-before.txt"
printf '%s\n' "$COST_BEFORE" > "$STATE/cost-before.txt"
```

- [ ] **Step 2: Create the ephemeral two-plugin dependency closure**

```bash
set -e
STATE=/Users/anicca/.local/state/life-manager/migration/elz-c/c02
test ! -e /Volumes/ELZ_C02
RAM_DEVICE=$(hdiutil attach -nomount ram://14680064 | xargs)
printf '%s\n' "$RAM_DEVICE" > "$STATE/ram-device.txt"
diskutil erasevolume APFS ELZ_C02 "$RAM_DEVICE"
test -d /Volumes/ELZ_C02
cd /Users/anicca
npx --yes turbo@2.10.10 prune @elizaos/plugin-openai @elizaos/plugin-life-manager \
  --cwd=/Users/anicca/Projects/life-manager-eliza-migration \
  --out-dir=/Volumes/ELZ_C02/build
test -f /Volumes/ELZ_C02/build/plugins/plugin-openai/package.json
test -f /Volumes/ELZ_C02/build/plugins/plugin-life-manager/package.json
cd /Volumes/ELZ_C02/build
cp /Users/anicca/Projects/life-manager-eliza-migration/bun.lock bun.lock
bun install --lockfile-only --network-concurrency=1 --concurrent-scripts=1
DERIVED_LOCK_SHA=$(shasum -a 256 bun.lock | awk '{print $1}')
printf '%s\n' "$DERIVED_LOCK_SHA" > "$STATE/derived-lock-sha.txt"
bun install --frozen-lockfile --cache-dir=/Volumes/ELZ_C02/cache \
  --backend=clonefile --ignore-scripts --network-concurrency=1 --concurrent-scripts=1
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = "$DERIVED_LOCK_SHA"
```

- [ ] **Step 3: Run one real structured model call through both plugins**

Create `/Volumes/ELZ_C02/build/c02-live.ts` with:

```ts
import { AgentRuntime, type Character, ModelType } from "@elizaos/core";
import { openaiPlugin } from "./plugins/plugin-openai/index.ts";
import lifeManagerPlugin from "./plugins/plugin-life-manager/src/index.ts";

const character = {
  name: "Life Manager C02",
  bio: ["Life Manager transport preflight"],
  system: "Return only the requested JSON object.",
  settings: {
    OPENAI_API_KEY: "x402",
    OPENAI_BASE_URL: "http://127.0.0.1:8402/v1",
    OPENAI_SMALL_MODEL: "free/gpt-oss-20b",
  },
} as Character;

const runtime = new AgentRuntime({ character, logLevel: "fatal" });
await runtime.registerPlugin(lifeManagerPlugin);
await runtime.registerPlugin(openaiPlugin);
const raw = await runtime.useModel(ModelType.TEXT_SMALL, {
  prompt: 'Return exactly this JSON object and nothing else: {"ok":true,"agent":"life-manager"}',
  maxTokens: 64,
  temperature: 0,
  responseFormat: { type: "json_object" },
  voiceOutput: "internal",
});
const text = typeof raw === "string" ? raw : String((raw as { text?: unknown }).text ?? "");
const value = JSON.parse(text) as { ok?: unknown; agent?: unknown };
if (value.ok !== true || value.agent !== "life-manager") process.exit(2);
const capafyCredentialCount = Object.keys(process.env).filter((key) => key.includes("CAPAFY")).length;
if (capafyCredentialCount !== 0) process.exit(3);
console.log(JSON.stringify({ ok: true, agent: value.agent, model: "free/gpt-oss-20b", capafyCredentialCount }));
await runtime.stop();
```

Run exactly once:

```bash
set -e
STATE=/Users/anicca/.local/state/life-manager/migration/elz-c/c02
cd /Volumes/ELZ_C02/build
env -i HOME=/Users/anicca USER=anicca LOGNAME=anicca \
  PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  bun c02-live.ts > "$STATE/structured-response.json"
jq -e '.ok==true and .agent=="life-manager" and .model=="free/gpt-oss-20b" and .capafyCredentialCount==0' \
  "$STATE/structured-response.json"
```

- [ ] **Step 4: Prove zero spend and unchanged proxy identity**

```bash
set -e
STATE=/Users/anicca/.local/state/life-manager/migration/elz-c/c02
NO_COLOR=1 clawrouter wallet > "$STATE/wallet-after.txt"
NO_COLOR=1 clawrouter stats --days 1 > "$STATE/stats-after.txt"
NO_COLOR=1 clawrouter logs --days 1 > "$STATE/logs-after.txt"
BALANCE_AFTER=$(awk '/Balance:/ {print $2; exit}' "$STATE/wallet-after.txt")
REQUESTS_AFTER=$(awk '/Requests:/ {print $2; exit}' "$STATE/stats-after.txt")
COST_AFTER=$(awk '/Cost:/ {print $2; exit}' "$STATE/stats-after.txt")
test "$BALANCE_AFTER" = "$(cat "$STATE/balance-before.txt")"
test "$COST_AFTER" = "$(cat "$STATE/cost-before.txt")"
test "$REQUESTS_AFTER" -ge "$(( $(cat "$STATE/requests-before.txt") + 1 ))"
rg -q 'free/gpt-oss-20b.*\$0\.0000.*OK' "$STATE/logs-after.txt"
PROXY_PID=$(cat "$STATE/proxy-pid.txt")
test "$(lsof -nP -tiTCP:8402 -sTCP:LISTEN)" = "$PROXY_PID"
test "$(ps -p "$PROXY_PID" -o lstart= | xargs)" = "$(cat "$STATE/proxy-start.txt")"
test "$(ps -p "$PROXY_PID" -o command= | shasum -a 256 | awk '{print $1}')" = "$(cat "$STATE/proxy-argv-sha.txt")"
```

- [ ] **Step 5: Write the receipt, detach RAM, and verify cleanup**

Write mode-0600 `/Users/anicca/.local/state/life-manager/migration/elz-c/model-provider-receipt.json` containing atom/status, source SHA, plugin names, endpoint, model, structured response, request counts, balance/cost before-after, proxy identity hashes, derived lock SHA, Capafy credential count 0, model/provider credential count 0, external spend `0.0000`, external effects 0, and RAM APFS 7 GiB.

Detach only the owned device from `ram-device.txt`, require `/Volumes/ELZ_C02` absent, set `ram_disk_detached=true`, and verify canonical Git status remains clean.

## Plan Self-Review

- Existing plugin/provider/runtime/proxy paths are reused; repository changes are zero.
- The model chooses text; deterministic code only validates the fixed JSON transport contract and accounting.
- Zero-spend is proven by free model, empty wallet, unchanged balance/cost, and ClawRouter log cost `$0.0000`.
- No model/provider/Capafy secret, marketplace action, tool call, retry, full suite, or CI.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one Luna implementer, primary readback, one bounded adversarial review.
