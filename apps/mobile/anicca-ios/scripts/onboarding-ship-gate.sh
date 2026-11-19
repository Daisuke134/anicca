#!/usr/bin/env bash
# Local, free XCUITest lane. Only the simulator created here is removed.
set -euo pipefail
app_dir="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -s)" != Darwin ]] || ! command -v xcodebuild >/dev/null; then
  echo 'BLOCKED: onboarding ship gate requires macOS, Xcode and an iOS Simulator runtime.' >&2
  exit 69
fi
: "${ONBOARDING_SIM_RUNTIME:?Set an installed iOS runtime identifier from xcrun simctl list runtimes}"
: "${ONBOARDING_SIM_DEVICE_TYPE:?Set a compatible iPhone device type from xcrun simctl list devicetypes}"
if [[ ! -s "$app_dir/Configs/Production.xcconfig" ]]; then
  echo 'BLOCKED: owner-provided Configs/Production.xcconfig is required; do not use placeholder keys.' >&2
  exit 69
fi
run_dir="$app_dir/build/onboarding-gate/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$run_dir"
sim_id=""
cleanup() {
  if [[ -n "$sim_id" ]]; then
    xcrun simctl shutdown "$sim_id" >/dev/null 2>&1 || true
    xcrun simctl delete "$sim_id" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
{
  git -C "$app_dir" rev-parse HEAD
  git -C "$app_dir" status --short
  xcodebuild -version
  printf 'configuration=Release\nruntime=%s\n' "$ONBOARDING_SIM_RUNTIME"
} > "$run_dir/source.txt"
cd "$app_dir"
# Fresh OS/keychain/notification state for each case; never erase a user's simulator.
for test_case in testFullOnboardingCenterTaps testFullOnboardingLeadingPaddingTaps testFullOnboardingTrailingPaddingTaps; do
  sim_id="$(xcrun simctl create "Anicca onboarding gate $$" "$ONBOARDING_SIM_DEVICE_TYPE" "$ONBOARDING_SIM_RUNTIME")"
  xcrun simctl boot "$sim_id"
  xcrun simctl bootstatus "$sim_id" -b
  xcodebuild test \
    -project aniccaios.xcodeproj \
    -scheme aniccaios \
    -testPlan OnboardingTap \
    -configuration Release \
    -destination "platform=iOS Simulator,id=$sim_id" \
    -parallel-testing-enabled NO \
    -maximum-test-execution-time-allowance 240 \
    -only-testing:"aniccaiosUITests/OnboardingTapE2ETests/$test_case" \
    -derivedDataPath "$run_dir/DerivedData" \
    -resultBundlePath "$run_dir/$test_case.xcresult" \
    CODE_SIGNING_ALLOWED=NO 2>&1 | tee "$run_dir/$test_case.log"
  xcrun xcresulttool get test-results summary --path "$run_dir/$test_case.xcresult" > "$run_dir/$test_case.json"
  python3 scripts/verify-onboarding-result.py "$run_dir/$test_case.json"
  cleanup
  sim_id=""
done
printf 'PASS: full onboarding normal-tap tests. Evidence: %s\n' "$run_dir"
