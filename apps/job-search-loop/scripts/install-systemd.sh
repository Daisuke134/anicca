#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

JOB_SEARCH_SYSTEMD_USER_DIR="${JOB_SEARCH_SYSTEMD_USER_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}"
JOB_SEARCH_SYSTEMCTL="${JOB_SEARCH_SYSTEMCTL:-$(command -v systemctl)}"
JOB_SEARCH_SYSTEMD_ANALYZE="${JOB_SEARCH_SYSTEMD_ANALYZE:-$(command -v systemd-analyze 2>/dev/null || true)}"

mkdir -p "$JOB_SEARCH_SYSTEMD_USER_DIR"
chmod 700 "$JOB_SEARCH_SYSTEMD_USER_DIR"
for name in daily inbox learning; do
  for kind in service timer; do
    template="$JOB_SEARCH_APP_ROOT/systemd/ai.anicca.job-search-$name.$kind"
    installed="$JOB_SEARCH_SYSTEMD_USER_DIR/ai.anicca.job-search-$name.$kind"
    "$JOB_SEARCH_PYTHON" - \
      "$template" "$installed" \
      "$JOB_SEARCH_APP_ROOT/scripts/run-$name.sh" \
      "$JOB_SEARCH_REPO_ROOT" <<'PY'
import os
import sys
from pathlib import Path

template, output, program, repo_root = map(Path, sys.argv[1:])
text = template.read_text(encoding="utf-8")
replacements = {
    "__JOB_SEARCH_PROGRAM__": str(program).replace("\\", "\\\\").replace('"', '\\"'),
    "__JOB_SEARCH_REPO_ROOT__": str(repo_root).replace("\\", "\\\\").replace('"', '\\"'),
}
for marker, value in replacements.items():
    text = text.replace(marker, value)
if "__JOB_SEARCH_" in text:
    raise SystemExit("unresolved systemd template marker")
temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
try:
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(output)
finally:
    temporary.unlink(missing_ok=True)
PY
  done
done

if [[ "${JOB_SEARCH_SKIP_SYSTEMD_ANALYZE:-0}" != "1" \
  && -n "$JOB_SEARCH_SYSTEMD_ANALYZE" ]]; then
  "$JOB_SEARCH_SYSTEMD_ANALYZE" --user verify \
    "$JOB_SEARCH_SYSTEMD_USER_DIR"/ai.anicca.job-search-*.service \
    "$JOB_SEARCH_SYSTEMD_USER_DIR"/ai.anicca.job-search-*.timer
fi

if [[ "${JOB_SEARCH_SKIP_SYSTEMCTL:-0}" != "1" ]]; then
  "$JOB_SEARCH_SYSTEMCTL" --user daemon-reload
  "$JOB_SEARCH_SYSTEMCTL" --user enable --now \
    ai.anicca.job-search-daily.timer \
    ai.anicca.job-search-inbox.timer \
    ai.anicca.job-search-learning.timer
fi
