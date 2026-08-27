#!/usr/bin/env bash
# tier1-remediate.sh — TIER 1 deterministic remediation table (spec
# 2026-07-01-openclaw-self-heal-design.md §3.2): scans every anicca-managed launchd
# service's err log for two known, machine-format failure signatures and fixes them
# with a real root-cause action (never a blind restart — P2):
#   F2 dependency missing  — "Cannot find package 'X'"      -> npm install (in the
#                            service's own WorkingDirectory) + restart + re-probe.
#   F3 binary missing      — "X: command not found" (bash/sh) or "command not found:
#                            X" (zsh's own reversed message format) -> brew install X +
#                            restart + `command -v` re-probe.
#   F5 disk/log bloat      — any service err/out log over SELF_HEAL_LOG_CAP_MB (20MB
#                            default) -> archive last 2000 lines (gzip) + truncate in
#                            place. Root cause: F2/F3 crash-loops are what actually grow
#                            these logs (the 2026-07-01 agentmail-webhook incident this
#                            spec cites logged 61k repeats of the same missing-package
#                            crash into a single err log) — this check runs AFTER F2/F3
#                            each cycle so a freshly-fixed loop's backlog gets capped too.
#                            F5 scans the SAME per-plist StandardErrorPath/StandardOutPath
#                            the F2/F3 loop already discovered (adversary finding
#                            2026-07-04: an earlier version hardcoded a narrower glob
#                            that never saw 2 of 3 real managed jobs' actual log paths —
#                            F2/F3 already know the truth, F5 must reuse it, not re-derive
#                            a second, incomplete answer).
#
# TIER 1 (not TIER 0): this runs as its own launchd job so it survives even if the
# OpenClaw gateway itself is mid-repair, but unlike TIER 0 it doesn't need to be the
# "outermost" watcher — the services it heals (agentmail-webhook, clip-core, etc.) are
# independent launchd jobs, not OpenClaw's own scheduler.
#
# F2 and F3 are checked INDEPENDENTLY for every job every cycle (not mutually exclusive)
# — adversary finding 2026-07-04: an earlier version `continue`d after an F2 match,
# which structurally prevented ever detecting a co-occurring F3 fault on the same job.
# Real case found live: ai.anicca.phone-conversation has BOTH a dep-missing (dotenv) AND
# a binary-missing (lsof) fault in the same log; the old code could only ever see one.
#
# Shared ledger/cooldown/mode-switch plumbing: skills/_shared/scripts/self-heal-lib.sh
# (HARD RULE 0.17 SSOT — do not hand-copy these primitives a second time).
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
source "$ANICCA_HOME/.env" 2>/dev/null || true
ST="$ANICCA_HOME/state"; mkdir -p "$ST"
NOW=$(date +%s)
TIER=1
. "$ANICCA_HOME/skills/_shared/scripts/self-heal-lib.sh"

# CONCURRENCY LOCK — same mkdir-mutex pattern as watchdog.sh: two overlapping runs must
# never race an `npm install` / log truncation on the same files.
LOCK="$ST/tier1-remediate.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -f "$LOCK/pid" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
    echo "tier1: another instance running (pid $(cat "$LOCK/pid")) — skipping this run"; exit 0
  fi
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || { echo "tier1: cannot acquire lock — skipping"; exit 0; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

# plist_field <plist> <key> -> string value. plistlib (stdlib) instead of hand-rolled
# XML grep — robust against multi-line/whitespace variance across plist authors.
plist_field() {
  python3 -c "
import plistlib, sys
try:
    d = plistlib.load(open(sys.argv[1], 'rb'))
    v = d.get(sys.argv[2], '')
    print(v if isinstance(v, str) else '')
except Exception:
    print('')
" "$1" "$2" 2>/dev/null
}

# WATERMARK — a fixed-size `tail -c 8000` alone re-detects the SAME old, already-fixed
# error forever if a job doesn't log much new output. Persist the byte offset already
# scanned per job; only look at bytes AFTER it for NEW errors, and advance the watermark
# every cycle regardless of match so old text is marked "seen" exactly once. Reset to 0
# if the file shrank (truncated) OR its inode changed (StandardErrorPath deleted+
# recreated as a genuinely different file — a byte offset from the old file is
# meaningless against a new one even at a similar size).
WATERMARK_DIR="$ST/tier1-watermark"; mkdir -p "$WATERMARK_DIR"
reset_watermark() {
  # reset_watermark <label> — used by F5 right after it truncates a log in place, so
  # the F2/F3 loop's NEXT cycle re-scans from 0 instead of trusting a now-stale offset
  # that's larger than the freshly-truncated file (bash-bug-shaped, but real: without
  # this, a job that crash-loops fast enough to regrow past the old watermark between
  # scans would have some of its new content silently skipped — found in adversary
  # review 2026-07-04 as a truncate-then-regrow race).
  rm -f "$WATERMARK_DIR/$1.offset" "$WATERMARK_DIR/$1.inode"
}

# KNOWN_LOGS_FILE — LABEL<TAB>ERRPATH<TAB>OUTPATH for every managed plist, built once
# below and reused by BOTH the F2/F3 loop and F5, so F5 checks the exact same paths
# F2/F3 already proved are real (no second, incomplete glob — bash 3.2 on macOS has no
# associative arrays, so this is a plain tab-separated file, not a hash map).
KNOWN_LOGS_FILE="$ST/tier1-known-logs.tsv"
: > "$KNOWN_LOGS_FILE"
for PLIST in "$HOME/Library/LaunchAgents"/ai.*.plist; do
  [ -f "$PLIST" ] || continue
  L=$(plist_field "$PLIST" "Label")
  E=$(plist_field "$PLIST" "StandardErrorPath")
  O=$(plist_field "$PLIST" "StandardOutPath")
  [ -n "$L" ] || continue
  printf '%s\t%s\t%s\n' "$L" "$E" "$O" >> "$KNOWN_LOGS_FILE"
done

# ---------------------------------------------------------------------------------
# F2 (dependency missing) + F3 (binary missing) — one pass over every managed plist.
# ---------------------------------------------------------------------------------
for PLIST in "$HOME/Library/LaunchAgents"/ai.*.plist; do
  [ -f "$PLIST" ] || continue
  LABEL=$(plist_field "$PLIST" "Label")
  ERRPATH=$(plist_field "$PLIST" "StandardErrorPath")
  WORKDIR=$(plist_field "$PLIST" "WorkingDirectory")
  [ -n "$LABEL" ] && [ -n "$ERRPATH" ] && [ -f "$ERRPATH" ] || continue

  WM_FILE="$WATERMARK_DIR/${LABEL}.offset"
  WM_INODE_FILE="$WATERMARK_DIR/${LABEL}.inode"
  WM=$(cat "$WM_FILE" 2>/dev/null | tr -cd '0-9'); WM=${WM:-0}
  CUR_SIZE=$(wc -c < "$ERRPATH" 2>/dev/null | tr -d ' '); CUR_SIZE=${CUR_SIZE:-0}
  CUR_INODE=$(stat -f %i "$ERRPATH" 2>/dev/null || echo "")
  PREV_INODE=$(cat "$WM_INODE_FILE" 2>/dev/null || echo "")
  if [ "$WM" -gt "$CUR_SIZE" ] || [ "$CUR_INODE" != "$PREV_INODE" ]; then
    WM=0
  fi
  echo "$CUR_INODE" > "$WM_INODE_FILE"

  TAIL=$(tail -c +"$(( WM + 1 ))" "$ERRPATH" 2>/dev/null | tail -c 8000 || echo "")
  echo "$CUR_SIZE" > "$WM_FILE"   # advance watermark now — every byte up to CUR_SIZE has
                                  # been considered this cycle whether or not it matched
  [ -n "$TAIL" ] || continue

  # F2 — only the LAST occurrence is actionable; a log can carry many historical errors.
  # extract_missing_package() is shared with tier2-agent-diagnose.sh via self-heal-lib.sh
  # (HARD RULE 0.17 SSOT — was independently hand-duplicated there once, adversary
  # finding TIER 2 2026-07-04; now one source).
  PKG=$(extract_missing_package "$TAIL")
  if [ -n "$PKG" ]; then
    KEY="F2_${LABEL}"
    if [ -z "$WORKDIR" ] || [ ! -d "$WORKDIR" ]; then
      record_action "F2_dep_missing" "🚨 $LABEL missing package '$PKG' but no valid WorkingDirectory in its plist — cannot auto npm-install" \
        "label=$LABEL pkg=$PKG errpath=$ERRPATH workdir=$WORKDIR" "none (no usable WorkingDirectory)" "unfixable_no_workdir" "F2_dep_missing_${LABEL}"
    elif should_remediate "$KEY"; then
      # P2 verify-after-remediation MUST only look at bytes written AFTER this fix, not
      # the file's stale tail — a `tail -c N` of the WHOLE file can still contain the OLD
      # crash text from before the fix if the newly-restarted process hasn't logged
      # anything new yet. BEFORE_SIZE anchors the re-probe to only NEW output.
      BEFORE_SIZE=$(wc -c < "$ERRPATH" 2>/dev/null | tr -d ' '); BEFORE_SIZE=${BEFORE_SIZE:-0}
      ( cd "$WORKDIR" && timeout 180 npm install >/tmp/tier1-npm-install-$$.log 2>&1 )
      NPM_EXIT=$?
      launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
      VERIFY="still_broken"
      for _try in 1 2 3 4 5; do
        sleep 4
        NEW_BYTES=$(tail -c +"$(( BEFORE_SIZE + 1 ))" "$ERRPATH" 2>/dev/null || echo "")
        # NOTE: `grep -c` ALWAYS prints a count (even "0") but exits 1 on no-match, so a
        # trailing `|| echo 0` fires too and doubles the output to "0\n0" — the exact
        # NEXTWAKE/STUCK integer bug class already fixed once in watchdog.sh (check #4).
        # `grep -c` alone is sufficient; do not add a `|| echo 0` fallback here.
        RUNNING=$(launchctl list "$LABEL" 2>/dev/null | grep -c '"PID"')
        RUNNING=$(printf '%s' "$RUNNING" | tr -cd '0-9'); RUNNING=${RUNNING:-0}
        if [ "$RUNNING" -gt 0 ] && ! printf '%s' "$NEW_BYTES" | grep -q "Cannot find package '$PKG'"; then
          VERIFY="verified_clean"; break
        fi
        if printf '%s' "$NEW_BYTES" | grep -q "Cannot find package '$PKG'"; then
          VERIFY="still_broken"; break  # crashed again with the SAME error — no point waiting out the rest of the tries
        fi
      done
      if [ "$NPM_EXIT" -eq 0 ] && [ "$VERIFY" = "verified_clean" ]; then
        record_action "F2_dep_missing" "🩹 $LABEL missing '$PKG' → npm install ($WORKDIR) + restart, verified clean (live PID, no repeat of the error)" \
          "label=$LABEL pkg=$PKG errpath=$ERRPATH" "npm install in $WORKDIR + launchctl kickstart $LABEL" "verified_clean" "F2_dep_missing_${LABEL}"
      else
        record_action "F2_dep_missing" "🚨 $LABEL missing '$PKG' → npm install attempted (exit=$NPM_EXIT) but still erroring/not-running after restart — MANUAL FIX NEEDED" \
          "label=$LABEL pkg=$PKG errpath=$ERRPATH npm_exit=$NPM_EXIT" "npm install in $WORKDIR + launchctl kickstart $LABEL" "$VERIFY" "F2_dep_missing_${LABEL}"
      fi
    fi
  fi
  # NOTE: no `continue` here — F3 is checked independently below for the SAME job in
  # the SAME cycle, even if F2 also matched (adversary finding: phone-conversation has
  # both faults simultaneously; a prior version's `continue` after F2 meant F3 could
  # never even be attempted for it).

  # F3 — binary missing. extract_missing_binary() (self-heal-lib.sh) handles both
  # bash/sh's "<bin>: command not found" and zsh's REVERSED "command not found: <bin>"
  # format (zsh is an actively-used wrapper among these very jobs — this script's own
  # launchd plist invokes `/bin/zsh -lc ...`) and denylists shell names themselves as
  # false root causes. Shared with tier2-agent-diagnose.sh (HARD RULE 0.17 SSOT).
  BIN=$(extract_missing_binary "$TAIL")
  # is_undefined_shell_function: bash reports an undefined shell FUNCTION with the
  # exact same "command not found" text as a missing binary. If the erroring script
  # defines the name itself, that is a code bug in the script — brew cannot supply it
  # and kickstart -k would SIGTERM a healthy in-flight worker (real incident
  # 2026-07-27: gig_pass.sh record_lane_attempt → worker killed, orphaned child held
  # the gig browser lock 12 min). Not an F3; leave it to the owning repo's own tests.
  if [ -n "$BIN" ] && ! command -v "$BIN" >/dev/null 2>&1 \
     && ! is_undefined_shell_function "$TAIL" "$BIN"; then
    KEY="F3_${LABEL}_${BIN}"
    if should_remediate "$KEY"; then
      brew install "$BIN" >/tmp/tier1-brew-install-$$.log 2>&1
      BREW_EXIT=$?
      if [ "$BREW_EXIT" -eq 0 ] && command -v "$BIN" >/dev/null 2>&1; then
        # Restart ONLY once the binary is verifiably present. A restart without the
        # binary cannot fix anything — it just kills whatever healthy work the service
        # was doing (the 2026-07-27 gig incident was exactly this branch misordered).
        launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
        sleep 5
        record_action "F3_binary_missing" "🩹 $LABEL missing binary '$BIN' → brew install + restart, $BIN now present" \
          "label=$LABEL bin=$BIN errpath=$ERRPATH" "brew install $BIN + launchctl kickstart $LABEL" "verified_present" "F3_binary_missing_${LABEL}_${BIN}"
      else
        record_action "F3_binary_missing" "🚨 $LABEL missing binary '$BIN' → brew install attempted (exit=$BREW_EXIT) but still missing — service left running, MANUAL FIX NEEDED" \
          "label=$LABEL bin=$BIN errpath=$ERRPATH brew_exit=$BREW_EXIT" "brew install $BIN (no restart — binary still absent)" "still_missing" "F3_binary_missing_${LABEL}_${BIN}"
      fi
    fi
  fi
done

# ---------------------------------------------------------------------------------
# F5 (disk/log bloat) — runs AFTER F2/F3 so a log that was just fixed this cycle still
# gets its pre-existing backlog capped. P4: log bloat is a first-class probe, not an
# afterthought. Scans the SAME per-plist paths F2/F3 already discovered (KNOWN_LOGS_FILE)
# UNION the generic $ANICCA_HOME/logs/* glob (for logs not tied to any single plist).
# ---------------------------------------------------------------------------------
LOG_SIZE_CAP_MB="${SELF_HEAL_LOG_CAP_MB:-20}"
# byte-precise cap, NOT MB-truncated: a 21,513,194-byte (20.5MB) file / 1048576 integer-
# divides down to exactly "20", which then fails `-gt 20` and silently never triggers.
LOG_SIZE_CAP_BYTES=$(( LOG_SIZE_CAP_MB * 1048576 ))
shopt -s nullglob
CANDIDATE_LOGS_FILE="$ST/tier1-f5-candidates.tmp.$$"
{
  awk -F'\t' '{ if ($2 != "") print $2; if ($3 != "") print $3 }' "$KNOWN_LOGS_FILE" 2>/dev/null
  for g in "$ANICCA_HOME"/logs/*.err.log "$ANICCA_HOME"/logs/*.err "$ANICCA_HOME"/logs/*.out.log "$ANICCA_HOME"/logs/*.out; do
    [ -f "$g" ] && printf '%s\n' "$g"
  done
} | sort -u > "$CANDIDATE_LOGS_FILE"

while IFS= read -r LOGFILE; do
  [ -n "$LOGFILE" ] && [ -f "$LOGFILE" ] || continue
  RAW_SIZE=$(stat -f %z "$LOGFILE" 2>/dev/null || echo 0)
  if [ "$RAW_SIZE" -gt "$LOG_SIZE_CAP_BYTES" ]; then
    SIZE_MB=$(( RAW_SIZE / 1048576 ))
    BASENAME=$(basename "$LOGFILE")
    KEY="F5_${BASENAME}"
    if should_remediate "$KEY"; then
      ARCHIVE_DIR="$ST/self-heal-log-archive"; mkdir -p "$ARCHIVE_DIR"
      ARCHIVE="$ARCHIVE_DIR/${BASENAME}.$(date +%Y%m%d-%H%M%S).tail.gz"
      tail -n 2000 "$LOGFILE" | gzip > "$ARCHIVE" 2>/dev/null || true
      # truncate IN PLACE (same inode) — a launchd StandardErrorPath fd stays open and
      # keeps appending to the now-empty file; no restart needed for this remediation.
      : > "$LOGFILE"
      # reset the owning job's watermark NOW so the next F2/F3 cycle re-scans from 0
      # instead of trusting an offset now larger than the truncated file.
      OWNER_LABEL=$(awk -F'\t' -v p="$LOGFILE" '$2==p || $3==p {print $1; exit}' "$KNOWN_LOGS_FILE" 2>/dev/null)
      [ -n "$OWNER_LABEL" ] && reset_watermark "$OWNER_LABEL"
      NEW_SIZE_MB=$(( $(stat -f %z "$LOGFILE" 2>/dev/null || echo 0) / 1048576 ))
      record_action "F5_disk_log_bloat" "🧹 $BASENAME was ${SIZE_MB}MB (> ${LOG_SIZE_CAP_MB}MB cap) → archived last 2000 lines to $(basename "$ARCHIVE"), truncated to ${NEW_SIZE_MB}MB" \
        "logfile=$LOGFILE size_mb=$SIZE_MB" "archived last 2000 lines to $ARCHIVE + truncated in place" "truncated_to_${NEW_SIZE_MB}mb" "F5_disk_log_bloat_${BASENAME}"
    fi
  fi
done < "$CANDIDATE_LOGS_FILE"
rm -f "$CANDIDATE_LOGS_FILE"
shopt -u nullglob

finish_and_escalate "F2 ok (no dep-missing crash loops), F3 ok (no binary-missing crash loops), F5 ok (no logs over ${LOG_SIZE_CAP_MB}MB)"
