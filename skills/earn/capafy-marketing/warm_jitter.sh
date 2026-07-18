#!/usr/bin/env bash
# warm_jitter.sh — human-like timing: sleep a random 0-3h before running the warmup, so the daily
# warmup does NOT fire at the exact same clock time every day (Dais 2026-07-18: kill the fixed-time
# bot tell). launchd fires this at a base time; the random sleep spreads the actual run across a window.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
sleep $(( RANDOM % 10800 ))   # 0..10800s = 0..3h jitter
exec /opt/homebrew/bin/python3 "$HOME/.agents/skills/ig-account-warmer/scripts/warm.py" useclaudeskills
