#!/bin/zsh

job_search_load_private_env() {
  local key="$1"
  local env_file="${2:-$JOB_SEARCH_PRIVATE_ENV}"
  [[ -n "${(P)key:-}" ]] && return 0
  [[ -f "$env_file" ]] || return 1

  local value
  value=$("$JOB_SEARCH_PYTHON" - "$env_file" "$key" <<'PY'
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:].lstrip()
    name, separator, encoded = line.partition("=")
    if separator and name.strip() == target:
        values = shlex.split(encoded, comments=True, posix=True)
        if len(values) != 1:
            raise SystemExit(2)
        print(values[0], end="")
        raise SystemExit(0)
raise SystemExit(1)
PY
  ) || return 1
  typeset -gx "$key=$value"
}
