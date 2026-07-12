#!/bin/bash
# config-delivery-verification FIND-004 fixture: HONORS SIGTERM (unlike
# claude-fake-hang-ignore-term.sh, which deliberately ignores it) and exits promptly once it receives
# one -- well within the 2000ms SIGKILL grace period. Used to exercise the "SIGTERM sent, child honors
# it and exits cleanly during the grace period" path, which adversary iteration-1 FIND-004 found was
# untested: the inner grace-period timer must be captured and cleared on this path, or it dangles and
# later fires a no-op kill() against an already-dead PID.
trap 'exit 0' TERM
sleep 60
