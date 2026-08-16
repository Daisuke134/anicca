#!/usr/bin/env bash
# Read-only aggregate entrypoint for the four direct Coconala revenue owners.
set -uo pipefail
PY=/opt/homebrew/bin/python3
UID_NOW="$(id -u)"
WAKE="${WAKE_ID:-$(date +%s)}"
LABELS=(
  ai.anicca.hf-gig-apply-direct
  ai.anicca.hf-gig-reply-detector
  ai.anicca.hf-gig-paid-direct
  ai.anicca.hf-gig-storefront-direct
)
STATUS=""
for label in "${LABELS[@]}"; do
  if launchctl print "gui/${UID_NOW}/${label}" >/dev/null 2>&1; then
    STATUS+="${label}=loaded "
  else
    STATUS+="${label}=missing "
  fi
done
"$PY" - "$WAKE" "$STATUS" "$HOME/gig/storefront-direct/current.json" <<'PY'
import json, pathlib, sys
wake, raw, current_path = sys.argv[1:]
owners = dict(item.split("=", 1) for item in raw.split() if "=" in item)
current = {}
try:
    current = json.loads(pathlib.Path(current_path).read_text())
except (OSError, json.JSONDecodeError):
    pass
print(json.dumps({
    "wallet": None, "source": "gig", "task": "direct-owner-status",
    "funding": "human(¥→MUFG)", "earn_usdc": 0, "cost_usdc": 0,
    "wake": wake, "owners": owners,
    "storefront": {k: current.get(k) for k in ("status", "mode", "reason", "observed_at_epoch")},
    "note": "Coconala direct owners; read-only status; no legacy tmux/gig-pass",
}, ensure_ascii=False, separators=(",", ":")))
PY
