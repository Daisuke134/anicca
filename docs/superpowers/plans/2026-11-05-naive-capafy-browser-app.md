# Naïve Capafy Browser App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement task-by-task in this session.

**Goal:** Naïve上の専用agentがCapafyのクラウドComputerをbrowser toolで操作し、実注文と支払証拠へ進める。

**Architecture:** Naïve fullstack AppはNode 22.xのroot Fetch entrypointとして`package.json.main=index.mjs`を指定する。root handlerは元の`/healthz`・`/mcp` pathを既存MCP handlerへ渡す。Vercel rewriteはroot routeを`/api?route=...`へ変えて404を起こすため置かず、`api/` function adapterも不要。`src/node.mjs`はローカル確認用に限る。新agentの`apps.allowed_apps`をこのApp idだけに絞り、Appのserver-side API keyは`computers:write`だけを許可する。agentは画面を観測し行動を決め、Appは固定Computer、Capafy domain、browser action、Idempotency-Keyだけを検査する。

**Tech Stack:** Vercel Node.js Function、Node.js 22.x固定、`@usenaive-sdk/vetta@0.10.0`、Fetch `Request`/`Response`、Node built-in test runner。

**Spec:** `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md` の「Naïve browser company」節。

## Global Constraints

- 原本agent/deployment、他owner、既存Publisher、既存商品を変更しない。
- App toolは一つの新agentだけに`apps.allowed_apps=[app_id]`で公開する。
- App API keyは`computers:write`だけ、Computerは専用ID、browserは`capafy.ai`とそのsubdomainだけに限定する。
- 商業行動はagentのbrowser操作で行い、Capafy固有の業務API/scriptは作らない。
- 既存Publisher内で新規商品を作る。重複Publisher/fake account/self-purchase/camera KYC迂回は禁止。
- 実売上は第三者注文の公式receiptと支払readbackだけで認定する。公開・申込数・モデル例・内部移動は売上ではない。
- 追加入金せず、有限runを既存Naïve残高と明示cap内で実行する。

## Review Focus

- 不正/欠落Bearerでbrowser APIを一切呼ばない。
- 非HTTPS、Capafy外、userinfo付き、非標準portのURLを拒否する。
- 同一operation_id・同一payloadの再送がNaïve provider idempotencyを再利用し、payload変更は409で止まる。
- body size超過、malformed JSON-RPC、未対応tool/methodが安全に拒否される。
- 既存agentがApp toolをcatalogで受け取らず、新専用agentだけが受け取る。

---

### Task 1: Browser-only App MCP handler

**Files:**
- Create: `apps/naive-capafy-browser/AGENTS.md`
- Create: `apps/naive-capafy-browser/package.json` / `package-lock.json`
- Create: `apps/naive-capafy-browser/index.mjs` (hosted root Fetch entrypoint)
- Create: `apps/naive-capafy-browser/src/server.mjs`
- Create: `apps/naive-capafy-browser/src/node.mjs` (local adapter only)
- Test: `apps/naive-capafy-browser/test/server.test.mjs`
- No `api/` Vercel adapter or `vercel.json` rewrite; hosted root Fetch deployment was verified.

**Interfaces:**
- `createBrowserMcpHandler({ env, fetchImpl }) -> (request: Request) => Promise<Response>`
- `capafy_browser` tool input: `{ operation_id, action, url?, selector?, text?, instruction?, contains?, limit? }`
- `action` supports only SDK `computers.browser` routes `goto`, `click`, `type`, `extract`, `act`, `observe`, `links`, `screenshot`, `login`, `signup`; browser computer id is server configuration, never an agent argument. `login`/`signup` take no agent-controlled identity, email, service or URL; the server supplies the dedicated agent identity/email and validated Capafy auth URL from write-only App secrets.

- [x] **Step 1: Write failing tests** for bearer rejection, external-URL rejection, a Capafy goto using the fixed Computer id and exact `Idempotency-Key`, and signup using only the server-held identity/email.
- [x] **Step 2: Run RED** with `node --test apps/naive-capafy-browser/test/server.test.mjs`; expect missing handler import or the asserted behavior to fail.
- [x] **Step 3: Implement the minimal Fetch MCP handler** using `createClient` with `NAIVE_API_KEY`, `NAIVE_COMPUTER_ID`, `NAIVE_IDENTITY_ID`, `CAPAFY_AGENT_EMAIL`, validated `CAPAFY_LOGIN_URL`/`CAPAFY_SIGNUP_URL`, `VETTA_MCP_TOKEN` and the call's UUID `operation_id` as the SDK idempotency-key provider. Never return credentials, email or internal API errors to the model.
- [x] **Step 4: Run GREEN** with `node --test apps/naive-capafy-browser/test/server.test.mjs`; add malformed/oversized request checks and verify the exact Computer/domain boundary.
- [x] **Step 5: Run App checks.** Latest: tests 8/8, JS syntax and `git diff --check` PASS.

### Task 2: Deploy and prove the actual Naïve cloud tool path

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md`
- Modify: `docs/team/BOARD.md`
- Evidence: private `/Users/anicca/.local/state/naive-browser-company/` receipts only.

**Interfaces:**
- Consumes: `capafy_browser` MCP tool from Task 1.
- Produces: a Naïve App deployment, app permission readback, dedicated agent/app binding, and a real event plus browser page readback from the dedicated Capafy allow-listed Computer.

- [x] **Step 1a: Create one Naïve fullstack App** with MCP path `/mcp`; the platform created `VETTA_MCP_TOKEN`. App id `app_z1g99d21zr5xx0v685c1y2zwgd` is `active`.
- [x] **Step 1b: Expose the unrewritten root Fetch handler.** Deployment `apd_0y0vrhejje98g2rpenvyrmmr9g` is ready; `/healthz`=200, `/mcp` GET=405/POST unauthenticated=401, root `main=index.mjs`, Node `22.x`, no rewrites. This proves routing/auth guard only.
- [ ] **Step 2: Create one deny-by-default dedicated agent** with `apps.allowed_apps=[app_id]`, `apps.request_access`=`ask`, App browser tool only, and one $0.15 session cap. Its session requests only `computers:write` for this App. Inspect pending card; approve only if exact App id/scope match, then read official permissions and secret names. Do not issue a generic org key.
- [ ] **Step 3: Use the same dedicated agent for one App MCP browser call** after permission readback; do not create a separate temporary requester or modify existing agents. No Identity/email is needed to read a public page.
- [ ] **Step 4: Verify the call** with official App tool event, fixed Computer/browser page readback, exact ledger delta, terminal session and paused Computer. This is a cloud-browser proof, not a revenue claim.
- [ ] **Step 5: Update the spec with observed results and retain remaining business TODOs.**

### Task 3: Existing Publisher sale and payout proof

The canonical task order is in the SSOT. Continue only through the existing Publisher and its official team-access route. Use the existing `skills/capafy/catalog/wnba-rotation-matchup-card` candidate only if a fresh seller/market read shows it is not already published or frozen and its claims remain accurate. Publish and distribute through browser/owned channels, then wait for a real third-party order and delivery. Reconcile order, payment, all Naïve/Computer/model/platform costs, refunds and net revenue from provider readbacks. Do not self-purchase or create a second Publisher. Record a screen demo only after a genuine order/payment state exists; a screenshot or synthetic example is not a money demo.
