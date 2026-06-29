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
MODE="${GIG_MODE:-detect}"        # detect | bid | deliver | inbound
TIMEOUT_S="${SKILL_TIMEOUT_S:-120}"

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
  [ -f "$feed" ] && jobs=$(python3 -c "import json;print(len(json.load(open('$feed')).get('jobs',[])))" 2>/dev/null || echo 0)
  [ -f "$queue" ] && pending=$(grep -c . "$queue" 2>/dev/null || echo 0)
  echo "[gig] detect wake=$WAKE jobs=$jobs pending_inbound=$pending"
  emit "detect" 0 0 "{\"jobs_seen\":$jobs,\"pending_inbound\":$pending}"
}

case "$MODE" in
  detect)  do_detect ;;
  bid|deliver|inbound)
    # GREEN skeleton: real rails land in tasks #5/#6. For now, no-op safely (earn 0, no fake tx).
    echo "[gig] mode=$MODE not yet wired (tasks #5/#6); safe no-op"
    emit "$MODE-noop" 0 0
    ;;
  *) echo "[gig] unknown GIG_MODE=$MODE; defaulting to detect"; do_detect ;;
esac
exit 0
