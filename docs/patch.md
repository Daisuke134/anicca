# PATCH — Beefy(#1)/Fluid(#2)/Aave(#3) auto highest-APY yield venue (NO opt-in)

PROPOSED ONLY. Not applied. Approve before I touch code.
Format per change: file:line · `-` deleted · `+` added · SOURCE = repo:file:line:snippet copied/tweaked.

Baseline = current committed `skills/earn/execute-yield.mjs` (reverted to HEAD, verified).

---

## PATCH 1 — add Fluid address + APY + ERC4626 deposit ABI
**File:** `skills/earn/execute-yield.mjs`  **Insert after line 64** (after `const aave = [...]`)

```diff
  const aave = [{ name: "supply", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }, { type: "address" }, { type: "uint16" }], outputs: [] }];
+ const FLUID = "0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169"; // Fluid fUSDC, ERC4626, 5.36% APY
+ const FLUID_APY = 0.0536;
+ const erc4626 = [
+   { name: "deposit", type: "function", stateMutability: "nonpayable", inputs: [{ type: "uint256" }, { type: "address" }], outputs: [{ type: "uint256" }] },
+ ];
```
**SOURCE:**
- `FLUID` address `0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169`, "ERC-4626 (deposit(assets,receiver))", supplyRate — copied from `docs/earn-verification-2026-06-18.md:233` ("fUSDC fToken(Base): 0xf42f5795… underlying USDC, supplyRate 5.28%, ERC-4626(deposit(assets,receiver)/convertToAssets)"). APY 5.36% updated from subagent live pull `api.fluid.instadapp.io/v2/lending/8453/tokens` (supplyRate:536).
- `erc4626` deposit ABI shape `deposit(uint256 assets, address receiver)` — tweaked from GOAT `goat-sdk/goat:typescript/packages/plugins/lulo/src/lulo.service.ts:6-26` (one method = one venue deposit returns tx) + the ERC4626 mint/deposit pattern in `plugins/ionic/src/ionic.service.ts:25-48` (`functionName:"mint"`). Adapted to viem ABI literal.

---

## PATCH 2 — replace Aave-default/Beefy-opt-in with AUTO highest-APY selection
**File:** `skills/earn/execute-yield.mjs`  **Replace lines 97–103**

```diff
-    // Default venue = Aave v3 (simple supply(), ~250k predictable gas, never the deep-strategy revert).
-    // The Beefy Morpho-gauntlet vault deposit costs ~1.5M gas and reverted intermittently (status 0x0)
-    // — a gas-heavy strategy that's fragile under the loop. Reliable 3.2% beats a reverting 5.35%.
-    // Set YIELD_PREFER_BEEFY=1 to opt back into the higher-APY Beefy vault.
-    const useBeefy = process.env.YIELD_PREFER_BEEFY === "1" && bf && bf.apy > AAVE_APY;
-    const venue = useBeefy ? vault : AAVE_POOL;
-    const protocol = useBeefy ? `beefy:${bf.id}` : "aave-v3-base";
+    // AUTO highest-APY, NO opt-in (money trees used by default). Beefy ~6.1% #1 (proven earner:
+    // $3.82 deposit → $3.85 withdraw, tx 0x55c71f84) → Fluid 5.36% #2 (clean ERC4626) → Aave 3.2% #3.
+    let venue, protocol, apy, depositKind;
+    if (bf && bf.apy >= FLUID_APY) { venue = vault; protocol = `beefy:${bf.id}`; apy = bf.apy; depositKind = "beefy"; }
+    else if (FLUID_APY >= AAVE_APY) { venue = FLUID; protocol = "fluid-fusdc"; apy = FLUID_APY; depositKind = "erc4626"; }
+    else { venue = AAVE_POOL; protocol = "aave-v3-base"; apy = AAVE_APY; depositKind = "aave"; }
```
**SOURCE:**
- "Beefy #1, proven $3.82→$3.85 (tx 0x55c71f84)" — copied from `docs/earn-verification-2026-06-18.md:112`; "Beefy 6.1% (tx 0x99ed9233), 2× Aave" from `:95`.
- "enumerate venues, pick best APY" decision shape — tweaked from `fetchai/agents-aea:packages/.../tac_negotiation/strategy.py:413` (`_generate_candidate_proposals` enumerates candidates) + `:485` (`is_profitable_transaction` gate picks ≥0). We collapse it to a code-side best-APY pick (Dais: park automatically, no model decision).
- `bestBeefy()` (`bf`, `vault`) already exists in our file lines 66–80, 91–92 — reused, not copied.

---

## PATCH 3 — deposit call handles 3 venue types (beefy / erc4626 / aave)
**File:** `skills/earn/execute-yield.mjs`  **Replace lines 115–117**

```diff
-    const tx = useBeefy
-      ? await w.writeContract({ address: venue, abi: beefy, functionName: "deposit", args: [surplus] })
-      : await w.writeContract({ address: venue, abi: aave, functionName: "supply", args: [USDC, surplus, acct.address, 0] });
+    const tx = depositKind === "beefy"
+      ? await w.writeContract({ address: venue, abi: beefy, functionName: "deposit", args: [surplus] })
+      : depositKind === "erc4626"
+      ? await w.writeContract({ address: venue, abi: erc4626, functionName: "deposit", args: [surplus, acct.address] })
+      : await w.writeContract({ address: venue, abi: aave, functionName: "supply", args: [USDC, surplus, acct.address, 0] });
```
**SOURCE:**
- Beefy `deposit(uint256)` + Aave `supply(asset,amount,onBehalfOf,referral)` branches — already in our file lines 115–117 (kept).
- Fluid branch `deposit(surplus, acct.address)` (ERC4626 deposit(assets,receiver)) — tweaked from GOAT `goat-sdk/goat:plugins/lulo/src/lulo.service.ts:6-26` (one-method-per-venue deposit returns tx hash) using the ERC4626 signature from `docs/earn-verification-2026-06-18.md:233`.

---

## PATCH 4 — return the real chosen APY (was hardcoded ternary)
**File:** `skills/earn/execute-yield.mjs`  **Line 119** (the `return out({...apy_pct...})`)

```diff
-    return out({ kind: "yield", action: "deploy", protocol, apy_pct: +((useBeefy ? bf.apy : AAVE_APY) * 100).toFixed(2), tx, status: r.status === "success" ? "0x1" : "0x0", deposited_usdc: Number(surplus) / 1e6, reserve_usdc: RESERVE / 1e6, wallet: acct.address });
+    return out({ kind: "yield", action: "deploy", protocol, apy_pct: +(apy * 100).toFixed(2), tx, status: r.status === "success" ? "0x1" : "0x0", deposited_usdc: Number(surplus) / 1e6, reserve_usdc: RESERVE / 1e6, wallet: acct.address });
```
**SOURCE:** trivial rename `useBeefy ? bf.apy : AAVE_APY` → `apy` (the variable PATCH 2 sets). No external source — internal consistency.

---

## VERIFY plan (after approval, no-mock)
1. `node --check skills/earn/execute-yield.mjs`
2. real run: withdraw $1 from Aave → liquid → run execute-yield → assert it deposits to **Beefy** (protocol=`beefy:*`), tx `status:0x1`, and on-chain Beefy `balanceOf > 0`.
3. record only on `status:0x1` (the ledger-lie fix is a SEPARATE patch in run.sh / record path — flagged, not in this file).
