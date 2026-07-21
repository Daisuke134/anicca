#!/usr/bin/env bash
set -euo pipefail
child_file=${GIG_FIXTURE_CHILD_FILE:?}
sleep 300 &
child=$!
printf '%s\n' "$child" > "$child_file"
while :; do sleep 1; done
