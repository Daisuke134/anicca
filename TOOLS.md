# TOOLS.md — Tool Notes

This file is for notes about your local toolchain. Felix reads it to understand what's available and how to use it.

## Coding Sub-Agents

### Ralph Loop (preferred for non-trivial tasks)
Use `ralphy` to wrap coding agents in a retry loop with completion validation. Ralph restarts with fresh context each iteration — prevents stalling, context bloat, and premature exits.

```bash
# Single task with Codex
ralphy --codex "Fix the authentication bug in the API"

# PRD-based workflow (best for multi-step work)
ralphy --codex --prd PRD.md

# With Claude Code instead
ralphy --claude "Refactor the database layer"

# Parallel agents on separate tasks
ralphy --codex --parallel --prd PRD.md

# Limit iterations
ralphy --codex --max-iterations 10 "Build the feature"
```

### Codex CLI (for direct use)
```bash
codex exec --full-auto "Task description here"
```

### When to Use What
- **Ralph**: Multi-step features, PRD checklists, tasks that have stalled
- **Raw Codex**: Tiny focused fixes, one-file changes, exploratory work

## tmux for Long-Running Agents

Background processes die on gateway restart. Anything expected to run >5 minutes goes in tmux.

**Always use the stable socket** (`~/.tmux/sock`):

```bash
# Create named session
tmux -S ~/.tmux/sock new -d -s my-task \
  "cd ~/project && ralphy --codex --prd PRD.md; \
   EXIT_CODE=\$?; echo 'EXITED:' \$EXIT_CODE; \
   openclaw system event --text 'my-task finished (exit \$EXIT_CODE)' --mode now; \
   sleep 999999"

# Check progress
tmux -S ~/.tmux/sock capture-pane -t my-task -p | tail -20

# List sessions
tmux -S ~/.tmux/sock list-sessions
```

The completion hook (`openclaw system event`) notifies you immediately when the agent finishes. The `sleep` keeps the shell alive so output is readable.

## Exec Timeout Defaults

| Category | yieldMs | timeout | Example |
|---|---|---|---|
| Quick commands | default | — | `ls`, `cat` |
| CLI tools | 30000 | 45 | `gh pr list` |
| Package installs | 60000 | 120 | `npm install` |
| Builds & deploys | 60000 | 180 | `npm run build` |
| Long-running | — | — | Use `background: true` + poll |

## Add Your Tools Below

Document your specific CLIs, scripts, and workflows here so Felix knows how to use them.
