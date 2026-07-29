#!/usr/bin/env bash
# earn/clip — ONE bounded unit per wake: post the next QUEUED captioned 9:16 clip to the
# next READY clip account (each account lives in its OWN isolated CloakBrowser profile+port,
# so there is never account-switch pollution). Per-view reward USDC accrues LATER, so a post
# records a narrate line (earn_usdc=0); a separate payout-check wake records the real
# on-chain inflow via record-earn (INV-7). NO HUMAN: login uses stored creds + auto-OTP,
# captcha→CapSolver, publish→autonomous. This is a LOCAL slot (needs CloakBrowser on this Mac).
#
# Contract (run-skill.mjs): reads env, does ONE bounded step, prints ONE structured stdout
# line, exits 0. Idempotent + bounded (respects SKILL_TIMEOUT_S). Never posts to the wrong
# account (the poster has a fail-closed account-guard).
#
#   EARN_MODE=discover (default) → report what's postable, no side effect.
#   EARN_MODE=execute            → post ONE queued clip to ONE ready account.
set -uo pipefail

EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-}"
HOME_DIR="${HOME}"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_instance_paths.sh"
QUEUE="$CLIP_QUEUE"                      # *.mp4 + matching *.txt caption, filled by the producer
POSTED="$CLIP_POSTED"
ACCTS="$CLIP_ACCTS"
LEDGER="$CLIP_LEDGER"
PENDING_VERIFY="$CLIP_PENDING_VERIFY"    # REQ-006: unverified-outcome clips land here, never queue/posted
# ★POST-11 (2026-07-14): the VERIFIED FREE posting path — instagrapi + browser sessionid + ffmpeg
# thumbnail. The web composer (post_reel.py) silently drops automated posts (IG detection); instagrapi
# via the mobile private API reliably publishes. See docs/earn/ig-posting-method-graph-api-pivot.md.★
INSTA_POSTER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../marketing-engine/poster.py"
INSTA_VENV="$HOME_DIR/.cache/instagrapi-venv"
INSTA_PY="$INSTA_VENV/bin/python"
# OBS-6: Telegram report (reel link so Dais can tap→watch→screenshot). Best-effort, never blocks posting.
TG_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../_shared/send-telegram.sh"
tg() { [ -f "$TG_SCRIPT" ] && bash "$TG_SCRIPT" "$1" >/dev/null 2>&1 || true; }
CDP_DIR="$HOME_DIR/.claude/skills/ig-account-create/scripts"
PY=/opt/homebrew/bin/python3
mkdir -p "$QUEUE" "$POSTED" "$PENDING_VERIFY" "$(dirname "$LEDGER")"

emit() { printf '{"slot":"earn/clip","did":%s,"earned_usdc":0,"cost_usdc":0}\n' "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"; }
note() { echo "$(date '+%F %T') run.sh: $*" >&2; }

# next queued clip (oldest first) that has a caption sidecar
CLIP=""; CAP=""
for f in "$QUEUE"/*.mp4; do
  [ -e "$f" ] || continue
  c="${f%.mp4}.txt"
  if [ -f "$c" ]; then CLIP="$f"; CAP="$c"; break; fi
done

# next ready account (status==ready) + its isolated profile port
read -r HANDLE PORT < <("$PY" - "$ACCTS" <<'PYJSON' 2>/dev/null
import json,sys
try:
    a=json.load(open(sys.argv[1]))
except Exception:
    a=[]
for x in a:
    if x.get("status")=="ready":
        print(x.get("handle",""), x.get("port",9222)); break
PYJSON
)

# REQ-008 (gating): self-heal needs a ready account+working browser too, but is INDEPENDENT of
# whether a new clip happens to be queued -- so the "nothing queued" check below must NOT skip it.
# Without a ready account at all, though, neither self-heal nor new posting can do anything.
if [ -z "${HANDLE:-}" ]; then
  # 2026-07-04 (Task#6 follow-up, self-heal-harness spec §8): right-altitude prompt hint --
  # not a hardcoded auto-fix, just steering the next wake's own judgment toward a slot that
  # genuinely exists and helps (earn/clip-producer is safe to slot-ify: deterministic, no
  # vision judgment). Only surfaced when the queue is ACTUALLY empty -- don't suggest it when
  # there's already a queued clip waiting (that's an account problem, not a queue problem).
  if [ -z "${CLIP:-}" ]; then
    emit "nothing to post (queued_clip=none ready_account=none) -- try the earn/clip-producer slot to generate a fresh clip while an account is not yet ready"
  else
    emit "nothing to post (queued_clip=${CLIP:-none} ready_account=none)"
  fi
  exit 0
fi

if [ "$EARN_MODE" != "execute" ]; then
  emit "discover: would post $(basename "${CLIP:-<none-queued>}") to @${HANDLE} (port ${PORT})"; exit 0
fi

# --- execute: prefer a CONFIRMED browser login; fall back to instagrapi's own settings-based
# login when the browser is down or not confirmed logged in. POST-11's poster.py has
# ITS OWN fail-closed account-guard in login_resilient() (tier1: instagrapi-<handle>.json
# settings, verified against cl.username==handle before ever posting; tier2: browser sessionid,
# also verified; tier3: password) — so gating posting on THIS script's separate DOM-based
# browser check is redundant once instagrapi-<handle>.json settings exist, and it wrongly
# skipped a genuinely postable account whenever the browser session happened to be down/logged
# out (2026-07-15/16: warming accounts stuck skipping despite instagrapi being postable).
# A browser is still REQUIRED (no fallback) when no instagrapi settings file exists yet.
# Test hooks (PROP-005), both unset in production: skip the real CDP liveness/login checks so
# run.sh's 3-way OUTCOME routing can be tested against a stubbed POSTER without a real browser.
INSTA_SETTINGS="$HOME_DIR/.cloak/instagrapi-${HANDLE}.json"
BROWSER_READY=0
if [ -n "${CLIP_TEST_TID_OVERRIDE:-}" ]; then
  TID="$CLIP_TEST_TID_OVERRIDE"
else
  TID="$(curl -sS --max-time 5 "http://localhost:${PORT}/json/list" 2>/dev/null | "$PY" -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
ps=[t for t in d if t.get("type")=="page" and "instagram.com" in (t.get("url") or "")]
print((ps[0] if ps else (next((t for t in d if t.get("type")=="page"), {}))).get("id",""))
')"
fi
if [ -z "$TID" ]; then
  if [ -f "$INSTA_SETTINGS" ]; then
    note "account @${HANDLE} browser not up on :${PORT} -- proceeding via instagrapi settings-only path (${INSTA_SETTINGS}), skipping browser-dependent self-heal"
  else
    emit "account @${HANDLE} browser not up on :${PORT} (warmer/creator must keep it logged in) and no instagrapi settings to fall back on"; exit 0
  fi
else
  # verify logged in as HANDLE (fail-closed: do not trust the browser as a login source unless confirmed)
  if [ -n "${CLIP_TEST_ACTIVE_OVERRIDE:-}" ]; then
    ACTIVE="$CLIP_TEST_ACTIVE_OVERRIDE"
  else
    ACTIVE="$(CDP_PORT="$PORT" "$PY" -c "
import sys,os; sys.path.insert(0,'$CDP_DIR'); import cdp
tid='$TID'
try:
    cdp.navigate(tid,'https://www.instagram.com/'); import time; time.sleep(5)
    print(cdp.evaluate(tid,'(()=>(document.querySelector(\"img[alt\$=のプロフィール写真]\")||{}).alt||\"\")()') or '')
except Exception as e:
    print('')
" 2>/dev/null | sed 's/のプロフィール写真//')"
  fi
  if [ "$ACTIVE" != "$HANDLE" ]; then
    if [ -f "$INSTA_SETTINGS" ]; then
      note "account @${HANDLE} browser on :${PORT} not confirmed logged in (active='${ACTIVE}') -- proceeding via instagrapi settings-only path (${INSTA_SETTINGS}), skipping browser-dependent self-heal"
    else
      emit "account @${HANDLE} not logged in on :${PORT} (active='${ACTIVE}') — skipping, no wrong-account post"; exit 0
    fi
  else
    BROWSER_READY=1
  fi
fi

# REQ-008: self-heal runs ONCE per wake, BEFORE new-content posting, using the SAME resolved
# HANDLE/TID this wake already confirmed logged-in. Runs regardless of whether a new clip is
# queued (independent of the QUEUE-empty check below) but never blocks the posting pipeline
# below regardless of its own outcome (best-effort; failure here must not prevent a new post).
# Requires BROWSER_READY (a confirmed browser session -- self-heal reads the browser DOM to
# verify pending posts); skipped on the instagrapi-settings-only fallback path above, where
# there is no confirmed browser session for it to read.
SELF_HEAL="${CLIP_SELF_HEAL_OVERRIDE:-$(dirname "${BASH_SOURCE[0]}")/self_heal.py}"  # test hook (PROP-009), unset in production
if [ "$BROWSER_READY" = "1" ] && [ -f "$SELF_HEAL" ]; then
  # FIXED after Phase 3 FIND-103: pass the paths run.sh ALREADY resolved via _instance_paths.sh
  # above, instead of self_heal.py re-deriving ANICCA_INSTANCE suffixing independently in Python
  # (a duplicate/drifting-logic risk with zero enforcement mechanism to keep the two in sync).
  CDP_PORT="$PORT" "$PY" "$SELF_HEAL" --handle "$HANDLE" --tid "$TID" --wake "$WAKE" \
    --pending-verify "$PENDING_VERIFY" --posted "$POSTED" --ledger "$LEDGER" 2>/dev/null || true
fi

if [ -z "${CLIP}" ]; then
  emit "nothing new to post (queue empty; self-heal already ran this wake)"; exit 0
fi

# ★FIX-1 (2026-07-14) POSTING-CADENCE GATE★ — a fresh/young account that burst-posts via
# automation gets ACTION-BLOCKED by IG. Observed on @aiclipsvault: 3 content-varied clips
# (28MB / 28MB+faststart / 2.6MB-15s) ALL hung at "シェア中" = IG silently drops the publish
# after over-posting (~12 reels then dead). Root cause = burst cadence + CDP detection + thin
# warm-up, NOT the poster code or the file. Enforce <=1 post per CADENCE window per account.
# Self-heal already ran above; this gates ONLY the new post. See
# docs/earn/ig-posting-restriction-and-warmup-policy.md.
CADENCE_H="${CLIP_CADENCE_HOURS:-20}"
LASTPOST="$POSTED/.last-post-${HANDLE}"
if [ -f "$LASTPOST" ]; then
  AGE=$(( $(date +%s) - $(cat "$LASTPOST" 2>/dev/null || echo 0) ))
  if [ "$AGE" -lt $(( CADENCE_H * 3600 )) ]; then
    emit "cadence: @${HANDLE} last posted ${AGE}s ago (<${CADENCE_H}h) — holding to avoid action-block"; exit 0
  fi
fi

# REQ-010: FRESH RANDOM per-attempt tracking token (NOT clip_id-derived — producer.sh's clip_id can
# legitimately repeat across separate attempts, e.g. a same-day channel repeat or a manual retry).
TOKEN="#c$("$PY" -c 'import secrets; print(secrets.token_hex(5))')"
# Write $CAP's ORIGINAL content + the token into a NEW temp file — $CAP itself is NEVER mutated.
# NOTE: BSD/macOS mktemp does NOT randomize a template with a suffix after the X's (verified: it
# creates the LITERAL "clip-cap-XXXXXX.txt" path every time, a real collision risk) — the X's must
# be the very last characters of the template. post_reel.py's --caption-file has no extension
# requirement (it just open()s + reads whatever path is given), so no extension is needed here.
TMPCAP="$(mktemp "${TMPDIR:-/tmp}/clip-cap-XXXXXX")"
trap 'rm -f "$TMPCAP"' EXIT
printf '%s\n%s\n' "$(cat "$CAP")" "$TOKEN" > "$TMPCAP"

# post the clip via instagrapi (POST-11). Self-heal the venv if missing (disk-cleaner may prune it).
if [ ! -x "$INSTA_PY" ]; then
  /opt/homebrew/bin/python3 -m venv "$INSTA_VENV" >/tmp/clip-insta-venv.log 2>&1
  "$INSTA_PY" -m pip install --quiet instagrapi websocket-client pillow >/tmp/clip-insta-pip.log 2>&1 \
    || emit "instagrapi venv self-heal FAILED (see /tmp/clip-insta-pip.log)"
fi
# instagrapi poster has its own fail-closed account-guard (cl.username == handle) + logged-out reality gate.
RES="$(CDP_PORT="$PORT" "$INSTA_PY" "${CLIP_POSTER_OVERRIDE:-$INSTA_POSTER}" --video "$CLIP" --caption-file "$TMPCAP" --handle "$HANDLE" --live 2>>"$HOME/.local/state/life-manager/logs/clip-insta-poster.err.log" | tail -1)"
# NOTE (2 real bugs caught while writing PROP-005's test, both fixed here): (1) json.dumps' DEFAULT
# separators include a space after each comma (e.g. `["a", "b"]`), which corrupts whitespace-based
# field-splitting. (2) bash `read`'s default whitespace IFS COLLAPSES consecutive separators, so an
# EMPTY middle field (post_url=="" when unverified) silently disappears and every field after it
# shifts left. Fix: use compact JSON separators AND a non-whitespace field delimiter (\x1f, "unit
# separator" — cannot appear in JSON/URL text) so empty fields are preserved correctly.
IFS=$'\x1f' read -r OUTCOME URL BEFORE_HREFS_JSON < <(printf '%s' "$RES" | "$PY" -c 'import json,sys
try:
    d=json.loads(sys.stdin.read())
except Exception:
    d={}
print("\x1f".join([d.get("outcome") or "failed", d.get("post_url") or "", json.dumps(d.get("before_hrefs") or [], separators=(",", ":"))]))')

case "$OUTCOME" in
  published)
    mv "$CLIP" "$POSTED/" 2>/dev/null || true
    mv "$CAP"  "$POSTED/" 2>/dev/null || true
    "$PY" - "$LEDGER" "$HANDLE" "$URL" "$WAKE" <<'PYL' 2>/dev/null
import json,sys,os
ledger,handle,url,wake=sys.argv[1:5]
line={"slot":"earn/clip","source":"ig-clip","task":f"posted reel to @{handle}: {url}",
      "status":"posted","earn_usdc":0,"cost_usdc":0,"net_usdc":0,"wake":wake or None,"post_url":url}
with open(ledger,"a") as f: f.write(json.dumps(line,ensure_ascii=False)+"\n")
PYL
    date +%s > "$POSTED/.last-post-${HANDLE}" 2>/dev/null || true  # FIX-1 cadence stamp
    tg "$(printf '🎬 clip @%s ✅ posted\n🔗 %s\n🎞 %s (1080x1920)\n❤️ instagrapi / cadence 1日1本' "$HANDLE" "$URL" "$(basename "$CLIP")")"
    emit "posted @${HANDLE}: ${URL}"; exit 0
    ;;
  unverified)
    # REQ-006/FIND-032: BOTH the clip AND its paired caption move together, mirroring the existing
    # $CLIP/$CAP move-together pattern above. REQ-008 step 6: sidecar records before_hrefs + token.
    BASE="$(basename "${CLIP%.mp4}")"
    mv "$CLIP" "$PENDING_VERIFY/" 2>/dev/null || true
    mv "$CAP"  "$PENDING_VERIFY/" 2>/dev/null || true
    "$PY" - "$PENDING_VERIFY/${BASE}.before-hrefs.json" "$BEFORE_HREFS_JSON" "$TOKEN" <<'PYS' 2>/dev/null
import json,sys
sidecar_path, before_hrefs_json, token = sys.argv[1:4]
before_hrefs = json.loads(before_hrefs_json)
with open(sidecar_path, "w") as f:
    json.dump({"before_hrefs": before_hrefs, "token": token}, f, ensure_ascii=False)
PYS
    "$PY" - "$LEDGER" "$HANDLE" "$WAKE" <<'PYL' 2>/dev/null
import json,sys,os
ledger,handle,wake=sys.argv[1:4]
line={"slot":"earn/clip","source":"ig-clip","task":f"post to @{handle} unverified — pending self-heal",
      "status":"unverified","earn_usdc":0,"cost_usdc":0,"net_usdc":0,"wake":wake or None,"post_url":None}
with open(ledger,"a") as f: f.write(json.dumps(line,ensure_ascii=False)+"\n")
PYL
    emit "post to @${HANDLE} unverified — moved to pending-verify for self-heal"; exit 0
    ;;
  *)
    tg "$(printf '⚠️ clip @%s 投稿失敗\n%s\nself-heal 予定' "$HANDLE" "$(printf '%s' "$RES" | head -c 300)")"
    emit "post attempt failed (res=${RES})"; exit 0
    ;;
esac
