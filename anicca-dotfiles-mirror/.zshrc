export PATH="/opt/homebrew/opt/node@22/bin:$PATH"

# Claude Code / Node.js symlink
export PATH="$HOME/bin:$PATH"
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin

# Claude Code - bypass permissions
alias claude='claude --dangerously-skip-permissions'

. "$HOME/.local/bin/env"
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
export PATH=$PATH:$HOME/.maestro/bin

# Firecrawl CLI
export FIRECRAWL_API_KEY=fc-a71ee897c8a04aee957733944fe5e9d5
export VIBECODE_API_KEY="vibecode_18a927ce7976721a13bef524fe172b75"
export PATH="$HOME/.local/bin:$PATH"
export NODE_PATH=/opt/homebrew/lib/node_modules
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin

# ─── Anicca v3.2 phone autostart ──────────────────────────────────
# Runs only inside a tmux session created by `phone` (MOSHI_PHONE=1).
# Replaces the shell with a fresh Claude (Opus 4.7) conversation.
# Idempotent: CLAUDE_AUTOSTARTED guard prevents re-exec on nested shells.
if [[ "$MOSHI_PHONE" == "1" && -z "$CLAUDE_AUTOSTARTED" ]]; then
  export CLAUDE_AUTOSTARTED=1
  SESSION_NAME=$(/opt/homebrew/bin/tmux display -p '#S' 2>/dev/null || echo "phone")
  SESSION_UUID=$(uuidgen 2>/dev/null)
  # Note: --max-budget-usd is print-mode only per Claude Code CLI ref;
  # interactive cost guard is left to /cost slash command + Anthropic dashboard.
  exec claude \
    --name "$SESSION_NAME" \
    --session-id "$SESSION_UUID" \
    --model claude-opus-4-7
fi
# ─────────────────────────────────────────────────────────────────
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin
export PATH=$PATH:$HOME/.maestro/bin

# OpenClaw Completion
source "/Users/anicca/.openclaw/completions/openclaw.zsh"
export PATH=$PATH:$HOME/.maestro/bin

source /Users/anicca/.daytona.completion_script.zsh
