#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' 'outbound runtime healthcheck launchd is retired; use the cloud worker monitor.' >&2
exit 78
