#!/usr/bin/env bash
# gig_single_instance.sh — guarantee ONE gig pass runs at a time.
# Best practice (Baeldung 'Ensure Only One Instance of a Bash Script Is Running'): two valid ways —
# flock (auto-releases on process exit) OR a lockfile/pidfile with staleness. flock is process-scoped
# so it CANNOT span an agent's discrete bash calls (the acquire shell exits between steps); this pass
# runs as a Claude agent, so we use the lockfile-with-staleness approach (their option 2).
# The hourly cron spawns a fresh agent each fire; a browser-driving pass can take >1h, so the next
# fire + healthcheck respawns + manual runs overlap and 6 agents fight over one Chromium / one Coconala
# account (double-applies, overwrite wars, 6x tokens). An agent runs discrete bash calls so an fd/PID
# lock is useless (the acquire shell exits immediately). Use a TIMESTAMP lockfile the pass refreshes:
# fresher than STALE_SEC = a live pass owns this cycle; older = crashed holder, steal it.
#   acquire : claim if free/stale, else print BUSY and exit 1 (the pass MUST then exit)
#   beat    : refresh the timestamp mid-pass so a long-but-alive pass is not stolen
#   release : free it at pass end
LOCK="$HOME/gig/.pass.lock"; STALE_SEC=1800; now=$(date +%s)
case "${1:-acquire}" in
  acquire)
    if [ -f "$LOCK" ] && [ $(( now - $(cat "$LOCK" 2>/dev/null || echo 0) )) -lt "$STALE_SEC" ]; then
      echo "BUSY age=$(( now - $(cat "$LOCK") ))s"; exit 1; fi
    echo "$now" > "$LOCK"; echo "ACQUIRED"; exit 0 ;;
  beat) echo "$now" > "$LOCK"; exit 0 ;;
  release) rm -f "$LOCK"; echo "RELEASED"; exit 0 ;;
  *) echo "usage: acquire|beat|release"; exit 2 ;;
esac
