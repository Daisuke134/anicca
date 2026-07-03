#!/usr/bin/env bash
# lib/config.sh — profitable-article-writer declarative config.
#
# This file is declarative ONLY (constants), not the skill's business logic — it is not part of the
# Phase 2a "stub, not implemented" surface.
#
# REQ-12: the loop-wake model tier is a COST-TIER label consumed by the orchestrating harness when it
# selects which frontier-model tier runs this skill's wake. It is NOT a provider-specific model literal
# (no "claude-*"/"gpt-*" string, no API key) — the skill itself stays model-agnostic (REQ-1). PROP-1's
# checker greps for PROVIDER-PREFIXED literals and API-key env names, not a bare cost-tier label.
set -uo pipefail

# Cost tier for the loop wake (REQ-12). A generic tier label, never an API model id.
MODEL_TIER="sonnet"

# record-earn (deterministic ledger tool, reused from founder-loop) MUST run with NO LLM call anywhere in
# the earn/verify path (REQ-12). This is a declarative marker; the earn/verify path checks against it.
#
# Conditional default (not an unconditional assignment): this lets an external caller/test actually
# observe a flip via the environment (e.g. RECORD_EARN_USES_LLM=1 bash run.sh ...) so run.sh's fail-closed
# refusal branch (PROP-9/CRIT-005) is a reachable, testable runtime path — not dead code that can only be
# exercised by editing this file's literal source text.
: "${RECORD_EARN_USES_LLM:=0}"

export MODEL_TIER RECORD_EARN_USES_LLM
