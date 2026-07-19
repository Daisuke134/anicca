#!/usr/bin/env bash

capafy_ig_accounts_file() {
  printf '%s\n' "${CAPAFY_IG_ACCOUNTS_FILE:-$HOME/.cloak/clip-accounts-capafy.json}"
}

_resolve_capafy_ig_account_field() {
  local accounts_path="${1:-$(capafy_ig_accounts_file)}"
  local field="$2"
  local python_bin="${CAPAFY_ACCOUNT_STATE_PYTHON:-/opt/homebrew/bin/python3}"
  [ -x "$python_bin" ] || python_bin="$(command -v python3)"
  "$python_bin" - "$accounts_path" "$field" <<'PY' 2>/dev/null
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

resolve_capafy_ig_handle() {
  _resolve_capafy_ig_account_field "${1:-$(capafy_ig_accounts_file)}" handle
}

resolve_capafy_ig_port() {
  _resolve_capafy_ig_account_field "${1:-$(capafy_ig_accounts_file)}" port
}

capafy_ig_provision_reason() {
  local handle="$1"
  local cooked_marker="$2"
  if [ -f "$cooked_marker" ]; then
    printf '%s\n' "cooked-marker"
  elif [ -z "$handle" ]; then
    printf '%s\n' "no-active-account"
  fi
}
