#!/usr/bin/env bash

render_ig_provision_prompt() {
  local state_file="${IG_PROVISION_ACCOUNT_STATE_FILE:?IG_PROVISION_ACCOUNT_STATE_FILE is required}"
  local handle_prefix="${IG_PROVISION_HANDLE_PREFIX:?IG_PROVISION_HANDLE_PREFIX is required}"
  local instance="${IG_PROVISION_INSTANCE:?IG_PROVISION_INSTANCE is required}"
  local gmail_plus_tag_prefix="${IG_PROVISION_GMAIL_PLUS_TAG_PREFIX:?IG_PROVISION_GMAIL_PLUS_TAG_PREFIX is required}"
  local bio_text="${IG_PROVISION_BIO_TEXT:?IG_PROVISION_BIO_TEXT is required}"
  local browser_instructions="${IG_PROVISION_BROWSER_INSTRUCTIONS:?IG_PROVISION_BROWSER_INSTRUCTIONS is required}"
  local profile_prefix="${IG_PROVISION_PROFILE_PREFIX:-${instance}-mkt}"
  local cooked_marker="${IG_PROVISION_COOKED_MARKER:-}"
  local provision_reason="${IG_PROVISION_REASON:-none}"
  local reach_marker="${IG_PROVISION_REACH_MARKER:-}"
  local last_pass_marker="${IG_PROVISION_LAST_PASS_MARKER:-}"
  local telegram_target="${IG_PROVISION_TELEGRAM_TARGET:-}"

  cat <<EOF
STEP PROVISION (1-loop-1-account, replace-on-cold, ZERO human): ${state_file} has no usable ready/warming account. Read ~/.claude/skills/ig-account-create/SKILL.md and follow its proven email-only flow. Create one brand-new ${instance} IG account on residential home IP with NO proxy. Use a unique handle beginning with ${handle_prefix}. Use a fresh Gmail plus-address keiodaisuke+${gmail_plus_tag_prefix}<random-tag>@gmail.com. Read the 6-digit OTP with: gog gmail search --account keiodaisuke@gmail.com "instagram in:anywhere newer_than:1h" --max 3 --plain. The in:anywhere term is mandatory because OTP can land in spam. Do not use phone flow unless Instagram forces it; if phone or text-CAPTCHA is forced, stop and report provision-blocked:<reason>. BROWSER ISOLATION: ${browser_instructions} Fill fields with trusted CDP typing, set DOB with trusted clicks, create the unique handle, and run setup_profile.py with a \$0 PIL monogram avatar plus this one-line bio containing NO link: "${bio_text}". Save signup credentials to ~/.cloak/ig-<handle>.json as JSON with username, name, email, pw, dob, and created.

DAY 1 SIGNUP ONLY: account creation day is day1. Do not run Client().login. Do not run login_by_sessionid. Do not call get_timeline_feed() or dump_settings(). Do not create ~/.cloak/instagrapi-<handle>.json. The isolated browser session is the only session owner on day1. warmer.py creates the one-and-only golden instagrapi session after the account reaches day3.

STATE WRITE: use ${state_file} only and preserve every existing row. Choose a free dedicated port that is neither 9222 nor 9223 after checking lsof, and a unique profile beginning with ${profile_prefix}. After signup and profile setup prove the account is LIVE in the browser, atomically append {"handle":"<handle>","profile":"<profile>","port":<free-port>,"lang":"en","status":"warming","session_owner":"browser","instance":"${instance}","created":"<today YYYY-MM-DD>","started_warming":"<today YYYY-MM-DD>"}. Parse the full JSON after writing, confirm row count increased by one and the final row matches the new handle. Signup + profile + credential file + warming state row is the complete day1 success condition.
EOF

  if [ -n "$cooked_marker" ]; then
    cat <<EOF
If provision reason is ${provision_reason} and equals cooked-marker, first mark prior ready/warming rows poisoned_manual_backup with poisoned_reason and poisoned_at so only the new appended row is active. On success remove ${cooked_marker}${reach_marker:+ and remove ${reach_marker}} so replacement account restarts clean validation.
EOF
  fi

  cat <<EOF
FAILURE: if signup, profile setup, credential save, or state verification fails, append a best-effort row with status=provision_failed and failure reason. Never label it ready/warming.
EOF

  if [ -n "$cooked_marker" ]; then
    printf 'Ensure %s remains present on failure.\n' "$cooked_marker"
  fi
  if [ -n "$telegram_target" ]; then
    cat <<EOF
Send Telegram chat ${telegram_target} a success message containing handle, port, session_owner=browser, status_written=warming, started_warming=<today>, and that this pass posted nothing. On failure send exactly one provision-blocked:<reason> report.
EOF
  else
    printf '%s\n' 'Report handle + port + session_owner=browser + status_written=warming + started_warming, or provision-blocked:<reason>.'
  fi
  if [ -n "$last_pass_marker" ]; then
    printf 'Touch %s and stop this pass after the provision success/failure report.\n' "$last_pass_marker"
  fi
}
