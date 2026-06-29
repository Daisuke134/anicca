#!/usr/bin/env bash
# earn/gig — ONE Anicca loop slot. The loop's runSkill('earn/gig') spawns this with a
# private-key-SCRUBBED env. Does ONE bounded unit per wake, prints a structured one-line
# JSON result on stdout (source=gig, task, earn_usdc, cost_usdc, wake), exits 0.
# Spec: ~/anicca/docs/superpowers/specs/2026-06-29-earn-gig-slot-design.md (D1-D6).
#
# NO-HUMAN (D4): captcha→CapSolver, OTP→gog gmail, login→stored creds, publish→CDP.
# ANTI-SHORTCUT (D5): only record-earn (external on-chain USDC) counts; detect/bid earn 0.
# The wallet is read from the standard path as an ADDRESS only — never a private key.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── safe env (allowlist; the loop already scrubbed keys, this is defense-in-depth) ──
WAKE="${WAKE_ID:-$(date -u +%s)}"
TIMEOUT_S="${SKILL_TIMEOUT_S:-120}"

# The loop passes the model's decision as $ANICCA_ARGS (JSON), NOT GIG_MODE. Parse it.
# {"mode":"detect|bid|deliver|settle","jobId":"...","proposal":"...","amount":40}
# Fallbacks: GIG_MODE (manual test) → detect (always-safe default).
_parse_args() {
  python3 - "${ANICCA_ARGS:-}" "${GIG_MODE:-}" <<'PY' 2>/dev/null || echo "detect||40|"
import json,sys
raw,gmode=(sys.argv[1] if len(sys.argv)>1 else ""),(sys.argv[2] if len(sys.argv)>2 else "")
a={}
try: a=json.loads(raw) if raw.strip() else {}
except Exception: a={}
mode=str(a.get("mode") or gmode or "detect")
jobid=str(a.get("jobId") or a.get("job_id") or "")
amount=str(a.get("amount") or "40")
proposal=str(a.get("proposal") or "")
# tab-separated; proposal last (may contain spaces, no tabs)
print(f"{mode}\t{jobid}\t{amount}\t" + proposal.replace("\t"," ").replace("\n"," "))
PY
}
IFS=$'\t' read -r MODE GIG_JOB_ID GIG_AMOUNT GIG_PROPOSAL <<<"$(_parse_args)"
MODE="${MODE:-detect}"; export GIG_JOB_ID GIG_AMOUNT GIG_PROPOSAL

# ── wallet ADDRESS only (never the key) from the standard path ──
wallet_address() {
  local wj="${ANICCA_WALLET_JSON:-$HOME/.anicca-founder/wallet.json}"
  [ -f "$wj" ] || { echo "unknown"; return; }
  python3 - "$wj" <<'PY' 2>/dev/null || echo "unknown"
import json,sys
d=json.load(open(sys.argv[1]))
# emit only an address-looking field; never anything key-shaped
for k in ("address","evm","base","wallet","pubkey","public"):
    v=d.get(k)
    if isinstance(v,str) and v.startswith("0x") and len(v)<=44:
        print(v); break
else:
    print("unknown")
PY
}
WALLET="$(wallet_address)"

# ── D1 can_run: which rails are available THIS wake (labor rails; capital-free) ──
# Reads only the KEY NAMES present in the creds file (never the secret values) + brain.
available_rails() {
  local envf="${ANICCA_CREDS_ENV:-$HOME/.openclaw/.env}"
  local brain="${ANICCA_BRAIN:-proxy}"
  local keys=""
  [ -f "$envf" ] && keys=$(grep -oE '^(export +)?[A-Z0-9_]+=' "$envf" 2>/dev/null | sed -E 's/^export +//; s/=$//' | sort -u | tr '\n' ' ')
  python3 - "$brain" "$keys" <<'PY' 2>/dev/null || echo ""
import sys
sys.argv_brain=sys.argv[1]; present=set(sys.argv[2].split())
RAIL_CREDS={"dealwork":["DEALWORK_API_KEY"]}
out=[r for r,ks in RAIL_CREDS.items() if all(k in present for k in ks)]
print(" ".join(out))
PY
}
RAILS="$(available_rails)"

# ── emit one structured result line (the loop/ledger parse this) ──
emit() { # $1=task $2=earn_usdc $3=cost_usdc [$4=extra-json]
  python3 - "$WALLET" "$1" "$2" "$3" "$WAKE" "${4:-}" <<'PY'
import json,sys
wallet,task,earn,cost,wake,extra=sys.argv[1:7]
o={"wallet":wallet,"source":"gig","task":task,"earn_usdc":float(earn),"cost_usdc":float(cost),"wake":wake}
if extra:
    try: o.update(json.loads(extra))
    except Exception: pass
print(json.dumps(o))
PY
}

# ── DETECT: the always-safe bounded unit (no side effects, earns 0) ──
do_detect() {
  local feed="$HERE/state/guild_feed.json" queue="$HERE/state/earn_action_queue.jsonl"
  local jobs=0 pending=0
  # refresh the verified-live feed (bounded; failure is non-fatal — stale feed still usable)
  timeout 40 node "$HERE/lib/detect.mjs" "$feed" >/dev/null 2>&1 || true
  [ -f "$feed" ] && jobs=$(python3 -c "import json;print(len(json.load(open('$feed')).get('jobs',[])))" 2>/dev/null || echo 0)
  [ -f "$queue" ] && pending=$(grep -c . "$queue" 2>/dev/null || echo 0)
  local rails_json
  rails_json=$(printf '%s' "$RAILS" | python3 -c "import sys,json;print(json.dumps(sys.stdin.read().split()))")
  echo "[gig] detect wake=$WAKE jobs=$jobs pending_inbound=$pending rails=[$RAILS]"
  emit "detect" 0 0 "{\"jobs_seen\":$jobs,\"pending_inbound\":$pending,\"available_rails\":$rails_json}"
}

# ── BID: one tailored proposal on one unbid AI-doable dealwork job (no-human) ──
do_bid() {
  local feed="$HERE/state/guild_feed.json" bids="$HERE/state/bids.jsonl"
  local key; key=$(grep -E '^(export +)?DEALWORK_API_KEY=' "${ANICCA_CREDS_ENV:-$HOME/.openclaw/.env}" 2>/dev/null | head -1 | sed -E 's/^(export +)?DEALWORK_API_KEY=//; s/^"//; s/"$//')
  [ -f "$feed" ] || timeout 40 node "$HERE/lib/detect.mjs" "$feed" >/dev/null 2>&1 || true
  local res; res=$(DEALWORK_API_KEY="$key" GIG_PROPOSAL="${GIG_PROPOSAL:-}" GIG_JOB_ID="${GIG_JOB_ID:-}" GIG_AMOUNT="${GIG_AMOUNT:-40}" \
    node "$HERE/lib/bid-run.mjs" "$feed" "$bids" 2>&1) || true
  echo "[gig] bid: $res"
  # bid-run.mjs prints a JSON line itself; if it didn't, emit a safe detect-style line
  echo "$res" | grep -q '"task"' || emit "bid-noop" 0 0
}

# ── DELIVER: detect accepted contracts needing a deliverable (V4); brain produces work ──
do_deliver() {
  local key; key=$(grep -E '^(export +)?DEALWORK_API_KEY=' "${ANICCA_CREDS_ENV:-$HOME/.openclaw/.env}" 2>/dev/null | head -1 | sed -E 's/^(export +)?DEALWORK_API_KEY=//; s/^"//; s/"$//')
  local res; res=$(DEALWORK_API_KEY="$key" node "$HERE/lib/deliver-run.mjs" 2>&1) || true
  echo "[gig] deliver: $res"
  echo "$res" | grep -q '"task"' || emit "deliver-noop" 0 0
}

# ── SETTLE: count ONLY real external on-chain USDC (record-earn INV-7). Anti-shortcut. ──
# record-earn is the CHAIN ORACLE (external-USDC truth). On a confirmed inflow the slot
# also writes a LOOP-FORMAT earn line to the loop's EARN_LEDGER tagged wake=$WAKE (WAKE_ID),
# because the loop classifies profitability by `line.wake === WAKE_ID` (FIND-001).
do_settle() {
  local re="${ANICCA_HOME:-$HOME/anicca}/skills/self/founder-loop/record-earn.mjs"  # portable (FIND-005)
  [ -f "$re" ] || { echo "[gig] settle: record-earn not found at $re"; emit "settle" 0 0; return; }
  local out earn=0
  out=$(timeout 45 node "$re" --source gig --task settle --wake "$WAKE" 2>&1) || true   # --wake (FIND-001)
  echo "[gig] settle: $out"
  earn=$(printf '%s' "$out" | sed -nE 's/.*VERIFIED \+([0-9.]+) USDC.*/\1/p' | head -1)
  [ -n "$earn" ] || earn=0
  if [ "$earn" != "0" ]; then
    # write a PROFITABLE-SHAPE line (real external tx + status 0x1 + external + net>0) to the loop's
    # EARN_LEDGER so classifyEarnResult finds wake===WAKE_ID AND isProfitable accepts it (FIND-001).
    local ledger="${EARN_LEDGER:-${ANICCA_HOME:-$HOME/anicca}/skills/earn/state/earn-ledger.jsonl}"
    local line; line=$(node "$HERE/lib/settle-write.mjs" "$earn" "$WALLET" "$WAKE" "$ledger" 2>/dev/null) || true
    echo "[gig] settle-line: $line"
    [ -n "$line" ] && echo "$line" || emit "settle" "$earn" 0 '{"external":true}'
  else
    emit "settle" 0 0
  fi
}

case "$MODE" in
  detect)  do_detect ;;
  settle)  do_settle ;;
  bid)     do_bid ;;
  deliver) do_deliver ;;
  inbound) do_deliver ;;   # inbound (accepted/messages) routes through deliver-detect for now
  *) echo "[gig] unknown GIG_MODE=$MODE; defaulting to detect"; do_detect ;;
esac
exit 0
