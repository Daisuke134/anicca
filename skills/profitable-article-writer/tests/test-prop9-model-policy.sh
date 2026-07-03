#!/usr/bin/env bash
# VSDD oracle — PROP-9 (REQ-12): loop wake model tier == sonnet (never opus); the earn/verify path
# invokes NO LLM call.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: config declares the tier ----------
# shellcheck disable=SC1090
source "$SKILL/lib/config.sh" 2>/dev/null || true
ok "$([ "${MODEL_TIER:-}" = "sonnet" ] && echo 1 || echo 0)" "lib/config.sh declares MODEL_TIER=sonnet"
ok "$([ "${MODEL_TIER:-}" != "opus" ] && echo 1 || echo 0)" "MODEL_TIER is never opus"
ok "$([ "${RECORD_EARN_USES_LLM:-1}" = "0" ] && echo 1 || echo 0)" "config declares RECORD_EARN_USES_LLM=0"

# ---------- DYNAMIC: a wake run in record-earn-only test mode emits a no-LLM marker ----------
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" ARTICLE_TEST_MODE=record_earn_only bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "record-earn-only test-mode wake completes, rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'RECORD_EARN_NO_LLM: true' <<<"$OUT" && echo 1 || echo 0)" "wake asserts its record-earn call made NO LLM call"

[ $fails -eq 0 ] && { echo "PASS — PROP-9 model policy (sonnet tier, no-LLM earn/verify path)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
