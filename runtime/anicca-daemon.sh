#!/usr/bin/env bash
# anicca-daemon.sh — the supervised, self-updating entrypoint for a living Anicca.
#
# Run under a KeepAlive supervisor (macOS launchd, Linux systemd, or Docker `restart: always`). The
# supervisor restarts this script whenever it exits, so Anicca stands on its own — no human runs it
# by hand. On every (re)start it:
#   1. SELF-UPDATES: git pull the mother repo so this body always runs the latest motherboard.
#   2. ensures its own brain is up (ClawRouter self-pay EVM, or Franklin's own Solana proxy — §ENGINE-PARITY).
#   3. ensures its telemetry poster is up (reports to the dashboard).
#   4. exec's the ReAct loop in the FOREGROUND — when the loop exits, this script exits, and the
#      supervisor brings the whole body back (freshly updated).
#
# ANICCA_INSTANCE selects the brain+telemetry backend (§ENGINE-PARITY-FRANKLIN 2026-07-05): default
# (unset or 'clawrouter') = the original EVM/Base ClawRouter + telemetry-poster.mjs path, UNCHANGED.
# 'franklin' = Franklin's OWN BlockRun Solana wallet (~/.blockrun/.solana-session, never touched here)
# via `franklin proxy` (OpenAI-compatible /v1/chat/completions, verified live 2026-07-05) + the ed25519
# telemetry-post-franklin.mjs poster (one-shot script, looped here since it has no built-in interval).
#
# The loop itself is already crash-resilient (while-true + per-wake try/catch); this wrapper adds
# OS-level persistence (survives reboots/logout) and keeps every Anicca in sync with the mother.
set -uo pipefail

REPO="${ANICCA_REPO:-$HOME/anicca}"
export ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"
INSTANCE="${ANICCA_INSTANCE:-clawrouter}"
if [ "$INSTANCE" = "franklin" ]; then
  PORT="${FRANKLIN_PROXY_PORT:-8403}"
else
  PORT="${COMPUTE_PROXY_PORT:-8402}"
fi
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
  # Franklin brain = `franklin proxy` (@blockrun/franklin CLI), NOT ClawRouter. ClawRouter derives
  # EVM+Solana keys from ONE mnemonic (~/.clawrouter/mnemonic) — Franklin's actual funded Solana
  # wallet is an INDEPENDENT keypair at ~/.blockrun/.solana-session (never derived from a mnemonic),
  # so ClawRouter cannot reuse it (would spin up a fresh, empty wallet). `franklin proxy` reads that
  # exact file via @blockrun/llm's getOrCreateSolanaWallet() and exposes an OpenAI-compatible
  # /v1/chat/completions on $PORT — verified live 2026-07-05: Wallet: 8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9
  # (Franklin's real address), and a free-model call (nvidia/llama-4-maverick) settled at $0 in
  # cost_log.jsonl. --model pins a FREE model + --no-fallback refuses to silently escalate to a paid
  # one, so routine THINK compute = $0 (same cost-free thesis as the ClawRouter path below).
  # export: the telemetry poster subshell (step 3 below) reads this to label model_live/model_tier
  # honestly instead of a stale hardcode (#31 FREE-MODE fix, 2026-07-05).
  export FRANKLIN_FREE_MODEL="${FRANKLIN_FREE_MODEL:-nvidia/llama-4-maverick}"
  ensure_brain() {
    command -v franklin >/dev/null 2>&1 || npm install -g @blockrun/franklin >/dev/null 2>&1 || true
    franklin proxy --port "$PORT" --model "$FRANKLIN_FREE_MODEL" --no-fallback >>"$LOGDIR/franklin-proxy.log" 2>&1 &
    for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 0.5; done
  }
  if ! curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
    log "starting franklin proxy on :$PORT (model=$FRANKLIN_FREE_MODEL, free, Franklin's own Solana wallet)"
    ensure_brain
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
if [ "$INSTANCE" != "franklin" ]; then
  # derive the wallet address (viem, from the privateKey) via the helper, run where viem resolves.
  # EVM-only helper — Franklin's wallet is Solana (balance.mjs only accepts 0x addresses; leaving
  # ANICCA_WALLET_ADDRESS unset for Franklin is correct — the loop just keeps tier=broke, non-fatal).
  export ANICCA_WALLET_ADDRESS="${ANICCA_WALLET_ADDRESS:-$(cd "$REPO/runtime/compute-proxy" && node "$REPO/runtime/wallet-address.mjs" 2>/dev/null)}"
fi

log "exec loop (model tiers from config; funded=$(node -e 'import("'"$REPO"'/runtime/loop/config.mjs").then(m=>console.log(m.loadConfig(process.env,"").ANICCA_FUNDED_MODEL)).catch(()=>console.log("?"))' 2>/dev/null))"
# 5. run the loop in the foreground — its exit (crash/shutdown) ends this script; supervisor restarts.
exec node "$REPO/runtime/loop/index.mjs"
