#!/usr/bin/env bash

resolve_ig_account_field() {
  local state_file="$1"
  local field="$2"
  local python_bin="${IG_ACCOUNT_STATE_PYTHON:-/opt/homebrew/bin/python3}"
  [ -x "$python_bin" ] || python_bin="$(command -v python3)"
  "$python_bin" - "$state_file" "$field" <<'PY' 2>/dev/null
import json
import sys

path, field = sys.argv[1:3]
try:
    with open(path) as f:
        accounts = json.load(f)
except Exception:
    accounts = []

usable = []
for account in accounts if isinstance(accounts, list) else []:
    status = str(account.get("status") or "").lower()
    if status not in {"ready", "warming"}:
        continue
    if any(account.get(key) for key in ("poisoned", "poisoned_at", "frozen_at", "blocked_at")):
        continue
    if not account.get("handle"):
        continue
    usable.append(account)

if usable:
    value = usable[-1].get(field)
    if value is not None:
        print(value)
PY
}

resolve_ig_handle() {
  resolve_ig_account_field "$1" handle
}

resolve_ig_port() {
  resolve_ig_account_field "$1" port
}

ig_provision_reason() {
  local handle="$1"
  local cooked_marker="$2"
  if [ -f "$cooked_marker" ]; then
    printf '%s\n' "cooked-marker"
  elif [ -z "$handle" ]; then
    printf '%s\n' "no-active-account"
  fi
}
