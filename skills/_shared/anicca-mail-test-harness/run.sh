#!/usr/bin/env bash
# run.sh — anicca-mail-test-harness entry point.
#
# Usage:
#   bash run.sh --all                    # 全 test-cases/*.yaml 実行
#   bash run.sh --category A             # category A のみ
#   bash run.sh --case TC-A1             # 1 case のみ
#   bash run.sh --case TC-A1 --dry-run   # mail 投函のみ・verify 飛ばし
#
# 出力: reports/test-report-{TS}.json {pass, fail, skip, total, failures: [...]}

set -uo pipefail

[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/_shared/anicca-mail-test-harness"
TEST_CASES_DIR="$SKILL_DIR/test-cases"
LIB_DIR="$SKILL_DIR/lib"
REPORTS_DIR="$SKILL_DIR/reports"
mkdir -p "$REPORTS_DIR"

NOW=$(date +%Y-%m-%dT%H-%M-%S)
TS=$(date +%s)
REPORT="$REPORTS_DIR/test-report-${NOW}.json"

# Parse args
MODE="all"
CATEGORY=""
CASE_ID=""
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --all) MODE="all" ;;
    --category) MODE="category" ;;
    --case) MODE="case" ;;
    --dry-run) DRY_RUN=1 ;;
    [A-G]) CATEGORY="$arg" ;;
    TC-*) CASE_ID="$arg" ;;
  esac
done

echo "▶ anicca-mail-test-harness mode=$MODE category=${CATEGORY:-all} case=${CASE_ID:-all} dry=$DRY_RUN"
echo "▶ report: $REPORT"

# Discover test cases
shopt -s nullglob
ALL_CASES=("$TEST_CASES_DIR"/*.yaml)
if [ "${#ALL_CASES[@]}" -eq 0 ]; then
  echo "❌ no test cases found in $TEST_CASES_DIR" >&2
  exit 1
fi

# Filter
SELECTED=()
for yaml in "${ALL_CASES[@]}"; do
  basename=$(basename "$yaml" .yaml)
  case "$MODE" in
    all) SELECTED+=("$yaml") ;;
    category)
      cat_letter=$(echo "$basename" | sed -E 's/^TC-([A-G]).*/\1/')
      [ "$cat_letter" = "$CATEGORY" ] && SELECTED+=("$yaml")
      ;;
    case)
      [ "$basename" = "$CASE_ID" ] && SELECTED+=("$yaml")
      ;;
  esac
done

if [ "${#SELECTED[@]}" -eq 0 ]; then
  echo "❌ no test cases matched filter" >&2
  exit 1
fi

echo "▶ ${#SELECTED[@]} case(s) selected"
echo ""

PASS=0
FAIL=0
SKIP=0
FAILURES=()

for yaml in "${SELECTED[@]}"; do
  case_id=$(basename "$yaml" .yaml)
  echo "── $case_id ──"

  # Env-substitute the YAML before send.
  # Order: {ts} first, then env vars (so a literal $X in subject is replaced).
  : "${OSS_TEST_RECIPIENT:=${GOG_ACCOUNT:-}}"
  : "${USER_NAME_EN:=${OSS_USER_NAME_EN}}"
  : "${USER_NAME_PREFERRED:=Dais}"
  : "${SLACK_REPORT_CHANNEL:=C091G3PKHL2}"
  CASE_YAML=$(sed \
    -e "s/{ts}/$TS/g" \
    -e "s|\${OSS_TEST_RECIPIENT}|$OSS_TEST_RECIPIENT|g" \
    -e "s|\${USER_NAME_EN}|$USER_NAME_EN|g" \
    -e "s|\${USER_NAME_PREFERRED}|$USER_NAME_PREFERRED|g" \
    -e "s|\${SLACK_REPORT_CHANNEL}|$SLACK_REPORT_CHANNEL|g" \
    "$yaml")

  # Extract input fields via python yaml
  FROM=$(echo "$CASE_YAML" | python3 -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['input']['from'])")
  TO=$(echo "$CASE_YAML" | python3 -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['input']['to'])")
  SUBJECT=$(echo "$CASE_YAML" | python3 -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['input']['subject'])")
  BODY=$(echo "$CASE_YAML" | python3 -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['input']['body'])")

  # 1. send test mail (correct gog flags: --body-file - for stdin)
  echo "  send: from=$FROM to=$TO subject=$(echo "$SUBJECT" | head -c 60)"
  SEND_OUT=$(echo "$BODY" | /opt/homebrew/bin/gog gmail send \
    --account "$GOG_ACCOUNT" \
    --to "$TO" \
    --subject "$SUBJECT" \
    --body-file - --json 2>&1 || true)
  MSG_ID=$(echo "$SEND_OUT" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('id') or d.get('messageId') or d.get('threadId',''))
except Exception:
    pass
" 2>/dev/null)

  if [ -z "${MSG_ID:-}" ]; then
    echo "  ❌ send failed"
    FAIL=$((FAIL+1))
    FAILURES+=("{\"id\":\"$case_id\",\"reason\":\"send_failed\"}")
    continue
  fi
  echo "  ✓ sent msg_id=$MSG_ID"

  if [ "$DRY_RUN" = "1" ]; then
    SKIP=$((SKIP+1))
    continue
  fi

  # 2. trigger heartbeat (= mail-auto-reply flow path)
  echo "  trigger mail-auto-reply skill..."
  bash "$HOME/.openclaw/skills/anicca-mail-auto-reply/scripts/run.sh" 2>&1 | tail -3 || true
  sleep 5

  # 3. verify (per category)
  # Dispatch: prefer evaluate-<N>.sh (e.g. evaluate-1.sh, evaluate-2.sh) for TC-<digit> ids,
  # else fall back to legacy evaluate-<letter>.sh (e.g. evaluate-a.sh) for TC-<letter> ids.
  if [[ "$case_id" =~ ^TC-([0-9]+) ]]; then
    EVAL_SCRIPT="$LIB_DIR/evaluate-${BASH_REMATCH[1]}.sh"
  elif [[ "$case_id" =~ ^TC-([A-Ga-g]) ]]; then
    L=$(echo "${BASH_REMATCH[1]}" | tr '[:upper:]' '[:lower:]')
    EVAL_SCRIPT="$LIB_DIR/evaluate-${L}.sh"
  else
    EVAL_SCRIPT=""
  fi
  if [ -f "$EVAL_SCRIPT" ]; then
    if bash "$EVAL_SCRIPT" "$yaml" "$TS"; then
      echo "  ✅ PASS"
      PASS=$((PASS+1))
    else
      echo "  ❌ FAIL"
      FAIL=$((FAIL+1))
      FAILURES+=("{\"id\":\"$case_id\",\"reason\":\"verify_failed\"}")
    fi
  else
    echo "  ⚠ evaluator $EVAL_SCRIPT not yet implemented — skip"
    SKIP=$((SKIP+1))
  fi
  echo ""
done

# 4. write report
TOTAL=$((PASS + FAIL + SKIP))
FAIL_JSON=$(IFS=,; echo "${FAILURES[*]:-}")
cat > "$REPORT" <<EOF
{
  "ts": "$NOW",
  "total": $TOTAL,
  "pass": $PASS,
  "fail": $FAIL,
  "skip": $SKIP,
  "failures": [$FAIL_JSON]
}
EOF

HARNESS="${ANICCA_HARNESS:-claude-anicca}"
if [ "$HARNESS" = "openclaw-anicca" ]; then
  ln -sf "$REPORT" "$REPORTS_DIR/latest-openclaw.json"
else
  ln -sf "$REPORT" "$REPORTS_DIR/latest.json"
fi

echo ""
echo "════════════════════════════════════════"
echo "  RESULT: pass=$PASS fail=$FAIL skip=$SKIP / total=$TOTAL"
echo "  report: $REPORT"
echo "════════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
