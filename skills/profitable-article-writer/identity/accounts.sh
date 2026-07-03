#!/usr/bin/env bash
# identity/accounts.sh — per-install credential registry (REQ-15, REQ-11).
#
# INTERFACE (honored once implemented in Phase 2b):
#   env in:  ARTICLE_DIR (state dir)
#   env in:  NOTE_SESSION_COOKIE / SUBSTACK_API_KEY / X_API_KEY / ZENN_TOKEN / DEVTO_API_KEY
#            (each optional; presence activates that rail's registry slot — REQ-15)
#   env in:  <RAIL>_SELF_CREATE=1 → attempt a zero-human self-create for a PROVEN rail (REQ-11);
#            otherwise an absent-credential rail is flagged "unavailable", never a loud failure.
#   writes:  $ARTICLE_DIR/state/accounts.json — { "<rail>": "active" | "unavailable", ... }
#   NEVER reads or writes a shared/hardcoded Dais account literal (REQ-15) — every credential comes from
#   THIS install's own environment.
#
# Phase 2a RED stub: intentionally unimplemented.
set -uo pipefail
echo "NOT_IMPLEMENTED: identity/accounts.sh (Phase 2b implements per-install credential gating + self-create-or-flag)" >&2
exit 1
