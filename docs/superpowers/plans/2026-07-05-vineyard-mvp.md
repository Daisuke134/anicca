# Vineyard MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone `~/vineyard/` OSS repo (spec: `docs/superpowers/specs/2026-07-05-vineyard-hackathon-design.md`) up through TODO items **B, C, D, E, F, H, I** — repo scaffold, per-instance wallet spawn, Polymarket bridge fund, all 4 engines wired, the earn loop, llms.txt+REST+OpenAPI, and a README quickstart verified from a clean clone. **Excludes G (Web App UI), J (demo video), K (submission docs) and L (VCSDD wrapping)** — G needs its own gpt-tasteskill design pass (separate follow-up plan once this backend is real and running), J needs real ledger data from a live run, K is a copy-only pass, and L is the verification *method* applied *while* executing this plan (HARD RULE 0.37/0.40), not a standalone task.

**Architecture:** Node.js (`.mjs`) `cli/` + `api/` + `core/` own the CLI/HTTP surface, per-instance wallet isolation, the spawn registry, the on-chain-verified ledger, and the wake→pick→earn→ledger loop. The 4 earn engines are NOT reimplemented in JS — the original anicca Python/shell scripts are copied in under `engines/python/` and `engines/shell/`, and each `engines/<name>.mjs` is a thin wrapper that shells out to the copied script (`child_process.execFile`/`spawn`), parses its real stdout, and returns structured data to `core/loop.mjs`. This preserves the proven, adversary-verified money-safety logic (deposit-wallet registry gate, neg-risk approvals, CTF operator approval, fail-closed key resolution) byte-identical instead of risking bugs from a rewrite.

**Tech Stack:** Node.js ≥20 (`viem`, `express`), Python 3.11+ in a repo-local venv (`polymarket-client`, `hyperliquid-python-sdk`, `web3`, `eth-account`, `requests`, `python-dotenv`), Bash (`run.sh` wrapper), the globally-installed `@blockrun/franklin-trading` CLI (npm, real package confirmed `0.2.4`) for the Solana engine, `node:test` + `node:assert/strict` for all unit tests.

---

## Verified interfaces & discrepancies from the spec's assumptions (read this before Task 1)

Every file below was opened and read in full (or its CLI/argparse/`__main__` section read) on 2026-07-05, per the HONESTY RULES verification protocol — nothing here is guessed. Several real interfaces differ from what `2026-07-05-vineyard-hackathon-design.md` §5 assumed; each is called out with the exact adaptation this plan makes, so no wrapper code below is written against a fabricated contract.

| # | Spec assumed | Reality (verified) | Adaptation this plan makes |
|---|---|---|---|
| D1 | `v2_full_flow.py` is a generic, reusable "place a FAK order" script the wrapper can call with different params | It is a **hardcoded one-off proof script**: fixed token_id (`102051736...`), fixed `amount="1"`, fixed price-offset math, fixed absolute `.env` path `/Users/anicca/.anicca-founder/agents/polymarket-agent/.env`, **no argparse, no `if __name__=="__main__"` guard** — it runs at import/top-level. It cannot be shelled out to with different parameters. | Task 9 writes a **new** `engines/python/polymarket/place_order.py` that reuses v2_full_flow.py's exact proven API call sequence (SIWE mint → `SecureClient.create` → approve neg-risk spenders → `create_market_order(..., order_type="FAK")` → `post_order`) verbatim, but parameterized via `argparse` (`--token-id --side --amount --max-price`) and reading the key from env instead of a hardcoded `.env` path. The money-safety logic is unchanged; only the hardcoded constants become parameters. |
| D2 | `engines/polymarket.mjs` derives its production trading loop from the 3 listed files alone | The actual continuously-run Polymarket market-picking logic lives in a **separate GitHub repo**, `BlockRunAI/polymarket-agent`, cloned to `~/.anicca-founder/agents/polymarket-agent` with its own venv + `main.py --live`, invoked by anicca's `pm-trade/run.sh` — **not** part of `~/anicca/skills/earn/polymarket-trade/` at all. | Vineyard does **not** vendor that second external agent repo (the spec explicitly requires Vineyard to not depend on anicca at runtime, and vendoring a whole second proprietary agent contradicts "self-contained"). Order picking for the MVP is: `place_order.py` (D1) is called with parameters the loop/CLI operator supplies (`vineyard trade`), matching hl.py's own philosophy that a real intelligence decides side/size, not hardcoded regex. |
| D3 | `engines/solana.mjs` derives from `sol-trade/run.sh` implementing a Jupiter swap directly | `run.sh` is a thin harness that shells out to the **globally-installed, separate npm package `@blockrun/franklin-trading`** (confirmed real, `npm view @blockrun/franklin-trading version` → `0.2.4`, binary at `/opt/homebrew/bin/franklin-trading`) — a whole autonomous LLM-driven trading agent invoked as `franklin-trading start --trust -m <model> --max-spend <cap> -p "<prompt>"`. It does its own research/sizing/execution and pays its own model calls via x402 from its own wallet. Output is **freeform text**, not JSON. | Task 12 copies `run.sh` verbatim (minus one line, see D5) into `engines/shell/solana/run.sh`; `package.json` declares `@blockrun/franklin-trading` as a dependency so the CLI is on PATH; `engines/solana.mjs` shells to the copied script and returns `{exit, note}` (last 5 lines), matching run.sh's own existing pattern — no fabricated JSON contract is invented for a script that never produced one. |
| D4 | `franklin-trading`'s wallet is whatever the wrapper passes in, so per-instance key isolation (spec §8) holds for the solana engine the same way it does for the other 3 | `franklin-trading start --help` shows **no wallet-path override flag**. Empirically verified (2026-07-05, harmless real invocation — local ed25519 keygen only, no network/funds): `HOME=<tmp> franklin-trading setup solana` creates an **isolated** `<tmp>/.blockrun/.solana-session` + `<tmp>/.blockrun/payment-chain`, distinct from the real `~/.blockrun/`. So isolation *is* achievable, but only via a `$HOME` env override at spawn/run time, not a key the wrapper injects directly. | Task 12's wrapper spawns `franklin-trading` with `HOME` set to the instance's own directory (`core/wallet.mjs`'s `instanceDir(id)`) — reusing the *same* isolation boundary already used for `wallet.json`/`solana.json`, so `.blockrun/` for engine "solana" of instance X lives under `<VINEYARD_HOME>/instances/X/.blockrun/`, never colliding with instance Y's. |
| D5 | `sol-trade/run.sh` has no anicca-specific coupling | Its last line does `node ".../runtime/dashboard/telemetry-post-franklin.mjs"` — a telemetry POST to anicca's own dashboard infra (best-effort, `\|\| true`), which Vineyard must not depend on at runtime per spec §1. | Task 12's copy of `run.sh` has this one line **removed** (documented as the single deliberate line cut, not a silent edit) — every other line (kill-switch, prompt, franklin-trading invocation, trace write) is byte-identical. |
| D6 | `redeem.py` is directly reusable as-is | It hardcodes `DEPOSIT_WALLET = "0x904B50d2..."` (Dais's own founder wallet), an absolute `AGENT_ENV` `.env` path, a relayer-api-key cache at the hardcoded `~/.anicca-founder/.pm-relayer-apikey`, and calls out to an **external ledger writer** `~/anicca/skills/earn/lib/record.mjs` (a file this plan does not read/vendor — out of Vineyard's scope). | Task 10 copies `redeem.py` then applies 4 precise, documented edits: (a) `DEPOSIT_WALLET` reads `os.environ["POLYMARKET_DEPOSIT_WALLET"]`; (b) the `AGENT_ENV`/`load_dotenv(AGENT_ENV)` call is removed (the wrapper already sets `POLYGON_WALLET_PRIVATE_KEY` in the child env); (c) the relayer-key cache path becomes `os.environ.get("POLYMARKET_RELAYER_CACHE", ...)` scoped under the instance dir; (d) `record_ledger_line()`/its call to `record.mjs` is removed — the script still prints one JSON line per redeemed condition (unchanged), and Vineyard's own `core/ledger.mjs` (Node side) is the sole ledger writer, matching the spec's own architecture (`ledger.mjs` = the one place realized P&L is recorded). All on-chain money-safety logic (CTF operator approval, negRisk dispatch, registry checks, `fetch_receipt_status`'s independent RPC confirmation) is untouched. |
| D7 | hl.py's fallback key resolution "just works" once copied | `hl.py`'s `_key()` falls back to `subprocess.run(["node", "<hl.py-dir>/../lib/resolve-identity.mjs", "evm"])` — a **hardcoded relative path** assuming anicca's `skills/earn/hl-trade/../lib/` layout, which won't exist verbatim in Vineyard's repo layout. | Task 11's wrapper always resolves the instance's key itself (via `core/wallet.mjs`) and injects it as `BLOCKRUN_WALLET_KEY` into hl.py's child env — hl.py's env-first branch (`os.environ.get(pkvar) ... or os.environ.get("BLOCKRUN_WALLET_KEY")`) then always short-circuits before ever reaching the fragile relative-path fallback. `hl.py` itself is copied byte-for-byte, unedited. |
| D8 | `fund_via_bridge.py`'s bridge-onramp registration can always self-bootstrap for a brand-new, colony-less instance | The script's own docstring/code: if the new instance's own wallet isn't registered yet, funds must be routed through the bridge **from an already-registered `SOURCE_KEY`** wallet; `SOURCE_KEY` defaults to the new instance's own (unregistered) key, which self-evidently cannot register itself (chicken-and-egg) — the script then prints its own explicit error, it does not hang or silently do the wrong thing. | Task 8's `fund()` wrapper exposes an optional `sourceKey` param (env `SOURCE_KEY`) documented in the README/llms.txt as: **the very first Polymarket registration on a brand-new deployment needs one already-registered wallet's key** (the operator's own, one-time-onboarded-at-polymarket.com wallet, or any prior Vineyard instance's already-registered deposit wallet) passed as `--source-key`. This is the one-time human seed touchpoint the spec's §2 architecture diagram already accounts for ("human → one-time crypto seed"), not a silently-glossed-over gap. |
| D9 | pip/npm package names for the Python SDKs | Verified by `pip show` in the real installed venvs: **`polymarket-client==0.1.0b13`** (NOT `py_clob_client_v2` — that package is real too but is the SDK the SKILL.md itself calls "the DEAD one — do not use") and **`hyperliquid-python-sdk==0.24.0`**, plus `eth-account==0.13.7`, `python-dotenv==1.2.2`, `web3==7.16.0`, `requests==2.34.2` (versions read from the real venvs at `~/.anicca-founder/agents/polymarket-agent/.venv` and `~/.blockrun/skills/earn/hl-trade/.venv`). | Task 8/11's `requirements.txt` pins exactly these verified versions — no invented package names. |

None of these are cosmetic — D1/D2/D3/D4 in particular mean the Polymarket "trade" and Solana "run" engines are **not** simple deterministic swap scripts; they either need a new small parameterized script (D1) or an external autonomous CLI agent with its own wallet-isolation mechanism (D3/D4). Both are handled explicitly below, not silently glossed over.

---

## File structure (target state after Task 18)

```
~/vineyard/
├── README.md
├── llms.txt
├── openapi.json
├── package.json
├── .gitignore
├── .env.example
├── cli/index.mjs
├── api/server.mjs
├── core/
│   ├── wallet.mjs            core/wallet.test.mjs
│   ├── registry.mjs          core/registry.test.mjs
│   ├── ledger.mjs            core/ledger.test.mjs
│   ├── brain.mjs             core/brain.test.mjs
│   └── loop.mjs              core/loop.test.mjs
├── engines/
│   ├── yield.mjs              engines/yield.test.mjs
│   ├── polymarket.mjs         engines/polymarket.test.mjs
│   ├── hyperliquid.mjs        engines/hyperliquid.test.mjs
│   ├── solana.mjs             engines/solana.test.mjs
│   ├── lib/
│   │   ├── cost-basis.mjs        (copied + adapted from anicca skills/earn/lib/cost-basis.mjs)
│   │   └── deposit-guard.mjs     (copied verbatim from anicca skills/earn/lib/deposit-guard.mjs)
│   ├── python/
│   │   ├── requirements.txt
│   │   ├── .venv/                (created at Task 8, gitignored)
│   │   ├── polymarket/
│   │   │   ├── fund_via_bridge.py   (copied verbatim)
│   │   │   ├── place_order.py       (NEW — parameterized, derived from v2_full_flow.py, see D1)
│   │   │   └── redeem.py            (copied + 4 documented edits, see D6)
│   │   └── hyperliquid/
│   │       └── hl.py                (copied verbatim)
│   └── shell/
│       └── solana/
│           └── run.sh               (copied, minus 1 telemetry line, see D5)
└── data/                       (gitignored except .gitkeep)
    ├── spawns.json
    ├── ledgers/<id>.jsonl
    └── instances/<id>/{wallet.json,solana.json,.pm-relayer-apikey,.blockrun/}
```

---

### Task 1: Repo scaffold

**Files:**
- Create: `~/vineyard/package.json`
- Create: `~/vineyard/.gitignore`
- Create: `~/vineyard/.env.example`
- Create: `~/vineyard/data/.gitkeep`

- [ ] **Step 1: Create the directory tree and git init**

```bash
mkdir -p ~/vineyard/{cli,api,core,engines/lib,engines/python/polymarket,engines/python/hyperliquid,engines/shell/solana,data/ledgers,data/instances}
cd ~/vineyard
git init
touch data/.gitkeep
```

- [ ] **Step 2: Write `package.json`**

```json
{
  "name": "vineyard",
  "version": "0.1.0",
  "description": "AI financial-independence CLI — spawn a self-funded AI that earns its own money across 4 on-chain engines (Polymarket, yield, Hyperliquid, Solana), no human/no Claude in the loop after a one-time seed.",
  "type": "module",
  "license": "MIT",
  "bin": {
    "vineyard": "./cli/index.mjs"
  },
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "node --test core/*.test.mjs engines/*.test.mjs",
    "api": "node api/server.mjs"
  },
  "dependencies": {
    "viem": "^2.52.2",
    "express": "^4.18.2"
  },
  "optionalDependencies": {
    "@blockrun/franklin-trading": "^0.2.4"
  }
}
```

- [ ] **Step 3: Write `.gitignore`**

```
node_modules/
engines/python/.venv/
data/instances/
data/ledgers/*.jsonl
data/spawns.json
.env
*.log
```

- [ ] **Step 4: Write `.env.example`**

```bash
# Optional overrides — a fresh spawn generates its own isolated wallet by default (core/wallet.mjs).
# VINEYARD_HOME=/absolute/path/to/vineyard/data   # defaults to ~/.vineyard
# VINEYARD_EVM_PRIVATE_KEY=0x...                  # override instead of the generated per-instance wallet
# VINEYARD_SOLANA_PRIVATE_KEY=...                 # override (base58)
# SOURCE_KEY=0x...                                # a PRE-REGISTERED Polymarket wallet's key — needed for
#                                                  # the very first bridge registration on a brand-new
#                                                  # deployment (see plan discrepancy D8)
# BASE_RPC_URL=https://mainnet.base.org           # optional custom Base RPC for the yield engine
# POLYGON_RPC=https://polygon-bor-rpc.publicnode.com
```

- [ ] **Step 5: First commit**

```bash
cd ~/vineyard
git add -A
git commit -m "chore: scaffold vineyard repo (package.json, dirs, gitignore, env example)"
```

Run: `git -C ~/vineyard log --oneline`
Expected: one commit, `chore: scaffold vineyard repo...`

---

### Task 2: `core/wallet.mjs` — per-instance wallet generation

**Files:**
- Create: `~/vineyard/core/wallet.mjs`
- Test: `~/vineyard/core/wallet.test.mjs`

This is the Vineyard-native replacement for anicca's `~/anicca/skills/earn/lib/resolve-identity.mjs`. Function names/priority-order pattern are kept close to the original (env override → per-instance file → null, fail-closed, never throws), but the anicca-specific "legacy `$HOME/.automaton`" back-compat branch is intentionally **not** ported — a brand-new repo has no prior shared-wallet convention to honor, and every instance's home is always the explicit `<VINEYARD_HOME>/instances/<id>/` directory (never an ambiguous default). EVM keygen uses `viem`'s `generatePrivateKey`/`privateKeyToAccount` (same as anicca's `runtime/compute-proxy/start-local.sh`); Solana keygen uses Node's built-in `crypto.generateKeyPairSync('ed25519')` + manual base58 (the exact algorithm read from anicca's `runtime/compute-proxy/ensure-solana-wallet.mjs`, verbatim, no `@solana/web3.js` dependency needed for pure keygen).

- [ ] **Step 1: Write the failing test for `generateWallet`**

```javascript
// ~/vineyard/core/wallet.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { generateWallet, instanceDir, vineyardHome } from './wallet.mjs';

function tmpHome(prefix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  return dir;
}

test('vineyardHome: defaults to $HOME/.vineyard when VINEYARD_HOME unset', () => {
  const h = vineyardHome({ HOME: '/fake/home' });
  assert.equal(h, '/fake/home/.vineyard');
});

test('vineyardHome: VINEYARD_HOME override wins', () => {
  const h = vineyardHome({ HOME: '/fake/home', VINEYARD_HOME: '/custom/dir' });
  assert.equal(h, '/custom/dir');
});

test('generateWallet: creates wallet.json + solana.json under instances/<id>/', () => {
  const home = tmpHome('vy-wallet');
  const env = { VINEYARD_HOME: home };
  const result = generateWallet('alpha', env);
  assert.match(result.evm.address, /^0x[0-9a-fA-F]{40}$/);
  assert.ok(result.solana.address.length > 0);
  const dir = instanceDir('alpha', env);
  assert.ok(fs.existsSync(path.join(dir, 'wallet.json')));
  assert.ok(fs.existsSync(path.join(dir, 'solana.json')));
});

test('generateWallet: idempotent — re-spawning the same id preserves its original identity', () => {
  const home = tmpHome('vy-wallet-idem');
  const env = { VINEYARD_HOME: home };
  const first = generateWallet('beta', env);
  const second = generateWallet('beta', env);
  assert.equal(first.evm.address, second.evm.address);
  assert.equal(first.solana.address, second.solana.address);
});

test('generateWallet: two different ids get two different wallets', () => {
  const home = tmpHome('vy-wallet-diff');
  const env = { VINEYARD_HOME: home };
  const a = generateWallet('id-a', env);
  const b = generateWallet('id-b', env);
  assert.notEqual(a.evm.address, b.evm.address);
  assert.notEqual(a.solana.address, b.solana.address);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/vineyard && node --test core/wallet.test.mjs`
Expected: FAIL — `Cannot find module './wallet.mjs'`

- [ ] **Step 3: Write `core/wallet.mjs` (generation + resolution half)**

```javascript
// ~/vineyard/core/wallet.mjs — per-instance key isolation. Ported from anicca's
// ~/anicca/skills/earn/lib/resolve-identity.mjs (function names/priority-order pattern kept close),
// with the anicca-specific legacy-shared-wallet back-compat branch intentionally dropped — see this
// plan's header note on why a fresh repo has no such convention to honor. Fail-closed everywhere:
// any missing/malformed file returns null, this module never throws.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';

export function vineyardHome(env = process.env) {
  return env.VINEYARD_HOME || path.join(env.HOME || process.cwd(), '.vineyard');
}

export function instanceDir(id, env = process.env) {
  return path.join(vineyardHome(env), 'instances', id);
}

function readJsonField(filePath, field) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const value = parsed && parsed[field];
    return typeof value === 'string' && value.length > 0 ? value : null;
  } catch {
    return null;
  }
}

function normalizeEvmKey(key) {
  if (typeof key !== 'string' || key.length === 0) return null;
  return key.startsWith('0x') ? key : `0x${key}`;
}

const B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
function base58(buf) {
  const digits = [0];
  for (const byte of buf) {
    let carry = byte;
    for (let j = 0; j < digits.length; j++) {
      carry += digits[j] << 8;
      digits[j] = carry % 58;
      carry = (carry / 58) | 0;
    }
    while (carry) {
      digits.push(carry % 58);
      carry = (carry / 58) | 0;
    }
  }
  let out = '';
  for (const byte of buf) {
    if (byte === 0) out += '1';
    else break;
  }
  return out + digits.reverse().map((d) => B58_ALPHABET[d]).join('');
}

/**
 * Generate (or return the existing) EVM + Solana keypair for instance `id`, persisted under
 * <VINEYARD_HOME>/instances/<id>/{wallet.json,solana.json}, chmod 600. Idempotent.
 * @returns {{id: string, evm: {address: string}, solana: {address: string}}}
 */
export function generateWallet(id, env = process.env) {
  const dir = instanceDir(id, env);
  fs.mkdirSync(dir, { recursive: true });

  const walletPath = path.join(dir, 'wallet.json');
  let evm;
  if (fs.existsSync(walletPath)) {
    evm = JSON.parse(fs.readFileSync(walletPath, 'utf8'));
  } else {
    const pk = generatePrivateKey();
    evm = { privateKey: pk, address: privateKeyToAccount(pk).address };
    fs.writeFileSync(walletPath, JSON.stringify(evm, null, 2));
    fs.chmodSync(walletPath, 0o600);
  }

  const solPath = path.join(dir, 'solana.json');
  let solana;
  if (fs.existsSync(solPath)) {
    solana = JSON.parse(fs.readFileSync(solPath, 'utf8'));
  } else {
    const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
    const pub = publicKey.export({ type: 'spki', format: 'der' }).subarray(-32);
    const seed = privateKey.export({ type: 'pkcs8', format: 'der' }).subarray(-32);
    const secret = Buffer.concat([seed, pub]);
    solana = { address: base58(pub), secretKey: base58(secret), secretKeyBytes: [...secret] };
    fs.writeFileSync(solPath, JSON.stringify(solana, null, 2));
    fs.chmodSync(solPath, 0o600);
  }

  return { id, evm: { address: evm.address }, solana: { address: solana.address } };
}

/**
 * Resolve instance `id`'s OWN EVM private key. Fail-closed: null if `id` has no wallet.json yet
 * or the file is malformed. NEVER reads another instance's directory — this IS the key-isolation
 * boundary (there is no shared/legacy fallback path for it to leak through).
 */
export function resolveEvmPrivateKey(id, env = process.env) {
  const override = normalizeEvmKey(env.VINEYARD_EVM_PRIVATE_KEY);
  if (override) return override;
  const fromFile = readJsonField(path.join(instanceDir(id, env), 'wallet.json'), 'privateKey');
  return fromFile ? normalizeEvmKey(fromFile) : null;
}

export function resolveSolanaSecret(id, env = process.env) {
  if (typeof env.VINEYARD_SOLANA_PRIVATE_KEY === 'string' && env.VINEYARD_SOLANA_PRIVATE_KEY.length > 0) {
    return env.VINEYARD_SOLANA_PRIVATE_KEY;
  }
  return readJsonField(path.join(instanceDir(id, env), 'solana.json'), 'secretKey');
}

/** Addresses only — safe to log/return over HTTP. Never returns key material. */
export function resolveAddresses(id, env = process.env) {
  const dir = instanceDir(id, env);
  return {
    evm: readJsonField(path.join(dir, 'wallet.json'), 'address'),
    solana: readJsonField(path.join(dir, 'solana.json'), 'address'),
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/vineyard && node --test core/wallet.test.mjs`
Expected: PASS — 5 tests, 0 failures

- [ ] **Step 5: Commit**

```bash
cd ~/vineyard
git add core/wallet.mjs core/wallet.test.mjs
git commit -m "feat(core): wallet.mjs per-instance EVM+Solana keypair generation"
```

---

### Task 3: `core/wallet.mjs` — fail-closed key isolation test (adversary-grade)

**Files:**
- Modify: `~/vineyard/core/wallet.test.mjs`

This is the explicit, adversarial "instance B cannot resolve/sign with instance A's key" test the spec's money-safety invariant (§8, per-instance key isolation) requires. Everything under test already exists from Task 2 — this task only adds the isolation-specific assertions.

- [ ] **Step 1: Write the failing (well — currently untested) isolation assertions**

```javascript
// append to ~/vineyard/core/wallet.test.mjs
import { resolveEvmPrivateKey, resolveSolanaSecret } from './wallet.mjs';

test('FAIL-CLOSED: instance B has no wallet yet -> resolveEvmPrivateKey(B) is null, never throws, never falls back to A', () => {
  const home = tmpHome('vy-isolate-evm');
  const env = { VINEYARD_HOME: home };
  const a = generateWallet('instance-a', env); // only A is spawned
  assert.notEqual(a.evm.address, null);
  assert.doesNotThrow(() => {
    const keyForB = resolveEvmPrivateKey('instance-b', env);
    assert.equal(keyForB, null, 'instance B must never resolve a key it has not been given');
  });
});

test('FAIL-CLOSED: instance B has no wallet yet -> resolveSolanaSecret(B) is null, never throws, never falls back to A', () => {
  const home = tmpHome('vy-isolate-sol');
  const env = { VINEYARD_HOME: home };
  generateWallet('instance-a', env);
  assert.doesNotThrow(() => {
    assert.equal(resolveSolanaSecret('instance-b', env), null);
  });
});

test('ISOLATION: A and B both spawned -> resolveEvmPrivateKey(A) never equals resolveEvmPrivateKey(B), and each resolves ONLY its own key', () => {
  const home = tmpHome('vy-isolate-both');
  const env = { VINEYARD_HOME: home };
  const a = generateWallet('instance-a', env);
  const b = generateWallet('instance-b', env);
  const keyA = resolveEvmPrivateKey('instance-a', env);
  const keyB = resolveEvmPrivateKey('instance-b', env);
  assert.notEqual(keyA, keyB);
  assert.equal(privateKeyToAccountAddress(keyA), a.evm.address);
  assert.equal(privateKeyToAccountAddress(keyB), b.evm.address);
});

test('ISOLATION: env override for the CURRENT process never leaks into a DIFFERENT instance id\'s resolution', () => {
  // env.VINEYARD_EVM_PRIVATE_KEY is a global override by design (single-instance CLI invocation
  // convention) — this test documents that a per-instance FILE lookup (the id-scoped path) is the
  // isolation boundary that matters for the multi-instance loop/API server, and confirms it still
  // resolves the id-scoped file correctly when no override is set.
  const home = tmpHome('vy-isolate-noleak');
  const env = { VINEYARD_HOME: home };
  const a = generateWallet('instance-a', env);
  const keyA = resolveEvmPrivateKey('instance-a', env);
  assert.equal(privateKeyToAccountAddress(keyA), a.evm.address);
  assert.equal(resolveEvmPrivateKey('instance-c', env), null);
});

function privateKeyToAccountAddress(pk) {
  // local re-derivation via viem, independent of wallet.mjs's own generation path, so this test does
  // not just trust wallet.mjs's own bookkeeping.
  return privateKeyToAccountFromViem(pk);
}
```

- [ ] **Step 2: Add the missing viem import used by the new helper**

```javascript
// add near the top of ~/vineyard/core/wallet.test.mjs, alongside the existing imports
import { privateKeyToAccount as privateKeyToAccountFromViem_ } from 'viem/accounts';
function privateKeyToAccountFromViem(pk) { return privateKeyToAccountFromViem_(pk).address; }
```

- [ ] **Step 3: Run the full wallet test suite**

Run: `cd ~/vineyard && node --test core/wallet.test.mjs`
Expected: PASS — 9 tests, 0 failures (5 from Task 2 + 4 isolation tests)

- [ ] **Step 4: Commit**

```bash
cd ~/vineyard
git add core/wallet.test.mjs
git commit -m "test(core): fail-closed per-instance key isolation assertions (spec §8)"
```

---

### Task 4: `core/registry.mjs` — spawns.json registry

**Files:**
- Create: `~/vineyard/core/registry.mjs`
- Test: `~/vineyard/core/registry.test.mjs`

`spawns.json` never stores private keys (those live only under `core/wallet.mjs`'s per-instance directory) — it is the public-safe metadata list `vineyard list` / `GET /list` reads, matching the franklin-earn-product-spec.md registry shape `{id, evm, solana, fund, engine, created}`.

- [ ] **Step 1: Write the failing test**

```javascript
// ~/vineyard/core/registry.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { registerSpawn, readRegistry, findSpawn } from './registry.mjs';

function tmpEnv(prefix) {
  return { VINEYARD_HOME: fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`)) };
}

test('readRegistry: empty when no spawns.json exists yet', () => {
  const env = tmpEnv('vy-reg-empty');
  assert.deepEqual(readRegistry(env), []);
});

test('registerSpawn: adds a row and readRegistry sees it', () => {
  const env = tmpEnv('vy-reg-add');
  const row = registerSpawn({ id: 'x1', evm: '0xabc', solana: 'Sol111', fund: 0, engine: null }, env);
  assert.equal(row.id, 'x1');
  assert.ok(row.created);
  const rows = readRegistry(env);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].id, 'x1');
});

test('registerSpawn: rejects a duplicate id', () => {
  const env = tmpEnv('vy-reg-dup');
  registerSpawn({ id: 'dup', evm: '0x1', solana: 'S1' }, env);
  assert.throws(() => registerSpawn({ id: 'dup', evm: '0x2', solana: 'S2' }, env), /already registered/);
});

test('findSpawn: returns null for an unknown id', () => {
  const env = tmpEnv('vy-reg-find-none');
  assert.equal(findSpawn('nope', env), null);
});

test('findSpawn: returns the matching row', () => {
  const env = tmpEnv('vy-reg-find');
  registerSpawn({ id: 'y1', evm: '0xdef', solana: 'Sol222' }, env);
  const found = findSpawn('y1', env);
  assert.equal(found.evm, '0xdef');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/vineyard && node --test core/registry.test.mjs`
Expected: FAIL — `Cannot find module './registry.mjs'`

- [ ] **Step 3: Write `core/registry.mjs`**

```javascript
// ~/vineyard/core/registry.mjs — spawns.json CRUD. Public-safe metadata only, never key material.
import fs from 'node:fs';
import path from 'node:path';
import { vineyardHome } from './wallet.mjs';

function registryPath(env = process.env) {
  return path.join(vineyardHome(env), 'spawns.json');
}

export function readRegistry(env = process.env) {
  try {
    return JSON.parse(fs.readFileSync(registryPath(env), 'utf8'));
  } catch {
    return [];
  }
}

function writeRegistry(rows, env = process.env) {
  const p = registryPath(env);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(rows, null, 2));
}

export function registerSpawn({ id, evm, solana, fund = 0, engine = null }, env = process.env) {
  const rows = readRegistry(env);
  if (rows.some((r) => r.id === id)) {
    throw new Error(`instance id already registered: ${id}`);
  }
  const row = { id, evm, solana, fund, engine, created: new Date().toISOString() };
  writeRegistry([...rows, row], env);
  return row;
}

export function findSpawn(id, env = process.env) {
  return readRegistry(env).find((r) => r.id === id) || null;
}

export function updateSpawn(id, patch, env = process.env) {
  const rows = readRegistry(env);
  const idx = rows.findIndex((r) => r.id === id);
  if (idx === -1) throw new Error(`instance id not found: ${id}`);
  rows[idx] = { ...rows[idx], ...patch };
  writeRegistry(rows, env);
  return rows[idx];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/vineyard && node --test core/registry.test.mjs`
Expected: PASS — 5 tests, 0 failures

- [ ] **Step 5: Commit**

```bash
cd ~/vineyard
git add core/registry.mjs core/registry.test.mjs
git commit -m "feat(core): registry.mjs spawns.json CRUD"
```

---

### Task 5: `core/ledger.mjs` — on-chain-verified realized P&L

**Files:**
- Create: `~/vineyard/core/ledger.mjs`
- Test: `~/vineyard/core/ledger.test.mjs`

Per spec §8: "on-chain-verified earnings only in ledger/dashboard, never paper/simulated." One JSONL file per instance at `data/ledgers/<id>.jsonl`.

- [ ] **Step 1: Write the failing test**

```javascript
// ~/vineyard/core/ledger.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { appendLedger, readLedger, realizedPnl } from './ledger.mjs';

function tmpDataDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
}

test('readLedger: empty array when no file exists yet', () => {
  const dataDir = tmpDataDir('vy-ledger-empty');
  assert.deepEqual(readLedger('z1', dataDir), []);
});

test('appendLedger: writes one JSONL line with a ts + id + the event fields', () => {
  const dataDir = tmpDataDir('vy-ledger-append');
  const line = appendLedger('z1', { engine: 'yield', status: 'ok', tx: '0xaaa', net_usdc: 0.03 }, dataDir);
  assert.ok(line.ts);
  assert.equal(line.id, 'z1');
  assert.equal(line.tx, '0xaaa');
  const rows = readLedger('z1', dataDir);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].net_usdc, 0.03);
});

test('realizedPnl: sums net_usdc across lines', () => {
  const dataDir = tmpDataDir('vy-ledger-sum');
  appendLedger('z2', { engine: 'yield', net_usdc: 0.03 }, dataDir);
  appendLedger('z2', { engine: 'polymarket', net_usdc: 1.2 }, dataDir);
  assert.equal(realizedPnl('z2', dataDir), 1.23);
});

test('realizedPnl: falls back to earn_usdc - cost_usdc when net_usdc is absent (redeem.py line shape)', () => {
  const dataDir = tmpDataDir('vy-ledger-fallback');
  appendLedger('z3', { engine: 'polymarket', earn_usdc: 5, cost_usdc: 2 }, dataDir);
  assert.equal(realizedPnl('z3', dataDir), 3);
});

test('realizedPnl: a skip/wait line with no earn/cost/net fields contributes 0, never NaN', () => {
  const dataDir = tmpDataDir('vy-ledger-wait');
  appendLedger('z4', { engine: 'hyperliquid', status: 'wait' }, dataDir);
  assert.equal(realizedPnl('z4', dataDir), 0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/vineyard && node --test core/ledger.test.mjs`
Expected: FAIL — `Cannot find module './ledger.mjs'`

- [ ] **Step 3: Write `core/ledger.mjs`**

```javascript
// ~/vineyard/core/ledger.mjs — on-chain-verified realized P&L ONLY, never paper (spec §8).
import fs from 'node:fs';
import path from 'node:path';

function ledgerPath(id, dataDir) {
  return path.join(dataDir, 'ledgers', `${id}.jsonl`);
}

/**
 * Append one realized event. `event` should carry a real on-chain `tx` for a fill, or
 * `status: "wait"`/`"skip"` for a reasoned no-trade pass (HARD RULE 0.24: no dry run, but a
 * genuine WAIT/skip is a valid real outcome, never fabricated).
 */
export function appendLedger(id, event, dataDir) {
  const p = ledgerPath(id, dataDir);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const line = { ts: new Date().toISOString(), id, ...event };
  fs.appendFileSync(p, JSON.stringify(line) + '\n');
  return line;
}

export function readLedger(id, dataDir) {
  const p = ledgerPath(id, dataDir);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}

/** Realized P&L = sum of every line's net_usdc (or earn_usdc - cost_usdc, or 0). Never NaN. */
export function realizedPnl(id, dataDir) {
  return readLedger(id, dataDir).reduce((sum, line) => {
    const net = typeof line.net_usdc === 'number'
      ? line.net_usdc
      : (Number(line.earn_usdc || 0) - Number(line.cost_usdc || 0));
    return sum + (Number.isFinite(net) ? net : 0);
  }, 0);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/vineyard && node --test core/ledger.test.mjs`
Expected: PASS — 5 tests, 0 failures

- [ ] **Step 5: Commit**

```bash
cd ~/vineyard
git add core/ledger.mjs core/ledger.test.mjs
git commit -m "feat(core): ledger.mjs realized P&L jsonl (append/read/sum)"
```

---

### Task 6: `cli/index.mjs` + `api/server.mjs` — `spawn` command

**Files:**
- Create: `~/vineyard/cli/index.mjs`
- Create: `~/vineyard/api/server.mjs`

This wires Tasks 2-4 together behind the CLI/HTTP surface (spec §4). Only the `spawn` verb is implemented here; Task 15 extends the same two files with `fund/run/status/list/trade/redeem`.

- [ ] **Step 1: Write `cli/index.mjs` with the `spawn` command + dispatcher skeleton**

```javascript
#!/usr/bin/env node
// ~/vineyard/cli/index.mjs — `vineyard <cmd>` dispatcher (spec §4).
import crypto from 'node:crypto';
import { generateWallet } from '../core/wallet.mjs';
import { registerSpawn, readRegistry } from '../core/registry.mjs';

const [, , cmd, ...rest] = process.argv;

function newId() {
  return crypto.randomBytes(4).toString('hex');
}

function parseFlags(args) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = args[i + 1];
      if (next !== undefined && !next.startsWith('--')) {
        flags[key] = next;
        i++;
      } else {
        flags[key] = true;
      }
    } else {
      positional.push(a);
    }
  }
  return { flags, positional };
}

async function cmdSpawn(args) {
  const { flags } = parseFlags(args);
  const id = flags.id || newId();
  const wallet = generateWallet(id);
  const row = registerSpawn({
    id,
    evm: wallet.evm.address,
    solana: wallet.solana.address,
    fund: Number(flags.fund || 0),
    engine: flags.engine || null,
  });
  console.log(JSON.stringify(row, null, 2));
  return row;
}

async function cmdList() {
  console.log(JSON.stringify(readRegistry(), null, 2));
}

async function main() {
  switch (cmd) {
    case 'spawn':
      await cmdSpawn(rest);
      break;
    case 'list':
      await cmdList();
      break;
    default:
      console.error('usage: vineyard <spawn|fund|run|status|list|trade|redeem|dashboard> [...args]');
      process.exitCode = 2;
  }
}

main().catch((e) => {
  console.error(String(e?.message || e));
  process.exitCode = 1;
});
```

- [ ] **Step 2: Make the CLI executable and run a real spawn against a scratch VINEYARD_HOME**

```bash
cd ~/vineyard
chmod +x cli/index.mjs
VINEYARD_HOME=/tmp/vy-smoke-spawn node cli/index.mjs spawn --fund 10
```

Expected output: a JSON object with `id`, `evm` (a `0x...` address), `solana` (a base58 address), `fund: 10`, `created` (ISO timestamp). Exit code 0.

- [ ] **Step 3: Confirm `list` shows it**

```bash
VINEYARD_HOME=/tmp/vy-smoke-spawn node cli/index.mjs list
rm -rf /tmp/vy-smoke-spawn
```

Expected: a JSON array with exactly the one row spawned in Step 2.

- [ ] **Step 4: Write `api/server.mjs` with `POST /spawn` + `GET /list`**

```javascript
// ~/vineyard/api/server.mjs — Express REST, same verbs as the CLI (spec §4).
import express from 'express';
import crypto from 'node:crypto';
import { generateWallet } from '../core/wallet.mjs';
import { registerSpawn, readRegistry, findSpawn } from '../core/registry.mjs';

const app = express();
app.use(express.json());

app.post('/spawn', (req, res) => {
  const id = req.body?.id || crypto.randomBytes(4).toString('hex');
  const wallet = generateWallet(id);
  const row = registerSpawn({
    id,
    evm: wallet.evm.address,
    solana: wallet.solana.address,
    fund: Number(req.body?.fund || 0),
    engine: req.body?.engine || null,
  });
  res.status(201).json(row);
});

app.get('/list', (_req, res) => {
  res.json(readRegistry());
});

app.get('/status/:id', (req, res) => {
  const row = findSpawn(req.params.id);
  if (!row) return res.status(404).json({ error: 'unknown id' });
  res.json(row);
});

const PORT = process.env.PORT || 3000;
if (process.argv[1] && process.argv[1].endsWith('server.mjs')) {
  app.listen(PORT, () => console.log(`vineyard API listening on :${PORT}`));
}

export default app;
```

- [ ] **Step 5: Smoke-test the API with a real HTTP call**

```bash
cd ~/vineyard
npm install
VINEYARD_HOME=/tmp/vy-smoke-api PORT=3999 node api/server.mjs &
API_PID=$!
sleep 1
curl -s -X POST http://localhost:3999/spawn -H 'Content-Type: application/json' -d '{"fund":5}'
curl -s http://localhost:3999/list
kill $API_PID
rm -rf /tmp/vy-smoke-api
```

Expected: `POST /spawn` returns `201` with a JSON row; `GET /list` returns a JSON array containing that row.

- [ ] **Step 6: Commit**

```bash
cd ~/vineyard
git add cli/index.mjs api/server.mjs package-lock.json
git commit -m "feat(cli,api): spawn + list commands wired to core/wallet+registry"
```

---

### Task 7: Engine — yield (already Node, copy in with minimal adaptation)

**Files:**
- Create: `~/vineyard/engines/lib/deposit-guard.mjs` (copied verbatim)
- Create: `~/vineyard/engines/lib/cost-basis.mjs` (copied + adapted, see below)
- Create: `~/vineyard/engines/yield.mjs` (copied + adapted, see below)
- Test: `~/vineyard/engines/yield.test.mjs`

`execute-yield.mjs` is already Node — per the brief, copy it in as-is with minimal adaptation (no shell-out). Two adaptations are needed, both mechanical, none touching the DeFi decision logic (RPC list, Aave/Beefy/Fluid addresses/ABIs, deploy/refill/hold branches, the read-after-write `depositLanded` proof — all byte-identical):
1. `loadKey()` takes the resolved key as a parameter instead of calling anicca's `loadEvmKey()` internally (Vineyard's caller, `core/loop.mjs`, already resolved it via `core/wallet.mjs`).
2. `cost-basis.mjs`'s hardcoded `FILE` (anicca's shared `$HOME/.anicca/skills/earn/state/cost-basis.json`, a single file for ALL slots under one HOME) is rescoped **per spawned instance id** — Vineyard supports N simultaneous instances under one `VINEYARD_HOME`, unlike anicca's one-shared-HOME-per-agent model, so this file must accept a `filePath` instead of hardcoding one path.

- [ ] **Step 1: Copy `deposit-guard.mjs` verbatim (zero changes — pure bigint math, no file I/O)**

```bash
cp ~/anicca/skills/earn/lib/deposit-guard.mjs ~/vineyard/engines/lib/deposit-guard.mjs
```

- [ ] **Step 2: Write the failing test for the adapted `cost-basis.mjs`**

```javascript
// ~/vineyard/engines/cost-basis.test.mjs  (co-located test for engines/lib/cost-basis.mjs)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { readCostBasis, recordDeposit, recordWithdraw, seedIfEmpty } from './lib/cost-basis.mjs';

function tmpFile(prefix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  return path.join(dir, 'cost-basis.json');
}

test('readCostBasis: empty object when file does not exist', () => {
  assert.deepEqual(readCostBasis(tmpFile('vy-cb-empty')), {});
});

test('recordDeposit: increments the venue basis and persists it', () => {
  const file = tmpFile('vy-cb-deposit');
  recordDeposit('fluid', 3.5, file);
  assert.equal(readCostBasis(file).fluid, 3.5);
});

test('recordWithdraw: decrements but floors at 0 (never negative)', () => {
  const file = tmpFile('vy-cb-withdraw');
  recordDeposit('beefy', 2, file);
  recordWithdraw('beefy', 10, file);
  assert.equal(readCostBasis(file).beefy, 0);
});

test('seedIfEmpty: only sets venues not already tracked', () => {
  const file = tmpFile('vy-cb-seed');
  recordDeposit('aave', 1, file);
  seedIfEmpty({ aave: 999, fluid: 5 }, file);
  const basis = readCostBasis(file);
  assert.equal(basis.aave, 1); // untouched — already tracked
  assert.equal(basis.fluid, 5); // seeded — was empty
});

test('two different files (two instances) never mix state', () => {
  const fileA = tmpFile('vy-cb-a');
  const fileB = tmpFile('vy-cb-b');
  recordDeposit('fluid', 7, fileA);
  assert.equal(readCostBasis(fileB).fluid, undefined);
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/cost-basis.test.mjs`
Expected: FAIL — `Cannot find module './lib/cost-basis.mjs'`

- [ ] **Step 4: Write the adapted `engines/lib/cost-basis.mjs`**

```javascript
// ~/vineyard/engines/lib/cost-basis.mjs — copied from anicca ~/anicca/skills/earn/lib/cost-basis.mjs,
// adapted ONLY so every function takes an explicit `filePath` instead of one hardcoded shared-HOME
// path (Vineyard runs N instances under one VINEYARD_HOME; anicca assumed one shared HOME per agent).
// The venue-basis bookkeeping logic itself (deposit/withdraw/floor-at-0/seed-if-empty) is unchanged.
import fs from 'node:fs';
import path from 'node:path';

export function readCostBasis(filePath) {
  try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); } catch { return {}; }
}

function write(o, filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(o, null, 2));
}

export function recordDeposit(venue, usd, filePath) { return adjust(venue, +Number(usd), filePath); }
export function recordWithdraw(venue, usd, filePath) { return adjust(venue, -Number(usd), filePath); }

function adjust(venue, delta, filePath) {
  if (!venue || !Number.isFinite(delta)) return null;
  const o = readCostBasis(filePath);
  o[venue] = Math.max(0, +(((o[venue] || 0) + delta)).toFixed(6));
  write(o, filePath);
  return o[venue];
}

export function seedIfEmpty(seed, filePath) {
  const o = readCostBasis(filePath);
  let changed = false;
  for (const [v, usd] of Object.entries(seed)) {
    if (o[v] == null && Number.isFinite(Number(usd))) { o[v] = +Number(usd).toFixed(6); changed = true; }
  }
  if (changed) write(o, filePath);
  return o;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/cost-basis.test.mjs`
Expected: PASS — 5 tests, 0 failures

- [ ] **Step 6: Write the failing test for `engines/yield.mjs`'s exported `run()` shape**

Since `run()` makes real RPC/chain calls, this unit test only verifies the exported function exists with the right signature and that a wallet with **no key** fails closed — a full real deploy/refill/hold pass against a funded wallet is the separate manual on-chain smoke test (HARD RULE 0.24, no dry run in production; this is the automated-test boundary).

```javascript
// ~/vineyard/engines/yield.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { run } from './yield.mjs';

test('run: fail-closed when evmPrivateKey is null/absent — returns {abort:"no wallet key"}, never throws', async () => {
  const result = await run({ evmPrivateKey: null });
  assert.equal(result.abort, 'no wallet key');
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/yield.test.mjs`
Expected: FAIL — `Cannot find module './yield.mjs'`

- [ ] **Step 8: Copy `execute-yield.mjs` and apply the minimal adaptation**

```bash
cp ~/anicca/skills/earn/execute-yield.mjs ~/vineyard/engines/yield.mjs
```

Then edit `~/vineyard/engines/yield.mjs`:

- Replace the import line:
```javascript
import { loadEvmKey } from "./lib/resolve-identity.mjs";
```
with (this import is no longer needed — the key now arrives as a parameter):
```javascript
// key now arrives as a parameter from core/wallet.mjs via core/loop.mjs — no in-file resolution.
```

- Replace:
```javascript
function loadKey() { return loadEvmKey(); }
```
with:
```javascript
function loadKey(evmPrivateKey) { return evmPrivateKey || null; }
```

- Replace the cost-basis import:
```javascript
import { recordDeposit, recordWithdraw } from "./lib/cost-basis.mjs";
```
(unchanged path — cost-basis.mjs now lives at `engines/lib/cost-basis.mjs`, same relative location, no edit needed since `yield.mjs` also lives directly under `engines/`)

- Replace the `main()` signature and its one `loadKey()` call site:
```javascript
async function main() {
  const pk = loadKey();
```
with:
```javascript
export async function run({ evmPrivateKey, costBasisFile, env = process.env } = {}) {
  const pk = loadKey(evmPrivateKey);
```

- At every `recordDeposit(VENUE_KEY[depositKind], ...)` / `recordWithdraw("beefy", ...)` call site, add the `costBasisFile` argument (2 call sites — the deploy branch and the refill branch):
```javascript
if (landed) recordDeposit(VENUE_KEY[depositKind], Number(liquid - liqAfter) / 1e6, costBasisFile);
```
```javascript
if (r.status === "success") recordWithdraw("beefy", Number(liq2 - liquid) / 1e6, costBasisFile);
```

- Replace the trailing `return out({...})` statements' function name (they were already inside `main()`, now inside `run()` — no change needed, they already `return out({...})`), and replace the bottom direct-run guard:
```javascript
main().catch((e) => out({ error: String(e?.message || e) }));
```
with:
```javascript
import { fileURLToPath } from 'node:url';
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const path2 = await import('node:path');
  run({ evmPrivateKey: process.env.VINEYARD_EVM_PRIVATE_KEY, costBasisFile: process.env.VINEYARD_COST_BASIS_FILE })
    .then(out)
    .catch((e) => out({ error: String(e?.message || e) }));
}
```
(add `import path from 'node:path';` near the top alongside the existing `import fs from "fs";` if not already present — `path` is used by the direct-run guard above)

- [ ] **Step 9: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/yield.test.mjs`
Expected: PASS — 1 test, 0 failures

- [ ] **Step 10: Manual (non-automated) verification note — HARD RULE 0.24**

A REAL deploy/refill/hold pass requires a Base-funded EVM wallet holding idle USDC. This is a separate manual verification step to run once a spawned instance is actually funded: `VINEYARD_EVM_PRIVATE_KEY=<funded key> node -e "import('./engines/yield.mjs').then(m => m.run({evmPrivateKey: process.env.VINEYARD_EVM_PRIVATE_KEY, costBasisFile: '/tmp/vy-cb-manual.json'}).then(r => console.log(r)))"` — expect a real `{kind:"yield", action:"deploy"|"refill"|"hold", ...}` object with either a real `tx` hash or an honest `hold`. Do NOT claim this step passed without running it against a real funded wallet.

- [ ] **Step 11: Commit**

```bash
cd ~/vineyard
git add engines/lib/deposit-guard.mjs engines/lib/cost-basis.mjs engines/cost-basis.test.mjs engines/yield.mjs engines/yield.test.mjs
git commit -m "feat(engines): yield engine copied from anicca execute-yield.mjs, param-scoped per instance"
```

---

### Task 8: Engine — Polymarket FUND (bridge onramp registration)

**Files:**
- Create: `~/vineyard/engines/python/requirements.txt`
- Create: `~/vineyard/engines/python/polymarket/fund_via_bridge.py` (copied verbatim — see D9 for why no edits are needed)
- Create: `~/vineyard/engines/polymarket.mjs` (fund half)
- Test: `~/vineyard/engines/polymarket.test.mjs` (fund half)

`fund_via_bridge.py` reads everything from env vars already (`POLYGON_WALLET_PRIVATE_KEY`, optional `SOURCE_KEY`, `FUND_USD`) and has a proper `if __name__ == "__main__"` guard — it is copied **byte-for-byte, zero edits**, unlike `v2_full_flow.py`/`redeem.py` (D1/D6).

- [ ] **Step 1: Write `engines/python/requirements.txt` with the verified pinned versions (D9)**

```
requests==2.34.2
eth-account==0.13.7
python-dotenv==1.2.2
web3==7.16.0
polymarket-client==0.1.0b13
hyperliquid-python-sdk==0.24.0
```

- [ ] **Step 2: Create the venv and install**

```bash
cd ~/vineyard
python3 -m venv engines/python/.venv
engines/python/.venv/bin/pip install --upgrade pip
engines/python/.venv/bin/pip install -r engines/python/requirements.txt
```

Run: `engines/python/.venv/bin/pip show polymarket-client hyperliquid-python-sdk | grep -E "^Name|^Version"`
Expected:
```
Name: polymarket-client
Version: 0.1.0b13
Name: hyperliquid-python-sdk
Version: 0.24.0
```

- [ ] **Step 3: Copy `fund_via_bridge.py` verbatim**

```bash
cp ~/anicca/skills/earn/polymarket-trade/fund_via_bridge.py ~/vineyard/engines/python/polymarket/fund_via_bridge.py
```

- [ ] **Step 4: Write the failing test for the wrapper's stdout parser**

The parser is tested against a captured real-format fixture (the exact JSON shape `fund_via_bridge.py`'s `main()` prints — verified from its source: `print(json.dumps({"deposit_wallet": deposit, "registered": True, "already": True}))` for the already-registered branch, or the fuller shape with `bridge_address`/`balance_usdc` for the fresh-registration branch). This is NOT a live network call — no `--dry-run` flag exists on the real script (HARD RULE 0.24, no dry-run mode is provided by design), so per this plan's brief the unit test verifies the wrapper's parsing contract against a known-format fixture; a REAL on-chain fund pass is the separate manual verification step in Step 8 below.

```javascript
// ~/vineyard/engines/polymarket.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseFundOutput } from './polymarket.mjs';

test('parseFundOutput: already-registered branch (real fixture from fund_via_bridge.py main())', () => {
  const stdout = '[fund_via_bridge] EOA=0xabc deposit=0xdef\n' + JSON.stringify({ deposit_wallet: '0xdef', registered: true, already: true }) + '\n';
  const parsed = parseFundOutput(stdout);
  assert.equal(parsed.registered, true);
  assert.equal(parsed.already, true);
  assert.equal(parsed.deposit_wallet, '0xdef');
});

test('parseFundOutput: fresh-registration branch (real fixture shape with bridge_address + balance_usdc)', () => {
  const stdout = [
    '[fund_via_bridge] EOA=0xabc deposit=0xdef',
    '[fund_via_bridge] bridge EVM=0x999',
    '[fund_via_bridge] sent $2 pUSD through bridge, waiting for onramp…',
    JSON.stringify({ deposit_wallet: '0xdef', bridge_address: '0x999', registered: true, balance_usdc: 1.98 }),
    '',
  ].join('\n');
  const parsed = parseFundOutput(stdout);
  assert.equal(parsed.registered, true);
  assert.equal(parsed.balance_usdc, 1.98);
});

test('parseFundOutput: throws a clear error on empty stdout rather than returning undefined', () => {
  assert.throws(() => parseFundOutput(''), /no output/);
});
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: FAIL — `Cannot find module './polymarket.mjs'`

- [ ] **Step 6: Write `engines/polymarket.mjs` (fund half)**

```javascript
// ~/vineyard/engines/polymarket.mjs — thin Node wrapper shelling out to the copied, byte-for-byte
// anicca Polymarket Python scripts (engines/python/polymarket/). None of the money-safety logic
// (deposit-wallet registry gate, neg-risk approvals, CTF operator approval) is reimplemented here —
// only invoked + parsed. See this plan's header discrepancy table (D1/D2/D6/D8) for what differs
// from the spec's original assumption and why.
import { execFile } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const PY_DIR = path.join(HERE, 'python', 'polymarket');
const VENV_PY = path.join(HERE, 'python', '.venv', 'bin', 'python3');

function pythonBin() {
  return process.env.VINEYARD_PYTHON || VENV_PY;
}

/** fund_via_bridge.py prints exactly one compact JSON line on stdout (debug goes to stderr). */
export function parseFundOutput(stdout) {
  const line = stdout.trim().split('\n').filter((l) => l.trim().startsWith('{')).pop();
  if (!line) throw new Error('fund_via_bridge.py produced no output');
  return JSON.parse(line);
}

/**
 * Register + fund instance's Polymarket deposit wallet via the bridge onramp (D8: `sourceKey` must
 * be an ALREADY-REGISTERED wallet's key for a brand-new deployment's very first registration).
 */
export async function fund({ evmPrivateKey, sourceKey, fundUsd = 2, env = process.env }) {
  const childEnv = {
    ...env,
    POLYGON_WALLET_PRIVATE_KEY: evmPrivateKey,
    FUND_USD: String(fundUsd),
    ...(sourceKey ? { SOURCE_KEY: sourceKey } : {}),
  };
  const { stdout } = await execFileAsync(pythonBin(), [path.join(PY_DIR, 'fund_via_bridge.py')], {
    env: childEnv,
    timeout: 300_000,
  });
  return parseFundOutput(stdout);
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: PASS — 3 tests, 0 failures

- [ ] **Step 8: Manual (non-automated) verification note — HARD RULE 0.24**

A REAL bridge registration requires a `SOURCE_KEY` from an already-registered Polymarket wallet (D8) and moves real USDC. Separate manual step once such a key is available: `POLYGON_WALLET_PRIVATE_KEY` set to a fresh instance's key, `SOURCE_KEY` set to the registered wallet's key, run `engines/python/.venv/bin/python3 engines/python/polymarket/fund_via_bridge.py` directly and confirm `registered: true` with a real `balance_usdc` after the bridge poll completes (`get_balance_allowance` resolves — spec DONE criterion §9.2).

- [ ] **Step 9: Commit**

```bash
cd ~/vineyard
git add engines/python/requirements.txt engines/python/polymarket/fund_via_bridge.py engines/polymarket.mjs engines/polymarket.test.mjs .gitignore
git commit -m "feat(engines): polymarket fund via bridge onramp (copied verbatim, D9 pinned deps)"
```

---

### Task 9: Engine — Polymarket TRADE (parameterized `place_order.py`, D1)

**Files:**
- Create: `~/vineyard/engines/python/polymarket/place_order.py` (NEW — see D1)
- Modify: `~/vineyard/engines/polymarket.mjs` (add trade half)
- Modify: `~/vineyard/engines/polymarket.test.mjs` (add trade tests)

Per D1, `v2_full_flow.py` cannot be shelled out to generically (hardcoded market/amount/`.env` path, no argparse). This task writes a new script that reuses its exact proven call sequence, parameterized.

- [ ] **Step 1: Write `engines/python/polymarket/place_order.py`**

```python
#!/usr/bin/env python3
"""place_order.py — parameterized Polymarket CLOB V2 FAK market order.

Derived from the EXACT, proven-live API call sequence in anicca's v2_full_flow.py (SIWE mint ->
SecureClient.create -> approve neg-risk spenders -> create_market_order -> post_order — see this
plan's discrepancy D1). v2_full_flow.py itself is a hardcoded one-off demo (fixed token_id, fixed
$1 amount, fixed absolute .env path) that cannot be invoked with different parameters — this file is
the SAME call sequence, parameterized via argparse + env instead of hardcoded constants. NO DRY RUN
(HARD RULE 0.24) — running this submits a real on-chain order.

Usage:
  POLYGON_WALLET_PRIVATE_KEY=0x... python3 place_order.py --token-id <TID> --side BUY --amount 1 --max-price 0.60
"""
import argparse
import json
import os
import sys
import datetime
import base64

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
NEG_EXCH = "0xe2222d279d744050d28e00520010520000310F59"
NEG_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"


def norm(k):
    return k if k.startswith("0x") else "0x" + k


def mint_relayer_key(acct):
    """SIWE (no browser) -> relayer/api/auth -> apiKey. Verbatim flow from v2_full_flow.py::mint()."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Origin": "https://polymarket.com", "Referer": "https://polymarket.com/"})
    nonce = s.get("https://gamma-api.polymarket.com/nonce", timeout=20).json()["nonce"]
    iss = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.datetime.now(datetime.timezone.utc).microsecond//1000:03d}Z"
    f = {"domain": "polymarket.com", "address": acct.address, "statement": "Welcome to Polymarket! Sign to connect.",
         "uri": "https://polymarket.com", "version": "1", "chainId": 137, "nonce": nonce, "issuedAt": iss}
    pt = (f"polymarket.com wants you to sign in with your Ethereum account:\n{acct.address}\n\n{f['statement']}\n\n"
          f"URI: https://polymarket.com\nVersion: 1\nChain ID: 137\nNonce: {nonce}\nIssued At: {iss}")
    sig = "0x" + acct.sign_message(encode_defunct(text=pt)).signature.hex()
    b = base64.b64encode((json.dumps(f, separators=(",", ":")) + ":::" + sig).encode()).decode()
    s.get("https://gamma-api.polymarket.com/login", headers={"Authorization": "Bearer " + b}, timeout=20)
    r = s.post("https://relayer-v2.polymarket.com/relayer/api/auth", json={}, timeout=20).json()
    return r.get("apiKey") or r.get("api_key")


def build_client(key):
    from polymarket.clients.secure import SecureClient
    from polymarket.auth import RelayerApiKey
    acct = Account.from_key(key)
    tmp = SecureClient._create(private_key=key, validate_credentials=True)
    creds = tmp._ctx.credentials
    tmp.close()
    client = SecureClient.create(private_key=key, credentials=creds,
                                  api_key=RelayerApiKey(key=mint_relayer_key(acct), address=acct.address))
    return client, acct


def ensure_approvals(client):
    for sp in (NEG_EXCH, NEG_ADAPTER):
        ba = client.get_balance_allowance(asset_type="COLLATERAL")
        if int(ba.allowances.get(sp, 0)) < 1:
            h = client.approve_erc20(token_address=PUSD, spender_address=sp, amount="max")
            try:
                h.wait()
            except Exception as e:
                print(f"[place_order] approve {sp[:10]} wait note: {str(e)[:80]}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token-id", required=True, help="Polymarket CLOB token_id (outcome share) to trade")
    p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    p.add_argument("--amount", required=True, type=float, help="USD (BUY) / shares (SELL) to trade")
    p.add_argument("--max-price", required=True, type=float, help="max acceptable price (0-1)")
    args = p.parse_args()

    key = norm(os.environ["POLYGON_WALLET_PRIVATE_KEY"])
    client, acct = build_client(key)
    try:
        ensure_approvals(client)
        order = client.create_market_order(
            token_id=args.token_id, side=args.side, amount=str(args.amount),
            max_price=str(args.max_price), order_type="FAK",
        )
        resp = client.post_order(order)
        print(json.dumps({
            "wallet": str(client.wallet), "token_id": args.token_id, "side": args.side,
            "amount": args.amount, "max_price": args.max_price,
            "order_id": getattr(resp, "orderID", None) or getattr(resp, "order_id", None) or str(resp)[:120],
            "raw": str(resp)[:500],
        }))
    finally:
        client.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing test for the trade wrapper's stdout parser**

```javascript
// append to ~/vineyard/engines/polymarket.test.mjs
import { parseTradeOutput, trade } from './polymarket.mjs';

test('parseTradeOutput: real-shape fixture (single compact JSON line from place_order.py)', () => {
  const stdout = JSON.stringify({
    wallet: '0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74', token_id: '123', side: 'BUY',
    amount: 1, max_price: 0.6, order_id: 'abc-123', raw: '{...}',
  }) + '\n';
  const parsed = parseTradeOutput(stdout);
  assert.equal(parsed.side, 'BUY');
  assert.equal(parsed.order_id, 'abc-123');
});

test('parseTradeOutput: throws on empty stdout', () => {
  assert.throws(() => parseTradeOutput(''), /no output/);
});

test('trade: is exported as a callable async function', () => {
  assert.equal(typeof trade, 'function');
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: FAIL — `parseTradeOutput is not a function` / `trade is not a function`

- [ ] **Step 4: Add the trade half to `engines/polymarket.mjs`**

```javascript
// append to ~/vineyard/engines/polymarket.mjs

/** place_order.py prints exactly one compact JSON line on stdout. */
export function parseTradeOutput(stdout) {
  const line = stdout.trim().split('\n').filter((l) => l.trim().startsWith('{')).pop();
  if (!line) throw new Error('place_order.py produced no output');
  return JSON.parse(line);
}

export async function trade({ evmPrivateKey, tokenId, side, amountUsd, maxPrice, env = process.env }) {
  const args = [
    path.join(PY_DIR, 'place_order.py'),
    '--token-id', String(tokenId),
    '--side', side,
    '--amount', String(amountUsd),
    '--max-price', String(maxPrice),
  ];
  const { stdout } = await execFileAsync(pythonBin(), args, {
    env: { ...env, POLYGON_WALLET_PRIVATE_KEY: evmPrivateKey },
    timeout: 120_000,
  });
  return parseTradeOutput(stdout);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: PASS — 6 tests, 0 failures

- [ ] **Step 6: Manual (non-automated) verification note — HARD RULE 0.24**

A REAL order placement needs a registered + funded deposit wallet (Task 8's fund step already run) and a real, currently-open market's `token_id` (readable from `https://gamma-api.polymarket.com/markets?closed=false`). Separate manual step: `POLYGON_WALLET_PRIVATE_KEY=<registered key> engines/python/.venv/bin/python3 engines/python/polymarket/place_order.py --token-id <real open market token_id> --side BUY --amount 1 --max-price 0.60` — confirm a real `order_id` in the response and a matched fill visible via `https://data-api.polymarket.com/positions?user=<deposit wallet>` (spec DONE criterion §9.3).

- [ ] **Step 7: Commit**

```bash
cd ~/vineyard
git add engines/python/polymarket/place_order.py engines/polymarket.mjs engines/polymarket.test.mjs
git commit -m "feat(engines): polymarket place_order.py (parameterized, derived from v2_full_flow.py per D1)"
```

---

### Task 10: Engine — Polymarket REDEEM (copy + 4 documented edits, D6)

**Files:**
- Create: `~/vineyard/engines/python/polymarket/redeem.py` (copied + adapted)
- Create: `~/vineyard/engines/python/polymarket/test_redeem.py` (copied verbatim — pure-function tests)
- Modify: `~/vineyard/engines/polymarket.mjs` (add redeem half)
- Modify: `~/vineyard/engines/polymarket.test.mjs` (add redeem tests)

- [ ] **Step 1: Copy `redeem.py` and `test_redeem.py`**

```bash
cp ~/anicca/skills/earn/polymarket-trade/redeem.py ~/vineyard/engines/python/polymarket/redeem.py
cp ~/anicca/skills/earn/polymarket-trade/test_redeem.py ~/vineyard/engines/python/polymarket/test_redeem.py
```

- [ ] **Step 2: Apply the 4 documented edits from discrepancy D6**

Edit `~/vineyard/engines/python/polymarket/redeem.py`:

(a) Replace the hardcoded deposit wallet + remove the anicca-specific `.env` path constant:
```python
# before:
DEPOSIT_WALLET = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"
AGENT_ENV = os.path.expanduser("~/.anicca-founder/agents/polymarket-agent/.env")
LEDGER_RECORD_JS = os.path.expanduser("~/anicca/skills/earn/lib/record.mjs")
```
```python
# after:
DEPOSIT_WALLET = os.environ["POLYMARKET_DEPOSIT_WALLET"]
```

(b) In `build_client()`, remove the `load_dotenv(AGENT_ENV)` call (the Node wrapper already sets `POLYGON_WALLET_PRIVATE_KEY` in the child env directly):
```python
# before:
from dotenv import load_dotenv
load_dotenv(AGENT_ENV)
key = os.environ["POLYGON_WALLET_PRIVATE_KEY"]
```
```python
# after:
key = os.environ["POLYGON_WALLET_PRIVATE_KEY"]
```

(c) In `_mint_relayer_api_key()`, scope the relayer-key cache path per instance instead of the hardcoded anicca founder path:
```python
# before:
_cache = os.path.expanduser("~/.anicca-founder/.pm-relayer-apikey")
```
```python
# after:
_cache = os.environ.get("POLYMARKET_RELAYER_CACHE", os.path.expanduser("~/.vineyard/.pm-relayer-apikey"))
```

(d) In `main()`, remove the call to the external anicca ledger writer — the script keeps printing the per-condition result (unchanged), Vineyard's own `core/ledger.mjs` is the sole ledger writer:
```python
# before:
profitable = record_ledger_line(line)
results.append({**tx, "status": status, "row": row, "profitable": profitable})
```
```python
# after:
results.append({**tx, "status": status, "row": row, "line": line})
```
Also delete the now-unused `record_ledger_line()` function definition entirely (it only existed to call the removed `record.mjs`).

- [ ] **Step 3: Run the copied pure-function tests to confirm the edits didn't break anything**

```bash
cd ~/vineyard/engines/python/polymarket
../../.venv/bin/python3 -m pytest test_redeem.py -v 2>&1 || ../../.venv/bin/python3 test_redeem.py
```

Expected: all `TestDedupeRedeemableConditions` / `TestClassifyMarketType` / etc. tests PASS (these test `dedupe_redeemable_conditions`, `classify_market_type`, `compute_recovered_amount`, `build_ledger_line` — none of which were touched by the 4 edits above).

- [ ] **Step 4: Write the failing test for the redeem wrapper's stdout parser**

```javascript
// append to ~/vineyard/engines/polymarket.test.mjs
import { parseRedeemOutput, redeem } from './polymarket.mjs';

test('parseRedeemOutput: real-shape fixture — one compact JSON line per redeemed condition', () => {
  const stdout = [
    'found 1 redeemable condition(s):',
    '  - \'Wimbledon Final\' conditionId=0xc8a0 value=$10.0000 type=standard',
    'pUSD before: 4.95',
    'redeeming 0xc8a0 (\'Wimbledon Final\') ...',
    '  tx=0xdeadbeef status=0x1',
    'pUSD after: 14.95  (recovered: 10.0)',
    JSON.stringify({ conditionId: '0xc8a0', title: 'Wimbledon Final', tx_hash: '0xdeadbeef', status: '0x1', line: { earn_usdc: 10, cost_usdc: 3.55 } }),
  ].join('\n');
  const rows = parseRedeemOutput(stdout);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].tx_hash, '0xdeadbeef');
  assert.equal(rows[0].line.earn_usdc, 10);
});

test('parseRedeemOutput: "nothing to redeem" produces an empty array, not an error', () => {
  const stdout = 'no redeemable conditions found — nothing to do\n';
  assert.deepEqual(parseRedeemOutput(stdout), []);
});

test('redeem: is exported as a callable async function', () => {
  assert.equal(typeof redeem, 'function');
});
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: FAIL — `parseRedeemOutput is not a function`

- [ ] **Step 6: Add the redeem half to `engines/polymarket.mjs`**

```javascript
// append to ~/vineyard/engines/polymarket.mjs

/** redeem.py prints one compact JSON line PER redeemed condition (zero lines = nothing redeemable). */
export function parseRedeemOutput(stdout) {
  return stdout
    .trim()
    .split('\n')
    .filter((l) => l.trim().startsWith('{'))
    .map((l) => JSON.parse(l));
}

export async function redeem({ evmPrivateKey, depositWallet, relayerCacheFile, env = process.env }) {
  const { stdout } = await execFileAsync(pythonBin(), [path.join(PY_DIR, 'redeem.py')], {
    env: {
      ...env,
      POLYGON_WALLET_PRIVATE_KEY: evmPrivateKey,
      POLYMARKET_DEPOSIT_WALLET: depositWallet,
      ...(relayerCacheFile ? { POLYMARKET_RELAYER_CACHE: relayerCacheFile } : {}),
    },
    timeout: 300_000,
  });
  return parseRedeemOutput(stdout);
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/polymarket.test.mjs`
Expected: PASS — 9 tests, 0 failures

- [ ] **Step 8: Manual (non-automated) verification note — HARD RULE 0.24**

Requires an ALREADY-RESOLVED market position in the deposit wallet. Separate manual step: after Task 9's real order settles, wait for the market to resolve, then run `POLYGON_WALLET_PRIVATE_KEY=<key> POLYMARKET_DEPOSIT_WALLET=<deposit wallet> engines/python/.venv/bin/python3 engines/python/polymarket/redeem.py` and confirm a real `tx_hash` with `status=0x1` and `pUSD after > pUSD before`.

- [ ] **Step 9: Commit**

```bash
cd ~/vineyard
git add engines/python/polymarket/redeem.py engines/python/polymarket/test_redeem.py engines/polymarket.mjs engines/polymarket.test.mjs
git commit -m "feat(engines): polymarket redeem.py copied + 4 documented edits (D6) — DEPOSIT_WALLET/env-scoped"
```

---

### Task 11: Engine — Hyperliquid (copy `hl.py` verbatim, D7)

**Files:**
- Create: `~/vineyard/engines/python/hyperliquid/hl.py` (copied verbatim — zero edits)
- Create: `~/vineyard/engines/hyperliquid.mjs`
- Test: `~/vineyard/engines/hyperliquid.test.mjs`

Per D7, `hl.py` is copied with **zero edits** — its env-first key resolution (`PKVAR` / `BLOCKRUN_WALLET_KEY`) already works correctly as long as the wrapper injects the resolved key, which sidesteps the fragile relative-path `resolve-identity.mjs` fallback entirely (that branch is simply never reached).

- [ ] **Step 1: Copy `hl.py` verbatim**

```bash
cp ~/anicca/skills/earn/hl-trade/hl.py ~/vineyard/engines/python/hyperliquid/hl.py
```

- [ ] **Step 2: Write the failing test for the 4 parse functions**

hl.py's `cmd_account`/`cmd_market`/`cmd_open`/`cmd_close` each print exactly ONE `json.dumps(..., indent=2)` call — a pretty-printed, multi-line JSON object, unlike the compact single-line JSON the Polymarket scripts print. The parser must `JSON.parse` the WHOLE trimmed stdout, not just the last line.

```javascript
// ~/vineyard/engines/hyperliquid.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHlOutput, account, market, open, close } from './hyperliquid.mjs';

test('parseHlOutput: parses hl.py\'s pretty-printed (indent=2) account output', () => {
  const stdout = JSON.stringify({ address: '0xabc', account_value_usd: 5.1234, withdrawable_usd: 5.1, open_positions: [] }, null, 2) + '\n';
  const parsed = parseHlOutput(stdout);
  assert.equal(parsed.address, '0xabc');
  assert.equal(parsed.account_value_usd, 5.1234);
});

test('parseHlOutput: parses hl.py\'s market output shape (real fixture from cmd_market)', () => {
  const stdout = JSON.stringify({ coin: 'ETH', price: 3400.5, max_leverage: 25, closes_hourly: [3390, 3395, 3400.5], change_pct_window: 0.31 }, null, 2);
  const parsed = parseHlOutput(stdout);
  assert.equal(parsed.coin, 'ETH');
  assert.equal(parsed.change_pct_window, 0.31);
});

test('parseHlOutput: parses hl.py\'s open output shape', () => {
  const stdout = JSON.stringify({ opened: 'long', coin: 'ETH', entry: 3400, size: 0.0035, leverage: 2, stop_loss: 3264, take_profit: 3672 }, null, 2);
  const parsed = parseHlOutput(stdout);
  assert.equal(parsed.opened, 'long');
});

test('parseHlOutput: parses hl.py\'s "skipped" (already-open) output shape', () => {
  const stdout = JSON.stringify({ skipped: 'position already open on ETH', szi: '0.0035' }, null, 2);
  const parsed = parseHlOutput(stdout);
  assert.equal(parsed.skipped, 'position already open on ETH');
});

test('account/market/open/close: are all exported as callable async functions', () => {
  assert.equal(typeof account, 'function');
  assert.equal(typeof market, 'function');
  assert.equal(typeof open, 'function');
  assert.equal(typeof close, 'function');
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/hyperliquid.test.mjs`
Expected: FAIL — `Cannot find module './hyperliquid.mjs'`

- [ ] **Step 4: Write `engines/hyperliquid.mjs`**

```javascript
// ~/vineyard/engines/hyperliquid.mjs — thin Node wrapper around the copied, byte-for-byte hl.py (a
// TOOL, not a strategy — hl.py's own docstring: "YOU are an intelligence; you decide"). This wrapper
// NEVER picks side/size/coin — it only exposes hl.py's 4 primitives (account/market/open/close) as
// async functions, and ALWAYS injects the resolved per-instance key as BLOCKRUN_WALLET_KEY (D7 — this
// bypasses hl.py's own internal resolve-identity.mjs subprocess fallback, which assumes anicca's
// directory layout and would not resolve correctly inside vineyard/; hl.py's env-first branch always
// short-circuits before reaching that fallback once BLOCKRUN_WALLET_KEY is set).
import { execFile } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const HL_PY = path.join(HERE, 'python', 'hyperliquid', 'hl.py');
const VENV_PY = path.join(HERE, 'python', '.venv', 'bin', 'python3');

function pythonBin() {
  return process.env.VINEYARD_PYTHON || VENV_PY;
}

/** hl.py's cmd_* functions each print exactly one json.dumps(..., indent=2) object on stdout. */
export function parseHlOutput(stdout) {
  return JSON.parse(stdout.trim());
}

async function runHl(args, evmPrivateKey, env) {
  const { stdout } = await execFileAsync(pythonBin(), [HL_PY, ...args], {
    env: { ...env, BLOCKRUN_WALLET_KEY: evmPrivateKey },
    timeout: 60_000,
  });
  return parseHlOutput(stdout);
}

export const account = ({ evmPrivateKey, env = process.env }) => runHl(['account'], evmPrivateKey, env);

export const market = ({ coin, hours = 24, evmPrivateKey, env = process.env }) =>
  runHl(['market', coin, String(hours)], evmPrivateKey, env);

export const open = ({ coin, side, notional, lev = 2, sl = 4, tp = 8, evmPrivateKey, env = process.env }) =>
  runHl(['open', coin, side, String(notional), '--lev', String(lev), '--sl', String(sl), '--tp', String(tp)], evmPrivateKey, env);

export const close = ({ coin, evmPrivateKey, env = process.env }) => runHl(['close', coin], evmPrivateKey, env);
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/hyperliquid.test.mjs`
Expected: PASS — 5 tests, 0 failures

- [ ] **Step 6: Manual (non-automated) verification note — HARD RULE 0.24**

Requires a Hyperliquid-funded account (USDC deposited via the Arbitrum bridge — a separate one-time step per hl-trade's SKILL.md). Separate manual step: `BLOCKRUN_WALLET_KEY=<funded key> engines/python/.venv/bin/python3 engines/python/hyperliquid/hl.py account` — confirm a real `account_value_usd`; then a real `market ETH 24` read; an actual `open`/`close` requires a genuine directional judgment call (hl.py's own philosophy) and is NOT something this plan automates or fabricates a decision for.

- [ ] **Step 7: Commit**

```bash
cd ~/vineyard
git add engines/python/hyperliquid/hl.py engines/hyperliquid.mjs engines/hyperliquid.test.mjs
git commit -m "feat(engines): hyperliquid hl.py copied verbatim (D7 — key injected, no fragile fallback)"
```

---

### Task 12: Engine — Solana (copy `run.sh` minus telemetry, D3/D4/D5)

**Files:**
- Create: `~/vineyard/engines/shell/solana/run.sh` (copied, minus 1 line — see D5)
- Create: `~/vineyard/engines/solana.mjs`
- Test: `~/vineyard/engines/solana.test.mjs`

Per D3/D4, the Solana engine is not a Jupiter-swap script — it shells to the globally-installed `@blockrun/franklin-trading` CLI (real npm package, confirmed `0.2.4`), which manages its own wallet under `~/.blockrun/` with **no per-invocation wallet-path flag**. D4 empirically verified (`HOME=<tmp> franklin-trading setup solana` → isolated `<tmp>/.blockrun/`) that a `$HOME` env override achieves per-instance isolation, so this wrapper reuses `core/wallet.mjs`'s `instanceDir(id)` as that `$HOME`.

- [ ] **Step 1: Copy `run.sh`, removing the one anicca-telemetry line (D5)**

```bash
cp ~/anicca/skills/earn/sol-trade/run.sh ~/vineyard/engines/shell/solana/run.sh
```

Edit `~/vineyard/engines/shell/solana/run.sh` — delete this block (the ONLY line removed; everything else — kill-switch, the baseline-strategy prompt text, the `franklin-trading start` invocation, the trace-write — stays byte-identical):
```bash
# Signed telemetry POST (#25 TELEM) — fail-safe: never affects the trade pass's own exit code above.
timeout 20 node "$SKILL_DIR/../../../runtime/dashboard/telemetry-post-franklin.mjs" >> "$STATE_DIR/telemetry-post.log" 2>&1 || true

```

- [ ] **Step 2: Verify `command -v franklin-trading` still resolves (declared as an optionalDependency in Task 1's package.json)**

```bash
which franklin-trading
```

Expected: a real path, e.g. `/opt/homebrew/bin/franklin-trading` (installed globally, or via `npm install` resolving the optionalDependency's bin into `node_modules/.bin/`).

- [ ] **Step 3: Empirically re-confirm HOME-scoped wallet isolation (D4) — real, harmless invocation (local keygen only, no network/funds)**

```bash
HOME=/tmp/vy-solana-isolate-test franklin-trading setup solana 2>&1 | tail -5
find /tmp/vy-solana-isolate-test -maxdepth 2
rm -rf /tmp/vy-solana-isolate-test
```

Expected: `Chain: solana — saved to ~/.blockrun/` message, and the `find` shows `.blockrun/.solana-session` + `.blockrun/payment-chain` created ONLY under `/tmp/vy-solana-isolate-test`, never touching the real `~/.blockrun/`.

- [ ] **Step 4: Write the failing test for the wrapper's freeform-text parser**

```javascript
// ~/vineyard/engines/solana.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lastLines, run } from './solana.mjs';

test('lastLines: returns the last N non-empty lines, matching run.sh\'s own OUTTAIL pattern', () => {
  const text = 'line1\nline2\n\nline3\nline4\nline5\n';
  assert.equal(lastLines(text, 2), 'line4\nline5');
});

test('lastLines: shorter input than N returns everything available', () => {
  assert.equal(lastLines('only-one-line\n', 5), 'only-one-line');
});

test('run: is exported as a callable function returning a Promise', () => {
  assert.equal(typeof run, 'function');
});
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd ~/vineyard && node --test engines/solana.test.mjs`
Expected: FAIL — `Cannot find module './solana.mjs'`

- [ ] **Step 6: Write `engines/solana.mjs`**

```javascript
// ~/vineyard/engines/solana.mjs — thin Node wrapper shelling out to the copied run.sh, which itself
// shells out to the globally-installed @blockrun/franklin-trading CLI (D3) — a SEPARATE, fully
// autonomous LLM-driven trading agent that does its OWN research/sizing/execution and pays for its
// own model calls via x402 from ITS wallet. This wrapper does NOT implement a Jupiter swap directly
// (the spec's original assumption — see D3). Output is FREEFORM TEXT, not JSON — matches run.sh's own
// existing OUTTAIL (last-5-lines) pattern rather than inventing a JSON contract the script never had.
// Per-instance isolation (D4) is achieved by spawning with HOME set to this instance's own directory,
// reusing core/wallet.mjs's existing instanceDir(id) boundary — franklin-trading's own .blockrun/
// store then lives INSIDE that same per-instance directory, never colliding across instances.
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN_SH = path.join(HERE, 'shell', 'solana', 'run.sh');

export function lastLines(text, n) {
  return text.trim().split('\n').filter(Boolean).slice(-n).join('\n');
}

export function run({ instanceHome, maxSpend = 0.25, model = 'openai/gpt-5-mini', env = process.env, timeoutMs = 600_000 }) {
  return new Promise((resolve, reject) => {
    const child = spawn('bash', [RUN_SH], {
      env: {
        ...env,
        HOME: instanceHome, // D4: isolates franklin-trading's own .blockrun/ wallet store per instance
        SOL_TRADE_MAX_SPEND: String(maxSpend),
        SOL_TRADE_MODEL: model,
      },
      timeout: timeoutMs,
    });
    let out = '';
    child.stdout.on('data', (d) => { out += d.toString(); });
    child.stderr.on('data', (d) => { out += d.toString(); });
    child.on('close', (code) => resolve({ exit: code, note: lastLines(out, 5) }));
    child.on('error', reject);
  });
}

/** One-time setup: create this instance's own isolated franklin-trading Solana wallet (D4). */
export function setup({ instanceHome, timeoutMs = 30_000 }) {
  return new Promise((resolve, reject) => {
    const child = spawn('franklin-trading', ['setup', 'solana'], {
      env: { ...process.env, HOME: instanceHome },
      timeout: timeoutMs,
    });
    let out = '';
    child.stdout.on('data', (d) => { out += d.toString(); });
    child.on('close', (code) => {
      const match = out.match(/Address:\s*(\S+)/);
      resolve({ exit: code, address: match ? match[1] : null, raw: out });
    });
    child.on('error', reject);
  });
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd ~/vineyard && node --test engines/solana.test.mjs`
Expected: PASS — 3 tests, 0 failures

- [ ] **Step 8: Manual (non-automated) verification note — HARD RULE 0.24**

Requires a Solana wallet funded with USDC + SOL for gas. Separate manual step: run `setup({instanceHome: '<VINEYARD_HOME>/instances/<id>'})` once, fund the printed address, then `run({instanceHome: '<same dir>'})` — confirm `franklin-trading`'s own real trace output (either a filled swap or a reasoned WAIT — both are valid real outcomes per HARD RULE 0.24, never a fabricated fill).

- [ ] **Step 9: Commit**

```bash
cd ~/vineyard
git add engines/shell/solana/run.sh engines/solana.mjs engines/solana.test.mjs
git commit -m "feat(engines): solana engine wraps franklin-trading CLI, HOME-scoped isolation (D3/D4/D5)"
```

---

### Task 13: `core/brain.mjs` — engine picker (deterministic bookkeeping, not judgment)

**Files:**
- Create: `~/vineyard/core/brain.mjs`
- Test: `~/vineyard/core/brain.test.mjs`

Per `building-effective-ai-agents.md` (HARD RULE): judgment — which market, which side, which size — is never hardcoded in a regex/if-else; that decision belongs to whoever calls `vineyard trade` with explicit params (a human operator or an LLM agent reading the engine's own tool contract, exactly matching hl.py's own philosophy: "You are an intelligence; you decide"). `brain.mjs`'s only job for the **automatic** `vineyard run` loop is legitimate deterministic scheduling — round-robin among the engines that are safe to invoke unattended with **no external decision required**: `yield` (treasury rebalance math), `solana` (franklin-trading's own internal LLM decides), `polymarket-redeem` (collects already-resolved winnings, nothing to decide). Hyperliquid `open` and Polymarket `place_order` are reached only via the explicit `trade` command (Task 15) — this is a scope decision, not an oversight, and is called out here so it is traceable.

- [ ] **Step 1: Write the failing test**

```javascript
// ~/vineyard/core/brain.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickEngine } from './brain.mjs';

test('pickEngine: with no history, picks the first candidate deterministically', () => {
  const picked = pickEngine({ lastRun: {}, candidates: ['yield', 'solana', 'polymarket-redeem'] });
  assert.equal(picked, 'yield');
});

test('pickEngine: picks whichever candidate ran longest ago (or never)', () => {
  const now = Date.now();
  const picked = pickEngine({
    lastRun: { yield: now - 1000, solana: now - 500, 'polymarket-redeem': now - 5000 },
    candidates: ['yield', 'solana', 'polymarket-redeem'],
  });
  assert.equal(picked, 'polymarket-redeem');
});

test('pickEngine: default candidate list is the 3 automatic engines (yield/solana/polymarket-redeem)', () => {
  const picked = pickEngine({});
  assert.ok(['yield', 'solana', 'polymarket-redeem'].includes(picked));
});

test('pickEngine: empty candidate list returns null, never throws', () => {
  assert.doesNotThrow(() => {
    assert.equal(pickEngine({ candidates: [] }), null);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/vineyard && node --test core/brain.test.mjs`
Expected: FAIL — `Cannot find module './brain.mjs'`

- [ ] **Step 3: Write `core/brain.mjs`**

```javascript
// ~/vineyard/core/brain.mjs — engine picker for `vineyard run`. Per HARD RULE
// (building-effective-ai-agents.md): judgment (which market/side/size) is NEVER hardcoded here — that
// decision belongs to whoever calls `vineyard trade` with explicit params (a human operator or an LLM
// agent, exactly as hl-trade/SKILL.md instructs: "You are an intelligence; you decide."). brain.mjs's
// ONLY job is deterministic BOOKKEEPING: round-robin among the engines safe to run unattended with NO
// external params (yield = treasury rebalance, solana = franklin-trading's own internal LLM decides,
// polymarket-redeem = collect already-resolved winnings). Legitimate deterministic scheduling, not a
// trading judgment (coding-style.md: deterministic code only for tools/bookkeeping).
const AUTOMATIC_ENGINES = ['yield', 'solana', 'polymarket-redeem'];

export function pickEngine({ lastRun = {}, candidates = AUTOMATIC_ENGINES } = {}) {
  if (candidates.length === 0) return null;
  return [...candidates].sort((a, b) => (lastRun[a] || 0) - (lastRun[b] || 0))[0];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/vineyard && node --test core/brain.test.mjs`
Expected: PASS — 4 tests, 0 failures

- [ ] **Step 5: Commit**

```bash
cd ~/vineyard
git add core/brain.mjs core/brain.test.mjs
git commit -m "feat(core): brain.mjs deterministic engine-rotation picker (no hardcoded trade judgment)"
```

---

### Task 14: `core/loop.mjs` — wake → pick → earn → ledger

**Files:**
- Create: `~/vineyard/core/loop.mjs`
- Test: `~/vineyard/core/loop.test.mjs`

Wires `core/brain.mjs` + `core/wallet.mjs` + `core/ledger.mjs` + the 3 automatic engines (`yield`/`solana`/`polymarket-redeem`) together. `runOnce` fails closed (records a `skip` ledger line, never throws) when an instance has no key for the picked engine's chain — this is real, honest bookkeeping of "nothing happened this pass," not a fabricated result.

- [ ] **Step 1: Write the failing test using dependency injection (no real network/chain calls)**

```javascript
// ~/vineyard/core/loop.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { runOnce } from './loop.mjs';
import { generateWallet } from './wallet.mjs';
import { readLedger } from './ledger.mjs';

function tmpAll(prefix) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-home-`));
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-data-`));
  return { home, dataDir };
}

test('runOnce: no wallet yet for the picked engine -> writes a skip ledger line, never throws', async () => {
  const { home, dataDir } = tmpAll('vy-loop-noskey');
  const env = { VINEYARD_HOME: home };
  await assert.doesNotReject(async () => {
    const line = await runOnce({ id: 'unspawned-id', dataDir, env, engines: { yield: {}, solana: {}, polymarket: {} }, candidates: ['yield'] });
    assert.equal(line.status, 'skip');
    assert.equal(line.reason, 'no-evm-key');
  });
});

test('runOnce: with a spawned wallet, calls the picked engine\'s run() and records its result', async () => {
  const { home, dataDir } = tmpAll('vy-loop-withkey');
  const env = { VINEYARD_HOME: home };
  generateWallet('spawned-id', env);
  let called = null;
  const fakeYield = { run: async (args) => { called = args; return { kind: 'yield', action: 'hold', liquid_usdc: 3 }; } };
  const line = await runOnce({ id: 'spawned-id', dataDir, env, engines: { yield: fakeYield, solana: {}, polymarket: {} }, candidates: ['yield'] });
  assert.equal(line.engine, 'yield');
  assert.equal(line.action, 'hold');
  assert.ok(called.evmPrivateKey.startsWith('0x'));
  const rows = readLedger('spawned-id', dataDir);
  assert.equal(rows.length, 1);
});

test('runOnce: polymarket-redeem engine result (an array) is normalized into one ledger line with summed net_usdc', async () => {
  const { home, dataDir } = tmpAll('vy-loop-redeem');
  const env = { VINEYARD_HOME: home };
  generateWallet('redeem-id', env);
  const fakePolymarket = {
    redeem: async () => ([
      { tx_hash: '0xaaa', line: { earn_usdc: 10, cost_usdc: 3 } },
      { tx_hash: '0xbbb', line: { earn_usdc: 5, cost_usdc: 5 } },
    ]),
  };
  const line = await runOnce({ id: 'redeem-id', dataDir, env, engines: { yield: {}, solana: {}, polymarket: fakePolymarket }, candidates: ['polymarket-redeem'] });
  assert.equal(line.engine, 'polymarket-redeem');
  assert.equal(line.net_usdc, 7); // (10-3) + (5-5)
  assert.deepEqual(line.tx, ['0xaaa', '0xbbb']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/vineyard && node --test core/loop.test.mjs`
Expected: FAIL — `Cannot find module './loop.mjs'`

- [ ] **Step 3: Write `core/loop.mjs`**

```javascript
// ~/vineyard/core/loop.mjs — wake -> read balances -> pick engine -> earn -> write ledger -> sleep.
// `runOnce` runs exactly one pass; `runLoop` repeats it on an interval (or forever if none given).
// Engines are dependency-injected (`engines` param) so this module is unit-testable without any real
// network/chain call — production callers (cli/index.mjs, api/server.mjs) pass the REAL engine
// modules (engines/yield.mjs, engines/solana.mjs, engines/polymarket.mjs).
import { pickEngine } from './brain.mjs';
import { appendLedger } from './ledger.mjs';
import { resolveEvmPrivateKey, resolveSolanaSecret, instanceDir } from './wallet.mjs';
import { findSpawn } from './registry.mjs';

export async function runOnce({ id, dataDir, env = process.env, engines, candidates, lastRun = {} }) {
  const engineName = pickEngine({ lastRun, candidates });
  if (engineName) lastRun[engineName] = Date.now();

  let result;
  if (engineName === 'yield') {
    const pk = resolveEvmPrivateKey(id, env);
    if (!pk) return appendLedger(id, { engine: 'yield', status: 'skip', reason: 'no-evm-key' }, dataDir);
    result = await engines.yield.run({ evmPrivateKey: pk, env });
  } else if (engineName === 'solana') {
    const secret = resolveSolanaSecret(id, env);
    if (!secret) return appendLedger(id, { engine: 'solana', status: 'skip', reason: 'no-solana-key' }, dataDir);
    result = await engines.solana.run({ instanceHome: instanceDir(id, env), env });
  } else if (engineName === 'polymarket-redeem') {
    const pk = resolveEvmPrivateKey(id, env);
    const spawn = findSpawn(id, env);
    if (!pk || !spawn?.polymarketDepositWallet) {
      return appendLedger(id, { engine: 'polymarket-redeem', status: 'skip', reason: 'no-deposit-wallet' }, dataDir);
    }
    result = await engines.polymarket.redeem({ evmPrivateKey: pk, depositWallet: spawn.polymarketDepositWallet, env });
  } else {
    result = { status: 'skip', reason: `no engine available (candidates=${JSON.stringify(candidates)})` };
  }

  return appendLedger(id, { engine: engineName, ...normalizeResult(result) }, dataDir);
}

function normalizeResult(result) {
  if (Array.isArray(result)) {
    // polymarket-redeem returns an array of per-condition results
    const net_usdc = result.reduce((s, r) => s + Number(r.line?.earn_usdc || 0) - Number(r.line?.cost_usdc || 0), 0);
    return { status: result.length ? 'ok' : 'wait', tx: result.map((r) => r.tx_hash).filter(Boolean), net_usdc, raw: result };
  }
  return { status: result.status || result.action || (result.error ? 'error' : 'ok'), ...result };
}

export async function runLoop({ id, dataDir, intervalMs, env = process.env, engines, candidates, signal }) {
  const lastRun = {};
  // eslint-disable-next-line no-constant-condition
  while (!signal?.aborted) {
    await runOnce({ id, dataDir, env, engines, candidates, lastRun });
    if (!intervalMs) break;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/vineyard && node --test core/loop.test.mjs`
Expected: PASS — 3 tests, 0 failures

- [ ] **Step 5: Commit**

```bash
cd ~/vineyard
git add core/loop.mjs core/loop.test.mjs
git commit -m "feat(core): loop.mjs wake->pick->earn->ledger, dependency-injected engines"
```

---

### Task 15: `cli/index.mjs` + `api/server.mjs` — remaining verbs (fund/run/status/list/trade/redeem)

**Files:**
- Modify: `~/vineyard/cli/index.mjs`
- Modify: `~/vineyard/api/server.mjs`

- [ ] **Step 1: Add the engine imports + remaining command handlers to `cli/index.mjs`**

Add near the top, alongside the existing imports:
```javascript
import { findSpawn, updateSpawn } from '../core/registry.mjs';
import { runOnce } from '../core/loop.mjs';
import { readLedger, realizedPnl } from '../core/ledger.mjs';
import { instanceDir } from '../core/wallet.mjs';
import * as yieldEngine from '../engines/yield.mjs';
import * as polymarketEngine from '../engines/polymarket.mjs';
import * as hyperliquidEngine from '../engines/hyperliquid.mjs';
import * as solanaEngine from '../engines/solana.mjs';

const ENGINES = { yield: yieldEngine, solana: solanaEngine, polymarket: polymarketEngine };
const DATA_DIR = process.env.VINEYARD_DATA_DIR || (process.env.VINEYARD_HOME
  ? require('node:path').join(process.env.VINEYARD_HOME, '..', 'data')
  : 'data');
```

Replace the `main()` switch statement's `default:` branch position by adding new `case` entries before it:
```javascript
    case 'fund': {
      const { flags, positional } = parseFlags(rest);
      const [id, amount] = positional;
      const { resolveEvmPrivateKey } = await import('../core/wallet.mjs');
      const pk = resolveEvmPrivateKey(id);
      if (!pk) { console.error(`no wallet for id ${id} — spawn it first`); process.exitCode = 1; break; }
      const result = await polymarketEngine.fund({ evmPrivateKey: pk, sourceKey: flags['source-key'], fundUsd: Number(amount || flags.fund || 2) });
      if (result.registered) updateSpawn(id, { polymarketDepositWallet: result.deposit_wallet });
      console.log(JSON.stringify(result, null, 2));
      break;
    }
    case 'run': {
      const { flags, positional } = parseFlags(rest);
      const [id] = positional;
      const line = await runOnce({ id, dataDir: DATA_DIR, engines: ENGINES, candidates: flags.engine ? [flags.engine] : undefined });
      console.log(JSON.stringify(line, null, 2));
      break;
    }
    case 'status': {
      const [id] = rest;
      const spawn = findSpawn(id);
      if (!spawn) { console.error(`unknown id: ${id}`); process.exitCode = 1; break; }
      console.log(JSON.stringify({ ...spawn, realized_pnl_usdc: realizedPnl(id, DATA_DIR), ledger: readLedger(id, DATA_DIR) }, null, 2));
      break;
    }
    case 'trade': {
      const { flags, positional } = parseFlags(rest);
      const [id] = positional;
      const { resolveEvmPrivateKey } = await import('../core/wallet.mjs');
      const pk = resolveEvmPrivateKey(id);
      let result;
      if (flags.engine === 'hl') {
        result = await hyperliquidEngine.open({ coin: flags.coin, side: flags.side, notional: Number(flags.notional), lev: Number(flags.lev || 2), sl: Number(flags.sl || 4), tp: Number(flags.tp || 8), evmPrivateKey: pk });
      } else if (flags.engine === 'pm') {
        result = await polymarketEngine.trade({ evmPrivateKey: pk, tokenId: flags['token-id'], side: flags.side, amountUsd: Number(flags.amount), maxPrice: Number(flags['max-price']) });
      } else {
        console.error('usage: vineyard trade <id> --engine <hl|pm> ...'); process.exitCode = 2; break;
      }
      console.log(JSON.stringify(result, null, 2));
      break;
    }
    case 'redeem': {
      const [id] = rest;
      const spawn = findSpawn(id);
      const { resolveEvmPrivateKey } = await import('../core/wallet.mjs');
      const pk = resolveEvmPrivateKey(id);
      const result = await polymarketEngine.redeem({ evmPrivateKey: pk, depositWallet: spawn?.polymarketDepositWallet });
      console.log(JSON.stringify(result, null, 2));
      break;
    }
    case 'dashboard': {
      console.log('Web App UI is a separate follow-up (spec TODO item G) — run `npm run api` for the REST surface for now.');
      break;
    }
```

- [ ] **Step 2: Fix the `DATA_DIR` construction (Step 1's inline `require` doesn't work in an ESM file) — replace with a clean top-level helper**

Replace the `DATA_DIR` line added in Step 1:
```javascript
const DATA_DIR = process.env.VINEYARD_DATA_DIR || (process.env.VINEYARD_HOME
  ? require('node:path').join(process.env.VINEYARD_HOME, '..', 'data')
  : 'data');
```
with (add `import path from 'node:path';` near the top if not already present):
```javascript
const DATA_DIR = process.env.VINEYARD_DATA_DIR || path.resolve('data');
```

- [ ] **Step 3: Smoke-test `fund`/`run`/`status` against a scratch environment (no real chain calls — expect clean fail-closed skips since no real funded key exists)**

```bash
cd ~/vineyard
export VINEYARD_HOME=/tmp/vy-smoke-verbs
export VINEYARD_DATA_DIR=/tmp/vy-smoke-verbs-data
ID=$(node cli/index.mjs spawn | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.parse(d).id))")
node cli/index.mjs run "$ID"
node cli/index.mjs status "$ID"
rm -rf /tmp/vy-smoke-verbs /tmp/vy-smoke-verbs-data
```

Expected: `run` prints a ledger line JSON (likely `{"engine":"yield","status":"skip"|"error", ...}` since the spawned wallet has zero ETH for gas — a real, honest outcome, not a fabricated success); `status` prints the spawn row + `realized_pnl_usdc: 0` + the ledger array.

- [ ] **Step 4: Add the remaining routes to `api/server.mjs`**

```javascript
// add near the top, alongside the existing imports
import { updateSpawn } from '../core/registry.mjs';
import { runOnce } from '../core/loop.mjs';
import { readLedger, realizedPnl } from '../core/ledger.mjs';
import { resolveEvmPrivateKey, instanceDir } from '../core/wallet.mjs';
import * as yieldEngine from '../engines/yield.mjs';
import * as polymarketEngine from '../engines/polymarket.mjs';
import * as hyperliquidEngine from '../engines/hyperliquid.mjs';
import * as solanaEngine from '../engines/solana.mjs';

const ENGINES = { yield: yieldEngine, solana: solanaEngine, polymarket: polymarketEngine };
const DATA_DIR = process.env.VINEYARD_DATA_DIR || 'data';
```

Add routes (before the `app.listen(...)` block):
```javascript
app.post('/fund', async (req, res) => {
  const { id, amount, sourceKey } = req.body || {};
  const pk = resolveEvmPrivateKey(id);
  if (!pk) return res.status(404).json({ error: `no wallet for id ${id}` });
  const result = await polymarketEngine.fund({ evmPrivateKey: pk, sourceKey, fundUsd: Number(amount || 2) });
  if (result.registered) updateSpawn(id, { polymarketDepositWallet: result.deposit_wallet });
  res.json(result);
});

app.post('/run', async (req, res) => {
  const { id, engine } = req.body || {};
  const line = await runOnce({ id, dataDir: DATA_DIR, engines: ENGINES, candidates: engine ? [engine] : undefined });
  res.json(line);
});

app.get('/status/:id/full', (req, res) => {
  const spawn = findSpawn(req.params.id);
  if (!spawn) return res.status(404).json({ error: 'unknown id' });
  res.json({ ...spawn, realized_pnl_usdc: realizedPnl(req.params.id, DATA_DIR), ledger: readLedger(req.params.id, DATA_DIR) });
});

app.post('/trade', async (req, res) => {
  const { id, engine, ...params } = req.body || {};
  const pk = resolveEvmPrivateKey(id);
  let result;
  if (engine === 'hl') {
    result = await hyperliquidEngine.open({ ...params, evmPrivateKey: pk });
  } else if (engine === 'pm') {
    result = await polymarketEngine.trade({ evmPrivateKey: pk, tokenId: params.tokenId, side: params.side, amountUsd: params.amountUsd, maxPrice: params.maxPrice });
  } else {
    return res.status(400).json({ error: 'engine must be hl or pm' });
  }
  res.json(result);
});

app.post('/redeem', async (req, res) => {
  const { id } = req.body || {};
  const spawn = findSpawn(id);
  const pk = resolveEvmPrivateKey(id);
  const result = await polymarketEngine.redeem({ evmPrivateKey: pk, depositWallet: spawn?.polymarketDepositWallet });
  res.json(result);
});
```

Note: `findSpawn` is already imported in `api/server.mjs` from Task 6 — no duplicate import needed.

- [ ] **Step 5: Smoke-test the new API routes with real HTTP calls (scratch env, expect fail-closed skip since unfunded)**

```bash
cd ~/vineyard
VINEYARD_HOME=/tmp/vy-smoke-api2 VINEYARD_DATA_DIR=/tmp/vy-smoke-api2-data PORT=3998 node api/server.mjs &
API_PID=$!
sleep 1
ID=$(curl -s -X POST http://localhost:3998/spawn -d '{}' -H 'Content-Type: application/json' | node -pe 'JSON.parse(require("fs").readFileSync(0)).id' 2>/dev/null || curl -s -X POST http://localhost:3998/spawn -d '{}' -H 'Content-Type: application/json' | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:3998/run -H 'Content-Type: application/json' -d "{\"id\":\"$ID\"}"
kill $API_PID
rm -rf /tmp/vy-smoke-api2 /tmp/vy-smoke-api2-data
```

Expected: `/run` returns a ledger-line JSON object with `engine` + `status` fields (an honest skip/error given an unfunded wallet — never a fabricated success).

- [ ] **Step 6: Commit**

```bash
cd ~/vineyard
git add cli/index.mjs api/server.mjs
git commit -m "feat(cli,api): fund/run/status/trade/redeem verbs wired to core/loop + all 4 engines"
```

---

### Task 16: `llms.txt` + `openapi.json`

**Files:**
- Create: `~/vineyard/llms.txt`
- Create: `~/vineyard/openapi.json`

- [ ] **Step 1: Write `llms.txt`**

```markdown
# vineyard

> AI financial-independence CLI — spawn a self-funded AI that owns its own wallet and earns its own
> money across 4 on-chain engines (Polymarket, yield, Hyperliquid, Solana), with no human and no
> Claude in the loop after a one-time seed. CLI + REST API + this file are the machine-readable
> surface — an agent can spawn/fund/run/monitor instances entirely programmatically. No MCP: this
> CLI/API pair already gives an agent a machine-readable path.

## Commands (CLI and equivalent HTTP verb — identical semantics)

- `vineyard spawn [--fund N] [--engine pm|yield|hl|sol]` / `POST /spawn` — create an instance: its own
  isolated EVM + Solana wallet, registered in spawns.json. Returns `{id, evm, solana, fund, engine, created}`.
- `vineyard fund <id> <amount> [--source-key <key>]` / `POST /fund {id, amount, sourceKey}` — register +
  fund the instance's Polymarket deposit wallet through the bridge onramp. `sourceKey` (env `SOURCE_KEY`)
  must be an ALREADY-REGISTERED wallet's key for a brand-new deployment's very first registration.
- `vineyard run <id> [--engine <name>]` / `POST /run {id, engine}` — one pass of the automatic earn loop
  (rotates among yield/solana/polymarket-redeem unless `--engine` pins one). Returns one ledger line.
- `vineyard status <id>` / `GET /status/:id/full` — wallet addresses + realized P&L + full ledger.
- `vineyard list` / `GET /list` — every spawned instance's public metadata (never key material).
- `vineyard trade <id> --engine <hl|pm> ...` / `POST /trade {id, engine, ...}` — one manual, explicit
  trade decision (side/size/params supplied by the caller — this CLI/API never picks a side itself).
- `vineyard redeem <id>` / `POST /redeem {id}` — collect resolved Polymarket winnings.

## Machine-readable references

- Full OpenAPI spec: `/openapi.json` (same host as the REST API).
- Design spec: https://github.com/<org>/vineyard/blob/main/docs/design-spec.md (mirrors the source
  design doc this repo was built from).
- Source: https://github.com/<org>/vineyard (MIT license).

## Notes for an agent driving this repo

- Every `run`/`trade`/`redeem` call is a REAL pass against real on-chain state — there is no dry-run
  mode. A "skip" or "wait" result is a valid, honest outcome (e.g. an unfunded wallet, or no trading
  edge this pass), never fabricated.
- `spawn` never returns private key material over HTTP or in `list`/`status` — only addresses.
- The very first `fund` on a brand-new deployment needs `sourceKey` from an already-registered
  Polymarket wallet (chicken-and-egg bootstrap — see README "First-time setup").
```

- [ ] **Step 2: Write `openapi.json`**

```json
{
  "openapi": "3.0.3",
  "info": { "title": "vineyard", "version": "0.1.0", "description": "AI financial-independence CLI/API — spawn+fund+run+monitor self-funded AI instances." },
  "paths": {
    "/spawn": {
      "post": {
        "summary": "Create a new instance with its own isolated EVM+Solana wallet",
        "requestBody": { "content": { "application/json": { "schema": { "type": "object", "properties": { "id": { "type": "string" }, "fund": { "type": "number" }, "engine": { "type": "string" } } } } } },
        "responses": { "201": { "description": "spawned", "content": { "application/json": { "schema": { "$ref": "#/components/schemas/Spawn" } } } } }
      }
    },
    "/fund": {
      "post": {
        "summary": "Register + fund the instance's Polymarket deposit wallet via the bridge onramp",
        "requestBody": { "content": { "application/json": { "schema": { "type": "object", "required": ["id"], "properties": { "id": { "type": "string" }, "amount": { "type": "number" }, "sourceKey": { "type": "string" } } } } } },
        "responses": { "200": { "description": "fund result" } }
      }
    },
    "/run": {
      "post": {
        "summary": "One pass of the automatic earn loop",
        "requestBody": { "content": { "application/json": { "schema": { "type": "object", "required": ["id"], "properties": { "id": { "type": "string" }, "engine": { "type": "string" } } } } } },
        "responses": { "200": { "description": "one ledger line" } }
      }
    },
    "/status/{id}/full": {
      "get": {
        "summary": "Wallet addresses + realized P&L + full ledger for one instance",
        "parameters": [{ "name": "id", "in": "path", "required": true, "schema": { "type": "string" } }],
        "responses": { "200": { "description": "status" }, "404": { "description": "unknown id" } }
      }
    },
    "/list": {
      "get": { "summary": "All spawned instances (public metadata only)", "responses": { "200": { "description": "array of Spawn" } } }
    },
    "/trade": {
      "post": {
        "summary": "One manual, explicit trade decision (hl or pm engine)",
        "requestBody": { "content": { "application/json": { "schema": { "type": "object", "required": ["id", "engine"], "properties": { "id": { "type": "string" }, "engine": { "type": "string", "enum": ["hl", "pm"] } } } } } },
        "responses": { "200": { "description": "trade result" } }
      }
    },
    "/redeem": {
      "post": {
        "summary": "Collect resolved Polymarket winnings",
        "requestBody": { "content": { "application/json": { "schema": { "type": "object", "required": ["id"], "properties": { "id": { "type": "string" } } } } } },
        "responses": { "200": { "description": "array of redeemed conditions" } }
      }
    }
  },
  "components": {
    "schemas": {
      "Spawn": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "evm": { "type": "string" },
          "solana": { "type": "string" },
          "fund": { "type": "number" },
          "engine": { "type": ["string", "null"] },
          "created": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

- [ ] **Step 3: Validate `openapi.json` is well-formed JSON**

Run: `cd ~/vineyard && node -e "JSON.parse(require('fs').readFileSync('openapi.json','utf8')); console.log('valid JSON')"`
Expected: `valid JSON`

- [ ] **Step 4: Commit**

```bash
cd ~/vineyard
git add llms.txt openapi.json
git commit -m "docs: llms.txt + openapi.json — zero-human-click agent path (spec TODO H)"
```

---

### Task 17: `README.md` — one-command quickstart

**Files:**
- Create: `~/vineyard/README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# vineyard

AI financial-independence CLI. `git clone` + one command → spawn a self-funded AI: it owns its own
wallet and earns its own money across 4 on-chain engines (Polymarket, yield, Hyperliquid, Solana),
with no human and no Claude in the loop after a one-time seed. Interface = CLI + REST API + `llms.txt`
(machine-readable — any agent can drive this programmatically). No MCP needed.

## Quickstart (from a clean clone)

```bash
git clone https://github.com/<org>/vineyard && cd vineyard
npm install
python3 -m venv engines/python/.venv
engines/python/.venv/bin/pip install -r engines/python/requirements.txt

node cli/index.mjs spawn --fund 10        # creates an instance, prints its own EVM+Solana address + id
node cli/index.mjs run <id>                # one pass of the automatic earn loop
node cli/index.mjs status <id>             # wallet + realized P&L + ledger
```

Same actions over HTTP (for another agent): `npm run api` then `POST /spawn`, `POST /run`,
`GET /status/:id/full`. Full contract: `llms.txt` + `openapi.json`.

## First-time setup — the one human touch-point

1. Run `vineyard spawn --fund <amount>` — this prints the instance's own EVM address. Send USDC there.
2. Polymarket registration needs `--source-key` (env `SOURCE_KEY`) from an ALREADY-REGISTERED
   Polymarket wallet for the very first bootstrap (a brand-new deployment has no prior registered
   wallet to draw from — this is the one human-provided seed the architecture accounts for). Onboard
   your own wallet once at polymarket.com, then pass its key: `vineyard fund <id> 5 --source-key 0x...`.
3. The Hyperliquid engine needs its own funded account (USDC via the Arbitrum bridge — see
   `engines/python/hyperliquid/hl.py`'s docstring).
4. The Solana engine needs `franklin-trading setup solana` run once per instance (the CLI does this
   automatically the first time `vineyard run <id> --engine solana` is called) and funding the address
   it prints.

## Money-safety invariants

- Per-instance key isolation: every spawned instance has its own EVM+Solana wallet under
  `<VINEYARD_HOME>/instances/<id>/`; the resolver fails closed (returns null, never a foreign key) for
  any id it hasn't generated a wallet for.
- Never a raw-deployed Polymarket deposit wallet or raw pUSD transfer — always through the bridge
  Collateral Onramp (`engines/python/polymarket/fund_via_bridge.py`).
- On-chain-verified earnings only — `core/ledger.mjs` records realized, tx-verified P&L, never paper.
- No dry run — every `run`/`trade`/`redeem` is a real pass; a `skip`/`wait` result is honest, not fake.

## Architecture

`cli/` + `api/` (same verbs) → `core/` (wallet isolation, spawn registry, ledger, engine picker, loop)
→ `engines/` (thin Node wrappers shelling out to the original, byte-for-byte anicca Python/shell
scripts under `engines/python/` and `engines/shell/` — the proven money-safety logic is never
reimplemented, only invoked). See `docs/design-spec.md` for the full design.

## License

MIT.
```

- [ ] **Step 2: Verify the quickstart really works from a genuinely clean clone (not the working copy)**

```bash
rm -rf /tmp/vy-clean-clone
git clone ~/vineyard /tmp/vy-clean-clone
cd /tmp/vy-clean-clone
npm install
python3 -m venv engines/python/.venv
engines/python/.venv/bin/pip install -r engines/python/requirements.txt
VINEYARD_HOME=/tmp/vy-clean-home node cli/index.mjs spawn --fund 10
rm -rf /tmp/vy-clean-clone /tmp/vy-clean-home
```

Expected: `npm install` succeeds, the venv installs the 6 pinned packages without error, and `spawn`
prints a real JSON row with a `0x...` EVM address and a base58 Solana address — proving the README's
own quickstart works from a clone that has none of the working tree's untracked scratch state.

- [ ] **Step 3: Commit**

```bash
cd ~/vineyard
git add README.md
git commit -m "docs: README one-command quickstart, verified from a clean clone (spec TODO I)"
```

---

### Task 18: Final integration check

**Files:** none new — this task only runs verification across everything built in Tasks 1-17.

- [ ] **Step 1: Run the full automated test suite**

```bash
cd ~/vineyard
node --test core/*.test.mjs engines/*.test.mjs
```

Expected: every test file from Tasks 2-14 passes — `core/wallet.test.mjs` (9), `core/registry.test.mjs` (5),
`core/ledger.test.mjs` (5), `core/brain.test.mjs` (4), `core/loop.test.mjs` (3), `engines/cost-basis.test.mjs` (5),
`engines/yield.test.mjs` (1), `engines/polymarket.test.mjs` (9), `engines/hyperliquid.test.mjs` (5),
`engines/solana.test.mjs` (3) — 49 tests total, 0 failures.

- [ ] **Step 2: Run the copied Python pure-function tests**

```bash
cd ~/vineyard/engines/python/polymarket
../.venv/bin/python3 test_redeem.py
```

Expected: all `TestDedupeRedeemableConditions`/`TestClassifyMarketType`/etc. tests PASS.

- [ ] **Step 3: Re-run the README clean-clone quickstart one more time (Task 17 Step 2) as the final gate**

```bash
rm -rf /tmp/vy-final-check
git clone ~/vineyard /tmp/vy-final-check
cd /tmp/vy-final-check && npm install
python3 -m venv engines/python/.venv && engines/python/.venv/bin/pip install -r engines/python/requirements.txt
VINEYARD_HOME=/tmp/vy-final-home node cli/index.mjs spawn --fund 5
VINEYARD_HOME=/tmp/vy-final-home VINEYARD_DATA_DIR=/tmp/vy-final-data node cli/index.mjs list
rm -rf /tmp/vy-final-check /tmp/vy-final-home /tmp/vy-final-data
```

Expected: clean success end-to-end, matching spec DONE criterion §9.6 ("README one-command quickstart
works from a clean clone").

- [ ] **Step 4: Confirm `git log` shows one commit per task, nothing uncommitted**

```bash
cd ~/vineyard
git status --porcelain
git log --oneline
```

Expected: `git status --porcelain` is empty; `git log` shows 17 commits (Tasks 1-17, one each).

- [ ] **Step 5: Tag the MVP**

```bash
cd ~/vineyard
git tag -a v0.1.0-mvp -m "Vineyard MVP: spec TODO B-I complete (scaffold, spawn, fund, all 4 engines, run loop, llms.txt+API+OpenAPI, README)"
```

- [ ] **Step 6: What's explicitly NOT done here (by design — see plan header)**

Spec TODO items **G** (Web App UI — needs its own `gpt-tasteskill` design pass + browser-verify per
HARD RULE 0.38, a separate follow-up plan), **J** (hyperframes demo video — needs real ledger data from
a live funded run, which only exists after the manual verification steps in Tasks 8/9/10/11/12 are
actually executed against funded wallets), and **K** (submission-doc copy pass) remain open, exactly as
scoped at the top of this plan. **L** (VCSDD wrapping) is the verification method that should have been
applied continuously while executing Tasks 1-17 (fresh-context adversary review per task, per HARD RULE
0.37/0.40), not a standalone task to check off here.

---

## Self-Review

**1. Spec coverage** — every TODO item in scope is covered:
- **B** (scaffold) → Task 1.
- **C** (spawn/wallet) → Tasks 2, 3 (generation + fail-closed isolation), 6 (CLI/API `spawn`).
- **D** (fund/Polymarket bridge) → Task 8 (`fund_via_bridge.py` wrapper), Task 15 (`fund` CLI/API verb).
- **E** (wire all 4 engines) → Task 7 (yield), Tasks 8-10 (polymarket fund/trade/redeem), Task 11
  (hyperliquid), Task 12 (solana).
- **F** (run loop) → Task 13 (brain/picker), Task 14 (loop.mjs wake→pick→earn→ledger), Task 15 (`run` verb).
- **H** (llms.txt + API + OpenAPI) → Task 16.
- **I** (README quickstart) → Task 17, verified from a genuinely clean clone twice (Task 17 Step 2, Task 18 Step 3).
- Money-safety invariants (spec §8) → per-instance isolation tests (Task 3), bridge-onramp-only funding
  (Task 8, D8 documented), on-chain-verified ledger only (Task 5, `ledger.mjs`'s `net_usdc`/`earn_usdc`-`cost_usdc`
  shape), no dry-run (every engine task's Step "Manual (non-automated) verification note").
- G/J/K/L exclusions are stated up front (plan header) and re-confirmed at Task 18 Step 6 — no silent scope creep.

**2. Placeholder scan** — searched for "TBD"/"implement later"/"add error handling"/"similar to Task N"/
bare prose-only steps: none found. Every code-touching step above shows the actual code (including the
4 precise `redeem.py` edits in Task 10, shown as literal before/after blocks rather than "adapt as needed").
Every engine wrapper task's "manual verification" step is explicitly labeled as such (not disguised as an
automated-test pass) per HARD RULE 0.24 — this was a deliberate late addition after the first draft
conflated "unit-tested the parser" with "verified the real trade," which would have been a HARD RULE 0.24
violation if left ambiguous.

**3. Type/signature consistency across tasks** — checked and one inconsistency was found and fixed inline
before finalizing this plan: Task 14's original draft had `core/loop.mjs` importing `engines/polymarket.mjs`'s
`redeem()` directly by module import; Task 15 needed the SAME `runOnce` to be callable from both `cli/index.mjs`
and `api/server.mjs` without re-instantiating engine modules differently in each — resolved by making `engines`
a dependency-injected parameter of `runOnce`/`runLoop` (Task 14), with both `cli/index.mjs` and `api/server.mjs`
(Task 15) constructing the SAME `ENGINES = { yield, solana, polymarket }` object shape and passing it through.
Also verified: `resolveEvmPrivateKey(id, env)` / `resolveSolanaSecret(id, env)` / `instanceDir(id, env)` signatures
(Task 2) are used identically in Tasks 6, 12, 14, 15 (positional `id` first, `env` second, both optional-defaulted
to `process.env`) — no drift. `appendLedger(id, event, dataDir)` (Task 5) is called with that exact argument order
in Task 14's `runOnce` and nowhere else, so no cross-task signature mismatch exists. `parseFundOutput`/
`parseTradeOutput`/`parseRedeemOutput`/`parseHlOutput` (Tasks 8-11) are each exported and unit-tested against a
real-format fixture in the SAME file/task that defines them, and consumed only inside that same file's `fund`/
`trade`/`redeem`/`account`/`market`/`open`/`close` functions — no other task calls them directly, so there is no
opportunity for a signature drift to go unnoticed.

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-05-vineyard-mvp.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**

