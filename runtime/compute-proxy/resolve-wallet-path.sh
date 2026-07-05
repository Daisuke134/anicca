#!/usr/bin/env bash
# resolve-wallet-path.sh — single source of truth for THIS instance's EVM wallet path
# (#26 EQUALIZE, R4). Sourced by start-local.sh; unit-tested by __tests__/resolve-wallet-path.test.sh.
#
# Every instance must be born with its OWN isolated EVM identity under its OWN $ANICCA_HOME, so
# two instances on one machine can never share a key (comparable P&L, fair swarm eval). The ONLY
# back-compat exception: the ORIGINAL default-home instance, which historically wrote its wallet
# to the shared legacy path $HOME/.automaton/wallet.json (old start-local.sh, pre-#26). We keep
# THAT instance on its legacy wallet so its on-chain identity never changes — but a spawn with a
# DIFFERENT $ANICCA_HOME must NEVER inherit it (that was the FIND-001 bug: a fresh spawn silently
# adopted the running automaton's private key because the legacy file merely existed).
#
# Rule: prefer $ANICCA_HOME/.automaton/wallet.json. Fall back to the legacy shared path ONLY when
# the effective home IS the default ($HOME/.anicca) — i.e. the legacy owner — AND no per-home
# wallet exists yet. Any non-default $ANICCA_HOME always gets its own path (generated if missing).
resolve_wallet_path() {
  local effective_home="${ANICCA_HOME:-$HOME/.anicca}"
  local wallet="$effective_home/.automaton/wallet.json"
  local legacy="$HOME/.automaton/wallet.json"
  if [ ! -f "$wallet" ] && [ -f "$legacy" ] && [ "$effective_home" = "$HOME/.anicca" ]; then
    wallet="$legacy"
  fi
  printf '%s\n' "$wallet"
}
