#!/usr/bin/env bash
# provision-vps.sh — #42 concrete remote-host provisioning recipe.
#
# This is the ONE step automaton outsources to Conway's paid sandbox API
# (automaton src/replication/spawn.ts:105 conway.createSandbox). automaton has
# NO generic-VPS code. This script is that substituted step for Anicca:
# rent a real VPS, install anicca-core + OpenClaw on it, start its heartbeat.
#
# Grounded sources (no invention):
#  - Hetzner Cloud API  POST /v1/servers  (docs.hetzner.cloud/reference/cloud)
#  - cloud-init via user_data (community.hetzner.com/tutorials/basic-cloud-config,
#    github.com/tech-otaku/hetzner-cloud-init)
#  - flow mirrors automaton spawn.ts steps 4-8 (apt+git clone → genesis →
#    propagateConstitution+hash → init identity → lifecycle)
#
# HONEST GATE: actually creating a server costs real money and needs a real
# provider token. HCLOUD_TOKEN is a Dais-credential/funding step (like Stripe/
# Apple-ID asks) — it CANNOT be faked here. Without it this script no-ops with
# a clear message; it does NOT pretend success. End-to-end "done" = one real
# cheap VPS run verified (task #42 acceptance).
#
# Usage:
#   provision-vps.sh create  <child_name> <genesis_file> <core_repo_url>
#   provision-vps.sh status  <child_name>
#   provision-vps.sh destroy <child_name>
#
# Env (all real, no placeholders consumed silently):
#   HCLOUD_TOKEN     Hetzner Cloud API token (REQUIRED to create — Dais funds)
#   HCLOUD_SSH_KEY   name of an SSH key already uploaded to the Hetzner project
#   ANICCA_SSH_KEY   local private key path matching HCLOUD_SSH_KEY (for exec)
#   CHILD_MODEL_KEY  the child's BYO model access (its own, never Dais's)
#   SERVER_TYPE      default cx22 (2vCPU/4GB, ~€3.79/mo) — smallest sane tier
#   IMAGE            default ubuntu-24.04
#   LOCATION         default nbg1

set -euo pipefail

API="https://api.hetzner.cloud/v1"
SERVER_TYPE="${SERVER_TYPE:-cx22}"
IMAGE="${IMAGE:-ubuntu-24.04}"
LOCATION="${LOCATION:-nbg1}"
CORE_REPO="${3:-https://github.com/Daisuke134/anicca.git}"
CORE_BRANCH="${ANICCA_BRANCH:-main}"      # for testing against prep before #76 PUBLIC swap
HARNESS="${ANICCA_HARNESS:-openclaw}"     # passes to install.sh --harness
STATE_DIR="$HOME/.openclaw/workspace/ops/children"
mkdir -p "$STATE_DIR"

log(){ printf '[provision-vps] %s\n' "$*" >&2; }

require_token(){
  if [ -z "${HCLOUD_TOKEN:-}" ]; then
    log "HCLOUD_TOKEN not set. Cannot create a real server."
    log "This is a Dais-credential/funding step (real money). NOT faking success."
    log "Escalate to #metrics: '🔑 need HCLOUD_TOKEN + funded Hetzner project to spawn a child'."
    exit 75   # EX_TEMPFAIL — real external dependency, not an error in this code
  fi
}

api(){ # api METHOD PATH [json]
  local m="$1" p="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -fsS -X "$m" "$API$p" -H "Authorization: Bearer $HCLOUD_TOKEN" \
      -H "Content-Type: application/json" -d "$body"
  else
    curl -fsS -X "$m" "$API$p" -H "Authorization: Bearer $HCLOUD_TOKEN"
  fi
}

cmd_create(){
  local name="$1" genesis_file="$2"
  require_token
  [ -f "$genesis_file" ] || { log "genesis file $genesis_file missing"; exit 64; }
  [ -n "${CHILD_MODEL_KEY:-}" ] || { log "CHILD_MODEL_KEY (child BYO model) required — child must fund itself"; exit 64; }

  # idempotent: reuse if a live record exists
  if [ -f "$STATE_DIR/$name.json" ] && \
     api GET "/servers/$(jq -r .server_id "$STATE_DIR/$name.json")" >/dev/null 2>&1; then
    log "child '$name' already provisioned — reuse"; cat "$STATE_DIR/$name.json"; return 0
  fi

  local const_hash; const_hash="$(shasum -a256 "$HOME/.openclaw/workspace/CONSTITUTION.md" | cut -d' ' -f1)"

  # cloud-init: install runtime, clone core, verify CONSTITUTION hash, start daemon.
  # The constitution hash is pinned here so the child REFUSES to boot if its
  # copied CONSTITUTION.md doesn't match the parent (五戒 immutable propagation,
  # automaton constitution.ts propagateConstitution + hash verification).
  local user_data
  user_data=$(cat <<CLOUDINIT
#cloud-config
package_update: true
packages: [git, curl, nodejs, npm]
write_files:
  - path: /root/genesis.json
    content: |
$(sed 's/^/      /' "$genesis_file")
  - path: /root/.anicca-const-sha
    content: "$const_hash"
runcmd:
  - git clone --depth 1 --branch $CORE_BRANCH $CORE_REPO /root/anicca-core
  - test "\$(shasum -a256 /root/anicca-core/CONSTITUTION.md | cut -d' ' -f1)" = "$const_hash" || (echo "CONSTITUTION hash mismatch — refusing to boot (五戒)"; halt)
  - npm i -g @openclaw/cli || true
  - su root -c 'ANICCA_HOME=/root/anicca-core CHILD_MODEL_KEY=$CHILD_MODEL_KEY bash /root/anicca-core/install.sh --harness=$HARNESS --substrate=local'
  - su root -c 'openclaw onboard --install-daemon || true'
  - su root -c 'openclaw gateway --port 18789 &'
CLOUDINIT
)

  log "creating Hetzner server '$name' ($SERVER_TYPE/$IMAGE/$LOCATION)…"
  local resp
  resp=$(api POST "/servers" "$(jq -n \
    --arg n "anicca-child-$name" --arg t "$SERVER_TYPE" --arg i "$IMAGE" \
    --arg l "$LOCATION" --arg k "${HCLOUD_SSH_KEY:-}" --arg u "$user_data" \
    '{name:$n,server_type:$t,image:$i,location:$l,ssh_keys:(if $k=="" then [] else [$k] end),user_data:$u,start_after_create:true}')")

  local sid ip
  sid=$(echo "$resp" | jq -r '.server.id')
  ip=$(echo "$resp" | jq -r '.server.public_net.ipv4.ip')
  [ "$sid" != "null" ] || { log "create failed: $resp"; exit 1; }

  jq -n --arg n "$name" --arg s "$sid" --arg ip "$ip" --arg ch "$const_hash" \
    '{name:$n,server_id:$s,ip:$ip,constitution_sha:$ch,status:"provisioning",createdAt:now|todate}' \
    > "$STATE_DIR/$name.json"
  log "server $sid @ $ip provisioning (cloud-init runs core install + hash-verify + node daemon)"
  cat "$STATE_DIR/$name.json"
}

cmd_status(){
  local name="$1"
  [ -f "$STATE_DIR/$name.json" ] || { echo '{"status":"unknown"}'; return 0; }
  local ip; ip=$(jq -r .ip "$STATE_DIR/$name.json")
  # child health = its own peer agent-api /status (task #27 contract)
  if curl -fsS --max-time 8 "http://$ip:7843/status" 2>/dev/null; then :; else
    echo "{\"name\":\"$name\",\"ip\":\"$ip\",\"status\":\"unreachable\"}"
  fi
}

cmd_destroy(){
  local name="$1"
  [ -f "$STATE_DIR/$name.json" ] || { log "no such child"; return 0; }
  require_token
  local sid; sid=$(jq -r .server_id "$STATE_DIR/$name.json")
  api DELETE "/servers/$sid" >/dev/null && log "destroyed server $sid"
  mv "$STATE_DIR/$name.json" "$STATE_DIR/$name.dead.json"
}

case "${1:-}" in
  create)  shift; cmd_create "$@";;
  status)  shift; cmd_status "$@";;
  destroy) shift; cmd_destroy "$@";;
  *) echo "usage: provision-vps.sh {create|status|destroy} <name> [genesis_file] [core_repo]"; exit 64;;
esac
