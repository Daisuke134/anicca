#!/bin/bash
# ralph.sh — snarktank/ralph complete copy
# Source: https://github.com/snarktank/ralph/blob/main/ralph.sh
# Quote: "for i in $(seq 1 $MAX_ITERATIONS); do
#   OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr)"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ITERATIONS="${1:-20}"

# Source secrets from .env (Twelve-Factor App: https://12factor.net/config)
if [ -f ~/.config/mobileapp-builder/.env ]; then
  set -a
  source ~/.config/mobileapp-builder/.env
  set +a
fi

echo "🏭 ralph.sh 起動: MAX_ITERATIONS=$MAX_ITERATIONS" >> /dev/stderr
echo "🏭 作業ディレクトリ: $SCRIPT_DIR" >> /dev/stderr

for i in $(seq 1 $MAX_ITERATIONS); do
  echo "" >> /dev/stderr
  echo "🏭 ========================================" >> /dev/stderr
  echo "🏭 Iteration $i / $MAX_ITERATIONS 開始: $(date)" >> /dev/stderr
  echo "🏭 ========================================" >> /dev/stderr

  OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true

  echo "" >> /dev/stderr
  echo "🏭 Iteration $i 終了: $(date)" >> /dev/stderr

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo "🏭 ✅ COMPLETE 検出。全 US 完了。" >> /dev/stderr
    exit 0
  fi

  echo "🏭 sleep 2..." >> /dev/stderr
  sleep 2
done

echo "🏭 ❌ MAX_ITERATIONS ($MAX_ITERATIONS) に到達。完了せず。" >> /dev/stderr
exit 1
