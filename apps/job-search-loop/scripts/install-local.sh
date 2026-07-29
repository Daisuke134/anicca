#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

PROFILE_SOURCE=""
PROVIDER="auto"
SCHEDULER="auto"
REPLACE_PROFILE=0
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ "$#" -ge 2 ]] || { print -u2 "install-local: --profile needs a path"; exit 2; }
      PROFILE_SOURCE="$2"
      shift 2
      ;;
    --provider)
      [[ "$#" -ge 2 ]] || { print -u2 "install-local: --provider needs a value"; exit 2; }
      PROVIDER="$2"
      shift 2
      ;;
    --scheduler)
      [[ "$#" -ge 2 ]] || { print -u2 "install-local: --scheduler needs a value"; exit 2; }
      SCHEDULER="$2"
      shift 2
      ;;
    --replace-profile)
      REPLACE_PROFILE=1
      shift
      ;;
    *)
      print -u2 "install-local: unknown argument: $1"
      exit 2
      ;;
  esac
done
[[ -n "$PROFILE_SOURCE" ]] || {
  print -u2 "install-local: --profile is required"
  exit 2
}

if [[ "$SCHEDULER" == "auto" ]]; then
  case "${JOB_SEARCH_PLATFORM:-$(uname -s)}" in
    Darwin) SCHEDULER="launchd" ;;
    Linux) SCHEDULER="systemd" ;;
    *)
      print -u2 "install-local: unsupported scheduler platform"
      exit 2
      ;;
  esac
fi

export PYTHONPATH="$JOB_SEARCH_APP_ROOT${PYTHONPATH:+:$PYTHONPATH}"
SETUP_ARGUMENTS=(
  --profile "$PROFILE_SOURCE"
  --provider "$PROVIDER"
  --scheduler "$SCHEDULER"
)
if [[ "$REPLACE_PROFILE" == "1" ]]; then
  SETUP_ARGUMENTS+=(--replace-profile)
fi
RECEIPT=$(
  "$JOB_SEARCH_PYTHON" -m job_search_loop.local_setup "${SETUP_ARGUMENTS[@]}"
)

case "$SCHEDULER" in
  launchd) "$SCRIPT_DIR/install-launchd.sh" ;;
  systemd) "$SCRIPT_DIR/install-systemd.sh" ;;
  none) ;;
  *)
    print -u2 "install-local: unsupported scheduler: $SCHEDULER"
    exit 2
    ;;
esac

print -r -- "$RECEIPT"
