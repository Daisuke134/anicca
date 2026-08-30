#!/usr/bin/env bash
# Legacy compatibility shim. This entrypoint intentionally performs no Capafy,
# browser, credential, or provider action. Use the split canonical flow instead:
# publish_prepare.sh → CP1_AGENTIC.md/cp1_agent.py → publish_finish.sh.
set -euo pipefail

echo "publish_one.sh is unsupported and performs no action." >&2
echo "Use publish_prepare.sh, CP1_AGENTIC.md/cp1_agent.py, then publish_finish.sh." >&2
exit 64
