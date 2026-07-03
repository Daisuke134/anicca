#!/usr/bin/env bash
# self/spawn — birth a child Anicca (own wallet + own AgentMail inbox) when the parent is profitable.
# Reserved registry slot: self/spawn (spec26 A4 / spec27 A-self-spawn). Decision core is pure JS
# (lib/spawn-decision.js + lib/child-spec.js, node:test-covered); this shell only orchestrates.
#
# Usage:
#   run.sh --dry-run            gate-only; reads balance + ledger, prints decision JSON, touches NOTHING. exit 0.
#   run.sh                      real run; if eligible, provisions child wallet + AgentMail inbox + droplet + seed,
#                               appends state/children.jsonl, prints verifiable facts. exit 1 on any provision failure.
#
# NO FAKE RUN (HARD 0.24): a real run reports success ONLY after a provider id + a DISTINCT child wallet exist.
# NO HUMAN IN LOOP: never asks "spawn OK?" / "where to host?" — the gate decides, the provider auto-bids.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq || true)"
NODE="$(command -v node || true)"
DRY_RUN=0
HOST="${ANICCA_SPAWN_HOST:-do}"   # do | akash

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --host=*)  HOST="${1#--host=}"; shift ;;
    --help)    sed -n '1,18p' "$0"; exit 0 ;;
    *)         echo "self/spawn: unknown arg $1" >&2; exit 64 ;;
  esac
done

[ -n "$JQ" ]   || { echo "self/spawn: jq missing" >&2; exit 64; }
[ -n "$NODE" ] || { echo "self/spawn: node missing" >&2; exit 64; }

# --- load env (parent identity, provider + AgentMail keys). Best-effort; absence is reported, never faked.
set -a
[ -f "$HOME/.hermes/.env" ]   && . "$HOME/.hermes/.env"
[ -f "$HOME/.openclaw/.env" ] && . "$HOME/.openclaw/.env"
set +a

# Durable state dir (fail-closed: refuse /tmp — the 2026-06 E2E lost children.jsonl to tmp-clean).
STATE_DIR="$("$NODE" -e '
  const { resolveStateDir } = require(process.argv[1] + "/lib/state-path");
  process.stdout.write(resolveStateDir({ env: process.env, home: process.env.HOME }));
' "$SKILL_DIR" 2>&1)" || { echo "self/spawn: $STATE_DIR" >&2; exit 1; }
COLONY="$STATE_DIR/children.jsonl"
WALLET_JSON="${ANICCA_WALLET_JSON:-$STATE_DIR/wallet.json}"

# --- read parent balance: REAL on-chain Base USDC (REQ-2). RPC failure => 0 => dormant (fail-closed).
PARENT_WALLET="$([ -f "$WALLET_JSON" ] && "$JQ" -r '.address // ""' "$WALLET_JSON" 2>/dev/null || echo "")"
BAL=0
if [ -n "$PARENT_WALLET" ]; then
  BAL="$(python3 "$SKILL_DIR/scripts/usdc-balance.py" "$PARENT_WALLET" 2>/dev/null || echo 0)"
fi

# --- read children ledger (jsonl -> JSON array) via the tested lib.
CHILDREN_JSON="$("$NODE" -e '
  const { readChildren } = require(process.argv[1] + "/lib/ledger");
  process.stdout.write(JSON.stringify(readChildren(process.argv[2])));
' "$SKILL_DIR" "$COLONY" 2>/dev/null || echo "[]")"

# --- gate decision (pure, tested). Params are ops config, env-overridable (REQ-1); logic untouched.
DECISION="$("$NODE" -e '
  const { decideSpawn } = require(process.argv[1] + "/lib/spawn-decision");
  const balance = Number(process.argv[2]);
  const children = JSON.parse(process.argv[3] || "[]");
  const num = (v, d) => { const n = Number(v); return Number.isFinite(n) && v !== undefined && v !== "" ? n : d; };
  process.stdout.write(JSON.stringify(decideSpawn({
    balanceUsdc: balance, children,
    minBalanceUsdc: num(process.env.ANICCA_SPAWN_MIN_BALANCE, 20),
    rateLimitDays: num(process.env.ANICCA_SPAWN_RATE_DAYS, 14),
    maxChildren: num(process.env.ANICCA_SPAWN_MAX_CHILDREN, 1),
  })));
' "$SKILL_DIR" "$BAL" "$CHILDREN_JSON")"

ELIGIBLE="$(printf '%s' "$DECISION" | "$JQ" -r '.eligible')"
REASON="$(printf '%s' "$DECISION" | "$JQ" -r '.reason')"

echo "self/spawn: balance=${BAL} USDC, children=$(printf '%s' "$CHILDREN_JSON" | "$JQ" 'length'), decision=${DECISION}"

if [ "$DRY_RUN" = "1" ]; then
  echo "self/spawn: --dry-run — no side effects."
  exit 0
fi

if [ "$ELIGIBLE" != "true" ]; then
  echo "self/spawn: dormant (${REASON}); nothing spawned."
  exit 0
fi

# ---------------------------------------------------------------------------
# REAL SPAWN (eligible). Every step is real or we exit non-zero with an honest ledger.
# ---------------------------------------------------------------------------
[ -n "$PARENT_WALLET" ] || { echo "self/spawn: parent wallet address unknown — cannot prove distinct lineage" >&2; exit 1; }

# Child id prefix: "anicca-c" for the real colony; overridable (ANICCA_CHILD_PREFIX) so an isolated
# verification run can mint a unique inbox/droplet name without colliding with the live colony's ids.
CHILD_PREFIX="${ANICCA_CHILD_PREFIX:-anicca-c}"
CHILD_ID="$("$NODE" -e '
  const { nextChildId } = require(process.argv[1] + "/lib/child-spec");
  process.stdout.write(nextChildId(JSON.parse(process.argv[2] || "[]"), process.argv[3]));
' "$SKILL_DIR" "$CHILDREN_JSON" "$CHILD_PREFIX")"

# 1) child wallet (secret; 600-perm temp under state).
mkdir -p "$STATE_DIR"
umask 077
WALLET_TMP="$(mktemp "$STATE_DIR/.tmp-childwallet-XXXX.json")"
trap 'shred -u "$WALLET_TMP" 2>/dev/null || rm -f "$WALLET_TMP"' EXIT
"$SKILL_DIR/scripts/gen-wallet.sh" > "$WALLET_TMP"
chmod 600 "$WALLET_TMP"
CHILD_WALLET="$("$JQ" -r '.address' "$WALLET_TMP")"
[ "$(printf '%s' "$CHILD_WALLET" | tr 'A-Z' 'a-z')" != "$(printf '%s' "$PARENT_WALLET" | tr 'A-Z' 'a-z')" ] \
  || { echo "self/spawn: generated child wallet collided with parent — abort" >&2; exit 1; }

# 2) own AgentMail inbox (sovereign, like the wallet). Requires AGENTMAIL_API_KEY.
CHILD_INBOX=""
if [ -n "${AGENTMAIL_API_KEY:-}" ]; then
  CHILD_INBOX="$(curl -fsS -X POST https://api.agentmail.to/v0/inboxes \
    -H "Authorization: Bearer ${AGENTMAIL_API_KEY}" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${CHILD_ID}\"}" 2>/dev/null | "$JQ" -r '.inbox_id // .address // empty' || true)"
fi
[ -n "$CHILD_INBOX" ] || { echo "self/spawn: AgentMail inbox provision failed (AGENTMAIL_API_KEY missing or API error) — abort, no fake success" >&2; exit 1; }

# 3) provisional ledger row (so we never lose track even if step 4 fails).
SEED_USDC="${ANICCA_SEED_USDC:-1}"
ROW="$("$NODE" -e '
  const { buildChildSpec } = require(process.argv[1] + "/lib/child-spec");
  const s = buildChildSpec({
    childId: process.argv[2], parentWallet: process.argv[3], childWallet: process.argv[4],
    childInbox: process.argv[5], generation: Number(process.argv[6]), seedUsdc: Number(process.argv[7]),
    constitutionHash: process.argv[8],
  });
  s.host = process.argv[9]; s.spawned_ms = Date.now();
  process.stdout.write(JSON.stringify(s));
' "$SKILL_DIR" "$CHILD_ID" "$PARENT_WALLET" "$CHILD_WALLET" "$CHILD_INBOX" \
  "${ANICCA_GENERATION:-1}" "$SEED_USDC" "${ANICCA_CONSTITUTION_HASH:-unknown}" "$HOST")"
"$NODE" -e '
  const { appendChild } = require(process.argv[1] + "/lib/ledger");
  appendChild(process.argv[2], JSON.parse(process.argv[3]));
' "$SKILL_DIR" "$COLONY" "$ROW"

# 4) provision the droplet (DO) or lease (Akash). Real provider call required — no mock.
PROVIDER_ID=""
case "$HOST" in
  do)
    [ -n "${DIGITALOCEAN_TOKEN:-}" ] || { echo "self/spawn: DIGITALOCEAN_TOKEN missing — cannot provision DO droplet" >&2; exit 1; }
    # cloud-init user_data: the droplet boots clawrouter + automaton (AUTOMATON_GOAL=earn) as restart-always
    # systemd units (proven cloud-init.sh), so the child is a REAL running Anicca on first boot — not a bare box.
    # Ubuntu 24.04 (matches the proven image), s-2vcpu-2gb (the automaton build needs the headroom).
    USER_DATA="$("$SKILL_DIR/scripts/cloud-init.sh" "$CHILD_ID" "$CHILD_INBOX")"
    DO_BODY="$("$JQ" -n \
      --arg name "${CHILD_ID}" \
      --arg region "${DO_REGION:-sfo3}" \
      --arg size "${DO_SIZE:-s-2vcpu-2gb}" \
      --arg image "${DO_IMAGE:-ubuntu-24-04-x64}" \
      --arg ud "$USER_DATA" \
      '{name:$name, region:$region, size:$size, image:$image, user_data:$ud, tags:["anicca","self-spawn"]}')"
    PROVIDER_ID="$(curl -fsS -X POST https://api.digitalocean.com/v2/droplets \
      -H "Authorization: Bearer ${DIGITALOCEAN_TOKEN}" -H 'Content-Type: application/json' \
      -d "$DO_BODY" \
      2>/dev/null | "$JQ" -r '.droplet.id // empty' || true)"
    ;;
  akash)
    command -v akash >/dev/null || { echo "self/spawn: akash CLI missing — cannot provision lease" >&2; exit 1; }
    PROVIDER_ID="$("$SKILL_DIR/scripts/deploy-akash.sh" "$CHILD_ID" 2>/dev/null || true)"
    ;;
  *) echo "self/spawn: unknown host '$HOST'" >&2; exit 64 ;;
esac
[ -n "$PROVIDER_ID" ] || { echo "self/spawn: provider provisioning failed (host=$HOST) — exit 1, ledger row left provisioning" >&2; exit 1; }

# 5) register the child on the LIVE dashboard: sign its FIRST telemetry heartbeat with its OWN key
#    (signer==id) and POST to the telemetry endpoint. telemetry.js verifies + upserts an instances row;
#    dashboard-sync aggregates it into the public leaderboard — so a successful POST (202) is the child
#    APPEARING on aniccaai.com under its own (parent-distinct) wallet address. No fake: a non-202 aborts.
TELEMETRY_URL="${TELEMETRY_URL:-https://aniccaai.com/.netlify/functions/telemetry}"
SIGNED="$(CHILD_PRIVKEY="$("$JQ" -r '.private_key' "$WALLET_TMP")" \
  CHILD_HOST="$HOST" CHILD_GEO="${ANICCA_GEO:-US}" CHILD_TS="$(date +%s)" \
  python3 "$SKILL_DIR/scripts/sign-telemetry.py" 2>/dev/null || true)"
[ -n "$SIGNED" ] || { echo "self/spawn: failed to sign child telemetry — abort (no fake registration)" >&2; exit 1; }
TEL_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$TELEMETRY_URL" \
  -H 'Content-Type: application/json' -d "$SIGNED" 2>/dev/null || echo 000)"
DASHBOARD_ID="$(printf '%s' "$SIGNED" | "$JQ" -r '.id')"
[ "$TEL_STATUS" = "202" ] || { echo "self/spawn: child telemetry POST failed (HTTP ${TEL_STATUS}) — child NOT on dashboard, abort" >&2; exit 1; }

# 6) AUTO-SEED the child ON-CHAIN (REQ-4, no human instruction). Validate via the pure plan first;
#    then the deterministic transfer tool broadcasts + waits for the receipt. Failure => honest ledger
#    row seed_status=failed + exit 1 (HARD 0.24).
SEED_PLAN="$("$NODE" -e '
  const { buildSeedPlan } = require(process.argv[1] + "/lib/seed");
  process.stdout.write(JSON.stringify(buildSeedPlan({
    seedUsdc: Number(process.argv[2]), parentWallet: process.argv[3],
    childWallet: process.argv[4], parentBalanceUsdc: Number(process.argv[5]),
  })));
' "$SKILL_DIR" "$SEED_USDC" "$PARENT_WALLET" "$CHILD_WALLET" "$BAL" 2>&1)" || {
  echo "self/spawn: seed plan rejected — ${SEED_PLAN}" >&2
  FAIL_ROW="$(printf '%s' "$ROW" | "$JQ" -c --arg pid "$PROVIDER_ID" '. + {status:"active", provider_id:$pid, seed_status:"failed"}')"
  "$NODE" -e 'const { appendChild } = require(process.argv[1] + "/lib/ledger"); appendChild(process.argv[2], JSON.parse(process.argv[3]));' "$SKILL_DIR" "$COLONY" "$FAIL_ROW"
  exit 1
}
AMOUNT_UNITS="$(printf '%s' "$SEED_PLAN" | "$JQ" -r '.amountUnits')"
SEED_OUT="$(PARENT_WALLET_JSON="$WALLET_JSON" python3 "$SKILL_DIR/scripts/seed-child.py" "$CHILD_WALLET" "$AMOUNT_UNITS" 2>&1)" || {
  echo "self/spawn: seed transfer FAILED — ${SEED_OUT}" >&2
  FAIL_ROW="$(printf '%s' "$ROW" | "$JQ" -c --arg pid "$PROVIDER_ID" '. + {status:"active", provider_id:$pid, seed_status:"failed"}')"
  "$NODE" -e 'const { appendChild } = require(process.argv[1] + "/lib/ledger"); appendChild(process.argv[2], JSON.parse(process.argv[3]));' "$SKILL_DIR" "$COLONY" "$FAIL_ROW"
  exit 1
}
SEED_TX="$(printf '%s\n' "$SEED_OUT" | sed -n 's/^SEED_TX=//p' | tail -1)"
[ -n "$SEED_TX" ] || { echo "self/spawn: seed tool printed no SEED_TX — abort" >&2; exit 1; }

# 7) finalize the colony row to active + earn-on-wake intent + dashboard id + the REAL seed tx
#    (lib/seed.finalizeSeedRow, pure/tested). Durable STATE_DIR, never /tmp.
FINAL_ROW="$(printf '%s' "$ROW" | "$JQ" -c \
  --arg pid "$PROVIDER_ID" --arg did "$DASHBOARD_ID" --arg tel "$TEL_STATUS" \
  '. + {status:"active", provider_id:$pid, wake_action:"earn", earn_on_wake:true, dashboard_id:$did, telemetry_status:($tel|tonumber)}')"
FINAL_ROW="$("$NODE" -e '
  const { finalizeSeedRow } = require(process.argv[1] + "/lib/seed");
  process.stdout.write(JSON.stringify(finalizeSeedRow(JSON.parse(process.argv[2]), { txHash: process.argv[3] })));
' "$SKILL_DIR" "$FINAL_ROW" "$SEED_TX")"
"$NODE" -e '
  const { appendChild } = require(process.argv[1] + "/lib/ledger");
  appendChild(process.argv[2], JSON.parse(process.argv[3]));
' "$SKILL_DIR" "$COLONY" "$FINAL_ROW"

echo "CHILD_ID=${CHILD_ID}"
echo "CHILD_WALLET=${CHILD_WALLET}"
echo "CHILD_INBOX=${CHILD_INBOX}"
echo "PROVIDER_ID=${PROVIDER_ID}"
echo "TELEMETRY_STATUS=${TEL_STATUS}"
echo "DASHBOARD_ID=${DASHBOARD_ID}"
echo "SEED_TX=${SEED_TX}"
echo "self/spawn: ${CHILD_ID} born on ${HOST} (provider ${PROVIDER_ID}, wallet ${CHILD_WALLET}, inbox ${CHILD_INBOX}), seeded \$${SEED_USDC} on-chain (tx ${SEED_TX}), live on the dashboard. It wakes on its own — no human step remains."
