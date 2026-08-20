#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/skills/article-writer/tests/_exact8-fixture.sh"
WORKER="$ROOT/skills/article-writer/scripts/zenn-deferred-worker.sh"
CONTROL="$ROOT/skills/article-writer/scripts/zenn-deferred-control.py"
TMP="$(mktemp -d /tmp/zenn-isolated-git.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
RUN=run-isolated
LEDGER="$TMP/articles.jsonl"
ARTIFACT="$TMP/runs/$RUN/gates/zenn-deferred.json"
mkdir -p "$(dirname "$ARTIFACT")" "$TMP/seed/articles"

printf '%s\n' '---' 'title: "Remote title"' 'published: true' '---' '# remote' >"$TMP/seed/articles/isolated-slug-1.md"
git init --bare "$TMP/remote.git" >/dev/null
git -C "$TMP/seed" init -b main >/dev/null
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test add articles
git -C "$TMP/seed" -c user.name=test -c user.email=test@example.test commit -m seed >/dev/null
git -C "$TMP/seed" remote add origin "$TMP/remote.git"
git -C "$TMP/seed" push origin main >/dev/null
git clone "$TMP/remote.git" "$TMP/repo" >/dev/null 2>&1
git -C "$TMP/repo" switch -c wrong-branch >/dev/null
printf 'local ahead must not publish\n' >"$TMP/repo/local-ahead"
git -C "$TMP/repo" -c user.name=test -c user.email=test@example.test add local-ahead
git -C "$TMP/repo" -c user.name=test -c user.email=test@example.test commit -m local-ahead >/dev/null
printf 'staged must not publish\n' >"$TMP/repo/staged-secret"
git -C "$TMP/repo" add staged-secret
python3 "$CONTROL" create --artifact "$ARTIFACT" --markdown-file "$TMP/repo/articles/isolated-slug-1.md" --slug isolated-slug-1
exact8_init_state "$ROOT" "$TMP/runs/$RUN" "$LEDGER" "$RUN" topic-1 isolated-slug-1
python3 "$CONTROL" handoff --repo "$TMP/repo" --ledger "$LEDGER" --run-id "$RUN" --artifact "$ARTIFACT" >/dev/null
printf '%s\n' '---' 'title: "Staged wrong title"' 'published: false' '---' >"$TMP/repo/articles/isolated-slug-1.md"
git -C "$TMP/repo" add articles/isolated-slug-1.md
printf '{"articles":[{"slug":"old","published_at":"2026-07-20T00:00:00Z"}]}\n' >"$TMP/api.json"
printf '#!/usr/bin/env bash\nexit 1\n' >"$TMP/reality.sh"; chmod +x "$TMP/reality.sh"

BASE=$(git --git-dir="$TMP/remote.git" rev-parse main)
BASE_TREE=$(git --git-dir="$TMP/remote.git" rev-parse main^{tree})
bash "$WORKER" --ledger "$LEDGER" --runs-root "$TMP/runs" --repo "$TMP/repo" \
  --expected-remote "$TMP/remote.git" --api-json "$TMP/api.json" --now 2026-07-21T01:00:00Z \
  --reality-gate "$TMP/reality.sh" --lock-file "$TMP/worker.lock" \
  --publication-lock-dir "$TMP/publication.lockdir" \
  --backlog-state "$TMP/backlog.json" --log "$TMP/worker.log"
REMOTE_HEAD=$(git --git-dir="$TMP/remote.git" rev-parse main)
test "$(git --git-dir="$TMP/remote.git" rev-parse "$REMOTE_HEAD^")" = "$BASE"
test "$(git --git-dir="$TMP/remote.git" rev-parse "$REMOTE_HEAD^{tree}")" = "$BASE_TREE"
test "$(git -C "$TMP/repo" branch --show-current)" = wrong-branch
test "$(git -C "$TMP/repo" diff --cached --name-only | sort | tr '\n' ' ')" = 'articles/isolated-slug-1.md staged-secret '
if git --git-dir="$TMP/remote.git" cat-file -e main:local-ahead 2>/dev/null || git --git-dir="$TMP/remote.git" cat-file -e main:staged-secret 2>/dev/null; then
  echo 'FAIL: local branch/index content reached remote main' >&2; exit 1
fi

# A remote advancement between commit-tree and push causes a non-FF rejection and remains pending.
git clone "$TMP/remote.git" "$TMP/racer" >/dev/null 2>&1
cat >"$TMP/race.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf 'race\n' >'$TMP/racer/race'
git -C '$TMP/racer' -c user.name=test -c user.email=test@example.test add race
git -C '$TMP/racer' -c user.name=test -c user.email=test@example.test commit -m race >/dev/null
git -C '$TMP/racer' push origin main >/dev/null
EOF
chmod +x "$TMP/race.sh"
bash "$WORKER" --ledger "$LEDGER" --runs-root "$TMP/runs" --repo "$TMP/repo" \
  --expected-remote "$TMP/remote.git" --api-json "$TMP/api.json" --now 2026-07-21T01:05:00Z \
  --before-push-hook "$TMP/race.sh" --reality-gate "$TMP/reality.sh" \
  --lock-file "$TMP/worker.lock" --publication-lock-dir "$TMP/publication.lockdir" \
  --backlog-state "$TMP/backlog.json" --log "$TMP/worker.log"
test "$(jq -r .status "$ARTIFACT")" = pending
test "$(jq -r .last_action "$ARTIFACT")" = network-error
test "$(git --git-dir="$TMP/remote.git" show main:race)" = race

echo 'PASS: retry commit is remote-main-only and concurrent advancement stays pending'
