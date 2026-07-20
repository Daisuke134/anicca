#!/usr/bin/env bash
set -euo pipefail

readonly RULESYNC_VERSION="14.1.0"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
STAGING_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/rulesync-apply.XXXXXX")"
readonly STAGING_ROOT
readonly STAGING_REPO="$STAGING_ROOT/repo"
readonly STAGING_HOME="$STAGING_ROOT/home"
readonly NPM_CACHE="$STAGING_ROOT/npm-cache"

cleanup() {
  rm -rf -- "$STAGING_ROOT"
}
trap cleanup EXIT

run_rulesync() {
  HOME="$STAGING_HOME" npm_config_cache="$NPM_CACHE" \
    npx -y "rulesync@$RULESYNC_VERSION" "$@"
}

backup_once() {
  local source_path="$1"
  local backup_path="$source_path.bak"

  if [[ -e "$source_path" || -L "$source_path" ]]; then
    if [[ ! -e "$backup_path" && ! -L "$backup_path" ]]; then
      cp -a -- "$source_path" "$backup_path"
    fi
  fi
}

cd "$REPO_ROOT"
mkdir -p "$STAGING_REPO/.claude" "$STAGING_HOME" "$NPM_CACHE"

for required_path in CLAUDE.md .mcp.json .claude/rules .claude/skills .claude/commands; do
  if [[ ! -e "$required_path" ]]; then
    printf 'Required input is missing: %s\n' "$required_path" >&2
    exit 1
  fi
done

cp -a -- CLAUDE.md .mcp.json "$STAGING_REPO/"
cp -a -- .claude/rules .claude/skills .claude/commands "$STAGING_REPO/.claude/"

# Most repository skill links use ../../.agents/skills. Preserve that layout in staging.
if [[ -e .agents ]]; then
  cp -a -- .agents "$STAGING_REPO/"
fi

broken_links="$(find -L "$STAGING_REPO/.claude/skills" -type l -print)"
if [[ -n "$broken_links" ]]; then
  printf 'Broken skill symlinks in staging; refusing partial import:\n%s\n' "$broken_links" >&2
  exit 1
fi

actual_version="$(run_rulesync --version)"
if [[ "$actual_version" != "$RULESYNC_VERSION" ]]; then
  printf 'rulesync version mismatch: expected %s, got %s\n' \
    "$RULESYNC_VERSION" "$actual_version" >&2
  exit 1
fi

(
  cd "$STAGING_REPO"
  run_rulesync import --targets claudecode --features '*'
  run_rulesync generate --targets codexcli --features '*' --dry-run
  run_rulesync generate --targets codexcli --features '*'
  run_rulesync generate --targets codexcli --features '*' --check
)

backup_once "$REPO_ROOT/.rulesync"
backup_once "$REPO_ROOT/AGENTS.md"
backup_once "$REPO_ROOT/.agents"
backup_once "$REPO_ROOT/.codex"

# These exact paths are the Phase 1 allowlist. Replace only after staging succeeds.
rm -rf -- "$REPO_ROOT/.rulesync"
cp -a -- "$STAGING_REPO/.rulesync" "$REPO_ROOT/.rulesync"

before_names="$STAGING_ROOT/before-names"
after_names="$STAGING_ROOT/after-names"
git status --porcelain=v1 | sed 's/^...//' | sort > "$before_names"

run_rulesync generate --targets codexcli --features '*'
run_rulesync generate --targets codexcli --features '*' --check
git status --porcelain=v1 | sed 's/^...//' | sort > "$after_names"

new_paths="$STAGING_ROOT/new-paths"
comm -13 "$before_names" "$after_names" > "$new_paths"
if awk '
  $0 == "AGENTS.md" { next }
  $0 == ".rulesync" || index($0, ".rulesync/") == 1 { next }
  $0 == ".agents" || index($0, ".agents/") == 1 { next }
  $0 == ".codex" || index($0, ".codex/") == 1 { next }
  $0 ~ /\.bak(\/|$)/ { next }
  { print; invalid = 1 }
  END { exit invalid }
' "$new_paths" >&2; then
  :
else
  printf 'Generation touched a path outside the Phase 1 allowlist.\n' >&2
  exit 1
fi

first_digest="$STAGING_ROOT/first-digest"
second_digest="$STAGING_ROOT/second-digest"
find AGENTS.md .agents .codex -type f -print0 2>/dev/null \
  | sort -z | xargs -0 shasum > "$first_digest"
run_rulesync generate --targets codexcli --features '*'
find AGENTS.md .agents .codex -type f -print0 2>/dev/null \
  | sort -z | xargs -0 shasum > "$second_digest"
cmp -s "$first_digest" "$second_digest"

git diff --check -- AGENTS.md .agents .codex .rulesync
printf 'rulesync Phase 1 applied locally. Review the allowlisted diff before commit.\n'
