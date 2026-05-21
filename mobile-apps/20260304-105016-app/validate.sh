#!/bin/bash
# validate.sh — External quality gate for mobileapp-factory
# Source: SonarQube quality gate pattern
# "A quality gate is a set of conditions that must be met before code can proceed to the next stage"
# https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates
#
# Source: fastlane precheck + deliver
# "Automatically uses precheck to ensure your app has the highest chances of passing app review"
# https://docs.fastlane.tools/actions/precheck/
#
# Source: Greenlight (RevylAI)
# "Keep looping until the output shows GREENLIT status (zero CRITICAL findings)"
# https://github.com/RevylAI/greenlight
#
# CC MUST NOT MODIFY THIS FILE. ralph.sh executes it after every iteration.
# If validation fails, ralph.sh resets passes:true to false automatically.

set -uo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
source ~/.config/mobileapp-builder/.env 2>/dev/null || true

FAIL=0

log_pass() { echo "  ✅ PASS: $1"; }
log_fail() { echo "  ❌ FAIL: $1"; FAIL=1; }
log_skip() { echo "  ⏭️ SKIP: $1"; }

PRD="$APP_DIR/prd.json"

us_passes() {
  python3 -c "
import json
with open('$PRD') as f: d = json.load(f)
for us in d['userStories']:
    if us['id'] == '$1' and us['passes']:
        print('true')
        exit()
print('false')
" 2>/dev/null
}

APP_ID=$(python3 -c "
import json,re
with open('$PRD') as f: d = json.load(f)
for us in d['userStories']:
    if us['id'] in ('US-005a', 'US-005b'):
        m = re.search(r'APP_ID=(\d+)', us.get('notes',''))
        if m: print(m.group(1))
" 2>/dev/null || echo "")

echo "=========================================="
echo "🔍 EXTERNAL VALIDATION GATE"
echo "  App Dir: $APP_DIR"
echo "  APP_ID: ${APP_ID:-NOT_FOUND}"
echo "=========================================="

##############################################
# GATE 1: Greenlight preflight (code quality)
# Source: https://github.com/RevylAI/greenlight
##############################################
echo ""
echo "--- Gate 1: Greenlight Preflight ---"
if [ "$(us_passes US-006)" = "true" ]; then
  XCODE_DIR=$(find "$APP_DIR" -name "*.xcodeproj" -maxdepth 2 | head -1 | xargs dirname 2>/dev/null || echo "")
  if [ -n "$XCODE_DIR" ] && command -v greenlight &>/dev/null; then
    GL_OUTPUT=$(greenlight preflight "$XCODE_DIR" --format json 2>/dev/null || echo '{"summary":{"critical":999}}')
    GL_CRITICAL=$(echo "$GL_OUTPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('summary',{}).get('critical',999))" 2>/dev/null || echo 999)
    if [ "$GL_CRITICAL" -eq 0 ]; then
      log_pass "Greenlight CRITICAL=0 (GREENLIT)"
    else
      log_fail "Greenlight CRITICAL=$GL_CRITICAL (must be 0)"
    fi
  else
    log_skip "greenlight not found or no .xcodeproj"
  fi
else
  log_skip "US-006 not yet passed"
fi

##############################################
# GATE 2: Greenlight scan (ASC API metadata)
# Source: https://github.com/RevylAI/greenlight
# Tier 1: "Metadata & completeness (API-based, fast)"
##############################################
echo ""
echo "--- Gate 2: Greenlight ASC Scan ---"
if [ "$(us_passes US-008)" = "true" ] && [ -n "$APP_ID" ]; then
  if command -v greenlight &>/dev/null && [ -f ~/.greenlight/config.json ]; then
    GL_SCAN=$(greenlight scan --app-id "$APP_ID" --tier 1 --format json 2>/dev/null || echo '{"summary":{"passed":false,"blocks":999}}')
    GL_PASSED=$(echo "$GL_SCAN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('summary',{}).get('passed',False))" 2>/dev/null || echo "False")
    if [ "$GL_PASSED" = "True" ]; then
      log_pass "Greenlight ASC scan passed"
    else
      GL_BLOCKS=$(echo "$GL_SCAN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('summary',{}).get('blocks',999))" 2>/dev/null || echo 999)
      log_fail "Greenlight ASC scan: $GL_BLOCKS blocking issues"
      echo "$GL_SCAN" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d.get('findings',[]):
    if f.get('severity',0) >= 2:
        print(f'    ⚠️  [{f.get(\"guideline\",\"\")}] {f.get(\"title\",\"\")}')
" 2>/dev/null || true
    fi
  else
    log_skip "greenlight scan not configured"
  fi
else
  log_skip "US-008 not yet passed or APP_ID not found"
fi

##############################################
# GATE 3: Subscription state
# Source: https://community.revenuecat.com/sdks-51/app-store-missing-metadata-but-can-t-figure-out-what-6981
##############################################
echo ""
echo "--- Gate 3: Subscription Completeness ---"
if [ "$(us_passes US-005b)" = "true" ] && [ -n "$APP_ID" ]; then
  MISSING=$(asc subscriptions groups list --app "$APP_ID" --output json 2>/dev/null | python3 -c "
import json,sys,subprocess
d=json.load(sys.stdin)
missing=[]
for g in d['data']:
    r=subprocess.run(['asc','subscriptions','list','--group',g['id'],'--output','json'],capture_output=True,text=True)
    subs=json.loads(r.stdout)
    for s in subs['data']:
        if s['attributes']['state']=='MISSING_METADATA':
            missing.append(s['attributes']['name']+' (MISSING_METADATA)')
        r2=subprocess.run(['asc','subscriptions','prices','list','--id',s['id'],'--output','json'],capture_output=True,text=True)
        prices=json.loads(r2.stdout)
        if prices['meta']['paging']['total']==0:
            missing.append(s['attributes']['name']+' (no prices)')
if missing:
    print(','.join(missing))
" 2>/dev/null || echo "CHECK_FAILED")

  if [ -z "$MISSING" ]; then
    log_pass "All subscriptions complete (metadata + prices)"
  elif [ "$MISSING" = "CHECK_FAILED" ]; then
    log_skip "Subscription check failed (API error)"
  else
    log_fail "Subscription issues: $MISSING"
  fi
else
  log_skip "US-005b not yet passed or APP_ID not found"
fi

##############################################
# GATE 4: Screenshots (>= 3 framed)
##############################################
echo ""
echo "--- Gate 4: Screenshots ---"
if [ "$(us_passes US-008)" = "true" ]; then
  FRAMED_COUNT=$(find "$APP_DIR/screenshots/framed" -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$FRAMED_COUNT" -ge 3 ]; then
    log_pass "Framed screenshots: $FRAMED_COUNT (>= 3)"
  else
    log_fail "Framed screenshots: $FRAMED_COUNT (need >= 3)"
  fi

##############################################
# GATE 4b: Screenshots must be unique (not all same image)
# Prevents CC from copying same screenshot to all slots
##############################################
if [[ "$(us_passes US-008)" == "true" ]]; then
  UNIQUE_HASHES=$(find "$APP_DIR/screenshots/framed" -name "*.png" 2>/dev/null | xargs shasum 2>/dev/null | awk '{print $1}' | sort -u | wc -l | tr -d ' ')
  TOTAL_SCREENSHOTS=$(find "$APP_DIR/screenshots/framed" -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$UNIQUE_HASHES" -ge 2 && "$TOTAL_SCREENSHOTS" -ge 3 ]]; then
    log_pass "Screenshots unique: $UNIQUE_HASHES unique of $TOTAL_SCREENSHOTS total"
  else
    log_fail "Screenshots NOT unique: all $TOTAL_SCREENSHOTS have same hash (copy-paste detected)"
  fi
else
  log_skip "Screenshot uniqueness (US-008 not passed)"
fi
else
  log_skip "US-008 not yet passed"
fi

##############################################
# GATE 5: Build status
##############################################
echo ""
echo "--- Gate 5: Build Status ---"
if [ "$(us_passes US-008)" = "true" ] && [ -n "$APP_ID" ]; then
  BUILD_STATE=$(asc builds list --app "$APP_ID" --limit 1 --output json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
if d['data']:
    print(d['data'][0]['attributes'].get('processingState','UNKNOWN'))
else:
    print('NO_BUILD')
" 2>/dev/null || echo "CHECK_FAILED")

  if [ "$BUILD_STATE" = "VALID" ]; then
    log_pass "Build processingState=VALID"
  else
    log_fail "Build processingState=$BUILD_STATE (must be VALID)"
  fi
else
  log_skip "US-008 not yet passed or APP_ID not found"
fi

##############################################
# Summary
##############################################
echo ""
echo "=========================================="
if [ "$FAIL" -eq 0 ]; then
  echo "🟢 ALL GATES PASSED — proceed to next US"
  exit 0
else
  echo "🔴 VALIDATION FAILED — CC must fix before proceeding"
  exit 1
fi
