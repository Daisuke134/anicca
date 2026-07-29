#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
PINNED_SHA="82a60300b65e3f9357c6b8910dbdbdab2241f7e1"
REPOSITORY="https://github.com/Daisuke134/ai-job-search.git"

mkdir -p "${JOB_SEARCH_FRAMEWORK_ROOT:h}"
chmod 700 "${JOB_SEARCH_FRAMEWORK_ROOT:h}"
if [[ ! -d "$JOB_SEARCH_FRAMEWORK_ROOT/.git" ]]; then
  git clone "$REPOSITORY" "$JOB_SEARCH_FRAMEWORK_ROOT"
fi
git -C "$JOB_SEARCH_FRAMEWORK_ROOT" fetch origin
git -C "$JOB_SEARCH_FRAMEWORK_ROOT" checkout --detach "$PINNED_SHA"
test "$(git -C "$JOB_SEARCH_FRAMEWORK_ROOT" rev-parse HEAD)" = "$PINNED_SHA"
