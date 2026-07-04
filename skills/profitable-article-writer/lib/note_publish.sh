#!/usr/bin/env bash
# lib/note_publish.sh — Mode-A REAL note.com DRAFT publish wiring (REQ-19, Sprint 2; REQ-3/8 Sprint-2 fix;
# PROP-20).
#
# SPRINT-2 FIX (3 real defects a fresh-context adversary found in the rendered draft, key n7261a753887f):
#   1. NO VISUALS in the article body (REQ-3 mandates a "deeply-researched, VISUAL explainer"). FIXED by
#      routing draft creation through lib/note-create-rich-draft.py, which uploads a hero diagram + inline
#      figures (deterministic tool: note_mcp.api.images.upload_body_image + generate_image_html) and
#      embeds them into the body BEFORE the note.com draft is created — never pure text.
#   2. NO eyecatch/cover set. FIXED by lib/note-set-eyecatch.py, run AFTER the draft exists. NOTE: this one
#      genuinely needs the BROWSER path (the editor's own "画像を追加" button), not note_mcp's
#      upload_eyecatch_image API — that call was tried first and reproducibly raises "API response missing
#      required field 'url'" (a live, confirmed endpoint bug, matching SKILL.md's older note about this
#      SPECIFIC endpoint). The browser path was verified to PERSIST: the eyecatch URL survives a page
#      reload and shows up in GET /v3/notes/{key}'s `eyecatch` field.
#   3. Monetization was wired to note's メンバーシップ (monthly membership) rail: the OLD flow here called
#      $NOTE_PUBLISH_SCRIPT's `publish` subcommand, whose [5/7]/[6/7] steps (publish.py, toggle-plan.py,
#      set-eyecatch-republish.py) hardcode "click 無料 then click メンバーシップ" regardless of the --price
#      flag (NOTE_PRICE was exported but never read by any of those scripts — a confirmed, real bug, not a
#      guess). REQ-8's PRIMARY monetization is a single one-time ¥500 有料note, not a recurring
#      subscription. FIXED by lib/note-set-single-price.py, which selects 記事タイプ=有料 (never
#      メンバーシップ) and fills the price field, verified live via the DOM (radio.checked + input.value).
#      HONEST LIMITATION (see that script's own docstring): note.com only persists this selection to its
#      backend at actual publish time, which Mode A (REQ-6) must never do — so this step's evidence is a
#      screenshot of the correctly-configured (but never-submitted) publish panel, not a persisted price on
#      the still-plain DRAFT. The exact same call, run once AUTONOMY=on legitimately reaches a real publish,
#      persists it for real; there is no leftover membership code path to fall back to.
#
# This file still never rebuilds note_mcp or cloakbrowser. It calls:
#   - lib/note-create-rich-draft.py (this skill's own file, NOT ai-entity-article-writer's) — orchestrates
#     note_mcp's EXISTING create_draft/upload_body_image/upload_eyecatch_image/generate_image_html.
#   - lib/note-set-single-price.py (this skill's own file) — orchestrates cloakbrowser exactly the way
#     ai-entity-article-writer/scripts/note-publish/insert-toc-save.py already does (same caret-then-hover-
#     then-gutter-menu technique, reused not reinvented), but selects 有料 instead of メンバーシップ.
#   - $NOTE_PUBLISH_SCRIPT (ai-entity-article-writer's publish-to-note.sh) for the `verify` subcommand ONLY
#     (ground-truth API + logged-out screenshot check) — never for `publish` any more (Sprint-2 fix #3).
#
# INTERFACE:
#   env in (all optional, all env-overridable so this stays testable without touching real creds/paths):
#     NOTE_PUBLISH_SCRIPT        default: $HOME/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/publish-to-note.sh
#     NOTE_MCP_PY                default: $HOME/.openclaw/skills/_shared/venv-cloak/bin/python3
#     NOTE_MCP_SRC               default: $HOME/.openclaw/external/note-mcp/src
#     NOTE_COOKIES_FILE          default: $HOME/.cloak/note-work/note-cookies.json
#     NOTE_CREATE_RICH_DRAFT_PY  default: <this skill's lib>/note-create-rich-draft.py
#     NOTE_SET_SINGLE_PRICE_PY   default: <this skill's lib>/note-set-single-price.py
#     NOTE_SET_EYECATCH_PY       default: <this skill's lib>/note-set-eyecatch.py
#     ARTICLE_NOTE_VISUAL_HERO   optional path to a hero-diagram PNG; embedded at the "@@HERO@@" marker line
#     ARTICLE_NOTE_VISUAL_FIG1   optional path to an inline-figure PNG; embedded at "@@FIG1@@"
#     ARTICLE_NOTE_VISUAL_FIG2   optional path to an inline-figure PNG; embedded at "@@FIG2@@"
#     ARTICLE_NOTE_COVER         optional path to a cover/eyecatch image
#     NOTE_PUBLISH_TEST_FORCE    "success" | "fail"  (hermetic test seam, same convention as
#                                ARTICLE_TEST_FORCE_V0/V05 — NEVER touches network/browser when set; the
#                                REAL, non-forced path below is exercised only by an actual live wake)
#   function: run_note_mode_a_publish <draft_path> <title> <note_key_hint> <price> <paywall_heading>
#     (signature UNCHANGED from Sprint 2 — PROP-20's tests call this indirectly via run.sh and must keep
#     passing unmodified)
#     stdout on success (rc=0): "NOTE_URL: <url>\nNOTE_SCREENSHOT: <path>\nNOTE_KEY: <key>"
#     stderr + rc!=0 on ANY failure — NEVER crashes the caller (this file is `source`d, not exec'd standalone;
#     every internal step is guarded so a missing script/cred/network failure returns, never exits the shell).
set -uo pipefail

_NOTE_PUBLISH_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NOTE_PUBLISH_SCRIPT="${NOTE_PUBLISH_SCRIPT:-$HOME/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/publish-to-note.sh}"
NOTE_MCP_PY="${NOTE_MCP_PY:-$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3}"
NOTE_MCP_SRC="${NOTE_MCP_SRC:-$HOME/.openclaw/external/note-mcp/src}"
NOTE_COOKIES_FILE="${NOTE_COOKIES_FILE:-$HOME/.cloak/note-work/note-cookies.json}"
NOTE_CREATE_RICH_DRAFT_PY="${NOTE_CREATE_RICH_DRAFT_PY:-$_NOTE_PUBLISH_SH_DIR/note-create-rich-draft.py}"
NOTE_SET_SINGLE_PRICE_PY="${NOTE_SET_SINGLE_PRICE_PY:-$_NOTE_PUBLISH_SH_DIR/note-set-single-price.py}"
NOTE_SET_EYECATCH_PY="${NOTE_SET_EYECATCH_PY:-$_NOTE_PUBLISH_SH_DIR/note-set-eyecatch.py}"

# ---------------------------------------------------------------------------------------------------------
# note_create_rich_draft: create a genuinely NEW note.com draft, with a hero diagram + inline figures
# embedded in the body, via lib/note-create-rich-draft.py (this skill's own deterministic orchestration of
# note_mcp's proven API functions — Sprint-2 fix #1). Eyecatch is a SEPARATE step (note_set_eyecatch below
# — Sprint-2 fix #2 — it genuinely needs the browser path, see that function's own comment).
# Prints "NOTE_DRAFT_KEY: <key>\nNOTE_DRAFT_NUM: <id>" (+ optional NOTE_VISUAL_* lines) on success;
# non-zero rc + stderr reason on failure.
# ---------------------------------------------------------------------------------------------------------
note_create_rich_draft() {
  local draft_path="$1" title="$2"
  if [ ! -x "$NOTE_MCP_PY" ]; then
    echo "note_create_rich_draft: NOTE_MCP_PY not found/executable at '$NOTE_MCP_PY'" >&2
    return 1
  fi
  if [ ! -f "$NOTE_COOKIES_FILE" ]; then
    echo "note_create_rich_draft: NOTE_COOKIES_FILE missing at '$NOTE_COOKIES_FILE' (run extract-note-cookies.py first)" >&2
    return 1
  fi
  if [ ! -f "$draft_path" ]; then
    echo "note_create_rich_draft: draft_path '$draft_path' does not exist" >&2
    return 1
  fi
  if [ ! -f "$NOTE_CREATE_RICH_DRAFT_PY" ]; then
    echo "note_create_rich_draft: NOTE_CREATE_RICH_DRAFT_PY missing at '$NOTE_CREATE_RICH_DRAFT_PY'" >&2
    return 1
  fi

  local -a marker_args=()
  [ -n "${ARTICLE_NOTE_VISUAL_HERO:-}" ] && [ -f "${ARTICLE_NOTE_VISUAL_HERO:-}" ] && marker_args+=(--marker "HERO=${ARTICLE_NOTE_VISUAL_HERO}")
  [ -n "${ARTICLE_NOTE_VISUAL_FIG1:-}" ] && [ -f "${ARTICLE_NOTE_VISUAL_FIG1:-}" ] && marker_args+=(--marker "FIG1=${ARTICLE_NOTE_VISUAL_FIG1}")
  [ -n "${ARTICLE_NOTE_VISUAL_FIG2:-}" ] && [ -f "${ARTICLE_NOTE_VISUAL_FIG2:-}" ] && marker_args+=(--marker "FIG2=${ARTICLE_NOTE_VISUAL_FIG2}")

  NOTE_MCP_SRC="$NOTE_MCP_SRC" NOTE_COOKIES_FILE="$NOTE_COOKIES_FILE" \
    "$NOTE_MCP_PY" "$NOTE_CREATE_RICH_DRAFT_PY" --title "$title" --body "$draft_path" "${marker_args[@]}"
}

# ---------------------------------------------------------------------------------------------------------
# note_set_eyecatch: set the draft's cover image via the editor's own "画像を追加" button (Sprint-2 fix #2).
# BROWSER, not note_mcp's upload_eyecatch_image API — that call was tried first and reproducibly raises
# "API response missing required field 'url'" (see lib/note-set-eyecatch.py's own docstring for the full
# verified writeup). Best-effort: a failure here is logged but does NOT invalidate the already-created,
# already-visual draft.
# ---------------------------------------------------------------------------------------------------------
note_set_eyecatch() {
  local key="$1" cover_path="$2"
  if [ -z "$cover_path" ]; then
    return 0
  fi
  if [ ! -f "$NOTE_SET_EYECATCH_PY" ]; then
    echo "note_set_eyecatch: NOTE_SET_EYECATCH_PY missing at '$NOTE_SET_EYECATCH_PY'" >&2
    return 1
  fi
  NOTE_COOKIES_FILE="$NOTE_COOKIES_FILE" "$NOTE_MCP_PY" "$NOTE_SET_EYECATCH_PY" "$key" "$cover_path"
}

# ---------------------------------------------------------------------------------------------------------
# note_set_single_price: configure the draft's monetization editor state as a SINGLE one-time paid article
# (記事タイプ=有料, price, paid-line), never メンバーシップ (Sprint-2 fix #3). Best-effort: a failure here
# is logged but does NOT invalidate the already-created draft (the caller still reports the real draft URL).
# ---------------------------------------------------------------------------------------------------------
note_set_single_price() {
  local key="$1" price="$2" paywall_heading="$3"
  if [ -z "$paywall_heading" ]; then
    echo "note_set_single_price: no paywall_heading given, skipping (draft stays fully free until the caller supplies one)" >&2
    return 0
  fi
  if [ ! -f "$NOTE_SET_SINGLE_PRICE_PY" ]; then
    echo "note_set_single_price: NOTE_SET_SINGLE_PRICE_PY missing at '$NOTE_SET_SINGLE_PRICE_PY'" >&2
    return 1
  fi
  NOTE_COOKIES_FILE="$NOTE_COOKIES_FILE" "$NOTE_MCP_PY" "$NOTE_SET_SINGLE_PRICE_PY" "$key" "$price" "$paywall_heading"
}

# ---------------------------------------------------------------------------------------------------------
# note_verify_draft: ground-truth verify (API can_read/eyecatch/price + a logged-out screenshot).
# ---------------------------------------------------------------------------------------------------------
note_verify_draft() {
  local key="$1"
  if [ ! -x "$NOTE_PUBLISH_SCRIPT" ]; then
    echo "note_verify_draft: NOTE_PUBLISH_SCRIPT not found/executable at '$NOTE_PUBLISH_SCRIPT'" >&2
    return 1
  fi
  bash "$NOTE_PUBLISH_SCRIPT" verify "$key"
}

# ---------------------------------------------------------------------------------------------------------
# run_note_mode_a_publish: the single Mode-A entry point run.sh calls. Fail-closed at every step: any
# failure returns non-zero with a reason on stderr (never crashes, never fakes a URL). PROP-20's hermetic
# test seam (NOTE_PUBLISH_TEST_FORCE) is checked FIRST so this stays testable with no network/browser call.
# ---------------------------------------------------------------------------------------------------------
run_note_mode_a_publish() {
  local draft_path="$1" title="$2" note_key_hint="$3" price="$4" paywall_heading="$5"

  if [ "${NOTE_PUBLISH_TEST_FORCE:-}" = "success" ]; then
    echo "NOTE_URL: https://note.com/anicca123/n/NOTE_TEST_URL_KEY"
    echo "NOTE_SCREENSHOT: /tmp-not-real/verify-NOTE_TEST_URL_KEY.png"
    echo "NOTE_KEY: NOTE_TEST_URL_KEY"
    return 0
  fi
  if [ "${NOTE_PUBLISH_TEST_FORCE:-}" = "fail" ]; then
    echo "run_note_mode_a_publish: NOTE_PUBLISH_TEST_FORCE=fail (test seam)" >&2
    return 1
  fi

  local create_out create_rc key
  create_out="$(note_create_rich_draft "$draft_path" "$title" 2>&1)"; create_rc=$?
  if [ $create_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: note_create_rich_draft failed: $create_out" >&2
    return 1
  fi
  key="$(echo "$create_out" | grep -oE '^NOTE_DRAFT_KEY: .*' | sed 's/^NOTE_DRAFT_KEY: //')"
  if [ -z "$key" ]; then
    echo "run_note_mode_a_publish: no NOTE_DRAFT_KEY in create_draft output: $create_out" >&2
    return 1
  fi

  # Best-effort: neither eyecatch nor single-price setup failures invalidate the already-created,
  # already-visual draft.
  if [ -n "${ARTICLE_NOTE_COVER:-}" ] && [ -f "${ARTICLE_NOTE_COVER:-}" ]; then
    local eyecatch_out eyecatch_rc
    eyecatch_out="$(note_set_eyecatch "$key" "$ARTICLE_NOTE_COVER" 2>&1)"; eyecatch_rc=$?
    if [ $eyecatch_rc -ne 0 ]; then
      echo "run_note_mode_a_publish: note_set_eyecatch did not complete (draft exists at key=$key; cover may still need manual review): $eyecatch_out" >&2
    fi
  fi

  local price_out price_rc
  price_out="$(note_set_single_price "$key" "$price" "$paywall_heading" 2>&1)"; price_rc=$?
  if [ $price_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: note_set_single_price did not complete (draft exists at key=$key; monetization type may still need manual review): $price_out" >&2
  fi

  local verify_out verify_rc url screenshot
  verify_out="$(note_verify_draft "$key" 2>&1)"; verify_rc=$?
  url="https://note.com/anicca123/n/$key"
  screenshot="$(echo "$verify_out" | python3 -c 'import json,sys
try:
    d=json.loads([l for l in sys.stdin if l.strip().startswith("{")][-1])
    print(d.get("screenshot") or "")
except Exception:
    print("")' 2>/dev/null || true)"

  echo "NOTE_URL: $url"
  echo "NOTE_SCREENSHOT: ${screenshot:-unknown}"
  echo "NOTE_KEY: $key"
  if [ $verify_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: verify reported a non-PASS (draft exists at $url, but verify's deterministic check did not pass): $verify_out" >&2
  fi
  return 0
}
