#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SELECTOR="$ROOT/scripts/select-next-topic.sh"
QUEUE="$(mktemp -d)"
trap 'rm -rf "$QUEUE"' EXIT

cat >"$QUEUE/blocked.md" <<'EOF'
---
created: 2026-01-01
priority: 1
---
blocked
EOF
cat >"$QUEUE/alternate.md" <<'EOF'
---
created: 2026-01-02
priority: 1
---
alternate
EOF

first="$(bash "$SELECTOR" "$QUEUE")"
[ "$first" = "$QUEUE/blocked.md" ]

same_pass="$(bash "$SELECTOR" "$QUEUE" --exclude-basename blocked.md)"
[ "$same_pass" = "$QUEUE/alternate.md" ]

next_pass="$(bash "$SELECTOR" "$QUEUE")"
[ "$next_pass" = "$QUEUE/blocked.md" ]

cat >"$QUEUE/lane-b-carry-over.md" <<'EOF'
---
created: 2025-01-01
priority: 0
---
lane B carry-over
EOF
cat >"$QUEUE/lane-b-alternate.md" <<'EOF'
---
created: 2025-01-02
priority: 0
---
lane B alternate
EOF
lane_b_same_pass="$(bash "$SELECTOR" "$QUEUE" \
  --exclude-basename blocked.md \
  --exclude-basename lane-b-carry-over.md)"
[ "$lane_b_same_pass" = "$QUEUE/lane-b-alternate.md" ]
lane_b_next_pass="$(bash "$SELECTOR" "$QUEUE")"
[ "$lane_b_next_pass" = "$QUEUE/lane-b-carry-over.md" ]

printf 'FIRST=%s\nSAME_PASS=%s\nNEXT_PASS=%s\nLANE_B_SAME_PASS=%s\nLANE_B_NEXT_PASS=%s\n' \
  "$(basename "$first")" "$(basename "$same_pass")" "$(basename "$next_pass")" \
  "$(basename "$lane_b_same_pass")" "$(basename "$lane_b_next_pass")"
