#!/bin/bash
# config-delivery-verification REQ-009 / PROP-015 fixture: stands in for the real `claude` binary via
# CLAUDE_BIN (the SAME existing override point brain.mjs already reads —
# `config.CLAUDE_BIN || process.env.CLAUDE_BIN || 'claude'` — no production code change needed to use
# this fixture). Exits almost immediately with a valid `claude -p --output-format json` shaped body, so
# thinkClaudeP must resolve normally well within any reasonable timeout.
echo '{"id":"fake-fast","choices":[{"message":{"role":"assistant","content":"ok"}}]}'
exit 0
