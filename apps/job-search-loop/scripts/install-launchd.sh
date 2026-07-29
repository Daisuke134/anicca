#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

UID_VALUE="$(id -u)"
mkdir -p "$JOB_SEARCH_LAUNCH_AGENT_DIR" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 "$JOB_SEARCH_STATE_ROOT" "$JOB_SEARCH_STATE_ROOT/logs"

if [[ "${JOB_SEARCH_SKIP_BOOTSTRAP:-0}" != "1" ]]; then
  "$JOB_SEARCH_APP_ROOT/scripts/bootstrap-framework.sh"
fi

for name in ai.anicca.job-search-daily ai.anicca.job-search-inbox; do
  template="$JOB_SEARCH_APP_ROOT/launchd/$name.plist"
  installed="$JOB_SEARCH_LAUNCH_AGENT_DIR/$name.plist"
  program="${name##*-}"
  "$JOB_SEARCH_PYTHON" - \
    "$template" "$installed" \
    "$JOB_SEARCH_APP_ROOT/scripts/run-$program.sh" \
    "$JOB_SEARCH_STATE_ROOT/logs/$program.out.log" \
    "$JOB_SEARCH_STATE_ROOT/logs/$program.err.log" <<'PY'
import os
import plistlib
import sys
from pathlib import Path

template, output, program, stdout, stderr = map(Path, sys.argv[1:])
value = plistlib.loads(template.read_bytes())
value["ProgramArguments"] = [str(program)]
value["StandardOutPath"] = str(stdout)
value["StandardErrorPath"] = str(stderr)
temporary = output.with_suffix(".plist.tmp")
temporary.write_bytes(plistlib.dumps(value, sort_keys=False))
os.chmod(temporary, 0o644)
temporary.replace(output)
PY
  "$JOB_SEARCH_PLUTIL" -lint "$installed" >/dev/null
done

if [[ "${JOB_SEARCH_SKIP_LAUNCHCTL:-0}" != "1" ]]; then
  for name in ai.anicca.job-search-daily ai.anicca.job-search-inbox; do
    "$JOB_SEARCH_LAUNCHCTL" bootout "gui/$UID_VALUE/$name" 2>/dev/null || true
    "$JOB_SEARCH_LAUNCHCTL" bootstrap \
      "gui/$UID_VALUE" "$JOB_SEARCH_LAUNCH_AGENT_DIR/$name.plist"
  done
fi
