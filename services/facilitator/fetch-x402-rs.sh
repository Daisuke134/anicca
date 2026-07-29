#!/usr/bin/env bash
# Fetch, verify, and build the one pinned x402-rs facilitator dependency.
set -euo pipefail

X402_RS_COMMIT="d439a91bda1caee486b0f841c4c6dd265fbee9df"
X402_RS_ARCHIVE_SHA256="7b24f6f67561c29174a03d2e5f35068e0e7c8d2c14451794cd0ac08877d57bac"
X402_RS_ARCHIVE_URL="https://codeload.github.com/x402-rs/x402-rs/tar.gz/$X402_RS_COMMIT"

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo "fetch-x402-rs.sh: shasum or sha256sum is required" >&2
    return 1
  fi
}

tree_digest() {
  python3 - "$1" <<'PY'
import hashlib
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
digest = hashlib.sha256()
for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
    relative = path.relative_to(root)
    if relative.parts and relative.parts[0] == "target":
        continue
    if path.is_symlink():
        raise SystemExit(f"symlink is not allowed in verified source: {relative}")
    if not path.is_file():
        continue
    digest.update(relative.as_posix().encode("utf-8"))
    digest.update(b"\0")
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    digest.update(b"\0")
print(digest.hexdigest())
PY
}

verified_cache_tree() {
  local final_root="$1"
  local expected_sha="$2"
  local expected_commit="$3"
  local source_root="$final_root/source"
  local archive="$final_root/source.tar.gz"

  [ -f "$archive" ] || return 1
  [ -f "$final_root/archive.sha256" ] || return 1
  [ -f "$final_root/tree.sha256" ] || return 1
  [ -f "$final_root/commit" ] || return 1
  [ -f "$source_root/LICENSE" ] || return 1
  [ -f "$source_root/Cargo.lock" ] || return 1
  [ -f "$source_root/Cargo.toml" ] || return 1
  [ "$(tr -d '[:space:]' < "$final_root/archive.sha256")" = "$expected_sha" ] || return 1
  [ "$(tr -d '[:space:]' < "$final_root/commit")" = "$expected_commit" ] || return 1
  [ "$(sha256_file "$archive")" = "$expected_sha" ] || return 1
  [ "$(tree_digest "$source_root")" = \
    "$(tr -d '[:space:]' < "$final_root/tree.sha256")" ] || return 1
  printf '%s\n' "$source_root"
}

validate_archive_members() {
  python3 - "$1" <<'PY'
import pathlib
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
with tarfile.open(archive, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members:
        raise SystemExit("archive is empty")
    prefixes = set()
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 1:
            raise SystemExit("archive contains an unsafe path")
        prefixes.add(path.parts[0])
        if member.issym() or member.islnk():
            raise SystemExit("archive contains a link")
    if len(prefixes) != 1:
        raise SystemExit("archive must have exactly one root directory")
PY
}

fetch_verified_tree() {
  local archive_url="$1"
  local expected_sha="$2"
  local commit="$3"
  local cache_root="$4"
  local final_root="$cache_root/$commit"
  local temp_root
  local actual_sha

  [[ "$expected_sha" =~ ^[0-9a-f]{64}$ ]] || {
    echo "fetch-x402-rs.sh: invalid pinned SHA-256" >&2
    return 2
  }
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || {
    echo "fetch-x402-rs.sh: invalid pinned commit" >&2
    return 2
  }
  command -v curl >/dev/null 2>&1 || {
    echo "fetch-x402-rs.sh: curl is required" >&2
    return 2
  }
  command -v tar >/dev/null 2>&1 || {
    echo "fetch-x402-rs.sh: tar is required" >&2
    return 2
  }
  command -v python3 >/dev/null 2>&1 || {
    echo "fetch-x402-rs.sh: python3 is required" >&2
    return 2
  }

  if verified_cache_tree "$final_root" "$expected_sha" "$commit"; then
    return 0
  fi

  mkdir -p "$cache_root"
  if [ -e "$final_root" ]; then
    rm -rf "$final_root"
  fi
  temp_root="$(mktemp -d "$cache_root/.${commit}.tmp.XXXXXX")"
  mkdir -p "$temp_root/source"

  if ! curl --fail --location --retry 3 --silent --show-error \
    "$archive_url" -o "$temp_root/source.tar.gz"; then
    rm -rf "$temp_root"
    echo "fetch-x402-rs.sh: pinned archive download failed" >&2
    return 1
  fi
  actual_sha="$(sha256_file "$temp_root/source.tar.gz")"
  if [ "$actual_sha" != "$expected_sha" ]; then
    rm -rf "$temp_root"
    echo "fetch-x402-rs.sh: pinned archive SHA-256 mismatch" >&2
    return 1
  fi
  if ! validate_archive_members "$temp_root/source.tar.gz"; then
    rm -rf "$temp_root"
    echo "fetch-x402-rs.sh: pinned archive layout is unsafe" >&2
    return 1
  fi
  if ! tar -xzf "$temp_root/source.tar.gz" \
    --strip-components=1 -C "$temp_root/source"; then
    rm -rf "$temp_root"
    echo "fetch-x402-rs.sh: pinned archive extraction failed" >&2
    return 1
  fi
  if [ ! -f "$temp_root/source/LICENSE" ] ||
    [ ! -f "$temp_root/source/Cargo.lock" ] ||
    [ ! -f "$temp_root/source/Cargo.toml" ]; then
    rm -rf "$temp_root"
    echo "fetch-x402-rs.sh: pinned archive is missing required source files" >&2
    return 1
  fi

  printf '%s\n' "$expected_sha" > "$temp_root/archive.sha256"
  printf '%s\n' "$commit" > "$temp_root/commit"
  tree_digest "$temp_root/source" > "$temp_root/tree.sha256"
  mv "$temp_root" "$final_root"
  verified_cache_tree "$final_root" "$expected_sha" "$commit"
}

build_x402_binary() {
  local source_root="$1"
  local target_root="$2"
  local binary="$target_root/release/x402-facilitator"

  if [ ! -x "$binary" ]; then
    command -v cargo >/dev/null 2>&1 || {
      echo "fetch-x402-rs.sh: cargo is required to build x402-rs" >&2
      return 2
    }
    echo "building pinned x402-facilitator at $source_root" >&2
    (
      cd "$source_root"
      CARGO_TARGET_DIR="$target_root" cargo build \
        --package x402-facilitator \
        --features chain-eip155,chain-solana \
        --release \
        --locked
    )
  fi
  [ -x "$binary" ] || {
    echo "fetch-x402-rs.sh: build produced no executable" >&2
    return 1
  }
  printf '%s\n' "$binary"
}

main() {
  local cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/life-manager/x402-rs"
  local source_root
  source_root="$(fetch_verified_tree \
    "$X402_RS_ARCHIVE_URL" \
    "$X402_RS_ARCHIVE_SHA256" \
    "$X402_RS_COMMIT" \
    "$cache_root")"
  build_x402_binary "$source_root" "$cache_root/$X402_RS_COMMIT/target"
}

if [ "${FETCH_X402_RS_LIBRARY:-0}" != "1" ]; then
  main "$@"
fi
