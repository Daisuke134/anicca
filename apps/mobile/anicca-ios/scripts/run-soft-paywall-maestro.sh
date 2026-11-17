#!/usr/bin/env bash
set -euo pipefail
# Compatibility entrypoint for existing CI. Native StoreKit testing replaces
# sandbox login dismissal; the recording must never contain an Apple sign-in.
exec bash "$(dirname "$0")/run-onboarding-winner-recording.sh" "$@"
