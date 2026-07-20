#!/usr/bin/env bash
set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
OPENCLAW_REPO=${OPENCLAW_REPO:-"$HOME/.openclaw"}
ANICCA_REPO=${ANICCA_REPO:-"$HOME/anicca"}
ANICCA_PROJECT_REPO=${ANICCA_PROJECT_REPO:-"$HOME/anicca-project"}
COMMIT_MESSAGE=${SYNC_COMMIT_MESSAGE:-"chore: sync live assets $(date -u '+%Y-%m-%dT%H:%M:%SZ')"}

results='[]'

record() {
  local repo=$1 status=$2 detail=${3:-}
  results=$(jq -c --arg repo "$repo" --arg status "$status" --arg detail "$detail" \
    '. + [{repo:$repo,status:$status,detail:$detail}]' <<<"$results")
}

scan_staged() {
  local repo=$1
  if gitleaks stdin --help >/dev/null 2>&1; then
    (set -o pipefail
      git -C "$repo" diff --cached --binary --no-ext-diff --diff-filter=ACMRTUXB |
        gitleaks stdin --redact --gitleaks-ignore-path "$repo" >/dev/null)
  else
    (set -o pipefail
      git -C "$repo" diff --cached --binary --no-ext-diff --diff-filter=ACMRTUXB |
        gitleaks detect --pipe --redact --gitleaks-ignore-path "$repo" >/dev/null)
  fi
}

sync_repo() {
  local name=$1 repo=$2
  shift 2
  local paths=("$@") add_pathspecs=() scan_roots=() detail git_marker embedded_dir relative path

  if [[ ! -d "$repo/.git" ]]; then
    record "$name" error "not a git repository: $repo"
    return
  fi
  if ! detail=$(git -C "$repo" fetch 2>&1); then
    record "$name" error "git fetch failed: ${detail//$'\n'/ }"
    return
  fi
  for path in "${paths[@]}"; do
    if [[ -e "$repo/$path" ]] && ! git -C "$repo" check-ignore -q -- "$path"; then
      add_pathspecs+=("$path")
      scan_roots+=("$repo/$path")
    fi
  done
  if ((${#add_pathspecs[@]} == 0)); then
    record "$name" skipped "no eligible paths"
    return
  fi
  if ((${#scan_roots[@]})); then
    while IFS= read -r -d '' git_marker; do
      embedded_dir=${git_marker%/.git}
      relative=${embedded_dir#"$repo"/}
      # ignored dirs never get descended into by git add; naming them
      # (even as :(exclude)) trips the addIgnoredFile fatal — skip them
      git -C "$repo" check-ignore -q -- "$relative" && continue
      add_pathspecs+=(":(exclude)$relative")
    done < <(find "${scan_roots[@]}" -mindepth 2 -name .git -print0)
  fi
  if ! detail=$(git -C "$repo" add -- "${add_pathspecs[@]}" 2>&1); then
    record "$name" error "git add failed: ${detail//$'\n'/ }"
    return
  fi
  if git -C "$repo" diff --cached --quiet; then
    record "$name" skipped "no staged changes"
    return
  fi
  if ! detail=$(scan_staged "$repo" 2>&1); then
    git -C "$repo" restore --staged -- "${add_pathspecs[@]}" >/dev/null 2>&1 || true
    record "$name" error "gitleaks failed: ${detail//$'\n'/ }"
    return
  fi
  if ! detail=$(git -C "$repo" commit -m "$COMMIT_MESSAGE" 2>&1); then
    record "$name" error "git commit failed: ${detail//$'\n'/ }"
    return
  fi
  if ! detail=$(git -C "$repo" push 2>&1); then
    record "$name" error "git push failed: ${detail//$'\n'/ }"
    return
  fi
  record "$name" pushed "committed and pushed"
}

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' '[{"repo":"all","status":"error","detail":"jq is required"}]'
  exit 1
fi
if ! command -v gitleaks >/dev/null 2>&1; then
  printf '%s\n' '[{"repo":"all","status":"error","detail":"gitleaks is required"}]'
  exit 1
fi

if ! detail=$(ANICCA_PROJECT_REPO="$ANICCA_PROJECT_REPO" "$SCRIPT_DIR/status-live.sh" 2>&1); then
  record status-live error "${detail//$'\n'/ }"
fi

# OpenClaw stages only designated live asset directories; configuration,
# credentials, identity, logs, and gateway cron storage are deliberately excluded.
sync_repo openclaw "$OPENCLAW_REPO" state delivery-queue cron agents/anicca/agent skills workspace
sync_repo anicca "$ANICCA_REPO" .
sync_repo anicca-project "$ANICCA_PROJECT_REPO" docs

printf '%s\n' "$results"
