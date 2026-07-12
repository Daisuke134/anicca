#!/bin/bash
# config-delivery-verification FIND-002 regression fixture: instead of a fixed reply, echoes back the
# EXACT argv it was invoked with (NUL-separated, base64-encoded so no bash JSON-escaping is needed),
# wrapped in a valid `claude -p --output-format json` completion body. The test decodes `content` and
# asserts `--dangerously-skip-permissions` is present in the real argv thinkClaudeP passed to spawn() --
# pinning that flag's presence so nobody silently drops it again (adversary iteration-1 FIND-002: the
# flag itself is CORRECT and pre-existing, not a regression to remove -- this fixture only guards it).
encoded=$(printf '%s\0' "$@" | base64 | tr -d '\n')
echo "{\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":\"$encoded\"}}]}"
exit 0
