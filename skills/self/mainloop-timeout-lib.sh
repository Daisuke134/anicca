#!/bin/bash
# mainloop-timeout-lib.sh — pure timeout-value resolution for claude-p-mainloop.sh, extracted so it
# can be unit-tested without invoking the real `claude` binary (mirrors this same directory's
# healthcheck-lib.sh / test-healthcheck-lib.sh split).
#
# Why 3600s was wrong: claude-p-mainloop.out.log's last 6 fires (2026-07-10/11) show 3 killed by
# `timeout` (exit status=124) mid-run. MAINLOOP-LOG.md records full VCSDD passes (spec ->
# fresh-adversary spec-review -> TDD -> impl -> fresh-adversary impl-review -> harden -> converge
# -> self-merge) as routine work for this loop, and that legitimately runs past 1h. This was TODO
# `T-revive` in docs/loop-engineering/10-STATUS-verified.md since 2026-07-10, never fixed until now.
#
# Default chosen (18000s / 5h): 5x the old ceiling, while staying below the plist's 21600s
# (6h) StartInterval so a stuck run still yields to the single-instance pidfile guard before
# racing the next scheduled fire.
# Upper bound: GNU `timeout` silently no-ops on absurdly large durations (setitimer overflow),
# defeating the ceiling entirely. Clamp any override to <=21600 (the plist's own StartInterval) so
# a typo'd override can never exceed the fire cadence itself.
MAINLOOP_TIMEOUT_MAX_SEC=21600

resolve_mainloop_timeout_sec() {
  local val="${CLAUDE_P_MAINLOOP_TIMEOUT_SEC:-}"
  if [[ "$val" =~ ^[0-9]+$ ]] && [ "$val" -gt 0 ]; then
    if [ "$val" -gt "$MAINLOOP_TIMEOUT_MAX_SEC" ]; then
      echo "$MAINLOOP_TIMEOUT_MAX_SEC"
    else
      echo "$val"
    fi
  else
    echo "18000"
  fi
}
