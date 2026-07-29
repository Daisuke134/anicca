#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FETCHER="$SOURCE_DIR/fetch-x402-rs.sh"
TEST_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

[ -f "$FETCHER" ] || {
  echo "fetch-x402-rs.sh is missing" >&2
  exit 1
}

export FETCH_X402_RS_LIBRARY=1
# shellcheck source=/dev/null
source "$FETCHER"

FIXTURE_PARENT="$TEST_ROOT/archive-input"
FIXTURE_NAME="x402-rs-fixture"
FIXTURE_ROOT="$FIXTURE_PARENT/$FIXTURE_NAME"
mkdir -p "$FIXTURE_ROOT"
printf 'Apache License fixture\n' > "$FIXTURE_ROOT/LICENSE"
printf '[workspace]\nmembers = []\n' > "$FIXTURE_ROOT/Cargo.toml"
printf '# fixture lock\n' > "$FIXTURE_ROOT/Cargo.lock"
ARCHIVE="$TEST_ROOT/source.tar.gz"
COPYFILE_DISABLE=1 tar -czf "$ARCHIVE" -C "$FIXTURE_PARENT" "$FIXTURE_NAME"
ARCHIVE_SHA="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
COMMIT="1111111111111111111111111111111111111111"

WRONG_CACHE="$TEST_ROOT/wrong-cache"
if fetch_verified_tree \
  "file://$ARCHIVE" \
  "0000000000000000000000000000000000000000000000000000000000000000" \
  "$COMMIT" \
  "$WRONG_CACHE" >/dev/null 2>&1; then
  echo "wrong SHA-256 was accepted" >&2
  exit 1
fi
[ ! -e "$WRONG_CACHE/$COMMIT/source/Cargo.toml" ]

CACHE="$TEST_ROOT/cache"
TREE="$(fetch_verified_tree "file://$ARCHIVE" "$ARCHIVE_SHA" "$COMMIT" "$CACHE")"
[ "$TREE" = "$CACHE/$COMMIT/source" ]
[ -f "$TREE/LICENSE" ]
[ -f "$TREE/Cargo.lock" ]

FAKE_BIN="$TEST_ROOT/fake-bin"
mkdir -p "$FAKE_BIN"
cat > "$FAKE_BIN/curl" <<'SH'
#!/usr/bin/env bash
echo "network must not be used for a verified cache hit" >&2
exit 99
SH
chmod +x "$FAKE_BIN/curl"
PATH="$FAKE_BIN:$PATH" \
  SECOND_TREE="$(fetch_verified_tree \
    "https://invalid.example/never-requested.tar.gz" \
    "$ARCHIVE_SHA" \
    "$COMMIT" \
    "$CACHE")"
[ "$SECOND_TREE" = "$TREE" ]

DECOY="$TEST_ROOT/home/profitable-claude/x402-rs"
mkdir -p "$DECOY"
printf 'must-not-be-read\n' > "$DECOY/LOCAL_CHECKOUT_MARKER"
HOME="$TEST_ROOT/home" \
  THIRD_TREE="$(fetch_verified_tree \
    "https://invalid.example/never-requested.tar.gz" \
    "$ARCHIVE_SHA" \
    "$COMMIT" \
    "$CACHE")"
[ "$THIRD_TREE" = "$TREE" ]
[ ! -e "$TREE/LOCAL_CHECKOUT_MARKER" ]
! rg -n 'profitable-claude|anicca-project|services/facilitator/x402-rs' "$FETCHER"

printf 'PASS pinned x402-rs fetch rejects bad archives and reuses only verified cache\n'
