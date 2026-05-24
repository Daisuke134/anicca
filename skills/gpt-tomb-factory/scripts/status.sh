#!/usr/bin/env bash
SKILL_DIR="$HOME/.openclaw/skills/gpt-tomb-factory"
echo "=== gpt-tomb-factory status ==="
echo "Stripe products: 4 live"
[ -f "$SKILL_DIR/data/products.json" ] && jq -r '.products[] | "  \(.slug) · \(.amount) \(.currency) · \(.payment_link)"' "$SKILL_DIR/data/products.json"
