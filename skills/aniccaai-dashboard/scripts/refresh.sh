#!/usr/bin/env bash
# Orchestrate dashboard data fetch + merge + deploy.
# Outputs ~/anicca-products/apps/landing/public/dashboard.json

set -uo pipefail  # NOT -e: keep going if a fetcher fails (use last_known fallback)

SKILL=~/.openclaw/skills/aniccaai-dashboard
LANDING=~/anicca-products/apps/landing
OUT=$LANDING/public/dashboard.json
BACKUP=$SKILL/data/dashboard-last.json
TMP=$(mktemp -d)

# Load envs from anicca-monk-factory .env (existing source of secrets)
if [ -f ~/anicca-monk-factory/.env ]; then
  set -a
  # shellcheck disable=SC1090
  source ~/anicca-monk-factory/.env
  set +a
fi

# Allow overrides from openclaw env
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

echo "🔄 dashboard refresh starting at $(date -u +%FT%TZ)..."

# Run fetchers in parallel
node "$SKILL/scripts/fetch-stripe.js"     > "$TMP/stripe.json"     2> "$TMP/stripe.err"     & PID_STRIPE=$!
node "$SKILL/scripts/fetch-rc.js"          > "$TMP/rc.json"         2> "$TMP/rc.err"          & PID_RC=$!
node "$SKILL/scripts/fetch-postiz.js"      > "$TMP/postiz.json"     2> "$TMP/postiz.err"      & PID_POSTIZ=$!
node "$SKILL/scripts/fetch-followers.js"   > "$TMP/followers.json"  2> "$TMP/followers.err"   & PID_FOL=$!
node "$SKILL/scripts/fetch-spend.js"       > "$TMP/spend.json"      2> "$TMP/spend.err"       & PID_SPEND=$!

wait $PID_STRIPE $PID_RC $PID_POSTIZ $PID_FOL $PID_SPEND

# Print errors summary
for f in stripe rc postiz followers spend; do
  if [ -s "$TMP/$f.err" ]; then
    echo "⚠️  $f errors:"
    cat "$TMP/$f.err"
  fi
done

# Merge into final dashboard.json
node "$SKILL/scripts/merge.js" \
  --stripe "$TMP/stripe.json" \
  --rc "$TMP/rc.json" \
  --postiz "$TMP/postiz.json" \
  --followers "$TMP/followers.json" \
  --spend "$TMP/spend.json" \
  --config "$SKILL/data/config.json" \
  > "$TMP/dashboard.json" 2> "$TMP/merge.err"

if [ ! -s "$TMP/dashboard.json" ]; then
  echo "❌ merge failed:"
  cat "$TMP/merge.err"
  if [ -f "$BACKUP" ]; then
    echo "↩️  using last_known backup"
    cp "$BACKUP" "$OUT"
  fi
  exit 1
fi

# Save backup + deploy
cp "$TMP/dashboard.json" "$BACKUP"
mkdir -p "$(dirname "$OUT")"
cp "$TMP/dashboard.json" "$OUT"

echo "✅ dashboard.json written to $OUT"
echo "preview:"
jq '.' "$OUT" | head -40

# Git commit + push (Netlify auto-build)
cd ~/anicca-products
if git diff --quiet apps/landing/public/dashboard.json; then
  echo "ℹ️  no changes vs HEAD; skipping commit"
else
  git add apps/landing/public/dashboard.json
  git -c credential.helper= commit -m "chore(dashboard): refresh $(date -u +%FT%TZ)" || true
  git -c credential.helper= push origin "$(git symbolic-ref --short HEAD)" 2>&1 | tail -3
fi

rm -rf "$TMP"
echo "🟢 done at $(date -u +%FT%TZ)"
