#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SETTINGS="${HOME}/.claude/settings.json"
SERENA_CONFIG="${HOME}/.serena/serena_config.yml"
ZSHRC="${HOME}/.zshrc"
SETTINGS_PATCH="${SCRIPT_DIR}/settings-user-patch.json"
SERENA_PATCH="${SCRIPT_DIR}/serena-excluded-tools.yml"

require_file() {
  if [[ ! -f "$1" ]]; then
    printf 'missing required file: %s\n' "$1" >&2
    exit 1
  fi
}

backup_once() {
  local source_file="$1"
  local backup_file="${source_file}.bak"
  if [[ ! -e "${backup_file}" ]]; then
    cp -p "${source_file}" "${backup_file}"
    printf 'backup: %s\n' "${backup_file}"
  fi
}

require_file "${USER_SETTINGS}"
require_file "${SERENA_CONFIG}"
require_file "${ZSHRC}"
require_file "${SETTINGS_PATCH}"
require_file "${SERENA_PATCH}"
command -v jq >/dev/null 2>&1 || {
  printf 'jq is required\n' >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  printf 'python3 is required\n' >&2
  exit 1
}

backup_once "${USER_SETTINGS}"
settings_tmp="$(mktemp "${TMPDIR:-/tmp}/floor-settings.XXXXXX")"
serena_tmp="$(mktemp "${TMPDIR:-/tmp}/floor-serena.XXXXXX")"
trap 'rm -f "${settings_tmp}" "${serena_tmp}"' EXIT

jq -s '
  .[0] as $base
  | .[1] as $patch
  | ($base * $patch)
  | .permissions.deny = (
      (($base.permissions.deny // []) + ($patch.permissions.deny // []))
      | unique
    )
' "${USER_SETTINGS}" "${SETTINGS_PATCH}" >"${settings_tmp}"
jq empty "${settings_tmp}"
mv "${settings_tmp}" "${USER_SETTINGS}"
printf 'applied: %s\n' "${USER_SETTINGS}"

sed -i.bak 's/ENABLE_TOOL_SEARCH=false/ENABLE_TOOL_SEARCH=true/g' "${ZSHRC}"
printf 'applied: %s (backup: %s.bak)\n' "${ZSHRC}" "${ZSHRC}"

backup_once "${SERENA_CONFIG}"
python3 - "${SERENA_CONFIG}" "${SERENA_PATCH}" "${serena_tmp}" <<'PY'
from pathlib import Path
import re
import sys

config_path, patch_path, output_path = map(Path, sys.argv[1:])
config = config_path.read_text(encoding="utf-8")
patch = patch_path.read_text(encoding="utf-8").rstrip() + "\n"
pattern = re.compile(
    r"(?m)^excluded_tools:[^\n]*\n(?:^[ \t]+-[^\n]*\n)*"
)
if not pattern.search(config):
    raise SystemExit("excluded_tools key not found in Serena config")
updated = pattern.sub(patch, config, count=1)
Path(output_path).write_text(updated, encoding="utf-8")
PY
mv "${serena_tmp}" "${SERENA_CONFIG}"
printf 'applied: %s\n' "${SERENA_CONFIG}"

printf '%s\n' 'manual: review floor-reduction/hooks-audit.md and apply its SessionStart patch only after Fable approval.'
