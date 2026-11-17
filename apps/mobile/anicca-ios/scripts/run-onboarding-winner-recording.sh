#!/usr/bin/env bash
set -euo pipefail
# An installed app launched by simctl/Maestro does not inherit a scheme's
# StoreKit config. The native test owns SKTestSession before launching instead.
cd "$(dirname "$0")/.."
evidence=${1:?Usage: run-onboarding-winner-recording.sh EVIDENCE_DIR [SIMULATOR_UUID]}
mkdir -p "$evidence"
evidence=$(cd "$evidence" && pwd)
simulator=${2:-}
if [[ -z "$simulator" ]]; then
    simulator=$(xcrun simctl list devices available -j | python3 -c '
import json,sys
for runtime, devices in json.load(sys.stdin)["devices"].items():
    if runtime != "com.apple.CoreSimulator.SimRuntime.iOS-26-2": continue
    for device in devices:
        if device.get("isAvailable") and "iPhone" in device["name"]:
            print(device["udid"]); sys.exit(0)
sys.exit("No available iOS 26.2 iPhone simulator")
')
fi
xcrun simctl bootstatus "$simulator" -b
xcrun simctl status_bar "$simulator" override --time '9:41' --batteryState charged --batteryLevel 100
xcrun simctl io "$simulator" recordVideo --codec=h264 "$evidence/experience.mp4" > "$evidence/recording.log" 2>&1 &
recorder=$!
started=$SECONDS
recording_result=0
stop_recording() {
    if ! kill -0 "$recorder" 2>/dev/null; then
        recording_result=1
    else
        kill -INT "$recorder" 2>/dev/null || recording_result=1
    fi
    local code=0
    wait "$recorder" || code=$?
    if [[ "$code" != 0 && "$code" != 130 ]]; then recording_result=1; fi
}
trap stop_recording EXIT
sleep 1
kill -0 "$recorder"
set +e
xcodebuild test -project aniccaios.xcodeproj -scheme aniccaios \
  -destination "platform=iOS Simulator,id=$simulator" \
  -only-testing:aniccaiosUITests/OnboardingWinnerE2ETests \
  -resultBundlePath "$evidence/winner.xcresult" \
  CODE_SIGNING_ALLOWED=NO > "$evidence/build-test.log" 2>&1
result=$?
set -e
elapsed=$((SECONDS - started))
stop_recording
trap - EXIT
printf '%s\n' "$result" > "$evidence/exit-code.txt"
git rev-parse HEAD > "$evidence/source-commit.txt"
if [[ "$recording_result" != 0 || ! -s "$evidence/experience.mp4" ]]; then
    echo 'Simulator recording failed or ended before the test completed.' >&2
    exit 1
fi
xcrun swift scripts/verify-maestro-recording.swift "$evidence/experience.mp4" "$elapsed" > "$evidence/video-validation.json"
exit "$result"
