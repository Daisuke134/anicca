#!/usr/bin/env bash
# publish-to-oss — one-way private → public publisher (copybara-style).
#
# Copies the GENERAL parts of $ANICCA_HOME into a staging dir, scrubs every
# personal value (data-driven from profile.json + static infra patterns), runs
# a 3-tool secret/personal gate, and ONLY pushes if the gate is 100% clean.
#
# The git histories are NEVER connected — staging is a fresh tree pushed to the
# public repo. Personal data physically cannot leak: it's scrubbed before the
# gate, and the gate blocks the push if anything remains.
#
# Usage:
#   publish.sh                 # dry-run: {{profile.lateness.stakeholders.senderType}} + scrub + GATE, no push (safe default)
#   publish.sh --push          # if gate passes, push {{profile.lateness.stakeholders.senderType}}d tree to $ANICCA_OSS_DIR
#   ANICCA_OSS_DIR=~/anicca-oss publish.sh --push
set -uo pipefail

ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
OSS_DIR="${ANICCA_OSS_DIR:-$HOME/anicca-oss}"
STAGE="${ANICCA_PUBLISH_STAGE:-/tmp/anicca-oss-publish}"
SKILL_DIR="$ANICCA_HOME/skills/publish-to-oss/scripts"
PUSH=0; [ "${1:-}" = "--push" ] && PUSH=1

echo "═══ publish-to-oss ═══  src=$ANICCA_HOME  {{profile.lateness.stakeholders.senderType}}=$STAGE  push=$PUSH"

# 1. fresh staging
rm -rf "$STAGE" && mkdir -p "$STAGE"

# 2. copy the PUBLISHABLE set (whitelist of paths) with excludes.
#    rsync excludes keep secrets/runtime/personal-accumulation out from the start.
RSYNC_EXCLUDES=(
  --exclude='.git/' --exclude='.env' --exclude='.env.*' --exclude='!.env.example'
  --exclude='node_modules/' --exclude='__pycache__/' --exclude='.venv/' --exclude='.cache/'
  --exclude='agents/'                          # auth-profiles, sessions
  --exclude='identity/profile.json'            # real profile (ship .example + schema only)
  --exclude='identity/device*.json'
  --exclude='identity/scrub-patterns.json'     # the scrub rules CONTAIN real values — never publish
  --exclude='cron/jobs.json' --exclude='cron/jobs.json.*' --exclude='cron/runs/'
  --exclude='*.bak-*'
  --exclude='skills/_private/' --exclude='skills/_vendor/' --exclude='skills/_backups/'
  --exclude='_backups/' --exclude='*.bak' --exclude='*.bak.*' --exclude='*.backup'
  --exclude='skills/*/data/' --exclude='skills/*/reports/' --exclude='skills/*/snapshots/'
  --exclude='skills/*/state/' --exclude='skills/*/output/' --exclude='skills/*/runs/' --exclude='skills/*/logs/'
  --exclude='*.mp4' --exclude='*.mov' --exclude='*.wav' --exclude='*.mp3' --exclude='*.p12'
  --exclude='*.pem' --exclude='*.p8' --exclude='*.key' --exclude='*.log'
  --exclude='workspace/'                       # runtime workspace (templates added back below)
  --exclude='logs/' --exclude='.DS_Store'
)
# publishable top-level paths (the "whitelist")
for path in skills adapters identity cron canvas completions docs scripts \
            README.md CONSTITUTION.md SOUL.md LICENSE CONTRIBUTING.md SECURITY.md \
            AGENT_SETUP.md API_KEYS.md install.sh openclaw.json.example \
            .gitignore .gitleaks.toml .pre-commit-config.yaml .env.example; do
  [ -e "$ANICCA_HOME/$path" ] && rsync -a "${RSYNC_EXCLUDES[@]}" "$ANICCA_HOME/$path" "$STAGE/" 2>/dev/null
done
# workspace: only ship templates (HEARTBEAT.md + *.example + ops examples)
mkdir -p "$STAGE/workspace/ops"
for f in HEARTBEAT.md CONSTITUTION.md PERSONAL_CLAUDE.md.example pending-questions.md.example; do
  [ -f "$ANICCA_HOME/workspace/$f" ] && cp "$ANICCA_HOME/workspace/$f" "$STAGE/workspace/$f"
done
find "$ANICCA_HOME/workspace/ops" -maxdepth 1 -name '*.example' -exec cp {} "$STAGE/workspace/ops/" \; 2>/dev/null
chmod -R u+w "$STAGE"   # rsync -a preserves read-only perms; scrub needs to rewrite files
echo "{{profile.lateness.stakeholders.senderType}}d files: $(find "$STAGE" -type f | wc -l | tr -d ' ')"

# 3. SCRUB personal values (data-driven)
echo "═══ scrub ═══"
python3 "$SKILL_DIR/scrub.py" "$STAGE" || { echo "scrub failed"; exit 1; }

# 4. GATE — 3 tools, must all be clean
echo "═══ gate ═══"
( cd "$STAGE" && git init -q -b main && git add -A && git -c user.{{profile.lateness.stakeholders.channel}}=x@x -c user.name=x commit -qm snap )
FAIL=0
echo "-- gitleaks --"
gitleaks detect --source "$STAGE" --redact 2>&1 | grep -E "no leaks|leaks found" || true
gitleaks detect --source "$STAGE" --redact >/dev/null 2>&1 || { echo "❌ gitleaks FOUND leaks"; FAIL=1; }
echo "-- trufflehog (verified only) --"
TH=$(trufflehog filesystem "$STAGE" --no-update --only-verified --json 2>/dev/null | wc -l | tr -d ' ')
echo "verified secrets: $TH"; [ "$TH" != "0" ] && FAIL=1
echo "-- residual personal grep --"
RES=$(grep -rniE "your-email-user|daisuke_2_<username>|@company|<your-school>|<your-address>|cbns03|<username>\.daisuke|#ai-<username>|mrr_target.{0,6}[0-9]{4}|obou\.anicca|your-tiktok-handle|anicca\.jp8|100\.(99|108)\.[0-9]+\.[0-9]+|$HOME" "$STAGE" 2>/dev/null | grep -vE "\.git/|profile\.example|node_modules|package-lock|publish-to-oss/|scrub-patterns\.json" | head -20)
if [ -n "$RES" ]; then echo "❌ residual personal values:"; echo "$RES"; FAIL=1; else echo "✅ no residual personal values"; fi

if [ "$FAIL" != "0" ]; then
  echo "═══ GATE FAILED — NOT publishing. Staged tree at $STAGE for inspection. ═══"
  exit 1
fi
echo "═══ ✅ GATE PASSED ═══"

# 5. push (only with --push)
if [ "$PUSH" != "1" ]; then
  echo "dry-run done. Re-run with --push to publish to $OSS_DIR → its remote."
  exit 0
fi
[ -d "$OSS_DIR/.git" ] || { echo "❌ $OSS_DIR is not a git clone of the public repo"; exit 1; }
rsync -a --delete \
  --exclude='.git/' \
  "$STAGE/" "$OSS_DIR/"
( cd "$OSS_DIR" && git add -A && git commit -q -m "publish: sync general skills from private (scrubbed + gated)" && git push )
echo "═══ ✅ published to $OSS_DIR remote ═══"
