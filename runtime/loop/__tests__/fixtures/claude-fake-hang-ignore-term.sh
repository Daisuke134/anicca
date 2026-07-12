#!/bin/bash
# config-delivery-verification REQ-009 / PROP-016 fixture: a `claude` stand-in (via CLAUDE_BIN) that
# deliberately IGNORES SIGTERM (`trap '' TERM`) and then sleeps far longer than any test timeout. This
# is what forces the two-stage kill pattern (index.mjs:1037-1041's existing SIGTERM -> 2000ms ->
# SIGKILL sequence, ported to thinkClaudeP by REQ-009) to actually reach its SIGKILL stage -- a
# naive/no-timeout thinkClaudeP (today's bug) would hang on this fixture forever; a SIGTERM-only
# thinkClaudeP would ALSO hang forever (this fixture ignores TERM); only a real two-stage
# SIGTERM-then-SIGKILL implementation can ever terminate this process.
trap '' TERM
sleep 60
