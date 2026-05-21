Fixed observer scripts default observation path to daily file under OBSERVER_DIR.
- observer/observer.sh: OBSERVATION_FILE set to ${OBSERVER_DIR:-$HOME/.openclaw/observer}/observations/$(date +%Y-%m-%d).jsonl
- observer/shell-watcher.sh: added same OBSERVATION_FILE default and log target unified.
Deployed scripts to ~/.openclaw/observer/, validated writes to ~/.openclaw/observer/observations/2026-02-12.jsonl via --self-test, and reloaded launchd agents (ai.anicca.observer, ai.anicca.shell-watcher, ai.anicca.observer-sync).