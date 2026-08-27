#!/usr/bin/env bash
# cfo-core hourly runner (cron entrypoint).
#   1) build-anicca → data/anicca-cfo.json
#   2) bridge to ~/anicca-products/apps/landing/public/dashboard.json (old schema)
#   3) git add + commit + push → Netlify auto-deploy
#   4) Slack #metrics に簡易 1-行 status
# Bank scrape は cfo-daily に任せ、ここは Link + RC + Stripe のみ (軽量)。
set -uo pipefail

SK=~/.openclaw/skills/cfo-core
DATA=$SK/data
LANDING=~/anicca-products/apps/landing
SLACK_CH="C091G3PKHL2"
set -a; [ -f ~/.openclaw/.env ] && source ~/.openclaw/.env; set +a

echo "🕐 cfo-anicca-hourly @ $(date -u +%FT%TZ)" >&2

# 1) build-anicca (内部で Link scrape + RC + Stripe を走らせる)
if timeout 360 node "$SK/build-anicca.js" > "$DATA/anicca-cfo.json" 2>"$DATA/anicca-hourly.err"; then
  echo "✅ build-anicca.js OK" >&2
else
  echo "❌ build-anicca.js failed:" >&2
  cat "$DATA/anicca-hourly.err" >&2
  exit 1
fi

# 2) bridge → old dashboard.json schema (TheSpend.tsx が読む shape)
node "$SK/bridge-to-dashboard.js" "$DATA/anicca-cfo.json" "$LANDING/public/dashboard.json" \
  2>>"$DATA/anicca-hourly.err" || { echo "❌ bridge failed" >&2; exit 1; }
echo "✅ bridge → $LANDING/public/dashboard.json" >&2

# 3) git push (差分あれば) — robust against unstaged dirty files + upstream divergence
cd ~/anicca-products
if git diff --quiet apps/landing/public/dashboard.json; then
  echo "ℹ️  no diff vs HEAD, skipping push" >&2
else
  # stash all dirty changes (including untracked) so rebase doesn't choke on them
  STASHED=0
  if ! git diff-index --quiet HEAD -- || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    git stash push --include-untracked -m "cfo-hourly-autostash $(date -u +%FT%TZ)" 2>&1 | tail -1 >&2 && STASHED=1
  fi
  # fast-forward to latest origin/main
  git fetch origin main 2>&1 | tail -1 >&2
  git rebase origin/main 2>&1 | tail -2 >&2 || git rebase --abort
  # re-run the bridge in case rebase overwrote dashboard.json
  node "$SK/bridge-to-dashboard.js" "$DATA/anicca-cfo.json" "$LANDING/public/dashboard.json" >/dev/null 2>&1
  git add apps/landing/public/dashboard.json
  git commit -m "chore(cfo): hourly refresh $(date -u +%FT%TZ) [skip ci]" 2>&1 | tail -1 >&2
  git push origin main 2>&1 | tail -2 >&2
  echo "✅ pushed to git" >&2
  # restore stashed work (best-effort, ignore conflicts)
  if [ "$STASHED" = "1" ]; then
    git stash pop 2>&1 | tail -1 >&2 || echo "ℹ️  stash pop had conflicts (ignored)" >&2
  fi

  # Netlify は anicca-products の git auto-deploy が壊れているので
  # netlify CLI で明示 deploy する (manual deploy mode)
  # out/ を作って dashboard.json を反映 → --no-build で deploy
  mkdir -p "$LANDING/out"
  cp "$LANDING/public/dashboard.json" "$LANDING/out/dashboard.json"
  cd "$LANDING"
  netlify deploy --prod --no-build --dir=out --site=d67537f0-21bd-477e-ac1a-323f7ec6d5cd 2>&1 \
    | grep -E "Deployed to|Deploy URL|Error" | head -3 >&2
  echo "✅ Netlify deploy fired" >&2
fi

# 4) Slack 簡易 status (full diary は cfo-daily 担当・hourly は 1 line)
MAKES=$(jq -r '.makes.monthly_total_usd // 0' "$DATA/anicca-cfo.json")
SPENDS=$(jq -r '.spends.anicca_runtime_usd // 0' "$DATA/anicca-cfo.json")
NET=$(jq -r '.lifeline.net_monthly_usd // 0' "$DATA/anicca-cfo.json")
STATUS=$(jq -r '.lifeline.status // "?"' "$DATA/anicca-cfo.json")
MSG=$(printf "🕐 *CFO hourly* %s · makes \$%s · spends \$%s · net \$%s (%s) · → aniccaai.com refresh" \
       "$(date +%H:%M)" "$MAKES" "$SPENDS" "$NET" "$STATUS")
curl -sS -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" -H 'Content-Type: application/json; charset=utf-8' \
  -d "$(jq -n --arg ch "$SLACK_CH" --arg t "$MSG" '{channel:$ch,text:$t}')" \
  | jq -r 'if .ok then "✅ slack hourly ok ts=\(.ts)" else "❌ slack hourly: \(.error)" end' >&2

echo "🟢 cfo-anicca-hourly done @ $(date -u +%FT%TZ)" >&2
