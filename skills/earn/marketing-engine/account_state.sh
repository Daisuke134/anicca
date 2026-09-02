#!/usr/bin/env bash

resolve_ig_account_field() {
  local state_file="$1" field="$2"
  local python_bin="${IG_ACCOUNT_STATE_PYTHON:-$(command -v python3)}"
  "$python_bin" - "$state_file" "$field" <<'PY' 2>/dev/null
import json, sys
try:
    accounts = json.load(open(sys.argv[1]))
except Exception:
    accounts = []
active = {"publisher_ready", "posted", "measuring", "commercial"}
usable = [a for a in accounts if a.get("status") in active and a.get("handle")]
if usable and usable[-1].get(sys.argv[2]) is not None:
    print(usable[-1][sys.argv[2]])
PY
}

count_ig_usable_accounts() {
  local state_file="$1"
  local python_bin="${IG_ACCOUNT_STATE_PYTHON:-$(command -v python3)}"
  "$python_bin" - "$state_file" <<'PY' 2>/dev/null
import json, sys
try:
    accounts = json.load(open(sys.argv[1]))
except Exception:
    accounts = []
active = {"setup", "publisher_ready", "posted", "measuring", "commercial"}
print(sum(a.get("status") in active for a in accounts if isinstance(a, dict)))
PY
}

resolve_ig_handle() { resolve_ig_account_field "$1" handle; }
resolve_ig_port() { resolve_ig_account_field "$1" port; }
resolve_ig_session_owner() { resolve_ig_account_field "$1" publisher; }
resolve_ig_lifecycle_status() { resolve_ig_account_field "$1" status; }

ig_provision_reason() {
  local handle="$1" cooked_marker="$2"
  if [ -f "$cooked_marker" ]; then printf '%s\n' cooked-marker
  elif [ -z "$handle" ]; then printf '%s\n' no-active-account
  fi
}
