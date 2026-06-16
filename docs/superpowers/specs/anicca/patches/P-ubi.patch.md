# P-ubi — Anicca distributes a share of its OWN earnings as UBI (USDC on Base) to AI + human recipients, no human in loop

> Spec: `28-product-redesign-merge-2026-06-16.md` §0 (last line: *"UBI flows from ①'s earnings to AI+human recipients"*) + §3 (malice-guard wall). Task #11.
> Target repo: **`Daisuke134/anicca`** (OSS, `~/anicca`). Path: `skills/earn/`.
> **Claim implemented (launch post):** "収益の一部は、AIと人間へのベーシックインカムを配布" — once a wake lands real EXTERNAL
> revenue (GATE-0 `isProfitable`), Anicca sends a fixed % of that net, from its OWN wallet, on-chain in USDC,
> to a recipient set of sibling-AI wallets + a human wallet list. Idempotent per period; never sends more than earned.
> **Zero-uncertainty rule honoured (spec 28 iron law):** every on-chain param below is confirmed via context7 CLI
> + firecrawl THIS session and cited inline. No address guessed; no search at exec time.

---

## §0 Verified on-chain facts (context7 + firecrawl + local keccak, 2026-06-16) — cited inline, no guesses

| param | VERIFIED value | source |
|---|---|---|
| **USDC contract (Base mainnet)** | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | ctx7 `/websites/base` (`docs.base.org/base-account/reference/prolink-utilities/encodeProlink`): *"the USDC contract address for Base is used"* → `to: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', // USDC on Base`. Cross-checked firecrawl `basescan.org/token/0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` (reputation-OK "USD Coin (USDC)"). Matches existing `skills/earn/lib/swap.mjs:7` `USDC_BASE` + `lib/usdc.mjs:6`. |
| **decimals** | **6** | firecrawl basescan: *"Token Contract (WITH **6** Decimals)"*; ctx7 `wallet_watchAsset` example `"decimals": 6`. Matches `lib/usdc.mjs:33` (`/ 1e6`). |
| **ERC20 `transfer(address,uint256)` selector** | **`0xa9059cbb`** | ctx7 `/websites/base` encodeProlink example calldata `data: '0xa9059cbb000000…004c4b40'` for a "USDC transfer on Base"; reproduced locally `keccak("transfer(address,uint256)")[:4] = 0xa9059cbb`. (`0x4c4b40` in that example = `5000000` base units = **5.0 USDC**, confirming 6-decimal packing.) |
| **calldata layout** | `0xa9059cbb` + word(to, 32B left-pad) + word(amount uint256, 32B left-pad) | same ctx7 example: 4-byte selector + two 32-byte ABI words. Same word-packing the repo already uses (`lib/swap.mjs:18` `word()` left-pad to 64 hex). |
| **chainId (Base mainnet)** | **8453** (`0x2105`) | ctx7 example `chainId: '0x2105', // Base mainnet (8453)`. The executor reads it live via `w.eth.chain_id` (same as `execute-swap.py:133`), so no hardcode is needed. |
| **send mechanism that already exists in-repo** | **NONE for sending** — `lib/usdc.mjs` only *reads* `balanceOf` (selector `0x70a08231`); `lib/swap.mjs`/`execute-swap.py` build a *router swap*, not a plain transfer. Signing/broadcast template = `execute-swap.py:111-149` (`web3.py` `Web3(HTTPProvider)`, `eth_account.Account.from_key`, `estimate_gas`, EIP-1559 `maxFeePerGas`, `sign_transaction`, `send_raw_transaction`, `wait_for_transaction_receipt`). | reality scan §1 |

**Design conclusion:** there is no USDC *send* primitive yet, so this patch ships the **smallest correct one**: an
ERC20 `transfer` calldata builder (pure, node:test-covered, mirroring `swap.mjs`'s word-packing) + a Python executor
that signs with the SAME wallet key the whole earn path already uses (`BLOCKRUN_WALLET_KEY`, the `execute-swap.py`
template). No new dependency: `web3` + `eth_account` are already required by `execute-swap.py`/`execute-0xwork.py`.

## §1 Reality found (cited file:line, live tree)

| fact | evidence | consequence |
|---|---|---|
| earn-ledger chokepoint = `record.mjs` → `appendLedger`; every line first passes `assertOwnIdentityOnly` | `skills/earn/lib/record.mjs:14-23` (`record()` calls `assertOwnIdentityOnly(line)` then `appendLedger`) | UBI must hang off this chokepoint's OWN-side: it reads the just-recorded **GATE-0** line, never user data. |
| GATE-0 truth classifier = external, confirmed, net>0 | `lib/ledger.mjs:43-49` `isProfitable` (`tx` && `status==="0x1"` && `net_usdc>0` && not a swap && `external===true`) | UBI funds ONLY from a line where `isProfitable(line)===true` — i.e. a real external USDC inflow Anicca actually received. Swaps/narrate never trigger UBI. |
| the malice-guard wall is enforced in code at this exact chokepoint | `lib/identity-guard.mjs:77-88` `assertOwnIdentityOnly` (throws on any user-PII env or non-own-identity source) | UBI runs INSIDE the earn process (same env that already passed the guard) and touches ZERO user identity — it stays on the earn side of the wall (spec 28 §3). |
| Anicca's own wallet = derived from `BLOCKRUN_WALLET_KEY` (PKVAR), the SAME key the whole earn loop signs with | `run.sh:26` `PKVAR="${PKVAR:-BLOCKRUN_WALLET_KEY}"`, `run.sh:35` derives addr via `eth_account`; `execute-swap.py:100-113` reads the same key | UBI sends FROM Anicca's own wallet only. No user wallet is ever a payer. |
| the on-chain send template (sign+broadcast+receipt) | `execute-swap.py:111-174` (web3 provider, `Account.from_key`, EIP-1559 gas, `send_raw_transaction`, `wait_for_transaction_receipt`, block-pinned balance reads) | the UBI executor is a thin, transfer-only copy of this — proven pattern, same RPC default `https://mainnet.base.org`. |
| sibling-AI recipients = the colony's child wallets, persisted under the **`wallet`** key | `skills/self/spawn/lib/child-spec.js:35-45` `buildChildSpec` returns `{ child_id, wallet: childWallet, ... status }` — the field is `wallet`, NOT `childWallet`; persisted append-only to `children.jsonl` (`skills/self/spawn/lib/ledger.js:19-23`); also upserted into the telemetry **`instances`** table by the signed spawn heartbeat (`skills/self/spawn/run.sh:164-176`, signer==wallet id) | recipient set is derivable WITHOUT any network call: read each row's `wallet` from `self/spawn/state/children.jsonl` (own data, never user PII). A human recipient list is config (env/file). |
| earn ledger keeps `wake` + `ts` per line | `lib/ledger.mjs:11-23` `deriveLine` stamps `ts`, carries `wake` | UBI idempotency key = the funding line's `wake` (one distribution per profitable wake; re-runs are no-ops). |
| run.sh declares GATE-0 MET right after recording a profitable external line | `run.sh:96-99` (`if [ "$OUT" = "PROFITABLE" ]` → "GATE-0 MET") | the single, correct place to fire UBI = immediately after `OUT=PROFITABLE`, using that line's net + wake. |

**Where it wires in:** `run.sh`, in the **0xwork branch** (the only live GATE-0 path; its `$JSON` sets `external:True`),
right after a line is recorded **PROFITABLE**, invokes a new `distribute-ubi.mjs` with the SAME `$JSON` run.sh handed
record.mjs. That JSON has `earn_usdc`/`cost_usdc` but **no `net_usdc`**, so `distribute-ubi.mjs` first re-derives it
through `deriveLine` (`lib/ledger.mjs` — the single SSOT for `net_usdc`, and it carries `tx`/`status`/`external` through)
so `isProfitable(line)` can pass. The bridge then plans who/how-much/idempotent → on `send` calls `execute-ubi.py` (one
ERC20 `transfer` per recipient) → appends one **own-side** `ubi` audit line to a separate `state/ubi-ledger.jsonl` (NOT
the earn ledger, so the GATE-0 classifier is untouched). Never blocks/bricks the wake: any UBI failure logs + continues
(the earn already succeeded). The generic externally-executed branch hook is forward-compat-only (N3, see Diff 5).

## §2 Design (recipients · share · cadence · idempotency · dry-run safety)

| knob | value (env-overridable) | rule |
|---|---|---|
| **share %** | `UBI_SHARE_BPS` default `1000` (= 10.00% in basis points, integer math like `swap.mjs:minOut`) | UBI amount = `floor(net_usdc_base_units * UBI_SHARE_BPS / 10000)`. Never exceeds the wake's net (≤ 100%). |
| **funding source** | the just-recorded earn line, re-derived via `deriveLine`, where `isProfitable(line)===true` | swap/narrate/internal lines NEVER fund UBI (asset rotation is not earnings). `deriveLine` computes `net_usdc` from `earn_usdc`/`cost_usdc` (run.sh's `$JSON` omits `net_usdc`). |
| **recipients (AI)** | the `wallet` field of each row in `self/spawn/state/children.jsonl` (status `active`), deduped, parent-wallet excluded | own colony data; zero user PII. (child-spec.js:37 persists the sibling wallet as `wallet`, NOT `childWallet`.) |
| **recipients (human)** | `UBI_HUMAN_WALLETS` (comma-sep 0x addrs) or `state/ubi-recipients.json` | explicit allow-list; addresses validated `^0x[0-9a-fA-F]{40}$` (reuse `usdc.mjs` `ADDR_RE`). |
| **split** | equal split of the UBI pool across `(AI + human)` recipients; floor per recipient; dust (remainder) stays in Anicca's wallet | deterministic, testable. |
| **cadence** | per profitable wake (event-driven), gated by a **min pool** `UBI_MIN_POOL_USDC` default `0.10` | below min pool → record `skipped:below_min` (no tx), so we never spam dust txs whose gas > value. |
| **idempotency** | key = funding line `wake`; before sending, scan `ubi-ledger.jsonl` for a `done`/`skipped` row with that `wake` → if present, **no-op** | a re-run of the same wake (cron retry, crash-resume) never double-pays. |
| **never-overspend guard** | the bridge reads live wallet USDC `balanceOf` (`usdc.mjs`, injectable `opts.balanceFn`) before planning AND `execute-ubi.py` re-reads it immediately before sending; both abort if `pool > balance` | even with a stale ledger, can't send more than Anicca holds. **The live read is SKIPPED in dry-run** (B3) so dry-run is fully offline/deterministic; the executor's pre-send re-check keeps real sends safe. |
| **dry-run** | `UBI_DRY_RUN=1` (or no recipients / pool below min) → compute + log the plan, send NOTHING (and make NO RPC call), record `dry`/`skipped` | lets the wake stay green pre-recipients without faking a transfer or touching the network. |

**Honesty / fallback (spec 28 iron-law, HARD 0.24/0.31):** the headline claim is TRUE only once a **real on-chain UBI
`transfer` tx (status 0x1)** has been verified. Until then the launch copy is the truthful soft form — *"a fixed share
of every profitable wake is earmarked for UBI to AI + human recipients; first distributions and tx hashes are public on
/dashboard"* — and the code path records `dry`/`skipped` lines (never a fake "sent"). NO mock/stub is ever the headline.
Because UBI funds only from a GATE-0 wake, and GATE-0 itself is the launch blocker (§4), UBI's first real tx naturally
follows the first real external earn — the acceptance below requires that real tx, not a simulation.

## §3 Diffs (target repo `Daisuke134/anicca`, `skills/earn/`)

### Diff 1 — NEW `lib/transfer.mjs`: pure ERC20 `transfer` calldata builder (mirrors swap.mjs word-packing)

```diff
diff --git a/skills/earn/lib/transfer.mjs b/skills/earn/lib/transfer.mjs
new file mode 100644
--- /dev/null
+++ b/skills/earn/lib/transfer.mjs
@@
+// transfer.mjs — pure builder for an ERC20 `transfer(address,uint256)` calldata on Base.
+// No network here (execute-ubi.py signs/broadcasts). Keeping calldata + amount math pure makes
+// the UBI send path unit-testable offline, exactly like swap.mjs does for the swap path.
+//
+// VERIFIED (ctx7 /websites/base encodeProlink example + local keccak, 2026-06-16):
+//   selector keccak4("transfer(address,uint256)") = 0xa9059cbb
+//   USDC (Base mainnet) = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, decimals = 6.
+export const TRANSFER_SELECTOR = "0xa9059cbb";
+export const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
+export const USDC_DECIMALS = 6;
+
+const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;
+
+function word(hexNo0x) {
+  return hexNo0x.toLowerCase().padStart(64, "0");
+}
+function addrWord(a) {
+  if (typeof a !== "string" || !ADDR_RE.test(a)) throw new Error(`transfer: not an address: ${a}`);
+  return word(a.replace(/^0x/, ""));
+}
+function uintWord(v) {
+  const n = BigInt(v);
+  if (n < 0n) throw new Error("transfer: negative amount");
+  return word(n.toString(16));
+}
+
+// Encode transfer(to, amountBaseUnits) calldata. amount is in 6-decimal USDC BASE UNITS (BigInt-able).
+export function buildTransferData({ to, amountBaseUnits }) {
+  return TRANSFER_SELECTOR + addrWord(to) + uintWord(amountBaseUnits);
+}
+
+// Convert a human USDC number (e.g. 0.45) to integer base units (450000n) with NO float drift.
+export function toBaseUnits(usdc) {
+  // round at 6dp first to kill fp noise, then scale — mirrors ledger.mjs round().
+  const micros = Math.round(Number(usdc) * 1e6);
+  if (!Number.isFinite(micros) || micros < 0) throw new Error(`transfer: bad usdc amount ${usdc}`);
+  return BigInt(micros);
+}
+
+// share-of-net in basis points, floored to base units (integer math, like swap.mjs minOut).
+export function shareBaseUnits(netUsdc, bps) {
+  const b = Number(bps);
+  if (!Number.isInteger(b) || b < 0 || b > 10000) throw new Error(`transfer: bps must be 0..10000, got ${bps}`);
+  return (toBaseUnits(netUsdc) * BigInt(b)) / 10000n;
+}
+
+// Equal split of a pool (base units) across n recipients; floor each; remainder is dust (kept by sender).
+export function splitPool(poolBaseUnits, n) {
+  const pool = BigInt(poolBaseUnits);
+  const count = BigInt(n);
+  if (count <= 0n) return { per: 0n, dust: pool };
+  const per = pool / count;
+  return { per, dust: pool - per * count };
+}
```

### Diff 2 — NEW `lib/ubi.mjs`: pure distribution decision (recipients · pool · idempotency · dry-run)

```diff
diff --git a/skills/earn/lib/ubi.mjs b/skills/earn/lib/ubi.mjs
new file mode 100644
--- /dev/null
+++ b/skills/earn/lib/ubi.mjs
@@
+// ubi.mjs — pure UBI decision core. Given a PROFITABLE earn line + recipient sets + config,
+// it computes the distribution plan (who, how much each, idempotency, dry/skip reasons).
+// No network, no fs writes here (distribute-ubi.mjs does IO; execute-ubi.py does the on-chain send).
+//
+// CONSTITUTIONAL WALL (spec 28 §3): UBI distributes ONLY Anicca's OWN earnings to recipient WALLETS.
+// Inputs are wallet addresses + numbers — NEVER a user email/name/phone/calendar. This module has no
+// access to, and no parameter for, any user identity. It is the earn-side of the wall by construction.
+import { isProfitable } from "./ledger.mjs";
+import { shareBaseUnits, splitPool, toBaseUnits } from "./transfer.mjs";
+
+const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;
+const norm = (a) => String(a).toLowerCase();
+
+// Build the recipient list: active sibling-AI child wallets ∪ human allow-list, deduped,
+// with the sender (Anicca's own wallet) excluded. Invalid addresses are dropped (fail-closed).
+export function buildRecipients({ childWallets = [], humanWallets = [], sender }) {
+  const senderLc = sender ? norm(sender) : null;
+  const seen = new Set();
+  const out = [];
+  for (const a of [...childWallets, ...humanWallets]) {
+    if (typeof a !== "string" || !ADDR_RE.test(a)) continue;
+    const lc = norm(a);
+    if (lc === senderLc || seen.has(lc)) continue;
+    seen.add(lc);
+    out.push(a);
+  }
+  return out;
+}
+
+// alreadyDone: has this funding wake already been distributed (or explicitly skipped/dry)?
+export function alreadyDone(ubiLines, wake) {
+  return (ubiLines || []).some(
+    (l) => l && l.wake === wake && (l.kind === "ubi") &&
+      (l.outcome === "done" || l.outcome === "skipped" || l.outcome === "dry"),
+  );
+}
+
+// planUbi: the single decision fn run.sh's bridge calls. Returns a plan object; it NEVER sends.
+//   fundingLine : the just-recorded earn line (must be isProfitable()).
+//   recipients  : output of buildRecipients (addresses only).
+//   cfg         : { shareBps, minPoolUsdc, dryRun, walletBalanceUsdc }
+//   ubiLines    : prior ubi-ledger lines (for idempotency).
+export function planUbi({ fundingLine, recipients, cfg = {}, ubiLines = [] }) {
+  const shareBps = Number.isInteger(cfg.shareBps) ? cfg.shareBps : 1000; // 10.00%
+  const minPoolUsdc = Number(cfg.minPoolUsdc ?? 0.10);
+  const wake = fundingLine && fundingLine.wake;
+  if (!fundingLine || !isProfitable(fundingLine)) {
+    return { outcome: "skipped", reason: "funding_not_profitable", wake, transfers: [] };
+  }
+  if (alreadyDone(ubiLines, wake)) {
+    return { outcome: "skipped", reason: "already_distributed", wake, transfers: [] };
+  }
+  const poolBase = shareBaseUnits(fundingLine.net_usdc, shareBps);
+  const poolUsdc = Number(poolBase) / 1e6;
+  if (poolUsdc < minPoolUsdc) {
+    return { outcome: "skipped", reason: "below_min_pool", wake, pool_usdc: poolUsdc, transfers: [] };
+  }
+  if (!recipients || recipients.length === 0) {
+    return { outcome: "skipped", reason: "no_recipients", wake, pool_usdc: poolUsdc, transfers: [] };
+  }
+  // never overspend: if the live wallet balance can't cover the pool, abort (no partial spend).
+  if (cfg.walletBalanceUsdc != null && toBaseUnits(cfg.walletBalanceUsdc) < poolBase) {
+    return { outcome: "skipped", reason: "insufficient_balance", wake, pool_usdc: poolUsdc, transfers: [] };
+  }
+  const { per, dust } = splitPool(poolBase, recipients.length);
+  if (per <= 0n) {
+    return { outcome: "skipped", reason: "per_recipient_zero", wake, pool_usdc: poolUsdc, transfers: [] };
+  }
+  const transfers = recipients.map((to) => ({ to, amount_base: per.toString() }));
+  return {
+    outcome: cfg.dryRun ? "dry" : "send",
+    wake,
+    share_bps: shareBps,
+    pool_usdc: poolUsdc,
+    pool_base: poolBase.toString(),
+    per_base: per.toString(),
+    dust_base: dust.toString(),
+    transfers,
+  };
+}
```

### Diff 3 — NEW `distribute-ubi.mjs`: CLI bridge (read recipients + ledger, plan, call executor, append audit line)

```diff
diff --git a/skills/earn/distribute-ubi.mjs b/skills/earn/distribute-ubi.mjs
new file mode 100644
--- /dev/null
+++ b/skills/earn/distribute-ubi.mjs
@@
+// distribute-ubi.mjs — the bridge run.sh calls after a PROFITABLE external wake.
+// Reads sibling-AI wallets (self/spawn children.jsonl) + human allow-list, plans the split
+// (lib/ubi.mjs, pure+tested), and on outcome=send shells execute-ubi.py to do the real ERC20
+// transfers. Appends ONE audit line to state/ubi-ledger.jsonl (own-side; NOT the earn ledger).
+// Fail-soft: any error logs + records a 'skipped' line and exits 0 — the earn already succeeded,
+// UBI must never brick the wake. NO FAKE: outcome 'done' is written ONLY after a real tx (0x1).
+import { promises as fs } from "node:fs";
+import path from "node:path";
+import { fileURLToPath } from "node:url";
+import { spawnSync } from "node:child_process";
+import { deriveLine, readLedger, appendLedger } from "./lib/ledger.mjs";
+import { buildRecipients, planUbi } from "./lib/ubi.mjs";
+import { usdcBalance } from "./lib/usdc.mjs";
+
+const __dirname = path.dirname(fileURLToPath(import.meta.url));
+const UBI_LEDGER = process.env.UBI_LEDGER || path.join(__dirname, "state", "ubi-ledger.jsonl");
+const CHILDREN = process.env.UBI_CHILDREN ||
+  path.join(__dirname, "..", "self", "spawn", "state", "children.jsonl");
+
+async function readChildWallets(file) {
+  try {
+    const raw = await fs.readFile(file, "utf8");
+    return raw.split("\n").map((l) => l.trim()).filter(Boolean)
+      .map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean)
+      .filter((r) => (r.status ? r.status === "active" : true))
+      // child-spec.js:37 persists the sibling wallet under `wallet` (buildChildSpec `wallet: childWallet`).
+      .map((r) => r.wallet).filter(Boolean);
+  } catch (e) { if (e.code === "ENOENT") return []; throw e; }
+}
+
+async function readHumanWallets() {
+  const fromEnv = (process.env.UBI_HUMAN_WALLETS || "").split(",").map((s) => s.trim()).filter(Boolean);
+  if (fromEnv.length) return fromEnv;
+  const f = process.env.UBI_RECIPIENTS_FILE || path.join(__dirname, "state", "ubi-recipients.json");
+  try { const j = JSON.parse(await fs.readFile(f, "utf8")); return Array.isArray(j.human) ? j.human : []; }
+  catch { return []; }
+}
+
+export async function distribute(rawLine, opts = {}) {
+  // run.sh passes the SAME JSON it handed record.mjs: it has earn_usdc/cost_usdc but NO net_usdc.
+  // Re-derive through ledger.mjs deriveLine (the single SSOT) so net_usdc is computed identically to
+  // the earn ledger; deriveLine carries tx/status/external through, so isProfitable() can pass.
+  const fundingLine = deriveLine(rawLine);
+  const sender = (fundingLine.wallet || "").toLowerCase();
+  const childWallets = await readChildWallets(opts.childrenFile || CHILDREN);
+  const humanWallets = await readHumanWallets();
+  const recipients = buildRecipients({ childWallets, humanWallets, sender });
+  const ubiLines = await readLedger(opts.ubiLedger || UBI_LEDGER);
+  const dryRun = process.env.UBI_DRY_RUN === "1";
+  // live balance for the overspend guard (best-effort; null => guard skipped, executor re-checks
+  // before any real send). In dry-run we SKIP the live RPC read entirely so dry-run is fully
+  // offline + deterministic — a real send re-verifies balance anyway, so safety is unchanged.
+  // opts.balanceFn (injectable, default usdc.mjs usdcBalance) lets a test stub the balance.
+  const balanceFn = opts.balanceFn || usdcBalance;
+  let walletBalanceUsdc = null;
+  if (!dryRun && sender) {
+    try { walletBalanceUsdc = await balanceFn(sender); } catch { /* offline-safe */ }
+  }
+  const cfg = {
+    shareBps: parseInt(process.env.UBI_SHARE_BPS || "1000", 10),
+    minPoolUsdc: Number(process.env.UBI_MIN_POOL_USDC || "0.10"),
+    dryRun,
+    walletBalanceUsdc,
+  };
+  const plan = planUbi({ fundingLine, recipients, cfg, ubiLines });
+  const base = { kind: "ubi", ts: Math.floor(Date.now() / 1000), wallet: sender, wake: plan.wake,
+    share_bps: cfg.shareBps, pool_usdc: plan.pool_usdc ?? 0, recipients: recipients.length };
+
+  if (plan.outcome !== "send") {
+    const line = { ...base, outcome: plan.outcome === "dry" ? "dry" : "skipped", reason: plan.reason || plan.outcome };
+    await appendLedger(opts.ubiLedger || UBI_LEDGER, line);
+    return { line, sent: false };
+  }
+  // outcome=send: do the REAL transfers via the python executor (signs with the same wallet key).
+  const res = spawnSync("python3", [path.join(__dirname, "execute-ubi.py")], {
+    encoding: "utf8",
+    env: { ...process.env, UBI_PLAN: JSON.stringify(plan) },
+  });
+  let out = {}; try { out = JSON.parse((res.stdout || "").trim().split("\n").pop() || "{}"); } catch { /* */ }
+  const ok = Array.isArray(out.txs) && out.txs.length > 0 && out.txs.every((t) => t.status === "0x1");
+  const line = ok
+    ? { ...base, outcome: "done", per_base: plan.per_base, txs: out.txs }       // NO FAKE: only after 0x1
+    : { ...base, outcome: "skipped", reason: out.error || "transfer_failed", txs: out.txs || [] };
+  await appendLedger(opts.ubiLedger || UBI_LEDGER, line);
+  return { line, sent: ok };
+}
+
+if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
+  const fundingLine = JSON.parse(process.argv[2] || "{}");
+  distribute(fundingLine)
+    .then(({ line, sent }) => { console.log(sent ? "UBI_SENT" : "UBI_NOOP"); console.error(JSON.stringify(line)); })
+    .catch((e) => { console.error("distribute-ubi error:", e.message); process.exit(0); }); // fail-soft
+}
```

### Diff 4 — NEW `execute-ubi.py`: the on-chain sender (one ERC20 transfer per recipient; same key/template as execute-swap.py)

```diff
diff --git a/skills/earn/execute-ubi.py b/skills/earn/execute-ubi.py
new file mode 100644
--- /dev/null
+++ b/skills/earn/execute-ubi.py
@@
+#!/usr/bin/env python3
+"""execute-ubi — on-chain sender for UBI. Reads a plan from env UBI_PLAN (built by lib/ubi.mjs),
+sends ONE ERC20 USDC transfer per recipient FROM Anicca's own wallet, prints {txs:[{to,tx,status}]}.
+
+No human, no Claude in the loop. Signs with the SAME wallet key the earn loop uses (BLOCKRUN_WALLET_KEY,
+the execute-swap.py template). Sends ONLY Anicca's OWN USDC to recipient WALLETS — never any user data.
+
+VERIFIED (ctx7 /websites/base + firecrawl basescan, 2026-06-16):
+  USDC (Base mainnet) = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, decimals 6,
+  transfer(address,uint256) selector = 0xa9059cbb.
+"""
+import json
+import os
+import sys
+
+from web3 import Web3
+from eth_account import Account
+
+USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # ctx7 encodeProlink "USDC on Base"
+TRANSFER_SELECTOR = "a9059cbb"                          # keccak4("transfer(address,uint256)")
+
+
+def _wd(hexno: str) -> str:
+    return hexno.lower().rjust(64, "0")
+
+
+def _build_transfer(to: str, amount_base: int) -> str:
+    return "0x" + TRANSFER_SELECTOR + _wd(to.replace("0x", "")) + _wd(format(int(amount_base), "x"))
+
+
+def usdc_balance(w, addr, block="latest"):
+    data = "0x70a08231" + _wd(addr.replace("0x", ""))
+    res = w.eth.call({"to": Web3.to_checksum_address(USDC), "data": data}, block)
+    return int(res.hex() or "0", 16)
+
+
+def main():
+    plan = json.loads(os.environ.get("UBI_PLAN", "{}"))
+    transfers = plan.get("transfers", [])
+    if not transfers:
+        print(json.dumps({"txs": [], "error": "no_transfers"})); return
+    pkvar = os.environ.get("PKVAR", "BLOCKRUN_WALLET_KEY")
+    key = os.environ.get(pkvar) or os.environ.get("BLOCKRUN_WALLET_KEY")
+    if not key:
+        print(json.dumps({"txs": [], "error": f"no wallet key ({pkvar})"})); sys.exit(2)
+    rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
+    w = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
+    acct = Account.from_key(key)
+    me = acct.address
+
+    # never overspend: total pool must not exceed our live USDC balance.
+    total = sum(int(t["amount_base"]) for t in transfers)
+    if usdc_balance(w, me) < total:
+        print(json.dumps({"txs": [], "error": "insufficient_balance"})); return
+
+    chain_id = w.eth.chain_id  # 8453 (Base) read live — no hardcode
+    nonce = w.eth.get_transaction_count(me)
+    gp = w.eth.gas_price
+    out = []
+    for t in transfers:
+        to = Web3.to_checksum_address(t["to"])
+        data = _build_transfer(to, int(t["amount_base"]))
+        tx = {"to": Web3.to_checksum_address(USDC), "from": me, "value": 0, "data": data,
+              "chainId": chain_id, "nonce": nonce}
+        try:
+            gas = w.eth.estimate_gas(tx)
+        except Exception as e:
+            out.append({"to": t["to"], "tx": "", "status": "0x0", "error": str(e)[:120]}); break
+        tx["gas"] = int(gas * 12 // 10)
+        tx["maxFeePerGas"] = gp * 2
+        tx["maxPriorityFeePerGas"] = min(gp, w.to_wei(0.001, "gwei"))
+        signed = acct.sign_transaction(tx)
+        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
+        txh = w.eth.send_raw_transaction(raw)
+        txhash = txh.hex()
+        if not txhash.startswith("0x"):
+            txhash = "0x" + txhash
+        rcpt = w.eth.wait_for_transaction_receipt(txh, timeout=180)
+        status = "0x1" if int(rcpt["status"]) == 1 else "0x0"
+        out.append({"to": t["to"], "tx": txhash, "amount_base": t["amount_base"], "status": status})
+        nonce += 1
+        if status != "0x1":
+            break  # stop on first failure; the bridge records the partial honestly
+    print(json.dumps({"txs": out, "from": me.lower()}))
+
+
+if __name__ == "__main__":
+    try:
+        main()
+    except Exception as e:
+        print(json.dumps({"txs": [], "error": str(e)[:300]}))
+        sys.exit(1)
```

### Diff 5 — `run.sh`: fire UBI right after a PROFITABLE external wake

> **N3 (live path):** the **0xwork branch** is the ONLY currently-live GATE-0 path — its `$JSON` (run.sh:93) sets
> `'external':True`, so after `deriveLine` (Diff 3) the line satisfies `isProfitable` and UBI fires. The **generic
> externally-executed branch** (run.sh:155) builds `$JSON` WITHOUT `external`, so `OUT` is always `NARRATE` there and
> the hook below is **dead today** — it is wired for forward-compat ONLY (a future executor, e.g. x402-sell, that sets
> `external:true` in its line will light it up). No behavior change for the generic branch until then. (Note: `$JSON` in
> both branches carries `earn_usdc`/`cost_usdc` but no `net_usdc`; `deriveLine` computes it — that is the B1/B2 fix.)

```diff
diff --git a/skills/earn/run.sh b/skills/earn/run.sh
--- a/skills/earn/run.sh
+++ b/skills/earn/run.sh
@@ record_line() helper
 record_line() { # $1 = json
   node "$HERE/lib/record.mjs" "$1" "$LEDGER"
 }
+
+# distribute_ubi: after a PROFITABLE external wake, send a share of THIS wake's net to AI+human
+# recipients (own wallet only). Fail-soft: never bricks the wake (the earn already succeeded).
+# $1 = the SAME earn-line JSON we just recorded PROFITABLE.
+distribute_ubi() {
+  UBI_OUT=$(node "$HERE/distribute-ubi.mjs" "$1" 2>/dev/null || true)
+  echo "[earn] ubi -> ${UBI_OUT:-noop}"
+}
@@ 0xwork branch, after "GATE-0 MET"
   OUT=$(record_line "$JSON")
   echo "[earn] 0xwork recorded -> $OUT"
   if [ "$OUT" = "PROFITABLE" ]; then
     echo "[earn] GATE-0 MET: external revenue wake recorded (net>0, status 0x1, external inbound)."
+    distribute_ubi "$JSON"
     exit 0
   fi
@@ generic externally-executed earn branch, after "GATE-0 MET"
 # 3) GATE-0: only a confirmed, net-positive wake is a real launch gate.
 if [ "$OUT" = "PROFITABLE" ]; then
   echo "[earn] GATE-0 MET: profitable wake recorded (net>0, status 0x1)."
+  distribute_ubi "$JSON"
   exit 0
 fi
```

### Diff 6 — NEW node:test for the pure cores (`__tests__/ubi.test.js`) + transfer builder (`lib/__tests__/transfer.test.js`)

```diff
diff --git a/skills/earn/lib/__tests__/transfer.test.js b/skills/earn/lib/__tests__/transfer.test.js
new file mode 100644
--- /dev/null
+++ b/skills/earn/lib/__tests__/transfer.test.js
@@
+import { test } from "node:test";
+import assert from "node:assert/strict";
+import { buildTransferData, TRANSFER_SELECTOR, USDC_BASE, toBaseUnits, shareBaseUnits, splitPool } from "../transfer.mjs";
+
+test("selector is the verified ERC20 transfer selector 0xa9059cbb", () => {
+  assert.equal(TRANSFER_SELECTOR, "0xa9059cbb"); // ctx7 /websites/base encodeProlink + local keccak
+});
+test("buildTransferData matches the ctx7 verified example (5 USDC to fe21..e51)", () => {
+  // ctx7 example: data 0xa9059cbb + word(fe21034794a5a574b94fe4fdfd16e005f1c96e51) + word(0x4c4b40=5_000_000)
+  const data = buildTransferData({ to: "0xfe21034794a5a574b94fe4fdfd16e005f1c96e51", amountBaseUnits: 5000000n });
+  assert.equal(
+    data,
+    "0xa9059cbb000000000000000000000000fe21034794a5a574b94fe4fdfd16e005f1c96e5100000000000000000000000000000000000000000000000000000000004c4b40",
+  );
+});
+test("buildTransferData rejects a bad address / negative amount", () => {
+  assert.throws(() => buildTransferData({ to: "nope", amountBaseUnits: 1n }), /address/);
+  assert.throws(() => buildTransferData({ to: USDC_BASE, amountBaseUnits: -1n }), /negative/);
+});
+test("toBaseUnits scales 6dp with no float drift; shareBaseUnits floors bps", () => {
+  assert.equal(toBaseUnits(0.45), 450000n);
+  assert.equal(shareBaseUnits(0.45, 1000), 45000n);   // 10% of 0.45 = 0.045 USDC
+  assert.throws(() => shareBaseUnits(1, 10001), /bps/);
+});
+test("splitPool floors per recipient and keeps the remainder as dust", () => {
+  assert.deepEqual(splitPool(100n, 3), { per: 33n, dust: 1n });
+  assert.deepEqual(splitPool(90n, 3), { per: 30n, dust: 0n });
+});
```
```diff
diff --git a/skills/earn/__tests__/ubi.test.js b/skills/earn/__tests__/ubi.test.js
new file mode 100644
--- /dev/null
+++ b/skills/earn/__tests__/ubi.test.js
@@
+import { test } from "node:test";
+import assert from "node:assert/strict";
+import { buildRecipients, planUbi, alreadyDone } from "../lib/ubi.mjs";
+
+const AI1 = "0x1111111111111111111111111111111111111111";
+const AI2 = "0x2222222222222222222222222222222222222222";
+const HUMAN = "0x3333333333333333333333333333333333333333";
+const SELF = "0x9999999999999999999999999999999999999999";
+// A real GATE-0 external line shape (lib/ledger.mjs deriveLine + external:true).
+const prof = { wallet: SELF, source: "0xwork", net_usdc: 1.0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w1" };
+
+test("buildRecipients dedupes, drops invalid, excludes the sender's own wallet", () => {
+  const r = buildRecipients({ childWallets: [AI1, AI2, SELF, "bad"], humanWallets: [HUMAN, AI1], sender: SELF });
+  assert.deepEqual(r, [AI1, AI2, HUMAN]); // SELF excluded, AI1 deduped, "bad" dropped
+});
+test("planUbi: 10% of net split equally across recipients (integer base units)", () => {
+  const plan = planUbi({ fundingLine: prof, recipients: [AI1, AI2, HUMAN], cfg: { shareBps: 1000, minPoolUsdc: 0.05 } });
+  assert.equal(plan.outcome, "send");
+  assert.equal(plan.pool_base, "100000");      // 10% of 1.0 USDC = 0.1 USDC = 100000 base units
+  assert.equal(plan.per_base, "33333");        // floor(100000/3)
+  assert.equal(plan.dust_base, "1");           // remainder kept by sender
+  assert.equal(plan.transfers.length, 3);
+});
+test("planUbi: a non-profitable (swap / narrate) line never funds UBI", () => {
+  const swap = { ...prof, source: "swap-eth-usdc", external: undefined };
+  assert.equal(planUbi({ fundingLine: swap, recipients: [AI1] }).outcome, "skipped");
+  assert.equal(planUbi({ fundingLine: { ...prof, status: "0x0" }, recipients: [AI1] }).outcome, "skipped");
+});
+test("planUbi: below-min pool, no recipients, and insufficient balance all skip (no send)", () => {
+  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { shareBps: 1, minPoolUsdc: 0.10 } }).reason, "below_min_pool");
+  assert.equal(planUbi({ fundingLine: prof, recipients: [], cfg: { minPoolUsdc: 0.01 } }).reason, "no_recipients");
+  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01, walletBalanceUsdc: 0 } }).reason, "insufficient_balance");
+});
+test("planUbi: dryRun computes the plan but marks it 'dry' (sends nothing)", () => {
+  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01, dryRun: true } }).outcome, "dry");
+});
+test("idempotency: a wake already distributed is a no-op", () => {
+  const done = [{ kind: "ubi", wake: "w1", outcome: "done" }];
+  assert.equal(alreadyDone(done, "w1"), true);
+  assert.equal(planUbi({ fundingLine: prof, recipients: [AI1], cfg: { minPoolUsdc: 0.01 }, ubiLines: done }).reason, "already_distributed");
+});
```
```diff
diff --git a/skills/earn/__tests__/distribute-ubi.test.js b/skills/earn/__tests__/distribute-ubi.test.js
new file mode 100644
--- /dev/null
+++ b/skills/earn/__tests__/distribute-ubi.test.js
@@
+// node:test — the bridge wiring: proves the data-contract fixes, fully OFFLINE + deterministic.
+// (1) B1/B2: a run.sh-shape line (earn_usdc/cost_usdc, NO net_usdc) is re-derived via deriveLine
+//     so isProfitable passes — without this the dry plan would be 'funding_not_profitable'.
+// (2) N1: sibling-AI recipients are read from children.jsonl rows' `wallet` field (not childWallet).
+// (3) B3: in dry-run the bridge SKIPS the live RPC balance read, so the test passes ONLINE too
+//     (no network; the fake wallet's real balance would otherwise be 0 -> insufficient_balance).
+// UBI_DRY_RUN=1 so NOTHING is sent on-chain; the overspend test injects opts.balanceFn (no RPC).
+import { test } from "node:test";
+import assert from "node:assert/strict";
+import { promises as fs } from "node:fs";
+import os from "node:os";
+import path from "node:path";
+import { distribute } from "../distribute-ubi.mjs";
+
+const SELF = "0x9999999999999999999999999999999999999999";
+const CHILD = "0x1111111111111111111111111111111111111111";
+
+test("B1/B2 + N1: run.sh-shape line (no net_usdc) is derived; child `wallet` is the AI recipient", async () => {
+  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ubi-"));
+  const childrenFile = path.join(dir, "children.jsonl");
+  const ubiLedger = path.join(dir, "ubi-ledger.jsonl");
+  // child-spec.js:37 shape: the wallet is under `wallet`, status active.
+  await fs.writeFile(childrenFile, JSON.stringify({ child_id: "anicca-c001", wallet: CHILD, status: "active" }) + "\n");
+  // EXACT run.sh 0xwork $JSON shape: earn_usdc/cost_usdc + external:true, but NO net_usdc.
+  const rawLine = { wallet: SELF, source: "0xwork", task: "t1", earn_usdc: 1.0, cost_usdc: 0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w-derive" };
+  process.env.UBI_DRY_RUN = "1";
+  process.env.UBI_MIN_POOL_USDC = "0.0001";
+  delete process.env.UBI_HUMAN_WALLETS; // AI-only: forces the children.jsonl `wallet` read to matter
+  const { line } = await distribute(rawLine, { childrenFile, ubiLedger });
+  // If net_usdc were undefined (the bug) -> outcome 'skipped'/funding_not_profitable. Derived -> 'dry'.
+  assert.equal(line.outcome, "dry");
+  assert.equal(line.recipients, 1);              // the child `wallet` was picked up (N1 fixed)
+  assert.ok(line.pool_usdc > 0);                 // net_usdc derived from earn/cost (B1/B2 fixed)
+  await fs.rm(dir, { recursive: true, force: true });
+});
+
+test("B3: NON-dry-run threads opts.balanceFn into the overspend guard (no RPC) — pool>balance skips", async () => {
+  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ubi-"));
+  const childrenFile = path.join(dir, "children.jsonl");
+  const ubiLedger = path.join(dir, "ubi-ledger.jsonl");
+  await fs.writeFile(childrenFile, JSON.stringify({ child_id: "anicca-c001", wallet: CHILD, status: "active" }) + "\n");
+  const rawLine = { wallet: SELF, source: "0xwork", task: "t1", earn_usdc: 1.0, cost_usdc: 0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w-overspend" };
+  delete process.env.UBI_DRY_RUN;                // real path -> the live-balance guard is active
+  process.env.UBI_MIN_POOL_USDC = "0.0001";
+  delete process.env.UBI_HUMAN_WALLETS;
+  // inject a balance BELOW the 0.1 USDC pool via opts.balanceFn — deterministic, no Base RPC call,
+  // and no executor reached (skipped never spawns python). Proves the bridge wires balanceFn correctly.
+  const { line, sent } = await distribute(rawLine, { childrenFile, ubiLedger, balanceFn: async () => 0 });
+  assert.equal(sent, false);
+  assert.equal(line.outcome, "skipped");
+  assert.equal(line.reason, "insufficient_balance");
+  await fs.rm(dir, { recursive: true, force: true });
+});
```

### Diff 7 — `SKILL.md`: document the UBI side-channel + its honesty gate

```diff
diff --git a/skills/earn/SKILL.md b/skills/earn/SKILL.md
--- a/skills/earn/SKILL.md
+++ b/skills/earn/SKILL.md
@@ after the Ledger section
+## UBI (spec 28 §0) — share OWN earnings with AI + human recipients
+After a wake records **PROFITABLE** (real external USDC, `isProfitable`), `run.sh` calls
+`distribute-ubi.mjs`: it sends `UBI_SHARE_BPS` (default 10.00%) of THIS wake's net, split equally,
+to sibling-AI child wallets (`self/spawn/state/children.jsonl`) + a human allow-list
+(`UBI_HUMAN_WALLETS` / `state/ubi-recipients.json`), via one ERC20 USDC `transfer` each
+(`0xa9059cbb`, USDC `0x8335…2913`, 6dp — ctx7-verified). It funds ONLY from Anicca's OWN wallet and
+touches ZERO user identity (earn-side of the spec 28 §3 wall). Idempotent per `wake`; never sends
+more than earned; `UBI_DRY_RUN=1`/below-min/no-recipients → record `dry`/`skipped` (NO fake send).
+Audit trail: append-only `state/ubi-ledger.jsonl` (`{kind:"ubi",wake,outcome,txs:[{to,tx,status}]}`)
+— separate from the earn ledger so the GATE-0 classifier is untouched.
```

## §4 Run commands

```bash
cd ~/anicca/skills/earn
# 1) pure cores + bridge wiring (offline, deterministic):
node --test lib/__tests__/transfer.test.js __tests__/ubi.test.js __tests__/distribute-ubi.test.js
node --test __tests__/*.test.js lib/__tests__/*.test.js     # full earn suite stays green (no regression)

# 2) dry-run the bridge against the EXACT run.sh 0xwork $JSON shape — earn_usdc/cost_usdc + external, NO
#    net_usdc (deriveLine must fill it). Dry-run makes NO RPC call (B3), so this is fully offline:
UBI_DRY_RUN=1 UBI_MIN_POOL_USDC=0.0001 UBI_HUMAN_WALLETS=0x3333333333333333333333333333333333333333 \
  node distribute-ubi.mjs '{"wallet":"0x9999999999999999999999999999999999999999","source":"0xwork","task":"t1","earn_usdc":1.0,"cost_usdc":0,"tx":"0xaaaa","status":"0x1","external":true,"wake":"w-dry"}'
tail -1 state/ubi-ledger.jsonl     # -> {"kind":"ubi","wake":"w-dry","outcome":"dry","pool_usdc":0.1,...}
#   (skipped/funding_not_profitable => deriveLine regressed; skipped/insufficient_balance => B3 regressed.)

# 3) LIVE (real money, only after GATE-0): the next real external wake auto-fires distribute_ubi from run.sh.
#    To force a real distribution from a known profitable line (small amount), point at the real children.jsonl:
EARN_MODE=execute EARN_STRATEGY=0xwork ./run.sh      # on PROFITABLE -> distribute_ubi -> execute-ubi.py
```

## §5 E2E acceptance (HARD 0.24 / 0.31 — real on-chain evidence, no mock as headline)

1. **Pure unit + bridge gate (offline, deterministic — must pass ONLINE too):**
   `node --test lib/__tests__/transfer.test.js __tests__/ubi.test.js __tests__/distribute-ubi.test.js` green; the
   `buildTransferData` test reproduces the ctx7-verified `0xa9059cbb…004c4b40` calldata byte-for-byte; the
   `distribute-ubi` tests prove (a) deriveLine fills `net_usdc` from a run.sh-shape line → `dry`, (b) the child
   `wallet` field is the AI recipient, (c) B3 — dry-run makes no RPC call so it passes online, and the overspend
   guard is exercised via injected `opts.balanceFn` (no Base RPC); full earn suite still green (no GATE-0 regression).
2. **Dry-run gate:** step-2 above records a `dry` line and sends NOTHING (no tx hash, no RPC call) — proves the path
   is wired without faking a transfer or touching the network (B3-safe).
3. **REAL on-chain distribution (the headline truth):** a profitable external wake fires `distribute_ubi`, and
   `execute-ubi.py` lands **at least one real USDC `transfer` tx to a recipient with receipt status `0x1`**.
   Evidence required: (a) the **tx hash** on basescan.org showing a USDC Transfer FROM Anicca's wallet TO the
   recipient; (b) recipient USDC `balanceOf` increased by `per_base` (`node -e "import('./lib/usdc.mjs')…"`);
   (c) Anicca's wallet USDC decreased by the pool; (d) one `state/ubi-ledger.jsonl` line `outcome:"done"` whose
   `txs[].status==="0x1"` and whose `wake` matches the funding earn line. Re-running the same wake = `already_distributed`
   no-op (idempotency proven on disk).
4. **Wall proof:** the whole UBI path runs inside the earn process that already passed `assertOwnIdentityOnly`
   (`record.mjs:19`); `ubi.mjs` has no user-identity parameter and is import-tested to take only wallet addresses
   + numbers. A grep shows no user-PII env/source reaches it.
5. **Honesty fallback (if no real external earn by launch):** UBI records only `dry`/`skipped` lines (never `done`),
   and the launch copy uses the softened truthful form (§2). The claim flips to the hard form ONLY when acceptance
   item 3 has a real `0x1` tx hash on /dashboard.

## §6 Boundaries

- **Repo:** `Daisuke134/anicca` (OSS), `skills/earn/` ONLY. NEW: `lib/transfer.mjs`, `lib/ubi.mjs`,
  `distribute-ubi.mjs`, `execute-ubi.py`, `lib/__tests__/transfer.test.js`, `__tests__/ubi.test.js`,
  `__tests__/distribute-ubi.test.js`, `state/ubi-ledger.jsonl` (runtime, append-only). EDIT: `run.sh`
  (fire hook), `SKILL.md` (docs).
- **No new deps:** `web3` + `eth_account` already required by `execute-swap.py`/`execute-0xwork.py`; node side is
  `node:*` only. No `viem`/`base-mcp` introduced (ctx7 examples were reference, not a runtime dep).
- **Reads** `self/spawn/state/children.jsonl` (own colony, read-only) for AI recipient wallets — never writes it.
- **Does NOT touch** the earn ledger, the GATE-0 classifier, or `identity-guard.mjs`. UBI is a strictly own-side
  side-channel funded by an already-verified GATE-0 line.
- **Open risk (stated honestly):** (a) UBI's first REAL tx depends on GATE-0 being met (Task #8) — until then only
  `dry`/`skipped` lines exist and the claim stays softened; (b) sibling-AI recipients require the colony to have
  spawned children (`children.jsonl` non-empty) — if empty at launch, only the human allow-list receives, and with
  no human wallet set the plan is `no_recipients` (skipped, no fake); (c) gas on Base is paid in ETH from Anicca's
  own wallet — the `EARN_MIN_ETH_RESERVE` survival logic is NOT shared here, so a UBI run when ETH≈0 will fail
  `estimate_gas` and record `transfer_failed` (honest skip), never bricking the earn wake.
