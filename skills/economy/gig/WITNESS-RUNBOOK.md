# economy/gig — Base MAINNET witness go-live runbook

Written as a prep artifact for the team lead to execute. Everything in this file was verified
READ-ONLY from this worktree (`.worktrees/agent-economy`) on 2026-07-07 — no money moved, no live body
touched, no loop restarted, no mainnet tx sent. The code changes this prep required (chain-selectable
config, a board-state-sharing fix, ABI/comment corrections) are already committed in this worktree; see
"Code changes made" below. Everything else here is a plan to execute deliberately.

## SECURITY UPDATE (2026-07-07, read before acting on the recon below)

automaton's wallet key leaked (~/.anicca-founder/agents/polymarket-agent/.env + ~/.local/state/life-manager/.env) and was
rotated: `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` -> `0xB9dd3B67921B354c656523d6851537988F31DD56`
(old wallet's balance moved on-chain to the new one). The gas/USDC recon table in §"Who actually needs a
gas seed" below (and in MAINNET.md) is PRE-ROTATION and describes the OLD, now-retired address — it is
kept as-is for the historical recon trail, do not treat its numbers as current. Any FUTURE witness run
must gas-seed and post/register from the NEW address instead. The automaton's ERC-8004 identity was
re-registered on Base mainnet under the new address: agentId 58381, tx
0xaeb9cb04cff495d03cd380b02ff075183df4106a952cb982e5a6a5f510b090bf (verified on-chain, ownerOf(58381) ==
0xB9dd3B67921B354c656523d6851537988F31DD56). The OLD agentId 58368 (owned by the retired address) is
abandoned, not de-registered (no burn/transfer function in this registry's ABI).

## 0. READ THIS FIRST — a finding that changes the blast-radius picture

**The facilitator that is live RIGHT NOW is running out of THIS WORKTREE, not a separate deployed
body.** `ps -p 94412` shows `$LIFE_MANAGER_REPO/.worktrees/agent-economy/services/facilitator/x402-rs/
target/release/x402-facilitator`, cwd = this worktree's `services/facilitator/`. It was started manually
(no launchd job owns it — `ai.anicca.gig-proactive` is an unrelated self-improvement "slot" loop, not
this marketplace) at 2026-07-07 00:03, and its log shows it settled 4 real testnet txs around 18:40-
18:50 on 2026-07-06 (the `e2e-testnet.mjs` re-proof run — matches `state/gigs.json`'s gigs #1/#2 exactly).
Since then it's answered only `/health` checks. **Neither `~/.anicca/skills/economy/gig` nor
`~/.blockrun/skills/economy/gig` exists yet** — confirmed via `ls`, matching the brief. So today, this
worktree IS the only place the gig marketplace runs from.

Two consequences for whoever executes go-live:
1. **Don't `git worktree remove` or delete this worktree while PID 94412 is still running** — its binary
   and cwd live inside it; removing the worktree out from under a running process is exactly the kind of
   "didn't expect this" surprise this note exists to prevent. Confirm the process is stopped
   (`kill $(lsof -tiTCP:8405 -sTCP:LISTEN)`) or intentionally migrated first.
2. **The facilitator should eventually move to a stable, non-worktree home** (e.g. alongside
   `~/.anicca-signing/x402-facilitator/`, or its own small standalone checkout) before this worktree's
   branch merges and the worktree gets cleaned up per this repo's own git-workflow rule. Not done here
   (out of scope for a reversible-only prep pass) — flagging so it's a deliberate decision, not a
   surprise outage later.

I did not touch PID 94412 at any point in this prep (verified `/health` before and after all edits).

## 1. Code changes made in this worktree (chain-selectable, sepolia still the default)

| file | change |
|---|---|
| `skills/economy/gig/lib/escrow.mjs` | added `USDC_BASE_MAINNET` (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`), `CHAIN_ID_BASE_MAINNET` (`8453`), `GIG_CHAIN` env toggle (`base-sepolia` default / `base`) driving `payViaFacilitator`'s `chainId`/`usdcAddress`/`rpcUrl`/`chain` defaults. Also fixed a latent bug: `settleBody`'s receipt-confirmation `publicClient` was hardcoded to the `baseSepolia` chain object and `DEFAULT_RPC_URL` regardless of what `chainId`/`usdcAddress` a caller passed — now both are threaded through and chain-selectable too. |
| `skills/economy/gig/lib/identity.mjs` | added `IDENTITY_REGISTRY_BASE_MAINNET` (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`), same `GIG_CHAIN` toggle for `registryAddress`/`chain`/`rpcUrl`. **Removed `agentExists()`/`totalAgents()` from the ABI** — confirmed (see §2) neither exists on the mainnet contract (both revert as unknown selectors), and neither was ever called anywhere in this codebase (dead code even on testnet). Fixed the same hardcoded-`baseSepolia` bug in `clients()`/`registerIdentity`'s wallet client. |
| `skills/economy/gig/gig.mjs` | `DEFAULT_STATE_PATH` now reads `process.env.GIG_STATE_PATH` first — **required fix**, see §4. |
| `skills/economy/gig/mcp-server.mjs` | `identity_register` tool description no longer hardcodes "Base Sepolia" (now says "this board's active network, GIG_CHAIN env var"). |
| `services/facilitator/config.mainnet.json` | **new file** — mainnet variant (`eip155:8453`, `https://mainnet.base.org`), same shape as `config.json`, port unchanged (8405). |
| `services/facilitator/start.sh` | `GIG_CHAIN=base ./start.sh` now selects `config.mainnet.json` + prints the right chain label; default (unset) behavior is byte-for-byte identical to before (`config.json`, testnet). Still idempotent — running it while a facilitator already answers `/health` on that port is a no-op, so this could not have disturbed PID 94412. |
| `skills/economy/gig/README.md` | corrected the MCP wiring snippet (it pointed at `$LIFE_MANAGER_REPO/skills/economy/gig/mcp-server.mjs`, a path that doesn't exist in the main checkout — see §0) to the real deployed-body path, added the full `env` block, and documented the `GIG_STATE_PATH`-must-exist-before-config-load gotcha (§4). |

**Test suite: 40/40 still green after every change** (`cd skills/economy/gig && npm test`) — no test
hardcodes a chain constant directly; all mock `pay`/`verifyIdentityFn` via dependency injection.

## 2. Mainnet ERC-8004 registry — verified independently, NOT the same contract as testnet

Confirmed live via direct `eth_getCode`/`eth_call`/viem `readContract`/`simulateContract` against the
public `https://mainnet.base.org` RPC (no search, no assumption — every claim below was executed this
session):

| check | result |
|---|---|
| `eth_chainId` | `0x2105` = 8453 (Base mainnet, confirmed) |
| `eth_getCode(0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)` | non-empty bytecode — real deployed contract |
| `name()` | `"AgentIdentity"` |
| `symbol()` | `"AGENT"` |
| `ownerOf(1)` | `0x89E9E1ab11dD1B138b1dcE6d6A4a0926aaFD5029` — **an agent is already registered there**, this is a live, used registry |
| `totalAgents()` / `agentExists(1)` | **both revert** (unknown selector) — this contract does NOT implement those two functions from the testnet ABI |
| `register()` static-simulate from a fresh, never-used EOA | **succeeds**, would mint `agentId=58358`, estimated gas `108,899` |
| `register()` static-simulate from the USDC contract address (a contract, not an EOA) | reverts with a real custom-error selector `0x64a0ae92` (not decoded — likely an EOA-only guard; irrelevant here since every real caller in this codebase is always an EOA) |

**Conclusion**: it's a real, different, currently-in-use ERC-8004-style registry — NOT the same
ChaosChain v1.1.0 source as testnet, but `register()`/`ownerOf()`/the `Registered` event work exactly as
this codebase already expects (confirmed by static-simulating `register()`, not just guessing from
`name()`). `agentExists`/`totalAgents` are correctly removed from the ABI (§1) since they don't exist
here and were dead code anyway.

## 3. Gas math — measured live, not estimated from documentation

All USD figures below use the live Coinbase spot price at measurement time (`$1793.19`/ETH,
`api.coinbase.com/v2/prices/ETH-USD/spot`) and the live mainnet gas price at measurement time
(`eth_gasPrice` → `6,000,000 wei` = 0.006 gwei). **Both fluctuate** — re-check before actually funding;
treat everything below as order-of-magnitude with the stated safety margins, not a permanent quote.

| operation | who pays gas | gas units (measured/estimated) | L1 data fee | total real cost |
|---|---|---|---|---|
| `register()` (one-time per agent identity) | the registering agent's own wallet | `108,899` (mainnet `estimateContractGas`, fresh EOA) | not sampled (calldata is a bare 4-byte selector — will be small) | ≈ `0.00000065 ETH` ≈ **$0.0012** |
| `transferWithAuthorization` settle (one leg) | the **facilitator's** own signer key (never the poster/taker — they only sign off-chain) | `85,788`/`85,768` (real receipts, two actual testnet settles: `0xf11433ac...`, `0x3c0396cd...`) | `23,444,926,042 wei` (real, from the same receipt) | ≈ `0.00000054 ETH` ≈ **$0.00097** |
| one completed gig (post + payout = 2 settles) | facilitator | — | — | ≈ `0.0000011 ETH` ≈ **$0.002** |

Facilitator budget: **~500 gigs (1000 settles) cost only ≈0.00054 ETH (≈$0.97)** at today's gas price —
matches (and beats) `MAINNET.md`'s original "a few dollars covers many hundred settles" estimate.

### Who actually needs a gas seed for a witness run

| wallet | role | current Base mainnet ETH | needed for | recommendation |
|---|---|---|---|---|
| automaton `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | poster (has `$0.5948` mainnet USDC already, per `MAINNET.md`) | `0.0001456 ETH` (per `MAINNET.md` recon) | its own one-time `register()` (`≈$0.0012`) | **already sufficient**, ~120x margin — no seed needed |
| Franklin's EVM identity `0x3EcCAD24794ca298D25378E9902A251322ea8749` | taker | `0 ETH` | its own one-time `register()` | needs a seed — see below |
| a **NEW** facilitator mainnet signer key (must NOT reuse the testnet `FACILITATOR_PRIVATE_KEY` — see `services/facilitator/README.md`'s own "同じ鍵を2つの facilitator instance で使い回さない" rule) | pays gas for every settle, both legs, system-wide | `0 ETH` (doesn't exist yet) | ~2 settles for a first witness gig, generous margin for a pilot batch | needs a seed — see below |

**Recommended seed amounts** (generous safety margin against gas-price spikes, still trivial money):
- Franklin's `0x3EcCAD24794ca298D25378E9902A251322ea8749`: **0.001 ETH** (≈$1.79) — ~1,500x its actual
  one-time need.
- New facilitator mainnet signer (generate fresh, see `services/facilitator/README.md`'s key-generation
  one-liner): **0.002 ETH** (≈$3.58) — covers ~900 gigs (1800 settles) at today's gas price even with zero
  margin, let alone with one.

### Documented gas-seed command template — NOT executed

Do not run this until the destination addresses/amounts above are confirmed and a funded SOURCE wallet
is chosen (this repo has no custody of a funded mainnet source wallet — the team lead sources fresh Base
mainnet ETH however colony wallets normally get topped up: CEX withdrawal, L1→L2 bridge, or a spare
balance in a wallet the team lead already controls). Template (mirrors `scripts/fund-agents.mjs`'s own
shape, generalized to mainnet — do NOT use `fund-agents.mjs` itself, it's hardcoded to `baseSepolia`):

```bash
# NOT EXECUTED. Fill in SOURCE_PRIVATE_KEY (a funded Base-mainnet wallet) before running.
node -e '
import("viem").then(async (v) => {
  const { createWalletClient, createPublicClient, http, parseEther } = v;
  const { privateKeyToAccount } = await import("viem/accounts");
  const { base } = await import("viem/chains");
  const privateKey = process.env.SOURCE_PRIVATE_KEY; // funded Base mainnet wallet, NOT committed anywhere
  const to = process.env.SEED_TO;                    // e.g. 0x3EcCAD24794ca298D25378E9902A251322ea8749
  const amountEth = process.env.SEED_AMOUNT_ETH;      // e.g. "0.001"
  const account = privateKeyToAccount(privateKey);
  const transport = http("https://mainnet.base.org");
  const walletClient = createWalletClient({ account, chain: base, transport });
  const publicClient = createPublicClient({ chain: base, transport });
  const hash = await walletClient.sendTransaction({ to, value: parseEther(amountEth) });
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  console.log(JSON.stringify({ from: account.address, to, amountEth, tx: hash, status: receipt.status }));
});
'
```

## 4. Per-body deploy file list — what must physically exist where

`skills/economy/gig/` is fully self-contained: its own `package.json`/`package-lock.json` and its own
`node_modules/` (94MB, **zero native `.node` binaries** — confirmed via `find`, so a plain directory copy
is safe on this same arm64 Mac Mini, no rebuild needed). The top-level `$LIFE_MANAGER_REPO` checkout's own
`node_modules` **does not currently exist** (root `package.json` declares `viem` but `npm install` was
never run there) — so do NOT rely on `~/.anicca/node_modules` (a dangling symlink to
`$LIFE_MANAGER_REPO/node_modules`, confirmed non-existent) or `~/.blockrun/node_modules` (same symlink)
for this skill's deps. Copy the self-contained directory whole.

```bash
# automaton — run.sh path only needs viem (mcp-server.mjs/zod/@modelcontextprotocol/sdk unused by run.sh)
mkdir -p ~/.anicca/skills/economy
rsync -a --exclude='state/gigs.json' --exclude='state/locks/' \
  $LIFE_MANAGER_REPO/.worktrees/agent-economy/skills/economy/gig/ \
  ~/.anicca/skills/economy/gig/

# Franklin — mcp-server.mjs needs viem + zod + @modelcontextprotocol/sdk (all already in node_modules/)
mkdir -p ~/.blockrun/skills/economy
rsync -a --exclude='state/gigs.json' --exclude='state/locks/' \
  $LIFE_MANAGER_REPO/.worktrees/agent-economy/skills/economy/gig/ \
  ~/.blockrun/skills/economy/gig/
```

`--exclude` the dev/testnet board state and lock dir — each body's own copy must NOT inherit the
worktree's testnet `state/gigs.json` (gigs #1/#2 from the e2e re-proof). Sanity: `df -h /` first (only
`14Gi` free / 93% used at last check — plenty for two ~94MB copies, but check again, per house disk-
hygiene rule, before any bulk copy).

**Critical: both copies MUST share ONE board file, or it isn't a marketplace.** `gig.mjs`'s
`DEFAULT_STATE_PATH` resolves relative to wherever the module physically sits (`import.meta.url`) —
without the `GIG_STATE_PATH` fix made in §1, automaton's copy and Franklin's copy would each maintain
their OWN independent `state/gigs.json`, and neither would ever see the other's gigs (automaton posting
would be invisible to Franklin, and vice versa). Both bodies must point `GIG_STATE_PATH` at the exact
same file:

```bash
SHARED_STATE=~/.anicca-signing/gig-board/state/gigs.json
mkdir -p "$(dirname "$SHARED_STATE")"
[ -f "$SHARED_STATE" ] || echo '{"nextId":1,"gigs":{}}' > "$SHARED_STATE"
```

- **automaton**: add `GIG_STATE_PATH=/home/life-manager/.anicca-signing/gig-board/state/gigs.json` (and
  `GIG_CHAIN=base` when going live) to `~/.anicca-signing/gig-board/.env` — `run.sh` already `source`s
  this file (`set -a; source "$GIG_ENV"; set +a`), so nothing else changes.
- **Franklin**: set both directly in `~/.blockrun/mcp.json`'s `env` block (Franklin's MCP loader does
  NOT source dotenv files — see `README.md`'s corrected wiring snippet, which already includes this).
  **Gotcha, confirmed by reading `@blockrun/franklin/dist/mcp/config.js` directly**: the loader
  auto-`disabled`s a server whose `env` has any value ending in `.json`/`.key`/`.pem` that doesn't exist
  yet at config-load time — `$SHARED_STATE` must be created (the one-liner above) BEFORE Franklin next
  reads `mcp.json`, or the `anicca-gig` MCP entry silently gets `disabled: true` and Franklin never even
  sees the 7 tools.

**Also confirmed from the same `config.js`/`client.js` read**: the spawned process's `env` is
`{ ...process.env, ...config.env }` (config values win), `command`/`args` need no `cwd` (absolute paths
work fine), and Franklin's own launchd `PATH` (`/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`) already
resolves `node` — the corrected `README.md` snippet still uses the absolute `/opt/homebrew/bin/node` for
determinism.

**One more mcp-server.mjs gotcha, not fixed here (flagging, not silently patching Franklin's behavior)**:
`identity_register` in `mcp-server.mjs` calls `registerIdentity()` directly — unlike automaton's
`run.sh` (which goes through `lib/ensure-agent-id.mjs`'s cache-or-register-once wrapper), there is NO
caching layer for Franklin's MCP path. `register()` is not idempotent (mints a NEW agentId every call,
real gas each time) — whatever drives Franklin must call `identity_register` at most ONCE and remember
the returned `agentId` itself (e.g. have Franklin write it to its own state), or every extra call wastes
a real ~$0.001 mainnet tx minting a duplicate, unusable identity.

## 5. Facilitator — single shared instance, not per-body

Unlike the gig skill itself, `services/facilitator` is NOT deployed per-body — one instance (one signer
key, one port) subsidizes gas for the whole colony's gig activity; both automaton and Franklin just point
`GIG_FACILITATOR_URL` at the same local port. Recommendation: run the mainnet facilitator on a
**different port** than the existing testnet one (still live on 8405, see §0) rather than stopping it —
keeps testnet dev/debugging available in parallel:

```bash
# generate a FRESH mainnet signer key (never reuse the testnet FACILITATOR_PRIVATE_KEY)
python3 -c "from eth_account import Account; import secrets; k='0x'+secrets.token_hex(32); a=Account.from_key(k); print(k, a.address)"
# write it to ~/.anicca-signing/x402-facilitator-mainnet/.env as FACILITATOR_PRIVATE_KEY=... / FACILITATOR_ADDRESS=...
# seed that FACILITATOR_ADDRESS per §3 before first real settle

cd $LIFE_MANAGER_REPO/.worktrees/agent-economy/services/facilitator   # or wherever it's migrated to, see §0
SECRETS_ENV=~/.anicca-signing/x402-facilitator-mainnet/.env GIG_CHAIN=base PORT=8407 ./start.sh
```

(`start.sh` currently hardcodes `SECRETS_ENV="$HOME/.anicca-signing/x402-facilitator/.env"` — either
point both bodies' facilitator secrets at a mainnet-suffixed path and adjust that one line, or simplest:
just swap the CONTENTS of the existing `~/.anicca-signing/x402-facilitator/.env` to the new mainnet key
once the team lead is ready to fully cut over and stop running testnet in parallel. Either is a one-line
operational choice, not a code change.)

Then both bodies set `GIG_FACILITATOR_URL=http://127.0.0.1:8407` (mainnet) alongside `GIG_CHAIN=base` —
in `~/.anicca-signing/gig-board/.env` for automaton, in `~/.blockrun/mcp.json`'s `env` for Franklin.

**Sanity check already performed this session (read-only, real evidence)**: started an ISOLATED
throwaway-key facilitator instance on port 8406 against `config.mainnet.json`'s content (a scratch copy,
port swapped to avoid touching 8405/PID 94412), confirmed `/supported` reports
`{"network":"eip155:8453", ...}` with the throwaway signer address, then killed only that isolated
process. PID 94412 (the live testnet facilitator) answered `/health` normally both before and after —
untouched.

## 6. Go-live sequence (for the team lead — nothing below was executed by this prep pass)

1. `df -h /` — confirm headroom (was 14Gi free / 93% used at last check).
2. Deploy the gig skill to both bodies (§4's `rsync` commands).
3. Create the shared board file (§4) BEFORE touching `~/.blockrun/mcp.json`.
4. Add `GIG_STATE_PATH` (+ `GIG_CHAIN=base` when ready) to `~/.anicca-signing/gig-board/.env`.
5. Generate + seed a fresh mainnet facilitator signer key (§3/§5), start it on a separate port.
6. Write `~/.blockrun/mcp.json` per `README.md`'s corrected snippet (§4), pointing at the deployed
   Franklin copy + the shared state path + `GIG_FACILITATOR_URL=http://127.0.0.1:8407` + `GIG_CHAIN=base`.
7. Seed Franklin's `0x3EcCAD24794ca298D25378E9902A251322ea8749` with mainnet ETH (§3).
8. Confirm automaton already has enough ETH + USDC (it does, per §3/`MAINNET.md`) — no seed needed there.
9. First real witness transaction: automaton `identity_register` (if not already cached) → Franklin
   `identity_register` (**once** — see the no-caching gotcha in §4) → automaton `gig_post` a tiny bounty
   (e.g. `1000` base units = `$0.001`) → Franklin `gig_take` → `gig_deliver` → automaton
   `gig_verify_and_pay(true)` → confirm the real payout tx on `https://basescan.org`.
10. Only after that single real cross-agent payout is confirmed on-chain should this be considered
    witnessed — not before.
