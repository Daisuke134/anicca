#!/usr/bin/env bash
# anicca-daemon.sh — the supervised, self-updating entrypoint for a living Anicca.
#
# Run under a KeepAlive supervisor (macOS launchd, Linux systemd, or Docker `restart: always`). The
# supervisor restarts this script whenever it exits, so Anicca stands on its own — no human runs it
# by hand. On every (re)start it:
#   1. SELF-UPDATES: git pull the mother repo so this body always runs the latest motherboard.
#   2. ensures its own brain is up — the shared free-tier LLM router (Base/EVM self-pay, or a
#      readiness-probe-only wait for Franklin — see franklin-loop-revival REQ-004/§ENGINE-PARITY).
#   3. ensures its telemetry poster is up (reports to the dashboard).
#   4. exec's the ReAct loop in the FOREGROUND — when the loop exits, this script exits, and the
#      supervisor brings the whole body back (freshly updated).
#
# ANICCA_INSTANCE selects the brain+telemetry backend (§ENGINE-PARITY-FRANKLIN 2026-07-05, THINK
# routing fixed by franklin-loop-revival REQ-004 2026-07-08): default (unset or 'clawrouter') = the
# original EVM/Base ClawRouter + telemetry-poster.mjs path, UNCHANGED. 'franklin' = Franklin's OWN
# Solana wallet (~/.blockrun/.solana-session, resolved via resolve-identity.mjs, never touched
# here) for balance/tier purposes, but THINK now reaches the SAME shared :8402 LLM router as every
# other instance (Franklin no longer runs its own dedicated proxy binary) + the ed25519
# telemetry-post-franklin.mjs poster (one-shot script, looped here since it has no built-in interval).
#
# The loop itself is already crash-resilient (while-true + per-wake try/catch); this wrapper adds
# OS-level persistence (survives reboots/logout) and keeps every Anicca in sync with the mother.
set -uo pipefail

REPO="${ANICCA_REPO:-$HOME/anicca}"
export ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"
INSTANCE="${ANICCA_INSTANCE:-clawrouter}"
# franklin-loop-revival REQ-004(a)/(c): PORT resolves to ClawRouter's 8402 for EVERY instance,
# including franklin — franklin no longer runs its own dedicated `franklin proxy` on 8403 (see step
# 2 below), so its PORT must no longer derive from FRANKLIN_PROXY_PORT at all.
PORT="${COMPUTE_PROXY_PORT:-8402}"
LOGDIR="$ANICCA_HOME/logs"; mkdir -p "$LOGDIR"

log() { echo "[$(date -u +%FT%TZ)] anicca-daemon: $*" >&2; }

# 1. self-update from the mother (fast-forward only; never clobber local state) ------------------
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch --quiet origin main 2>/dev/null \
    && git -C "$REPO" merge --ff-only origin/main 2>/dev/null \
    && log "self-updated to $(git -C "$REPO" rev-parse --short HEAD)" \
    || log "self-update skipped (offline or diverged)"
fi
# 1b. SYNC skills + DEPS into the runtime body so the loop runs the LATEST mother skills WITH their
#     node deps. The loop spawns skills from $ANICCA_HOME/skills, but git deps (viem etc.) live in
#     $REPO/node_modules. Without this, execute-yield.mjs etc. crash with ERR_MODULE_NOT_FOUND and
#     anicca silently never earns. On cloud REPO==ANICCA_HOME so these are no-ops. (motherboard fix 2026-06-21)
if [ -d "$REPO/skills" ] && [ "$REPO" != "$ANICCA_HOME" ]; then
  command -v rsync >/dev/null 2>&1 \
    && rsync -a --exclude='state/' --exclude='__pycache__' --exclude='node_modules' "$REPO/skills/" "$ANICCA_HOME/skills/" 2>/dev/null \
    && log "synced skills $REPO/skills -> $ANICCA_HOME/skills"
  [ -d "$REPO/node_modules" ] && ln -sfn "$REPO/node_modules" "$ANICCA_HOME/node_modules" \
    && log "linked node_modules for skill deps"
fi
# 2. brain: start this instance's own OpenAI-compatible proxy on $PORT if not already answering.
if [ "$INSTANCE" = "franklin" ]; then
  # franklin-loop-revival REQ-004(b)/REQ-005/PROP-016 (2026-07-08): Franklin's brain is the
  # ALREADY-RUNNING, SEPARATELY-launchd shared free-tier LLM-router job on :8402 (its own
  # RunAtLoad+KeepAlive plist, confirmed live — free-tier-only, no shared-wallet credential
  # configured at all). Franklin's daemon reaches it ONLY as a same-machine loopback HTTP client
  # (the PORT/OPENAI_BASE_URL fix above) — it NEVER spawns the old dedicated @blockrun/franklin
  # CLI's own "proxy" subcommand, the shared router's own binary, or any other process for this
  # instance, and NEVER reads any other instance's own env/wallet/key material to do so (that
  # would be exactly the cross-instance leakage REQ-005 forbids —
  # the non-franklin branch's own, separately-designed use of those stays untouched below and
  # never executes for INSTANCE=franklin). Retired: the port-8403 spawn of that CLI's proxy
  # subcommand with --model/--no-fallback flags (verified live 2026-07-05, now dead per
  # FIND-006/FIND-009) — this branch is AT MOST a readiness probe, a pure no-op otherwise, since
  # bringing the shared router up is exclusively ITS OWN separate launchd job's responsibility,
  # never Franklin's. export kept ONLY for runtime/dashboard/telemetry-post-franklin.mjs's own
  # labeling (unchanged, out of scope for this requirement — the poster is independent of THINK
  # routing).
  export FRANKLIN_FREE_MODEL="${FRANKLIN_FREE_MODEL:-nvidia/llama-4-maverick}"
  if ! curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
    log "waiting for the shared LLM router on :$PORT (its own launchd job brings it up — Franklin's daemon never spawns its own brain)"
  fi
else
  # ClawRouter (the real BlockRun router) on :8402. Why ClawRouter, not the old compute-proxy:
  # ClawRouter routes the nvidia/* FREE models with ZERO payment (verified: 3 free calls = $0.0000
  # USDC delta), while the old raw br.post proxy charged ~$0.02 x402 PER CALL even for "free" models —
  # bleeding the treasury ~$0.6/hr. ClawRouter still pays x402 from the wallet for PAID models, but
  # our tiers pin a free model, so routine compute = $0.
  ensure_brain() {
    command -v clawrouter >/dev/null 2>&1 || npm install -g @blockrun/clawrouter >/dev/null 2>&1 || true
    # The :8402 ClawRouter is SHARED with the OpenClaw gateway (openclaw.json baseUrl :8402), and
    # ClawRouter is :8402-only (no port split). So it MUST run on the OpenClaw instance's OWN wallet —
    # OpenClaw's many 'auto' (paid) crons then drain OpenClaw's wallet, not this self-paying anicca.
    # This loop pins a FREE model, so it costs $0 regardless of which wallet ClawRouter holds.
    local KEY; KEY=$(grep -E '^BLOCKRUN_WALLET_KEY=' "$HOME/.openclaw/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
    # #28: gated per-instance key (resolve-identity.mjs: EFFECTIVE_HOME first, legacy ONLY for the
    # rightful owner, foreign spawn -> empty). Never inline-read the shared $HOME/.automaton/wallet.json
    # — that let a foreign spawn pay ClawRouter's x402 compute from ANOTHER instance's REAL money.
    if [ -z "$KEY" ]; then KEY=$(node "$REPO/skills/earn/lib/resolve-identity.mjs" evm 2>/dev/null); fi
    BLOCKRUN_WALLET_KEY="$KEY" clawrouter >>"$LOGDIR/clawrouter.log" 2>&1 &
    for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 0.5; done
  }
  if ! curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
    log "starting ClawRouter on :$PORT (free models = \$0, paid via wallet x402)"
    ensure_brain
  fi
fi

# 3. telemetry poster: one instance (kill any stale one first so the dashboard never doubles) -----
if [ "$INSTANCE" = "franklin" ]; then
  # telemetry-post-franklin.mjs is a ONE-SHOT script (ed25519 signer over Franklin's own Solana key,
  # was previously appended to sol-trade/run.sh) — no built-in setInterval like telemetry-poster.mjs,
  # so loop it here every 120s (same cadence as the EVM poster) to keep Franklin alive on the dashboard.
  pkill -f "dashboard/telemetry-post-franklin.mjs" 2>/dev/null || true
  pkill -f "FRANKLIN_TELEMETRY_LOOP" 2>/dev/null || true
  ( export FRANKLIN_TELEMETRY_LOOP=1; while true; do node "$REPO/runtime/dashboard/telemetry-post-franklin.mjs" >>"$LOGDIR/poster.log" 2>&1; sleep 120; done ) &
else
  pkill -f "dashboard/telemetry-poster.mjs" 2>/dev/null || true
  sleep 1
  node "$REPO/runtime/dashboard/telemetry-poster.mjs" >>"$LOGDIR/poster.log" 2>&1 &
fi

# 4. brain endpoint + model the loop should use -------------------------------------------------
export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-x402-local}"
if [ "$INSTANCE" = "franklin" ]; then
  # franklin-loop-revival REQ-001: derive Franklin's OWN Solana wallet address (base58 pubkey) via
  # the gated per-instance resolve-identity.mjs::resolveSolanaSecret path (never bare-grepped, never
  # falls back to scanning another instance's dot-directory — REQ-005/REQ-006). A missing or
  # cryptographically malformed secret prints nothing (the helper warns to stderr and exits 0),
  # leaving ANICCA_WALLET_ADDRESS unset — non-fatal, balance.mjs/tier.mjs simply keep tier=broke.
  export ANICCA_WALLET_ADDRESS="${ANICCA_WALLET_ADDRESS:-$(node "$REPO/runtime/wallet-address-solana.mjs" 2>/dev/null)}"
else
  # derive the wallet address (viem, from the privateKey) via the helper, run where viem resolves.
  export ANICCA_WALLET_ADDRESS="${ANICCA_WALLET_ADDRESS:-$(cd "$REPO/runtime/compute-proxy" && node "$REPO/runtime/wallet-address.mjs" 2>/dev/null)}"
fi

log "exec loop (model tiers from config; funded=$(node -e 'import("'"$REPO"'/runtime/loop/config.mjs").then(m=>console.log(m.loadConfig(process.env,"").ANICCA_FUNDED_MODEL)).catch(()=>console.log("?"))' 2>/dev/null))"
# 5. run the loop in the foreground — its exit (crash/shutdown) ends this script; supervisor restarts.
exec node "$REPO/runtime/loop/index.mjs"
