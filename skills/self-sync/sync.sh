#!/usr/bin/env bash
set -u

REPO_PATHS=(
  "${AGENTS_REPO_PATH:-$HOME/.agents}"
  "${CLAUDE_SKILLS_REPO_PATH:-$HOME/.claude/skills}"
)
REPO_BRANCHES=(
  "${AGENTS_REPO_BRANCH:-main}"
  "${CLAUDE_SKILLS_REPO_BRANCH:-main}"
)

LOG_FILE=${SYNC_LOG_FILE:-$HOME/.openclaw/logs/agents-skills-sync.log}
LOCK_DIR=${SYNC_LOCK_DIR:-${TMPDIR:-/tmp}/ai.anicca.agents-skills-sync.lock}
TELEGRAM_CHAT_ID=8547730585

mkdir -p "$(dirname -- "$LOG_FILE")"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

timestamp() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

warn_telegram() {
  message=$1
  if test "${TELEGRAM_STUB:-0}" = 1; then
    printf 'TELEGRAM_STUB: %s\n' "$message"
    return 0
  fi
  openclaw message send --channel telegram --target "$TELEGRAM_CHAT_ID" --message "$message"
}

release_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  printf '%s sync already running; skipping\n' "$(timestamp)"
  exit 0
fi
trap release_lock EXIT INT TERM

prepare_agents_db() {
  repo=$1
  ignore_line='/skills/agmsg/db/'
  ignore_file="$repo/.gitignore"

  if test "$repo" != "${REPO_PATHS[0]}"; then
    return 0
  fi
  touch "$ignore_file"
  if ! grep -Fqx "$ignore_line" "$ignore_file"; then
    printf '\n# agmsg runtime database\n%s\n' "$ignore_line" >>"$ignore_file"
  fi
  git -C "$repo" rm -r --cached --ignore-unmatch --quiet skills/agmsg/db
}

has_staged_secret() {
  repo=$1
  git -C "$repo" diff --cached --name-only --diff-filter=ACMR \
    | grep -Eiq '(^|/)\.env($|[./])|(^|/)[^/]*credentials[^/]*$|\.pem$|(^|/)secret[^/]*$|\.key$'
}

sync_repo() {
  repo=$1
  branch=$2
  label=$(basename -- "$repo")

  if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    printf '%s [%s] not a git repository; skipping\n' "$(timestamp)" "$repo"
    return 0
  fi

  printf '%s [%s] sync start\n' "$(timestamp)" "$repo"
  if ! git -C "$repo" pull --rebase --autostash origin "$branch"; then
    repo_git_dir=$(git -C "$repo" rev-parse --absolute-git-dir)
    if test -d "$repo_git_dir/rebase-merge" \
      || test -d "$repo_git_dir/rebase-apply"; then
      git -C "$repo" rebase --abort || true
      warn_telegram "github-sync conflict in $label; rebase aborted"
    else
      warn_telegram "github-sync pull failed in $label; retrying next interval"
    fi
    return 0
  fi

  prepare_agents_db "$repo"
  git -C "$repo" add -A

  if git -C "$repo" diff --cached --quiet; then
    printf '%s [%s] no local changes\n' "$(timestamp)" "$repo"
    return 0
  fi

  if has_staged_secret "$repo"; then
    secret_names=$(git -C "$repo" diff --cached --name-only --diff-filter=ACMR \
      | grep -Ei '(^|/)\.env($|[./])|(^|/)[^/]*credentials[^/]*$|\.pem$|(^|/)secret[^/]*$|\.key$' \
      | tr '\n' ' ')
    git -C "$repo" reset --quiet
    warn_telegram "github-sync secret guard blocked $label: $secret_names"
    return 0
  fi

  git -C "$repo" commit -m "chore: automatic skills sync"
  if ! git -C "$repo" push origin "$branch"; then
    warn_telegram "github-sync push failed in $label; retrying next interval"
    return 0
  fi
  printf '%s [%s] sync complete\n' "$(timestamp)" "$repo"
}

index=0
while test "$index" -lt "${#REPO_PATHS[@]}"; do
  sync_repo "${REPO_PATHS[$index]}" "${REPO_BRANCHES[$index]}"
  index=$((index + 1))
done
