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
- [x] **Step 1b: Expose the unrewritten root Fetch handler from main.** PR #9216 merged as `288e867668a00ead4de80efd2ebb1f4c54866ef2`; dedicated App deployment `apd_j8nn7p6vjs682cq87mb6txate4` is `ready` from that main snapshot. Its seven deployed files match `origin/main`; `/healthz`=200, `/mcp` GET=405/unauthenticated POST=401, root `main=index.mjs`, Node `22.x`, no rewrites.
- **Fresh root-cause readback:** `anicca-ceo` has a scheduled 09:00 JST deployment but `browser` and `apps` are disabled; its latest run is `budget_paused` at $0 spend with no Computer. `anicca-browser-operator` has `browser` enabled but `apps` disabled/denied. Preserve both; the new dedicated App-bound agent is required.
- **2026-11-05 official API re-read:** CEO v16 (`zai-org/GLM-5.2-FP8`) has a $1.00 monthly cap and $0.25 max task; the last session ended `budget_paused` at $0 with event `budget.exceeded` / `budget_exceeded` / “the agent's budget cap has no room for this call”. Its `browser` and `apps` tools are disabled. The browser operator has browser enabled but apps denied. The App permission read is `[]`, its secret-name list has no `NAIVE_API_KEY`, the fixed Computer is paused, and Naïve listings/blueprint installs both read as empty. This is an execution/configuration failure, not evidence that the model failed or that any sale occurred. Sanitized receipt: `/Users/anicca/.local/state/naive-browser-company/ceo-budget-blocker-readback-20261105.json`.
- **2026-11-05 initial agent setup readback:** Created `naive-capafy-cloud-operator` (`agt_y3zd3mkztbr079xc7xsg7wq5c7`, v1, `deepseek/deepseek-v4.1-flash`) with a $1.00 monthly cap / $0.15 per-session cap, default deny, `apps.allowed_apps=[app_id]`, and `apps.request_access=ask`; browser, MCP servers, and every other tool were disabled. Official GET matched the create request. This was the initial v1 state; the agent is now v2 with only its App browser tool allowed. Sanitized receipt: `/Users/anicca/.local/state/naive-browser-company/naive-dedicated-agent-created-20261105.json`.
- **2026-11-05 earlier payment/wallet readback:** Before the main-derived deployment, deployment `apd_0y0vrhejje98g2rpenvyrmmr9g` was `ready`, permissions were `[]`, and the secret-name list had no `NAIVE_API_KEY`. `GET /v1/apps/{id}/payments` returned 404; Naïve docs say this route is 404 until owner Stripe onboarding, and card checkout uses that owner account. `list_as_template` always asks a signed-in owner/admin and then requires Naïve review. A separate Base receiver-wallet control receipt does not identify a Naïve runtime wallet: `native_naive_wallet_created=false`, `runtime_signer_attached=false`, ETH/USDC balances 0, transfer/funding 0, realized revenue null, verified revenue receipts 0; the organization wallet-create request was rejected `forbidden` because mainnet wallets are not enabled. Do not count Naïve credits, wallet control, or Capafy’s site-wide marketing earnings as our revenue. Sanitized receipt: `/Users/anicca/.local/state/naive-browser-company/naive-finance-wallet-readback-20261105.json`.
- **2026-11-05 CI correction:** fresh GitHub run `41894532639` passed all required x86_64 and arm64 checks after the timing-fixture bound changed to 5 seconds (still below its 15-second cleanup grace). The earlier `41890833161` x86_64 timing failure is historical and resolved.
- [x] **Step 2a: Create one deny-by-default dedicated agent.** Agent `agt_y3zd3mkztbr079xc7xsg7wq5c7` is v2, `deepseek/deepseek-v4.1-flash`, $1/month and $0.15/session. Default permission is deny; `apps.allowed_apps` contains only this App; only `life-manager-capafy-browser.capafy_browser` is explicitly enabled with `allow`. All other browser, MCP and business tools remain disabled/denied.
- [x] **Step 2b: Give the App its least-scope server key.** A finite agent request to `apps.request_access` for exactly `computers:write` was rejected by Naïve validation; that tool permits only `agents:read`, `sessions:read`, `billing:read`, `files:read`, and `files:write`. No access was granted by that call. The owner API then created key `key_r39qv5cm5yc0sekehew464ncr3` with only the `computers:write` permission and stored it as the App's write-only `NAIVE_API_KEY`; official key metadata and secret-name readback matched. App `permissions` remains `[]` because this key was created directly and is not linked through `apps.request_access`. This is an organization-scoped key and `computers:write` can address organization Computers; it is not provider-enforced to this one Computer. The App code pins the Computer ID and Capafy domains, and `apps.allowed_apps` exposes it only to the dedicated agent. No unscoped or admin key was created.
- [x] **Step 3: Resume the fixed Computer and run the agent's App MCP browser tool.** The dedicated Computer read back `running`, `allowed_domains=["capafy.ai","*.capafy.ai"]`, `human_login=false`. Agent session `ses_jyncz4qpsefy5mnkagk6hsn04c` invoked `life-manager-capafy-browser.capafy_browser`: `goto https://capafy.ai/` returned `performed=true`, followed by read-only `extract selector=h1` returning `Capafy AI - Agent Skills Marketplace`. The browser session row has `session_id=null` because the App SDK calls the Computer browser REST API; the Naïve agent event stream independently records both tool calls and results.
- [x] **Step 3a: Close the browser and pause the Computer.** Browser `brw_1v61hhm025f1nm5n26r0n51kbc` read back `closed`; the Computer read back `paused` and has no open browser.
- [x] **Step 4: Reconcile this cloud-browser run.** Session terminal `idle/end_turn`; official model ledger total is 3,382 micro-USD and the browser ledger debit is 3,333 micro-USD. Total observed cost is 6,715 micro-USD ($0.006715). The actions were public read-only navigation/extraction: no order, sale, payout, or commercial action occurred, so this run proves cloud-browser operation only, not revenue. Capafy account-wide revenue was not read. Private receipt: `/Users/anicca/.local/state/naive-browser-company/naive-cloud-browser-proof-20261105.json`.
- [x] **Step 5: Update the SSOT with observed results and keep business TODOs active.** The canonical next cursor is NHC-01, below.

### Task 3: Existing Publisher sale and payout proof

The canonical next task is NHC-01: use Capafy’s official docs/UI to determine whether the existing certified Publisher supports a formal team/service-agent role with the rights needed for publishing and settlement. The owner reports that automation permission is already granted; accept that report and do not ask again. Capafy’s [Publisher Guide](https://capafy.ai/developer/doc/2.1) documents publishing via an Agent Client, while its [Publishing Flow](https://capafy.ai/developer/doc/2.2) describes an agent upload followed by Temporary Link screens to confirm the Agent Card, credential handling and review submission; neither page defines a machine-owned account or a service-agent delegation role for Naïve cloud access. Terms §3.3 says login credentials must not be shared, §3.4 limits an individual to one account, and §6 requires prior written permission for bots; the Publisher Agreement §2.7/§2.9/§3.6 covers account non-transferability, one Publisher per common-control entity, and pre-publication human review. Certification and payout also require real person/business identity materials and payout details. Do not use the owner's login, create another Publisher, submit personal identity documents, or bypass KYC. If official UI/docs do not provide an agent/team route, mark Capafy unverified for strict no-user-credential sales and evaluate the next ranked self-serve route (self-direct/x402) within existing caps. For any eligible platform, publish and distribute one legitimate product through the browser/owned channels, wait for a real third-party order and delivery, then reconcile the provider payment/settlement receipt and all Naïve/Computer/model/platform costs, refunds and net revenue. Do not record a money demo before the genuine order/payment evidence exists.
