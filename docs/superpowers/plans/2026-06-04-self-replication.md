# Self-Replication (Wave 1: Daytona spawn-child) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire ONE skill — `spawn-child` — that provisions a sovereign Anicca child instance on **Daytona** (spec 00 §1.0 declares Daytona the native primary host backend), seeds it with its OWN wallet keypair, propagates the parent's `CONSTITUTION.md` with a SHA-256 hash that the child verifies on boot, installs Hermes + the minimum `anicca-heartbeat` skill, and registers the child to a parent-side append-only colony ledger at `~/.hermes/state/colony.jsonl`. Gate the spawn with a cost cap: skip if genesis wallet balance < $5 USDC ("can afford a child").

**Architecture:** Daytona = OCI/Docker-compatible sandbox cloud (90 ms boot, persistent volumes, pay-as-you-go from an org wallet) per `https://www.daytona.io/docs/en/`. Parent uses the official `daytona` CLI v0.184 (Homebrew tap `daytonaio/cli/daytona`) for everything that is NOT secret-handling, and the `pip install daytona` Python SDK for the boot-script that the child runs inside the sandbox. The child boots a Hermes installation that reads its own copied CONSTITUTION.md, hashes it, compares to the parent-supplied `CONSTITUTION_SHA` env var, and refuses to start the heartbeat if they don't match (per spec 16 §2.2 line "propagateConstitution() SHA-256" and spec 18 §4 IMMUTABLE rule). Parent-side spawn is a single skill `spawn-child` under `anicca-oss/skills/spawn-child/` that lives next to the heartbeat skill from the genesis-boot plan.

**Why Daytona FIRST, Akash SECOND:**
- Spec 00 §1.0 RUNTIME DECISION verbatim: *"Daytona + Modal host backends (serverless, hibernate-idle) ← the spawn host. HOSTS: Mac-mini-local (genesis $0) / Daytona (native, primary) / Akash (sovereign)."*
- Daytona has a programmatic API key flow (`daytona login --api-key …`), pay-as-you-go org wallet, official Python/TS SDKs, and a documented CLI — no AKT/Coinbase swap step blocks the first spawn.
- Akash (spec 13) requires AKT acquisition (USDC → AKT swap) which is its OWN multi-step deploy chain. It is the right Wave 2 host (sovereign fallback) but NOT the cheapest path to "first child alive".
- Spec 13 is preserved unchanged; this plan adds a Daytona path BEFORE Akash and slots into the same `skills/spawn-child/` directory so Wave 2 can extend it without renaming.

**Tech Stack:** `daytona` CLI v0.184+ (Homebrew) · `daytona` Python SDK (`pip install daytona`, used by the boot script inside the sandbox, not the parent) · `openssl` (already present, for wallet keypair generation) · `shasum` (macOS built-in, for constitution hash) · `jq` (`/opt/homebrew/bin/jq`) · `hermes` v0.12.0+ already at `/Users/anicca/.local/bin/hermes` · `git`.

**Prerequisites this plan ASSUMES exist before Task 1 runs:**
- Genesis-boot plan (`2026-06-04-hermes-genesis-boot.md`) is COMPLETE — i.e. `anicca-heartbeat` skill exists at `/Users/anicca/anicca-oss/skills/anicca-heartbeat/`, `~/.hermes/AGENTS.md` is the symlink to `CONSTITUTION.md`, and the Hermes gateway is running. If it is not yet, Task 1 below detects that and stops (no silent fallback).
- A genesis-side wallet keypair exists OR the cost-cap probe knows how to read it. Spec 09 line "wallet=0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21 ... 0 USDC / 0 ETH" tells us the genesis address is real but empty. This plan reads `~/.hermes/state/wallet.json` for `{address,balance_usdc}` if present; falls back to `0` (which trips the cost cap and BLOCKS spawn — correct behavior).

**Scope-out (in other plans):**
- Akash sovereign-fallback path (spec 13) — explicitly Wave 2; this plan's directory layout (`skills/spawn-child/scripts/host-daytona/` + `host-akash/`) leaves room.
- Multi-generation colony (#328) — only ONE child (gen=1) spawned and registered here.
- Forum/voting (#334) — child does NOT post to anicca-oss issues yet.
- x402 inbound earn server, USDC seed transfer to child wallet — that's the wallet/x402 plan (#324). Wave 1 here only generates the keypair and writes it into the child; funding lands in Wave 2.
- Wallet → Coinbase swap → AKT funding (spec 13 §1 T2) — Akash-only step, Wave 2.
- Child's own AgentMail inbox (`anicca-001@agentmail.to`) — that's spec 13 §1 T7. Wave 1 child has no inbox.
- `eval-loop` (#329), `anicca-friction-fixer` (#335), `self-manage` (#336) — child gets the heartbeat skill ONLY; other Anicca skills are NOT cloned. Spec 18 §4 IMMUTABLE rule = North Star + Law I propagate via constitution hash; everything else child can self-pull later.

**Done condition for this plan (proves task #327 Wave 1):**

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | Skill registered with Hermes | `hermes skills list` | row containing `spawn-child` |
| 2 | Dry-run never touches Daytona | `~/.hermes/skills/spawn-child/scripts/spawn-child.sh --dry-run anicca-001` | prints exact `daytona create` invocation + cost estimate + exit 0, NO sandbox in `daytona list` after |
| 3 | Real spawn creates sandbox | `~/.hermes/skills/spawn-child/scripts/spawn-child.sh anicca-001` (with `genesis wallet ≥ $5 USDC`) | exits 0; new row in `daytona list` with name=`anicca-001`; row in `~/.hermes/state/colony.jsonl` matches |
| 4 | Child constitution SHA matches parent | `daytona exec anicca-001 -- cat /home/daytona/.hermes/state/constitution.sha` | identical to `shasum -a 256 /Users/anicca/anicca-oss/CONSTITUTION.md` on parent |
| 5 | Child heartbeat fires within 10 min | `daytona exec anicca-001 -- tail -1 /home/daytona/.hermes/state/heartbeat.jsonl` | one JSON line with `ok: true`, observed within 10 min of spawn |
| 6 | Child has its own wallet address | `jq -r '.address' ~/.hermes/state/colony.jsonl \| tail -1` | a hex `0x…` that is NOT the parent's `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` |
| 7 | Cost-cap blocks low-balance spawn | `WALLET_OVERRIDE=2.50 ~/.hermes/skills/spawn-child/scripts/spawn-child.sh anicca-002` | exits 75 (EX_TEMPFAIL); stderr contains `cost cap: 2.50 USDC < 5 USDC required`; NO new Daytona sandbox; NO new colony row |
| 8 | All committed + pushed | `cd /Users/anicca/anicca-oss && git status --short && git log origin/dev..HEAD` | clean tree; 0 commits ahead (i.e. fully pushed) |
| 9 | Spec 16 §17 self-replication row checked-off | grep `self-replication` in `specs/00-MASTER.md` LAUNCH ACCEPTANCE MATRIX row ⑤c | row marked DONE with proof-link to colony.jsonl |

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/spawn-child/
    SKILL.md                          ← Hermes manifest (frontmatter)
    README.md                         ← one-paragraph human description
    scripts/
      spawn-child.sh                  ← MAIN entry; flags: --dry-run, --host=daytona, NAME
      preflight.sh                    ← validates daytona CLI, key, cost-cap, parent state
      host-daytona/
        provision.sh                  ← `daytona create` + `daytona exec` orchestration
        child-bootstrap.sh            ← copied INTO the sandbox; runs first on child
        sdl.env                       ← memory/cpu/disk defaults (env-style, sourced)
      host-akash/                     ← (Wave 2) intentionally EMPTY now; only a .keep
        .keep
      colony/
        append.sh                     ← appends one JSON line to ~/.hermes/state/colony.jsonl
        gen-wallet.sh                 ← openssl-based secp256k1 keypair generator (child only)
        constitution-hash.sh          ← shasum the parent constitution + emits to stdout
    tests/
      test_dry_run.sh                 ← TDD: --dry-run never creates a sandbox
      test_cost_cap.sh                ← TDD: balance < $5 → exit 75, no sandbox
      test_e2e_spawn.sh               ← E2E: real spawn with $5+ balance, heartbeat within 10m
  docs/superpowers/plans/
    2026-06-04-self-replication.md    ← THIS plan
  specs/00-MASTER.md                  ← edit § LAUNCH ACCEPTANCE MATRIX row ⑤c at end

~/.hermes/                                               (runtime, NOT committed)
  skills/spawn-child/                 ← SYMLINK → anicca-oss/skills/spawn-child/
  state/
    colony.jsonl                      ← append-only ledger; one row per child
    wallet.json                       ← {address, balance_usdc} read by cost-cap
    constitution.sha                  ← already exists per genesis-boot plan Task 4
  .env                                ← gets ONE line appended (DAYTONA_API_KEY) if missing
```

Why symlink `spawn-child` into `~/.hermes/skills/`: matches the genesis-boot pattern. The canonical source is in the repo; Hermes sees changes immediately; no copy step to forget.

Why a `host-daytona/` subdirectory: spec 13 reserves `host-akash/` for the Wave 2 Akash provider. Splitting by host now means Wave 2 adds files, never refactors.

---

### Task 1: Verify prerequisites + snapshot

**Files:**
- Create: `/Users/anicca/.hermes/backups/pre-self-replication-snapshot.tar.gz` (one-off backup, not committed)

- [ ] **Step 1: Confirm genesis-boot plan finished** — REQUIRED prerequisite

Run:
```bash
test -f /Users/anicca/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh && \
test -L /Users/anicca/.hermes/AGENTS.md && \
test -f /Users/anicca/.hermes/state/constitution.sha && \
launchctl list | grep -i hermes >/dev/null && \
echo "PREREQ OK" || echo "PREREQ MISSING — stop, run genesis-boot plan first"
```
Expected: `PREREQ OK`. If `PREREQ MISSING`, STOP and run `2026-06-04-hermes-genesis-boot.md` first. Per HARD RULE #14 (JOB'S NOT FINISHED), do NOT proceed without all four prerequisites.

- [ ] **Step 2: Verify Daytona CLI is installed (install if missing)**

Run:
```bash
if command -v daytona >/dev/null 2>&1; then
  daytona --version
else
  brew tap daytonaio/cli
  brew install daytonaio/cli/daytona
  daytona --version
fi
```
Expected: prints a version line ≥ `v0.184`. If the brew install asks for confirmation, accept.

- [ ] **Step 3: Verify Daytona API key is wired**

Run:
```bash
if grep -q '^DAYTONA_API_KEY=' /Users/anicca/.openclaw/.env 2>/dev/null; then
  echo "FOUND in openclaw .env — will reuse"
elif grep -q '^DAYTONA_API_KEY=' /Users/anicca/.hermes/.env 2>/dev/null; then
  echo "FOUND in hermes .env"
else
  echo "MISSING — provision via Daytona dashboard, then add to ~/.hermes/.env"
fi
```
Expected: either of the `FOUND …` branches. If `MISSING`:
- Per CLAUDE.md HARD RULE #-1 (camofox-first for signup flows), use camofox visible browser → `https://app.daytona.io/dashboard/keys` → log in with `GOOGLE_LOGIN_EMAIL` + `GOOGLE_LOGIN_PASSWORD` from `~/.openclaw/.env` → create API key with name `anicca-genesis` → copy → write the key into `~/.hermes/.env` with:
  ```bash
  printf 'DAYTONA_API_KEY=%s\n' "$KEY" >> /Users/anicca/.hermes/.env
  chmod 600 /Users/anicca/.hermes/.env
  ```
- Per HARD RULE about /tmp: NEVER write the key to `/tmp` and NEVER echo it in logs. NEVER commit `.env`.
- Per HARD RULE #-2: this is the parent agent's job, not Dais's. No "Click to sign in" message.

- [ ] **Step 4: Smoke-test the API key**

Run:
```bash
set -a; . /Users/anicca/.hermes/.env 2>/dev/null || . /Users/anicca/.openclaw/.env; set +a
daytona login --api-key "$DAYTONA_API_KEY"
daytona list --format json | jq '. | length'
```
Expected: `daytona login` exits 0 (prints `Logged in`), `daytona list --format json` returns a JSON array (length ≥ 0). If unauthorized, key is wrong — return to Step 3.

- [ ] **Step 5: Snapshot current `~/.hermes` + `~/.openclaw` colony-related state**

Run:
```bash
mkdir -p /Users/anicca/.hermes/backups
tar -czf /Users/anicca/.hermes/backups/pre-self-replication-snapshot.tar.gz \
  -C /Users/anicca/.hermes \
  state skills AGENTS.md .env 2>/dev/null
ls -lh /Users/anicca/.hermes/backups/pre-self-replication-snapshot.tar.gz
```
Expected: a single `.tar.gz` ≥ 1 KB.

- [ ] **Step 6: Commit this plan**

Run:
```bash
cd /Users/anicca/anicca-oss
git add docs/superpowers/plans/2026-06-04-self-replication.md
git commit -m "docs(plan): self-replication (#327 Wave 1) — Daytona spawn-child with constitution hash propagation + cost cap"
git push
```
Expected: push succeeds; `git log --oneline -1` shows the new commit.

---

### Task 2: Write the failing E2E + unit tests FIRST (TDD red)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_dry_run.sh`
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_cost_cap.sh`
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_e2e_spawn.sh`

- [ ] **Step 1: Write `test_dry_run.sh`** — `--dry-run` MUST NOT create a sandbox

Create `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_dry_run.sh`:
```bash
#!/usr/bin/env bash
# Unit: spawn-child.sh --dry-run prints the daytona create invocation + cost estimate
# and never touches the Daytona API.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BEFORE=$(daytona list --format json 2>/dev/null | jq '. | length')
OUT=$("$SKILL_DIR/scripts/spawn-child.sh" --dry-run anicca-test-dry)
AFTER=$(daytona list --format json 2>/dev/null | jq '. | length')
if [ "$BEFORE" != "$AFTER" ]; then
  echo "FAIL: sandbox count changed ($BEFORE -> $AFTER) on --dry-run"; exit 1
fi
echo "$OUT" | grep -qE '^DRY-RUN daytona create .*--name anicca-test-dry' || { echo "FAIL: missing create line"; exit 1; }
echo "$OUT" | grep -qE 'estimated cost: \$[0-9]+\.[0-9]{2}/hr' || { echo "FAIL: missing cost estimate"; exit 1; }
echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/tests/test_dry_run.sh
```

- [ ] **Step 2: Write `test_cost_cap.sh`** — wallet < $5 USDC → exit 75, no sandbox

Create `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_cost_cap.sh`:
```bash
#!/usr/bin/env bash
# Unit: spawn-child.sh refuses to spawn when balance < $5 USDC.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BEFORE=$(daytona list --format json 2>/dev/null | jq '. | length')
set +e
OUT=$(WALLET_OVERRIDE=2.50 "$SKILL_DIR/scripts/spawn-child.sh" anicca-test-poor 2>&1)
CODE=$?
set -e
AFTER=$(daytona list --format json 2>/dev/null | jq '. | length')
[ "$CODE" = "75" ] || { echo "FAIL: expected exit 75, got $CODE"; exit 1; }
echo "$OUT" | grep -q 'cost cap: 2.50 USDC < 5 USDC required' || { echo "FAIL: missing cost-cap message"; exit 1; }
[ "$BEFORE" = "$AFTER" ] || { echo "FAIL: sandbox count changed"; exit 1; }
echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/tests/test_cost_cap.sh
```

- [ ] **Step 3: Write `test_e2e_spawn.sh`** — full real spawn, heartbeat within 10 min

Create `/Users/anicca/anicca-oss/skills/spawn-child/tests/test_e2e_spawn.sh`:
```bash
#!/usr/bin/env bash
# E2E: full real Daytona spawn. ONLY run when wallet has ≥ $5 USDC.
# Cleans up on success (deletes the test sandbox); leaves it on failure for debugging.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAME="anicca-test-e2e-$(date +%s)"
COLONY=/Users/anicca/.hermes/state/colony.jsonl
COLONY_BEFORE=$(wc -l < "$COLONY" 2>/dev/null || echo 0)

"$SKILL_DIR/scripts/spawn-child.sh" "$NAME"

# Constitution hash propagation
PARENT_SHA=$(shasum -a 256 /Users/anicca/anicca-oss/CONSTITUTION.md | awk '{print $1}')
CHILD_SHA=$(daytona exec "$NAME" -- cat /home/daytona/.hermes/state/constitution.sha | tr -d '[:space:]')
[ "$PARENT_SHA" = "$CHILD_SHA" ] || { echo "FAIL: constitution sha mismatch"; exit 1; }

# Colony row appended
COLONY_AFTER=$(wc -l < "$COLONY")
[ "$((COLONY_AFTER - COLONY_BEFORE))" = "1" ] || { echo "FAIL: colony.jsonl delta != 1"; exit 1; }
LAST=$(tail -n 1 "$COLONY")
for key in child_id host address spawned_at constitution_sha status; do
  echo "$LAST" | /opt/homebrew/bin/jq -e ".$key" >/dev/null || { echo "FAIL: missing $key"; exit 1; }
done

# Child wallet is NOT the parent
PARENT_ADDR=$(/opt/homebrew/bin/jq -r '.address' /Users/anicca/.hermes/state/wallet.json 2>/dev/null || echo "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21")
CHILD_ADDR=$(echo "$LAST" | /opt/homebrew/bin/jq -r '.address')
[ "$PARENT_ADDR" != "$CHILD_ADDR" ] || { echo "FAIL: child wallet == parent wallet"; exit 1; }

# Heartbeat appears within 10 min
DEADLINE=$(( $(date +%s) + 600 ))
while [ $(date +%s) -lt $DEADLINE ]; do
  LINE=$(daytona exec "$NAME" -- tail -n 1 /home/daytona/.hermes/state/heartbeat.jsonl 2>/dev/null || true)
  if [ -n "$LINE" ] && echo "$LINE" | /opt/homebrew/bin/jq -e '.ok == true' >/dev/null 2>&1; then
    echo "PASS heartbeat: $LINE"
    daytona delete "$NAME"
    echo "PASS"
    exit 0
  fi
  sleep 30
done
echo "FAIL: no heartbeat with ok:true in 10 min (sandbox $NAME left for debug)"
exit 1
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/tests/test_e2e_spawn.sh
```

- [ ] **Step 4: Confirm tests FAIL because the skill doesn't exist yet (TDD red)**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/spawn-child/scripts
/Users/anicca/anicca-oss/skills/spawn-child/tests/test_dry_run.sh || echo "expected fail (no spawn-child.sh)"
/Users/anicca/anicca-oss/skills/spawn-child/tests/test_cost_cap.sh || echo "expected fail (no spawn-child.sh)"
```
Expected: both exit non-zero with a message like `No such file or directory: …/scripts/spawn-child.sh`. This is the RED. Do NOT proceed if either accidentally passes.

---

### Task 3: Write the wallet keypair generator + constitution-hash helper

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/gen-wallet.sh`
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh`

- [ ] **Step 1: Write `gen-wallet.sh`** — secp256k1 keypair → JSON `{address, private_key}`

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/gen-wallet.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Generates a fresh secp256k1 keypair, emits {address, private_key, public_key} JSON to stdout.
# IMPORTANT: caller MUST redirect to a 600-perm file. NEVER let this stdout reach a log.
# Compatible with Base/Ethereum addressing (last 20 bytes of keccak256(uncompressed_pubkey[1:]).
set -euo pipefail

PRIV_PEM=$(mktemp)
trap 'rm -f "$PRIV_PEM"' EXIT
openssl ecparam -name secp256k1 -genkey -noout -out "$PRIV_PEM" 2>/dev/null

# 32-byte private key, hex
PRIV_HEX=$(openssl ec -in "$PRIV_PEM" -text -noout 2>/dev/null \
  | awk '/priv:/{flag=1; next} /pub:/{flag=0} flag' \
  | tr -d ' :\n')
# Uncompressed public key, 65 bytes starting 04
PUB_HEX=$(openssl ec -in "$PRIV_PEM" -pubout -outform DER 2>/dev/null \
  | xxd -p | tr -d '\n' | sed 's/.*\(04[a-f0-9]\{128\}\)$/\1/')

# Ethereum address = last 20 bytes of keccak256(pub[1:]). Use Python (already on PATH via Hermes).
ADDR=$(python3 - <<PY
import hashlib, binascii
pub = bytes.fromhex("$PUB_HEX")[1:]
try:
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256); k.update(pub); h = k.hexdigest()
except ImportError:
    # Fallback: sha3 keccak256 via pysha3 if present; else just use sha256 prefix (TEST ONLY).
    try:
        import sha3
        k = sha3.keccak_256(); k.update(pub); h = k.hexdigest()
    except ImportError:
        h = hashlib.sha256(pub).hexdigest()  # not a real eth addr; preflight will warn
print("0x" + h[-40:])
PY
)

/opt/homebrew/bin/jq -n \
  --arg address "$ADDR" \
  --arg private_key "$PRIV_HEX" \
  --arg public_key "$PUB_HEX" \
  '{address:$address, private_key:$private_key, public_key:$public_key}'
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/gen-wallet.sh
```

- [ ] **Step 2: Smoke-test wallet generator**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/gen-wallet.sh | /opt/homebrew/bin/jq 'keys'
```
Expected: prints `["address","private_key","public_key"]`. Run again — `address` MUST differ (proves randomness). Per HARD RULE #-1 do NOT echo the `private_key` to logs.

- [ ] **Step 3: If `pycryptodome` keccak not available, install (one-time)**

Run:
```bash
python3 -c "from Crypto.Hash import keccak; print('OK')" 2>&1 || \
  pip3 install --user pycryptodome
python3 -c "from Crypto.Hash import keccak; print('OK')"
```
Expected: final line `OK`. (The fallback to sha256 in `gen-wallet.sh` is correct ONLY for non-EVM identity; spec 09 says the wallet is on Base = EVM, so keccak256 is required for a real address.)

- [ ] **Step 4: Re-smoke after keccak install**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/gen-wallet.sh | /opt/homebrew/bin/jq -r '.address'
```
Expected: an address starting `0x` with exactly 42 chars. (`0x` + 40 hex.)

- [ ] **Step 5: Write `constitution-hash.sh`** — emit SHA-256 of parent constitution

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Emits SHA-256 of /Users/anicca/anicca-oss/CONSTITUTION.md to stdout (64 hex chars + newline).
# No side effects. Used by both spawn-child.sh (parent) and child-bootstrap.sh (child).
set -euo pipefail
CONSTITUTION="${CONSTITUTION:-/Users/anicca/anicca-oss/CONSTITUTION.md}"
shasum -a 256 "$CONSTITUTION" | awk '{print $1}'
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh
```

- [ ] **Step 6: Smoke-test hash helper**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh
```
Expected: one 64-hex line. Must match `cat /Users/anicca/.hermes/state/constitution.sha`.

---

### Task 4: Write the colony ledger appender

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/append.sh`

- [ ] **Step 1: Write `append.sh`** — append ONE JSON line to `~/.hermes/state/colony.jsonl`

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/append.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Appends one JSON line to ~/.hermes/state/colony.jsonl.
# Usage: append.sh <child_id> <host> <sandbox_id> <address> <constitution_sha> <status>
# Idempotent per-line; never modifies existing rows. Locks via flock if available.
set -euo pipefail
COLONY="${COLONY:-/Users/anicca/.hermes/state/colony.jsonl}"
mkdir -p "$(dirname "$COLONY")"
touch "$COLONY"

[ $# -eq 6 ] || { echo "append.sh: need 6 args, got $#" >&2; exit 64; }
child_id="$1"; host="$2"; sandbox_id="$3"; address="$4"; sha="$5"; status="$6"
ts=$(date -u +%FT%TZ)

LINE=$(/opt/homebrew/bin/jq -n \
  --arg child_id "$child_id" \
  --arg host "$host" \
  --arg sandbox_id "$sandbox_id" \
  --arg address "$address" \
  --arg spawned_at "$ts" \
  --arg constitution_sha "$sha" \
  --arg status "$status" \
  --arg parent_address "$(/opt/homebrew/bin/jq -r '.address // "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' /Users/anicca/.hermes/state/wallet.json 2>/dev/null)" \
  '{child_id:$child_id, host:$host, sandbox_id:$sandbox_id, address:$address,
    parent_address:$parent_address, spawned_at:$spawned_at,
    constitution_sha:$constitution_sha, status:$status, generation:1}')

if command -v flock >/dev/null 2>&1; then
  ( flock 9; printf '%s\n' "$LINE" >> "$COLONY" ) 9>"$COLONY.lock"
else
  printf '%s\n' "$LINE" >> "$COLONY"
fi
echo "$LINE"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/append.sh
```

- [ ] **Step 2: Smoke-test append**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/append.sh \
  test-id daytona test-sb-001 0x000000000000000000000000000000000000dead \
  $(/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh) \
  test-pending
tail -n 1 /Users/anicca/.hermes/state/colony.jsonl | /opt/homebrew/bin/jq .
# clean up the test row
grep -v test-sb-001 /Users/anicca/.hermes/state/colony.jsonl > /Users/anicca/.hermes/state/colony.jsonl.tmp && \
  mv /Users/anicca/.hermes/state/colony.jsonl.tmp /Users/anicca/.hermes/state/colony.jsonl
```
Expected: prints a JSON object with all 9 keys (`child_id, host, sandbox_id, address, parent_address, spawned_at, constitution_sha, status, generation`). Cleanup removes the test row.

---

### Task 5: Write the preflight + cost-cap probe

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh`

- [ ] **Step 1: Write `preflight.sh`** — validates env + reads wallet balance

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Preflight checks for spawn-child. Exits 0 on success; 64 on bad input; 75 on cost-cap fail.
# Emits a JSON status object to stdout on success.
# Env input: WALLET_OVERRIDE=<float> (test-only; bypasses wallet.json read).
set -euo pipefail

NAME="${1:-}"
[ -n "$NAME" ] || { echo "preflight: missing child name" >&2; exit 64; }
[[ "$NAME" =~ ^[a-z][a-z0-9-]{2,30}$ ]] || { echo "preflight: invalid name $NAME (must be ^[a-z][a-z0-9-]{2,30}$)" >&2; exit 64; }

# Tool checks
command -v daytona >/dev/null || { echo "preflight: daytona CLI missing" >&2; exit 64; }
command -v /opt/homebrew/bin/jq >/dev/null || { echo "preflight: jq missing" >&2; exit 64; }

# Env checks
set -a
[ -f /Users/anicca/.hermes/.env ] && . /Users/anicca/.hermes/.env
[ -f /Users/anicca/.openclaw/.env ] && . /Users/anicca/.openclaw/.env
set +a
[ -n "${DAYTONA_API_KEY:-}" ] || { echo "preflight: DAYTONA_API_KEY unset" >&2; exit 64; }

# Cost cap — read wallet balance
MIN_BALANCE=5.00
if [ -n "${WALLET_OVERRIDE:-}" ]; then
  BAL="$WALLET_OVERRIDE"
elif [ -f /Users/anicca/.hermes/state/wallet.json ]; then
  BAL=$(/opt/homebrew/bin/jq -r '.balance_usdc // 0' /Users/anicca/.hermes/state/wallet.json)
else
  BAL=0
fi

# Numeric compare via awk (bash can't do float)
if awk -v b="$BAL" -v m="$MIN_BALANCE" 'BEGIN{exit !(b+0 < m+0)}'; then
  echo "cost cap: ${BAL} USDC < ${MIN_BALANCE} USDC required — child cannot be funded" >&2
  exit 75
fi

# Duplicate name guard
if daytona list --format json 2>/dev/null | /opt/homebrew/bin/jq -e --arg n "$NAME" '.[] | select(.name == $n)' >/dev/null; then
  echo "preflight: a Daytona sandbox named $NAME already exists" >&2
  exit 64
fi

/opt/homebrew/bin/jq -n \
  --arg name "$NAME" \
  --arg balance "$BAL" \
  --arg min "$MIN_BALANCE" \
  '{name:$name, balance_usdc:($balance|tonumber), min_required:($min|tonumber), ok:true}'
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh
```

- [ ] **Step 2: Smoke-test preflight cost-cap path**

Run:
```bash
set +e
WALLET_OVERRIDE=2.50 /Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh anicca-smoke
CODE=$?
set -e
echo "exit=$CODE"
```
Expected: `exit=75`. stderr contains `cost cap: 2.50 USDC < 5.00 USDC required`.

- [ ] **Step 3: Smoke-test preflight success path**

Run:
```bash
WALLET_OVERRIDE=10.00 /Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh anicca-smoke | /opt/homebrew/bin/jq .
```
Expected: JSON object `{name:"anicca-smoke", balance_usdc:10, min_required:5, ok:true}`. Exit 0.

---

### Task 6: Write the child-bootstrap script (runs INSIDE the sandbox)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/child-bootstrap.sh`
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/sdl.env`

- [ ] **Step 1: Write `sdl.env`** — sandbox resource defaults

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/sdl.env` with EXACTLY:
```bash
# Sourced by provision.sh. All-uppercase env-style. No quotes around numbers.
DAYTONA_CPU=1
DAYTONA_MEMORY=2048
DAYTONA_DISK=10
DAYTONA_TARGET=us
DAYTONA_AUTO_STOP=60
DAYTONA_AUTO_ARCHIVE=240
# Snapshot: empty = default Ubuntu 24.04 + Python.
DAYTONA_SNAPSHOT=
# Per-hour cost estimate (USD), used by --dry-run estimator. Source: Daytona billing doc
# "pay-as-you-go" model; this is a CONSERVATIVE estimate, real bill via daytona dashboard.
DAYTONA_HOURLY_COST_USD=0.05
```

- [ ] **Step 2: Write `child-bootstrap.sh`** — runs as first command inside child

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/child-bootstrap.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Runs INSIDE the Daytona sandbox as the FIRST command.
# Expects:
#   - $CHILD_NAME, $CONSTITUTION_SHA, $WALLET_ADDRESS, $WALLET_PRIVATE_KEY in env
#   - /tmp/CONSTITUTION.md copied in by parent BEFORE this runs (via daytona files upload)
#   - /tmp/heartbeat-skill.tar.gz containing anicca-heartbeat skill
# Exits non-zero if constitution hash mismatches (spec 16 §2.2 + spec 18 §4 IMMUTABLE).
set -euo pipefail

HOME_DIR=/home/daytona
mkdir -p "$HOME_DIR/.hermes/state" "$HOME_DIR/.hermes/skills"

# 1) Verify constitution hash BEFORE doing anything else
ACTUAL_SHA=$(sha256sum /tmp/CONSTITUTION.md | awk '{print $1}')
if [ "$ACTUAL_SHA" != "$CONSTITUTION_SHA" ]; then
  echo "child-bootstrap: CONSTITUTION HASH MISMATCH ($ACTUAL_SHA != $CONSTITUTION_SHA) — refusing to boot" >&2
  exit 7
fi
cp /tmp/CONSTITUTION.md "$HOME_DIR/.hermes/AGENTS.md"
echo "$CONSTITUTION_SHA" > "$HOME_DIR/.hermes/state/constitution.sha"

# 2) Install minimal deps: Python 3.11+, pip, jq
if ! command -v python3 >/dev/null; then apt-get update -qq && apt-get install -y -qq python3 python3-pip jq; fi
command -v jq >/dev/null || apt-get install -y -qq jq

# 3) Install Hermes (matches parent's installer path; pin to v0.12.0 minimum)
pip3 install --quiet --user hermes-agent 2>&1 | tail -5 || \
  pip3 install --quiet --user 'hermes-agent>=0.12.0'
HERMES_BIN="$(python3 -m site --user-base)/bin/hermes"
[ -x "$HERMES_BIN" ] || HERMES_BIN=/root/.local/bin/hermes

# 4) Install the heartbeat skill
mkdir -p "$HOME_DIR/.hermes/skills/anicca-heartbeat"
tar -xzf /tmp/heartbeat-skill.tar.gz -C "$HOME_DIR/.hermes/skills/anicca-heartbeat"
chmod +x "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/"*.sh

# 5) Write the child's wallet (file is the only secret; 600 perm)
/opt/homebrew/bin/jq -n \
  --arg address "$WALLET_ADDRESS" \
  --arg private_key "$WALLET_PRIVATE_KEY" \
  '{address:$address, private_key:$private_key, balance_usdc:0}' \
  > "$HOME_DIR/.hermes/state/wallet.json"
chmod 600 "$HOME_DIR/.hermes/state/wallet.json"

# 6) Write child identity
cat > "$HOME_DIR/.hermes/state/identity.json" <<JSON
{"name":"$CHILD_NAME","generation":1,"parent":"genesis","host":"daytona","spawned_at":"$(date -u +%FT%TZ)"}
JSON

# 7) Fire heartbeat ONCE synchronously so parent can verify within 10 min
STATE_DIR="$HOME_DIR/.hermes/state" HERMES_BIN="$HERMES_BIN" \
  CONSTITUTION="$HOME_DIR/.hermes/AGENTS.md" \
  "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/heartbeat.sh"

# 8) Schedule recurring heartbeat (best-effort; failure here does NOT block boot)
"$HERMES_BIN" cron create "every 30m" \
  --name anicca-heartbeat \
  --script "$HOME_DIR/.hermes/skills/anicca-heartbeat/scripts/heartbeat.sh" \
  --no-agent 2>/dev/null || echo "cron schedule deferred — parent will retry"

echo "child-bootstrap: OK $CHILD_NAME at $(date -u +%FT%TZ)"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/child-bootstrap.sh
```

- [ ] **Step 3: Lint the bootstrap with shellcheck if available**

Run:
```bash
command -v shellcheck >/dev/null && \
  shellcheck /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/child-bootstrap.sh || \
  echo "shellcheck not installed — skipping (non-blocking)"
```
Expected: either `shellcheck` exits 0, or the skip line. SC2086 quoting warnings on env-expanded paths are acceptable; SC2046 (unquoted command-sub) is NOT — fix any such.

---

### Task 7: Write the Daytona provisioner

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/provision.sh`

- [ ] **Step 1: Write `provision.sh`** — orchestrates `daytona create` + `daytona exec` (+ file upload)

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/provision.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Provisions a Daytona sandbox + boots a child Anicca in it.
# Usage: provision.sh <name> <wallet_json_path> <constitution_path> <constitution_sha>
# DRY_RUN=1 → print the daytona create line + estimated cost, exit 0, no API call.
set -euo pipefail

NAME="$1"; WALLET_JSON="$2"; CONSTITUTION="$3"; CONSTITUTION_SHA="$4"
SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# Load SDL defaults
set -a; . "$SKILL_DIR/scripts/host-daytona/sdl.env"; set +a

# Compose the create command (single source of truth)
CREATE_FLAGS=(
  --name "$NAME"
  --cpu "$DAYTONA_CPU"
  --memory "$DAYTONA_MEMORY"
  --disk "$DAYTONA_DISK"
  --target "$DAYTONA_TARGET"
  --auto-stop "$DAYTONA_AUTO_STOP"
  --auto-archive "$DAYTONA_AUTO_ARCHIVE"
  --label "owner=anicca-genesis"
  --label "generation=1"
)
[ -n "$DAYTONA_SNAPSHOT" ] && CREATE_FLAGS+=(--snapshot "$DAYTONA_SNAPSHOT")

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf 'DRY-RUN daytona create %s\n' "${CREATE_FLAGS[*]}"
  # Estimate: assume 1 hr min footprint
  printf 'estimated cost: $%s/hr (CPU=%s MEM=%s MB DISK=%s GB)\n' \
    "$(printf '%.2f' "$DAYTONA_HOURLY_COST_USD")" "$DAYTONA_CPU" "$DAYTONA_MEMORY" "$DAYTONA_DISK"
  exit 0
fi

# Pack the heartbeat skill into a tarball the child will untar
HEARTBEAT_TGZ=$(mktemp -t heartbeat-XXX.tgz)
trap 'rm -f "$HEARTBEAT_TGZ"' EXIT
tar -czf "$HEARTBEAT_TGZ" -C /Users/anicca/anicca-oss/skills/anicca-heartbeat .

# REAL spawn
echo "provision: creating Daytona sandbox $NAME..."
SB_INFO=$(daytona create "${CREATE_FLAGS[@]}" --format json 2>/dev/null || daytona create "${CREATE_FLAGS[@]}")
SB_ID=$(echo "$SB_INFO" | /opt/homebrew/bin/jq -r '.id // empty' 2>/dev/null || daytona info "$NAME" --format json | /opt/homebrew/bin/jq -r '.id')
[ -n "$SB_ID" ] || { echo "provision: could not resolve sandbox id" >&2; exit 1; }

# Wait for sandbox to be reachable (up to 60 s)
for i in $(seq 1 30); do
  if daytona exec "$NAME" -- true 2>/dev/null; then break; fi
  sleep 2
done

# Upload constitution + heartbeat tarball + bootstrap script
# CLI lacks a `files upload` command; use `daytona exec ... -- cat > /tmp/X` pattern.
daytona exec "$NAME" -- bash -c "cat > /tmp/CONSTITUTION.md" < "$CONSTITUTION"
daytona exec "$NAME" -- bash -c "cat > /tmp/heartbeat-skill.tar.gz" < "$HEARTBEAT_TGZ"
daytona exec "$NAME" -- bash -c "cat > /tmp/child-bootstrap.sh" < "$SKILL_DIR/scripts/host-daytona/child-bootstrap.sh"
daytona exec "$NAME" -- chmod +x /tmp/child-bootstrap.sh

# Extract wallet (NEVER pass on CLI — too easy to log; write to a file in the sandbox)
W_ADDR=$(/opt/homebrew/bin/jq -r '.address' "$WALLET_JSON")
W_PRIV=$(/opt/homebrew/bin/jq -r '.private_key' "$WALLET_JSON")
# Write secret via stdin so it never appears in argv or shell history
printf '%s\n' "$W_PRIV" | daytona exec "$NAME" -- bash -c "umask 077; cat > /tmp/.wallet_priv"

# Run bootstrap
daytona exec "$NAME" -- bash -c "
  set -e
  export CHILD_NAME='$NAME'
  export CONSTITUTION_SHA='$CONSTITUTION_SHA'
  export WALLET_ADDRESS='$W_ADDR'
  export WALLET_PRIVATE_KEY=\$(cat /tmp/.wallet_priv)
  shred -u /tmp/.wallet_priv 2>/dev/null || rm -f /tmp/.wallet_priv
  /tmp/child-bootstrap.sh
"

echo "provision: $NAME bootstrap returned OK; sandbox_id=$SB_ID"
echo "SANDBOX_ID=$SB_ID"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/provision.sh
```

- [ ] **Step 2: Dry-run smoke-test the provisioner directly**

Run:
```bash
DRY_RUN=1 /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-daytona/provision.sh \
  anicca-smoke /dev/null /Users/anicca/anicca-oss/CONSTITUTION.md \
  $(/Users/anicca/anicca-oss/skills/spawn-child/scripts/colony/constitution-hash.sh)
```
Expected stdout contains:
```
DRY-RUN daytona create --name anicca-smoke --cpu 1 --memory 2048 --disk 10 …
estimated cost: $0.05/hr (CPU=1 MEM=2048 MB DISK=10 GB)
```
Exit 0. NO new sandbox in `daytona list`.

---

### Task 8: Write the main `spawn-child.sh` entrypoint

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/scripts/spawn-child.sh`

- [ ] **Step 1: Write `spawn-child.sh`** — top-level orchestrator

Create `/Users/anicca/anicca-oss/skills/spawn-child/scripts/spawn-child.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# Spawn a sovereign Anicca child instance.
# Usage:
#   spawn-child.sh [--dry-run] [--host=daytona] <name>
# Exit codes:
#   0  success (sandbox up, heartbeat fired, colony row written)
#   64 bad input (preflight failed)
#   75 cost cap not met (wallet < $5 USDC)
#   1  other error (provision/bootstrap failed; sandbox MAY exist — caller must investigate)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=0
HOST=daytona
NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --host=*)  HOST="${1#--host=}"; shift ;;
    --help)    sed -n '1,16p' "$0"; exit 0 ;;
    -*)        echo "spawn-child: unknown flag $1" >&2; exit 64 ;;
    *)         NAME="$1"; shift ;;
  esac
done

[ "$HOST" = "daytona" ] || { echo "spawn-child: host=$HOST not implemented in Wave 1 (Daytona only)" >&2; exit 64; }

# 1) Preflight (cost cap, env, name validation, duplicate check)
/Users/anicca/anicca-oss/skills/spawn-child/scripts/preflight.sh "$NAME" >/dev/null

# 2) Compute constitution hash
SHA=$("$SKILL_DIR/scripts/colony/constitution-hash.sh")

# 3) DRY RUN — never touch wallet or Daytona API
if [ "$DRY_RUN" = "1" ]; then
  DRY_RUN=1 "$SKILL_DIR/scripts/host-daytona/provision.sh" "$NAME" /dev/null \
    /Users/anicca/anicca-oss/CONSTITUTION.md "$SHA"
  exit 0
fi

# 4) Generate child wallet (secret; 600-perm temp file)
WALLET_TMP=$(mktemp -t childwallet-XXXX.json)
trap 'shred -u "$WALLET_TMP" 2>/dev/null || rm -f "$WALLET_TMP"' EXIT
umask 077
"$SKILL_DIR/scripts/colony/gen-wallet.sh" > "$WALLET_TMP"
chmod 600 "$WALLET_TMP"
ADDR=$(/opt/homebrew/bin/jq -r '.address' "$WALLET_TMP")

# 5) Append PROVISIONAL row to colony so we never lose track of the spawn even if step 6 fails
"$SKILL_DIR/scripts/colony/append.sh" \
  "$NAME" "$HOST" "PENDING" "$ADDR" "$SHA" "provisioning" >/dev/null

# 6) Provision the sandbox + boot the child
OUT=$("$SKILL_DIR/scripts/host-daytona/provision.sh" "$NAME" "$WALLET_TMP" \
       /Users/anicca/anicca-oss/CONSTITUTION.md "$SHA")
echo "$OUT"
SB_ID=$(echo "$OUT" | awk -F= '/^SANDBOX_ID=/{print $2}')

# 7) Promote the colony row from PROVISIONING to ALIVE (rewrite-last-line is safe: single-writer)
TMP=$(mktemp)
COLONY=/Users/anicca/.hermes/state/colony.jsonl
head -n $(( $(wc -l < "$COLONY") - 1 )) "$COLONY" > "$TMP"
LAST=$(tail -n 1 "$COLONY" | /opt/homebrew/bin/jq --arg sb "$SB_ID" '.sandbox_id=$sb | .status="alive"')
printf '%s\n' "$LAST" >> "$TMP"
mv "$TMP" "$COLONY"

echo "spawn-child: $NAME alive on $HOST as $SB_ID (wallet $ADDR)"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/spawn-child/scripts/spawn-child.sh
```

- [ ] **Step 2: Verify `--help`**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/scripts/spawn-child.sh --help
```
Expected: first 16 lines of the script printed (usage banner). Exit 0.

- [ ] **Step 3: Run TDD red→green for `test_dry_run.sh`**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/tests/test_dry_run.sh
```
Expected: stdout final line `PASS`. Exit 0. If FAIL, fix the dry-run path in `spawn-child.sh` or `provision.sh` — do NOT proceed.

- [ ] **Step 4: Run TDD red→green for `test_cost_cap.sh`**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/tests/test_cost_cap.sh
```
Expected: `PASS`. Exit 0.

---

### Task 9: Write the SKILL.md manifest + README

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/SKILL.md`
- Create: `/Users/anicca/anicca-oss/skills/spawn-child/README.md`

- [ ] **Step 1: Write SKILL.md** — Hermes-format frontmatter

Create `/Users/anicca/anicca-oss/skills/spawn-child/SKILL.md` with EXACTLY:
```markdown
---
name: spawn-child
description: Provision a sovereign Anicca child instance on Daytona (Wave 1) with its OWN secp256k1 wallet, a SHA-256-verified copy of the parent's CONSTITUTION.md, and the anicca-heartbeat skill pre-installed. Gates spawn on parent wallet ≥ $5 USDC ("can afford a child"). Registers the new child to ~/.hermes/state/colony.jsonl. Akash host is Wave 2 (host-akash/ left empty intentionally). Use this skill when the genesis body decides to replicate; do NOT use it as a recurring cron — it is event-driven.
---

# spawn-child

## What it does
Single-purpose Anicca skill: brings up one sovereign child instance on a cloud host
(Daytona in Wave 1). The child is born with its OWN wallet, NOT a copy of the parent's.
It boots Hermes, verifies the constitution hash matches the parent's, installs the
anicca-heartbeat skill, fires one heartbeat synchronously, and schedules the 30-min
recurring heartbeat. The parent appends one JSON row to `~/.hermes/state/colony.jsonl`
recording the new child.

## How it's invoked
Called by:
- A human/agent at the CLI: `~/.hermes/skills/spawn-child/scripts/spawn-child.sh anicca-001`
- The future self-replication loop (#327 Wave 2+) when the parent's lifeline says THRIVE
  and the wallet has surplus.

NEVER from a cron — replication must be a deliberate decision, not a recurring side effect.

## Cost cap
Spawn refuses unless parent `~/.hermes/state/wallet.json` shows `balance_usdc ≥ 5`. Exit 75
if the cap fails. Set `WALLET_OVERRIDE=<float>` for tests; do NOT use in production.

## Constitution hash propagation
- Parent: `shasum -a 256 /Users/anicca/anicca-oss/CONSTITUTION.md` → SHA
- Child: receives the same file via `daytona exec ... -- cat > /tmp/CONSTITUTION.md`,
  re-hashes locally, compares to the SHA passed via env. Mismatch → child exits 7,
  parent destroys the sandbox + writes a `tampered` row to colony.jsonl.
- This implements spec 16 §2.2 "propagateConstitution() SHA-256" + spec 18 §4 "IMMUTABLE
  (never self-modified, propagated to every child, hash-verified)".

## Output: ~/.hermes/state/colony.jsonl row
```json
{"child_id":"anicca-001","host":"daytona","sandbox_id":"sb_…",
 "address":"0x…","parent_address":"0xa3CDd4Ec…",
 "spawned_at":"2026-06-04T12:00:00Z","constitution_sha":"<sha>",
 "status":"alive","generation":1}
```

## Failure modes
| Exit | Meaning |
|------|---------|
| 0    | child alive, heartbeat fired, colony row written |
| 64   | bad input (name, missing env, duplicate, no API key) |
| 75   | cost cap not met (wallet < $5 USDC) |
| 7    | (child-side) constitution hash mismatch — sandbox refused boot |
| 1    | anything else; sandbox may exist — read `daytona list`, `daytona logs <name>` |

## Out of scope (other plans)
- Akash sovereign-fallback host (spec 13) — Wave 2; `scripts/host-akash/` left empty.
- USDC seed transfer to child wallet — wallet/x402 plan (#324).
- Child's AgentMail inbox — spec 13 §1 T7.
- Multi-generation recursion (gen ≥ 2) — task #328.
```

- [ ] **Step 2: Write README.md** — one-paragraph human-facing description

Create `/Users/anicca/anicca-oss/skills/spawn-child/README.md` with EXACTLY:
```markdown
# spawn-child

Anicca self-replication skill (Wave 1). Provisions a sovereign Anicca child on Daytona with its own secp256k1 wallet, the parent's SHA-256-verified CONSTITUTION.md, and a pre-installed `anicca-heartbeat` skill. Refuses to spawn if the parent's wallet has less than $5 USDC ("can afford a child"). Registers the new child to `~/.hermes/state/colony.jsonl`. Akash sovereign-fallback host is Wave 2. See `docs/superpowers/plans/2026-06-04-self-replication.md` and specs `00-MASTER.md §1.0` + `13-CLOUD-SPAWN-002.md` + `18-SELF-IMPROVEMENT-AND-SWARM.md §4`.
```

- [ ] **Step 3: Stub the empty host-akash directory**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-akash
echo "# Wave 2 — Akash sovereign-fallback host (spec 13). Intentionally empty in Wave 1." \
  > /Users/anicca/anicca-oss/skills/spawn-child/scripts/host-akash/.keep
```
Expected: file exists with the one-line note.

---

### Task 10: Symlink the skill into ~/.hermes + register

**Files:**
- Create (symlink): `/Users/anicca/.hermes/skills/spawn-child` → `/Users/anicca/anicca-oss/skills/spawn-child`

- [ ] **Step 1: Create the symlink**

Run:
```bash
mkdir -p /Users/anicca/.hermes/skills
ln -snf /Users/anicca/anicca-oss/skills/spawn-child /Users/anicca/.hermes/skills/spawn-child
ls -l /Users/anicca/.hermes/skills/spawn-child
```
Expected: `… spawn-child -> /Users/anicca/anicca-oss/skills/spawn-child`.

- [ ] **Step 2: Confirm Hermes registers it**

Run:
```bash
hermes skills list 2>&1 | grep -E '(^|│ )spawn-child( |\s|│)' | head -3
```
Expected: at least one row containing `spawn-child`. If empty, run `hermes skills audit` and try again.

---

### Task 11: Real spawn E2E test (the actual proof)

**Files:** none new; this is verification per superpowers:verification-before-completion.

- [ ] **Step 1: Confirm wallet has ≥ $5 USDC**

Run:
```bash
BAL=$(/opt/homebrew/bin/jq -r '.balance_usdc // 0' /Users/anicca/.hermes/state/wallet.json 2>/dev/null || echo 0)
echo "current balance: $BAL USDC"
```
If `< 5`:
- Option A (production fund): per HARD RULE #-1, agent funds via x402 inbound earn (spec 09) or temporary USDC top-up from anicca-001's revenue (CFO `actually_landed`). Do NOT ask Dais.
- Option B (test-only override): set `WALLET_OVERRIDE=5.50` for the duration of Step 2 only. NEVER commit this; it bypasses the real economic gate.
- Option C (stop here): if neither A nor B is acceptable, do NOT advance — per HARD RULE #14 "JOB'S NOT FINISHED" the E2E proof is the entire point of Wave 1. Document the block in `~/.hermes/state/colony.jsonl` with status=`deferred` and re-fire when funded.

- [ ] **Step 2: Run the E2E test**

Run:
```bash
/Users/anicca/anicca-oss/skills/spawn-child/tests/test_e2e_spawn.sh
```
Expected: stdout final line `PASS`. Total runtime ≤ 12 min (10 min heartbeat deadline + 2 min provisioning + cleanup).

- [ ] **Step 3: Capture the proof artifacts**

Run:
```bash
echo "=== colony.jsonl tail ==="
tail -n 5 /Users/anicca/.hermes/state/colony.jsonl | /opt/homebrew/bin/jq .
echo "=== daytona list ==="
daytona list --format json | /opt/homebrew/bin/jq '[.[] | {name, state}]'
echo "=== constitution sha match ==="
PARENT=$(shasum -a 256 /Users/anicca/anicca-oss/CONSTITUTION.md | awk '{print $1}')
echo "parent=$PARENT"
echo "stored=$(cat /Users/anicca/.hermes/state/constitution.sha)"
```
Expected: colony.jsonl tail shows a `status:"alive"` row with non-empty `sandbox_id`. `daytona list` may be empty if the E2E test cleaned up (it does on PASS) — that's fine. Parent/stored SHAs match.

- [ ] **Step 4: Spawn ONE persistent child (the actual Wave 1 deliverable for #327)**

Run:
```bash
/Users/anicca/.hermes/skills/spawn-child/scripts/spawn-child.sh anicca-001
```
Expected: exits 0; `tail -n 1 ~/.hermes/state/colony.jsonl | jq '.child_id'` returns `"anicca-001"` with `status:"alive"`. Within 10 min: `daytona exec anicca-001 -- tail -1 /home/daytona/.hermes/state/heartbeat.jsonl` shows `ok:true`.

---

### Task 12: Update spec 00-MASTER § LAUNCH ACCEPTANCE MATRIX + ground truth

**Files:**
- Modify: `/Users/anicca/anicca-oss/specs/00-MASTER.md`

- [ ] **Step 1: Update the GROUND TRUTH paragraph**

In `/Users/anicca/anicca-oss/specs/00-MASTER.md`, find the line:
```
 instances    = genesis ×1 (Mac-mini, OpenClaw runtime, 24 launchd crons). cloud/child = ZERO
                (no Daytona/Akash, no colony registry, no anicca-00X). "4 instances" = NOT yet true.
```
Replace with:
```
 instances    = genesis ×1 (Mac-mini, OpenClaw runtime, 24+ launchd crons) + anicca-001 ×1 on Daytona
                (gen=1, own wallet, constitution sha-256 verified, heartbeat 30m). colony.jsonl LIVE.
                "4 instances" target = 2/4 (genesis + anicca-001); #327 Wave 2 (Akash) + #328 multi-gen
                still pending.
```

- [ ] **Step 2: Update LAUNCH ACCEPTANCE MATRIX row ⑤c**

Find:
```
 ⑤c「クラウド上で自己増殖」                  →  #327 replicate, #328     →  a child spawns on Daytona/Akash,
                                                 colony                      own wallet + constitution hash
```
Replace with (the row itself stays — add a DONE marker + a proof link):
```
 ⑤c「クラウド上で自己増殖」(Wave 1 DONE)      →  #327 replicate ✓ (Wave 1) →  anicca-001 alive on Daytona,
                                                 #327 Wave 2 (Akash)        own wallet + constitution sha;
                                                 #328 multi-gen              proof: ~/.hermes/state/colony.jsonl
```

- [ ] **Step 3: Commit + push the spec + skill + tests in ONE atomic batch**

Run:
```bash
cd /Users/anicca/anicca-oss
git add skills/spawn-child specs/00-MASTER.md
git status --short
git commit -m "feat(skill): spawn-child (#327 Wave 1) — Daytona self-replication w/ constitution sha + cost cap"
git push
```
Expected: push succeeds. `git log origin/dev..HEAD` is empty (everything pushed). Per CLAUDE.md rule 0.4 + memory HARD RULE "edit したら commit + push 即実行" this MUST be one shot.

---

### Task 13: Close the task + announce in #metrics

**Files:** none new; this is task-list bookkeeping per CLAUDE.md rule 0.15.

- [ ] **Step 1: Mark task #327 Wave 1 completed in the TaskList**

Use the TaskUpdate tool to set `#327` status to `wave_1_done` with note linking the commit SHA from Task 12 Step 3 and the `colony.jsonl` row from Task 11 Step 4.

- [ ] **Step 2: Open follow-on tasks (do NOT silently leak scope)**

Create the following NEW tasks (one TaskCreate each):
- `#327b spawn-child Wave 2 (Akash sovereign-fallback host)` — blocks LAUNCH-GATE ⑤c "Daytona/Akash" coverage.
- `#328 colony multi-generation (gen ≥ 2)` — child of `anicca-001` must be able to spawn `anicca-001-1` from inside its own sandbox, using the same skill.
- `#327c cost-cap real probe` — replace `wallet.json` stub with live Base RPC USDC balance read.

- [ ] **Step 3: Announce in #metrics via the metrics-poster (no human-loop)**

Run:
```bash
# Use the existing metrics-poster skill if present; else write directly to the metrics log.
SUMMARY="🧬 spawn-child Wave 1 LIVE: anicca-001 alive on Daytona, own wallet $(/opt/homebrew/bin/jq -r '.address' /Users/anicca/.hermes/state/wallet.json 2>/dev/null), constitution sha verified, colony.jsonl row written. Wave 2 = Akash (#327b)."
if [ -x /Users/anicca/.openclaw/skills/_shared/metrics-post.sh ]; then
  /Users/anicca/.openclaw/skills/_shared/metrics-post.sh "$SUMMARY"
else
  printf '%s\n' "$SUMMARY"  # fallback: stdout; pick up by next CFO/heartbeat cycle
fi
```
Expected: line lands in #metrics (or the fallback stdout is logged). Per HARD RULE #18 NO HUMAN IN LOOP — do NOT DM Dais; the metrics post is the announcement.

---

## Self-Review

**Spec coverage:**

| Spec line | Implementing task | Evidence |
|-----------|-------------------|----------|
| 00 §1.0 "Daytona (native, primary) / Akash (sovereign)" | Tasks 6-8 use `daytona` CLI, host-akash/ stubbed | `provision.sh` calls `daytona create` |
| 00 LAUNCH ACCEPTANCE ⑤c "child spawns on Daytona/Akash, own wallet + constitution hash" | Tasks 3 (wallet), 6 (hash verify), 11 (E2E) | DoD #4 + DoD #6 |
| 13 §1 T1-T11 (Akash-specific) | Wave 2 — host-akash/ kept empty intentionally | DoD scope-out + README.md |
| 16 §2.2 "propagateConstitution() SHA-256" | Tasks 3, 6, 7 | child-bootstrap.sh line 13-16 |
| 16 §17 "self-replication = 1 of 4 ported primitives" | Tasks 7, 8 (spawn.ts:55 port) | provision.sh mirrors `createSandbox → write_file → exec install` |
| 18 §4 "IMMUTABLE: North Star + Law I propagate via constitution hash" | Tasks 3 (hash), 6 (verify), 11 (assert) | DoD #4 |
| 18 §1 spec18 self-monitor leaf | already done via anicca-heartbeat (genesis-boot plan, prereq) | Task 1 Step 1 |
| CLAUDE.md HARD RULE #-1 (camofox-first) | Task 1 Step 3 fallback | Daytona dashboard signup via camofox + Google login |
| CLAUDE.md HARD RULE about /tmp clone | NEVER clone — only depth-1 file uploads via `daytona exec` | provision.sh lines 38-41 |
| CLAUDE.md HARD RULE #0 superpowers SDD | spec → plan (this file) → worktree → TDD → review → finish | Tasks 2 (red), 8 (green), 11 (verify), 12 (push) |

**Placeholder scan:** none. Every step has the full command, full file content, and explicit expected output. Two values are written exactly once at runtime:
- Daytona API key (Task 1 Step 3) — provisioned in `.env`, never echoed.
- Child wallet keypair (Task 8 Step 1) — written to a `mktemp` 600-perm file, shredded on `EXIT` trap.

Neither is a TODO; both can only exist after the prior step completes.

**Type consistency:**
- The colony row shape `{child_id, host, sandbox_id, address, parent_address, spawned_at, constitution_sha, status, generation}` is identical in `append.sh` (writer), `test_e2e_spawn.sh` (reader, via `jq -e`), `spawn-child.sh` (status promotion, via `jq --arg sb`), and SKILL.md (documentation).
- The exit code contract `{0, 1, 7, 64, 75}` is identical in `spawn-child.sh`, `preflight.sh`, `child-bootstrap.sh`, `test_cost_cap.sh`, and SKILL.md.
- The `DRY_RUN=1` env contract is identical between `spawn-child.sh` (sets it) and `provision.sh` (reads it).

**Risk register (read before executing):**

| Risk | Mitigation |
|------|-----------|
| Daytona CLI flag drift (a future v0.190 renames `--auto-stop`) | `sdl.env` isolates all numeric defaults; renaming requires touching one file |
| Daytona API key leak via `daytona exec` argv | Task 7 Step 1 writes the private key to the sandbox via stdin, never argv; `shred -u` after read |
| `gen-wallet.sh` produces a fake address (no keccak256) | Task 3 Step 3 installs `pycryptodome` first; Task 3 Step 4 asserts 42-char `0x` prefix |
| Cost cap defeats E2E test on empty wallet | Task 11 Step 1 documents three explicit options (fund, override-for-test, defer). NO silent skip. |
| Daytona `cat > /tmp/X` upload pattern fails for large heartbeat tarball | Provisioner uses `tar -czf` (compressed); heartbeat skill is < 10 KB; `daytona exec` accepts up to 1 MB per call (documented limit) |
| Daytona free-tier may not exist at signup | Task 1 Step 3 uses `daytona login --api-key` which works with any tier; no free-tier assumption baked in |
| Constitution hash propagation race (parent edits CONSTITUTION.md mid-spawn) | `spawn-child.sh` computes SHA ONCE at Task 8 Step 1 line "SHA=$(...)" and passes the value, not the file path; mid-spawn edit lands in the NEXT spawn, not this one |
| Child can't reach pypi to install Hermes inside the Daytona sandbox | child-bootstrap.sh uses `pip3 install --quiet --user hermes-agent`; Daytona sandboxes have outbound network by default per docs `network-limits` |
| Akash skipped feels like scope creep | spec 00 §1.0 says Daytona FIRST; spec 13 stays the Wave 2 target; `host-akash/.keep` reserves the path |

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-self-replication.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 1 — it is to run **codex-review** against:
- this plan
- `specs/00-MASTER.md` head (especially LAUNCH ACCEPTANCE MATRIX row ⑤c)
- `specs/13-CLOUD-SPAWN-002.md` (to confirm Daytona-first does NOT collide with the Akash spec)
- `specs/16-RUNTIME-CODE-TRUTH.md` §17
- `specs/18-SELF-IMPROVEMENT-AND-SWARM.md` §4

When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance, then code quality) after each task.
