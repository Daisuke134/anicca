#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
AUTO="$ROOT/cloud-migration/auto-sync.sh"
STATUS="$ROOT/cloud-migration/status-live.sh"
CRON="$ROOT/cloud-migration/cron-register.md"
RUNBOOK="$ROOT/docs/reference/phone-runbook.md"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
assert_file() { [[ -f "$1" ]] || fail "missing $1"; }
assert_contains() { grep -Fq -- "$2" "$1" || fail "$1 lacks: $2"; }
assert_not_contains() { ! grep -Fq -- "$2" "$1" || fail "$1 contains forbidden text: $2"; }

assert_file "$AUTO"
assert_file "$STATUS"
assert_file "$CRON"
assert_file "$RUNBOOK"

bash -n "$AUTO"
bash -n "$STATUS"
shellcheck "$AUTO" "$STATUS"

assert_contains "$AUTO" 'status-live.sh'
assert_contains "$AUTO" 'git fetch'
assert_contains "$AUTO" 'git -C "$repo" diff --cached'
assert_contains "$AUTO" 'gitleaks stdin'
assert_not_contains "$AUTO" 'gitleaks protect --staged'
assert_contains "$AUTO" 'docs'
assert_contains "$AUTO" 'find "${scan_roots[@]}"'
assert_contains "$AUTO" '-name .git -print0'
assert_contains "$AUTO" '":(exclude)$relative"'
assert_contains "$AUTO" 'state delivery-queue cron agents/anicca/agent skills workspace'
assert_contains "$AUTO" 'git -C "$repo" check-ignore -q -- "$path"'
assert_not_contains "$AUTO" 'git add -A'
assert_not_contains "$AUTO" 'jobs.json'

# Regression: an explicitly named ignored directory must not make git add fail,
# and other eligible paths must still be staged.
fixture=$(mktemp -d "${TMPDIR:-/tmp}/cloud-migration-test.XXXXXX")
trap 'rm -rf "$fixture"' EXIT
mkdir -p "$fixture/bin" "$fixture/openclaw/.git" "$fixture/anicca/.git" \
  "$fixture/project/.git" "$fixture/project/docs" "$fixture/openclaw/state" \
  "$fixture/openclaw/agents/anicca/agent/codex-home"
: >"$fixture/openclaw/state/live.json"
: >"$fixture/openclaw/agents/anicca/agent/codex-home/ignored.txt"

cat >"$fixture/bin/git" <<'EOF'
#!/usr/bin/env bash
set -u
repo=
if [[ ${1:-} == -C ]]; then repo=$2; shift 2; fi
command=${1:-}; shift || true
case "$command" in
  fetch) exit 0 ;;
  check-ignore)
    [[ ${*: -1} == agents/anicca/agent/codex-home || ${*: -1} == .worktrees ]]
    ;;
  status)
    printf '%s\0' '!! agents/anicca/agent/codex-home/' '!! .worktrees/'
    ;;
  add)
    printf '%s\n' "$*" >>"$GIT_ADD_LOG"
    exit 0
    ;;
  diff) exit 0 ;;
  *) exit 0 ;;
esac
EOF
cat >"$fixture/bin/gitleaks" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$fixture/bin/git" "$fixture/bin/gitleaks"

sync_output=$(PATH="$fixture/bin:$PATH" GIT_ADD_LOG="$fixture/git-add.log" \
  OPENCLAW_REPO="$fixture/openclaw" ANICCA_REPO="$fixture/anicca" \
  ANICCA_PROJECT_REPO="$fixture/project" COLONY_STATUS_SCRIPT="$fixture/missing-status" \
  bash "$AUTO")
[[ $(jq -r '.[] | select(.repo == "openclaw") | .status' <<<"$sync_output") == skipped ]] || \
  fail "ignored explicit path prevented staging eligible paths: $sync_output"
grep -Fq -- 'state' "$fixture/git-add.log" || fail 'eligible path was not passed to git add'
! grep -Fq -- 'agents/anicca/agent/codex-home' "$fixture/git-add.log" || \
  grep -Fq -- ':(exclude)agents/anicca/agent/codex-home/' "$fixture/git-add.log" || \
  fail 'ignored descendant was not excluded from git add'

assert_contains "$STATUS" 'colony-status.sh'
assert_contains "$STATUS" 'STATUS-live.md'

assert_contains "$CRON" 'openclaw cron list'
assert_contains "$CRON" 'openclaw cron add'
assert_contains "$CRON" '--every 30m'
assert_contains "$CRON" 'jobs.json'

for text in anicca-products anicca-dais 100.99.82.95 'launchctl list | grep anicca' 'df -h /' 'colony-status.sh' 'launchctl kickstart -k gui/501/ai.anicca.franklin-loop'; do
  assert_contains "$RUNBOOK" "$text"
done

printf 'PASS: cloud migration acceptance checks\n'
