#!/usr/bin/env bash
# run-local.sh — sandboxed experiment runner.
# Usage: bash scripts/run-local.sh <plan.json> <results.json>
# AUTO_RESEARCH_DRY_RUN=true to skip Docker entirely.
set -euo pipefail

PLAN="${1:?plan.json required}"
RESULTS="${2:?results.json required}"
DRY="${AUTO_RESEARCH_DRY_RUN:-false}"

if [ ! -f "$PLAN" ]; then
  echo "run-local: plan not found: $PLAN" >&2
  exit 66
fi

IMAGE="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print((d.get("sandbox") or {}).get("image", "ghcr.io/sakana-ai/research-sandbox:latest"))' "$PLAN")"
WALL="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print((d.get("sandbox") or {}).get("wallclock_s", 1800))' "$PLAN")"
MEM="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print((d.get("sandbox") or {}).get("memory", "4g"))' "$PLAN")"

if [ "$DRY" = "true" ]; then
  cat <<EOF
[DRY_RUN] would: docker run --rm --network=none --memory=$MEM --cpus=2 --pids-limit=512 \\
                 --ulimit cpu=$WALL -v "$PLAN":/work/plan.json:ro -v "$RESULTS":/work/results.json \\
                 $IMAGE
EOF
  printf '{"status": "dry_run_skipped", "image": "%s"}\n' "$IMAGE" > "$RESULTS"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "run-local: docker not installed on host." >&2
  exit 127
fi

mkdir -p "$(dirname "$RESULTS")"
docker run --rm \
  --network=none \
  --memory="$MEM" \
  --cpus=2 \
  --pids-limit=512 \
  --ulimit cpu="$WALL" \
  -v "$PLAN":/work/plan.json:ro \
  -v "$(dirname "$RESULTS")":/work/out \
  "$IMAGE"
echo "run-local: docker exited cleanly. results at $RESULTS"
