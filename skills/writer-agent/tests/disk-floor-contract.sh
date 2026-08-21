#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DAILY="$ROOT/skills/writer-agent/article-daily.sh"
RESUME="$ROOT/skills/writer-agent/scripts/article-resume-pending.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Force the real host below an intentionally high threshold in an isolated
# HOME/state tree. Both owners must fail before creating a run or publication.
mkdir -p "$TMP/home" "$TMP/state/runs"
mkdir -p "$TMP/home/.openclaw/skills/_shared/scripts"
cat >"$TMP/home/.openclaw/skills/_shared/scripts/telegram-notify.sh" <<'SH'
telegram_notify() { :; }
SH
set +e
HOME="$TMP/home" \
  ARTICLE_ROOT="$ROOT/skills/writer-agent" \
  ARTICLE_STATE_DIR="$TMP/state" \
  ARTICLE_OWNER_FENCE_ACTIVE=1 \
  ARTICLE_DISK_MIN_FREE_BYTES=999999999999 \
  bash "$DAILY"
creator_rc=$?
set -e
if [[ "$creator_rc" -ne 1 ]]; then
  echo "expected creator disk floor refusal" >&2
  exit 1
fi
if find "$TMP/state/runs" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  echo "creator created a run before disk refusal" >&2
  exit 1
fi

set +e
HOME="$TMP/home" \
  ARTICLE_ROOT="$ROOT/skills/writer-agent" \
  ARTICLE_STATE_DIR="$TMP/state" \
  ARTICLE_RESUME_LOG="$TMP/resume.log" \
  ARTICLE_OWNER_FENCE_ACTIVE=1 \
  ARTICLE_RESUME_MIN_FREE_BYTES=999999999999 \
  bash "$RESUME"
resume_rc=$?
set -e
if [[ "$resume_rc" -ne 1 ]]; then
  echo "expected resume disk floor refusal" >&2
  exit 1
fi
grep -F 'disk floor blocked publication' "$TMP/resume.log" >/dev/null
[[ ! -e "$TMP/state/.article-daily.lockdir" ]]

for invalid_floor in 0 1 536870911; do
  set +e
  HOME="$TMP/home" \
    ARTICLE_ROOT="$ROOT/skills/writer-agent" \
    ARTICLE_STATE_DIR="$TMP/state" \
    ARTICLE_OWNER_FENCE_ACTIVE=1 \
    ARTICLE_DISK_MIN_FREE_BYTES="$invalid_floor" \
    bash "$DAILY"
  invalid_creator_rc=$?
  set -e
  if [[ "$invalid_creator_rc" -ne 1 ]]; then
    echo "expected creator to reject disk floor $invalid_floor" >&2
    exit 1
  fi

  set +e
  HOME="$TMP/home" \
    ARTICLE_ROOT="$ROOT/skills/writer-agent" \
    ARTICLE_STATE_DIR="$TMP/state" \
    ARTICLE_RESUME_LOG="$TMP/resume-invalid-$invalid_floor.log" \
    ARTICLE_OWNER_FENCE_ACTIVE=1 \
    ARTICLE_DISK_MIN_FREE_BYTES="$invalid_floor" \
    bash "$RESUME"
  invalid_resume_rc=$?
  set -e
  if [[ "$invalid_resume_rc" -ne 1 ]]; then
    echo "expected resume to reject disk floor $invalid_floor" >&2
    exit 1
  fi
done

for invalid_kib in 0 1 524287 not-a-number; do
  set +e
  HOME="$TMP/home" \
    ARTICLE_ROOT="$ROOT/skills/writer-agent" \
    ARTICLE_STATE_DIR="$TMP/state" \
    ARTICLE_OWNER_FENCE_ACTIVE=1 \
    GIG_DISK_HEADROOM_KIB="$invalid_kib" \
    ARTICLE_DISK_MIN_FREE_BYTES=999999999999 \
    bash "$DAILY"
  invalid_creator_rc=$?
  set -e
  if [[ "$invalid_creator_rc" -ne 1 ]]; then
    echo "expected creator to reject GIG disk floor $invalid_kib" >&2
    exit 1
  fi

  set +e
  HOME="$TMP/home" \
    ARTICLE_ROOT="$ROOT/skills/writer-agent" \
    ARTICLE_STATE_DIR="$TMP/state" \
    ARTICLE_RESUME_LOG="$TMP/resume-gig-invalid-$invalid_kib.log" \
    ARTICLE_OWNER_FENCE_ACTIVE=1 \
    GIG_DISK_HEADROOM_KIB="$invalid_kib" \
    ARTICLE_DISK_MIN_FREE_BYTES=999999999999 \
    bash "$RESUME"
  invalid_resume_rc=$?
  set -e
  if [[ "$invalid_resume_rc" -ne 1 ]]; then
    echo "expected resume to reject GIG disk floor $invalid_kib" >&2
    exit 1
  fi
done

echo 'PASS: creator and resume fail with rc=1 before external effects below the canonical disk floor'
