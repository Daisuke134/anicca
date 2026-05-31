#!/usr/bin/env bash
# anicca-earn-bounty/scripts/run.sh
# heartbeat 経由 から 1 beat = scan → select → solve → submit を 完走 (= P2 1 件)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
cd "$SKILL_DIR"

echo "=== anicca-earn-bounty heartbeat run @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# 1. scan
echo "[1/4] scan..."
bash scripts/scan.sh >/dev/null 2>&1 && echo "  ✓ scan done" || { echo "  ✗ scan failed" >&2; exit 1; }

# 2. select
echo "[2/4] select..."
SELECT_OUT=$(bash scripts/select.sh 2>&1) && echo "  ✓ select done" || {
  EC=$?
  echo "  - select returned $EC (no candidates / Claude declined)"
  # Not fatal, just skip this beat
  exit 0
}

# 3. solve
echo "[3/4] solve..."
SOLVE_OUT=$(bash scripts/solve.sh 2>&1) && echo "  ✓ solve done" || {
  EC=$?
  echo "  - solve returned $EC (no GitHub token / claude / push failed)"
  if [ "$EC" = "2" ]; then
    echo "  Note: anicca-github-account skill must run first to get GITHUB_TOKEN"
  fi
  exit 0
}

# 4. submit
echo "[4/4] submit..."
SUBMIT_OUT=$(bash scripts/submit.sh 2>&1) && echo "  ✓ submit done" || {
  EC=$?
  echo "  - submit returned $EC"
  exit 0
}

echo "=== beat complete ==="
echo "$SUBMIT_OUT" | tail -5
