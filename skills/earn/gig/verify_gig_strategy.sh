#!/usr/bin/env bash
# verify_gig_strategy.sh — VCSDD-lean verification for the "gig 稼ぎ戦略 prompt 格上げ" increment
# (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §6.5, increment 1: prompt + strategy.default.json only).
#
# Checks (all must PASS):
#   (a) gig-cli.sh is syntactically valid bash (bash -n) — a broken STARTUP string bricks the live loop.
#   (b) strategy.default.json is valid JSON (json.load).
#   (c) grep-verifiable presence of each required playbook/policy keyphrase across
#       gig-cli.sh + strategy.default.json (combined — some phrases live in the prompt,
#       some in the JSON scaffold, per spec §6.5).
#   (d) 占い (fortune-telling) is absent from skip_categories in strategy.default.json
#       (spec §4: reclassified from skip to listing target).
#
# Usage: bash verify_gig_strategy.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PASS=0
FAIL=0

check() {
  local desc="$1" cond="$2"
  if [ "$cond" = "0" ]; then
    echo "PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc"
    FAIL=$((FAIL+1))
  fi
}

echo "=== (a) gig-cli.sh bash syntax ==="
bash -n gig-cli.sh 2>&1
check "gig-cli.sh: bash -n syntax check" "$?"

echo ""
echo "=== (b) strategy JSON validity ==="
python3 -c "import json; json.load(open('strategy.default.json', encoding='utf-8'))" 2>&1
check "strategy.default.json: valid JSON" "$?"

if [ -f "$HOME/gig/strategy.json" ]; then
  python3 -c "import json; json.load(open('$HOME/gig/strategy.json', encoding='utf-8'))" 2>&1
  check "\$HOME/gig/strategy.json (live, informational — out of edit-scope): valid JSON" "$?"
fi

echo ""
echo "=== (c) required keyphrases (combined search across gig-cli.sh + strategy.default.json) ==="
COMBINED="$(cat gig-cli.sh strategy.default.json)"

grep_phrase() {
  local label="$1" pattern="$2"
  if printf '%s' "$COMBINED" | grep -Eq "$pattern"; then
    check "$label (pattern: $pattern)" 0
  else
    check "$label (pattern: $pattern)" 1
  fi
}

grep_phrase "松竹梅 3-tier plan"                       "松竹梅"
grep_phrase "モニター価格 (monitor pricing)"             "モニター価格"
grep_phrase "サムネ...文字入れ (thumbnail text overlay)" "サムネ.*文字"
grep_phrase "ベネフィット型タイトル (benefit-led title)"  "ベネフィット"
grep_phrase "掲載直後30分以内 (apply within 30min of posting)" "掲載.*30分"
grep_phrase "never-refuse policy"                       "(NEVER.*断らない|断ってよいのは)"
grep_phrase "feasibility gate"                          "(feasibility|可=browser)"

echo ""
echo "=== (d) 占い must NOT be in skip_categories (strategy.default.json) ==="
python3 - <<'PYEOF'
import json, sys
d = json.load(open("strategy.default.json", encoding="utf-8"))
skip = d.get("skip_categories", [])
bad = [c for c in skip if "占い" in c or "霊感" in c or "スピリチュアル" in c]
if bad:
    print("FOUND in skip_categories (should be absent):", bad)
    sys.exit(1)
sys.exit(0)
PYEOF
check "占い/霊感/スピリチュアル absent from strategy.default.json skip_categories" "$?"

echo ""
echo "=== SUMMARY ==="
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: ALL PASS"
exit 0
