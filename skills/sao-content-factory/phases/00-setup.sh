#!/usr/bin/env bash
# 00-setup.sh — bootstrap the per-run version dir.
# Replaces the old video orchestrator's setup. Prints `export` lines; caller:
#   eval "$(ENTITY=<slug> bash phases/00-setup.sh)"
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/sao-content-factory}"
[ -n "${ENTITY:-}" ] || { echo "ENTITY not set" >&2; exit 2; }

ENTITY_JSON="$SKILL_DIR/entities/$ENTITY.json"
[ -f "$ENTITY_JSON" ] || { echo "ENTITY_JSON not found: $ENTITY_JSON" >&2; exit 3; }

DATE=$(TZ=Asia/Tokyo date +%Y-%m-%d)
BASE="$SKILL_DIR/output/$ENTITY/$DATE"
N=1
while [ -d "$BASE/v$N" ]; do N=$((N+1)); done
VERSION_DIR="$BASE/v$N"
mkdir -p "$VERSION_DIR/docs" "$VERSION_DIR/img" "$VERSION_DIR/logs"
cp "$ENTITY_JSON" "$VERSION_DIR/docs/entity.json"

echo "export ENTITY='$ENTITY'"
echo "export ENTITY_JSON='$ENTITY_JSON'"
echo "export VERSION_DIR='$VERSION_DIR'"
echo "export JST_DATE='$DATE'"
