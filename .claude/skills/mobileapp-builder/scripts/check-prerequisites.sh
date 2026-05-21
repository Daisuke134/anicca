#!/bin/bash
# mobileapp-builder prerequisites checker
# Usage: bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh

set -euo pipefail

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_cmd() {
  local name="$1"
  local cmd="$2"
  local install="$3"
  if eval "$cmd" &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ $name${NC}"
    ((PASS++))
  else
    echo -e "${RED}❌ $name${NC}"
    echo "   → Install: $install"
    ((FAIL++))
  fi
}

check_env() {
  local name="$1"
  if [ -n "${!name:-}" ]; then
    echo -e "${GREEN}✅ $name${NC}"
    ((PASS++))
  else
    echo -e "${RED}❌ $name${NC}"
    echo "   → Add to ~/.config/mobileapp-builder/.env — see SETUP.md Section 2"
    ((FAIL++))
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  mobileapp-builder prerequisites check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Load .env if present
if [ -f ~/.config/mobileapp-builder/.env ]; then
  # shellcheck disable=SC1090
  source ~/.config/mobileapp-builder/.env
fi

# ── CLI Tools ────────────────────────────────────────────────────────
echo "[ CLI Tools ]"
check_cmd "asc" \
  "asc --version" \
  "brew install nickvdyck/tap/asc"

check_cmd "fastlane" \
  "fastlane --version" \
  "brew install fastlane"

check_cmd "greenlight" \
  "greenlight --version" \
  "cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build && sudo cp build/greenlight /usr/local/bin/"

check_cmd "imagemagick (convert)" \
  "convert --version" \
  "brew install imagemagick"

check_cmd "snapai" \
  "npx snapai --version --yes 2>/dev/null || npx snapai --version" \
  "npm install -g snapai"

check_cmd "ios-deploy" \
  "ios-deploy --version" \
  "brew install ios-deploy"

check_cmd "Python: Pillow" \
  "python3 -c 'import PIL'" \
  "pip3 install Pillow"

check_cmd "Python: PyJWT" \
  "python3 -c 'import jwt'" \
  "pip3 install PyJWT"

check_cmd "Python: requests" \
  "python3 -c 'import requests'" \
  "pip3 install requests"

echo ""

# ── Environment Variables ────────────────────────────────────────────
echo "[ Environment Variables ]"
check_env "ASC_KEY_ID"
check_env "ASC_ISSUER_ID"
check_env "ASC_KEY_PATH"
check_env "REVENUECAT_API_KEY"
check_env "MIXPANEL_TOKEN"
check_env "X_BEARER_TOKEN"
check_env "APIFY_TOKEN"
check_env "GEMINI_API_KEY"
check_env "OPENAI_API_KEY"
check_env "SLACK_BOT_TOKEN"
check_env "SLACK_APP_TOKEN"
check_env "SLACK_CHANNEL_ID"

echo ""

# ── Distribution Certificate ─────────────────────────────────────────
echo "[ Distribution Certificate ]"
if command -v asc &>/dev/null && \
   asc certificates list --type IOS_DISTRIBUTION --output json 2>/dev/null | \
   python3 -c "
import sys, json
d = json.load(sys.stdin)
valid = [c for c in d.get('data', []) if c['attributes'].get('certificateState') != 'REVOKED']
exit(0 if valid else 1)
" 2>/dev/null; then
  echo -e "${GREEN}✅ Distribution cert (valid, not REVOKED)${NC}"
  ((PASS++))
else
  echo -e "${RED}❌ Distribution cert (REVOKED or missing)${NC}"
  echo "   → Run PHASE 2.5 SIGNING PREFLIGHT in SKILL.md to create a new certificate"
  echo "   → Quick fix: asc certificates csr generate ~/Downloads/.signing/dist.csr"
  echo "                asc certificates create --certificate-type IOS_DISTRIBUTION --csr ~/Downloads/.signing/dist.csr"
  ((FAIL++))
fi

echo ""

# ── ASC API Key (.p8 file) ───────────────────────────────────────────
echo "[ Files ]"
if ls ~/Downloads/AuthKey_*.p8 &>/dev/null 2>&1; then
  echo -e "${GREEN}✅ ASC API Key (.p8 file in ~/Downloads)${NC}"
  ((PASS++))
else
  echo -e "${RED}❌ ASC API Key (.p8 file)${NC}"
  echo "   → ASC → Users and Access → Integrations → Keys → download .p8 to ~/Downloads"
  ((FAIL++))
fi

echo ""

# ── Claude Code Skills ───────────────────────────────────────────────
echo "[ Claude Code Sub-skills ]"
required_skills=("x-research" "tiktok-research" "apify-trend-analysis" "ralph-autonomous-dev" "screenshot-creator" "slack-approval" "app-icon")
for skill in "${required_skills[@]}"; do
  if npx skills list 2>/dev/null | grep -q "$skill"; then
    echo -e "${GREEN}✅ skill: $skill${NC}"
    ((PASS++))
  else
    echo -e "${RED}❌ skill: $skill${NC}"
    echo "   → Run: npx skills add Daisuke134/anicca-products@${skill} -g -y"
    ((FAIL++))
  fi
done

echo ""

# ── Summary ─────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Result: ${PASS} passed, ${FAIL} failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}🚀 All prerequisites met. Ready to build!${NC}"
  echo ""
  echo "  In Claude Code, say: \"Build an iOS app about [your idea]\""
  exit 0
else
  echo -e "${RED}🔧 Fix the ${FAIL} item(s) above, then re-run this script.${NC}"
  echo ""
  echo "  Full setup guide: SETUP.md"
  exit 1
fi
