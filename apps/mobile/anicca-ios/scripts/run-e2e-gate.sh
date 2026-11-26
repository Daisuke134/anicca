#!/usr/bin/env bash
# Anicca E2E release gate runner (Maestro).
#
# Builds the app from THIS checkout for a fresh iOS simulator, installs
# it, runs the gate flows in maestro/gate/ in filename order, proves the
# living-home words change on their own (hierarchy quote-text diff over
# a 35s foreground wait), and writes a machine-readable verdict to
#   $EVIDENCE/gate-result.json
# Exit code is 0 only if every gate flow passed AND the words-changed
# check passed. The e2e-gate checker (tools/e2e-gate) certifies App
# Store submissions against the record this run produces — a build
# with no fresh passing gate-result.json cannot be submitted.
#
# Usage: run-e2e-gate.sh EVIDENCE_DIR
set -uo pipefail

cd "$(dirname "$0")/.."
APP_DIR=$(pwd)
EVIDENCE=${1:?Usage: run-e2e-gate.sh EVIDENCE_DIR}
mkdir -p "$EVIDENCE/junit" "$EVIDENCE/logs" "$EVIDENCE/maestro-tests"
EVIDENCE=$(cd "$EVIDENCE" && pwd)
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "== e2e-gate: started $STARTED_AT =="

# --- 1. Fresh simulator: latest iOS runtime + latest iPhone type ----
RUNTIME=$(xcrun simctl list runtimes available --json | python3 -c "
import json,sys
rs=[r for r in json.load(sys.stdin)['runtimes'] if r['name'].startswith('iOS')]
print(rs[-1]['identifier'])")
DEVICE_TYPE=$(xcrun simctl list devicetypes --json | python3 -c "
import json,sys,re
ds=json.load(sys.stdin)['devicetypes']
cands=sorted((int(m.group(1)), d['name'], d['identifier']) for d in ds for m in [re.match(r'iPhone (\d+)', d['name'])] if m)
print(cands[-1][2])")
echo "runtime=$RUNTIME device_type=$DEVICE_TYPE"
# Remove a stale gate device from an earlier run, then create fresh so
# TCC permissions and app state are factory-clean.
OLD_UDID=$(xcrun simctl list devices --json | python3 -c "
import json,sys
for rt, devs in json.load(sys.stdin)['devices'].items():
    for d in devs:
        if d['name'] == 'AniccaE2EGate':
            print(d['udid']); sys.exit(0)
" || true)
if [[ -n "${OLD_UDID:-}" ]]; then
  xcrun simctl shutdown "$OLD_UDID" >/dev/null 2>&1 || true
  xcrun simctl delete "$OLD_UDID" || true
fi
xcrun simctl shutdown all >/dev/null 2>&1 || true
UDID=$(xcrun simctl create AniccaE2EGate "$DEVICE_TYPE" "$RUNTIME")
echo "simulator=$UDID"
xcrun simctl bootstatus "$UDID" -b
xcrun simctl status_bar "$UDID" override --time '9:41' --batteryState charged --batteryLevel 100

# --- 2. Build the app from this checkout ----------------------------
# Maestro's XCTest driver can be slow to start after several
# successive runs on a loaded CI simulator — flows 04/05 of run
# 45682131989 died with IOSDriverTimeoutException before executing a
# single step, and in run 45744355774 flows 02/03/03b/04 all died the
# same way even at 240s. Give the driver a generous startup budget;
# the reboot + retry in run_flow below is the structural fix, this
# is only the per-attempt budget.
export MAESTRO_DRIVER_STARTUP_TIMEOUT=${MAESTRO_DRIVER_STARTUP_TIMEOUT:-300000}

run_capped() {
  # $1 = cap in seconds; the rest is the command. Returns the
  # command's exit code, or 124 when the cap was exceeded (the
  # command is killed). Run 45638567807 wedged for 2h+ somewhere in
  # this step with no observable wedge point in the retained logs;
  # every long command here is capped so a wedge fails its stage in
  # bounded time WITH the evidence written up to that point, and the
  # workflow's job timeout is the outer backstop.
  local cap=$1; shift
  "$@" &
  local pid=$!
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [[ $waited -ge $cap ]]; then
      echo "run_capped: exceeded ${cap}s, killing: $*" >&2
      kill -TERM "$pid" 2>/dev/null || true
      sleep 10
      kill -KILL "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep 5; waited=$((waited + 5))
  done
  wait "$pid"
  return $?
}

fail_manifest() {
  # $1 = detail. Writes a failed gate-result.json and exits 1: a build
  # or install failure must fail the gate HERE, not cascade into
  # misleading per-flow failures (run 45596746084 did exactly that:
  # the app was built as Release-iphonesimulator while the runner
  # looked in Debug-iphonesimulator, install failed, and every flow
  # then "failed" against an app that was never installed).
  local detail=$1
  echo "E2E GATE BUILD STAGE FAILED: $detail" >&2
  python3 - "$EVIDENCE" "$STARTED_AT" "$detail" <<'PY'
import json, sys, datetime
ev, started, detail = sys.argv[1], sys.argv[2], sys.argv[3]
json.dump({
  "app_id": "ai.anicca.app.ios", "version": None, "build": None,
  "source_commit": None, "started_at": started,
  "finished_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
  "flows": [], "extra_checks": [{"name": "app-build", "status": "failed",
             "detail": detail}],
}, open(f"{ev}/gate-result.json", "w"), indent=2)
PY
  exit 1
}

run_capped 2700 xcodebuild build -project aniccaios.xcodeproj -scheme aniccaios \
  -destination "platform=iOS Simulator,id=$UDID" \
  -derivedDataPath "$EVIDENCE/DerivedData" \
  CODE_SIGNING_ALLOWED=NO > "$EVIDENCE/logs/build.log" 2>&1
BUILD_RC=$?
if [[ $BUILD_RC != 0 ]]; then
  fail_manifest "xcodebuild failed (rc=$BUILD_RC); see logs/build.log"
fi
# The scheme builds Release, not Debug — never hardcode the
# configuration directory; locate the product.
APP_PATH=$(find "$EVIDENCE/DerivedData/Build/Products" -maxdepth 2 \
  -name "aniccaios.app" -type d 2>/dev/null | head -1)
if [[ -z "$APP_PATH" ]]; then
  fail_manifest "aniccaios.app not found under DerivedData/Build/Products after a successful xcodebuild; see logs/build.log"
fi
VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$APP_PATH/Info.plist")
BUILD_NUM=$(/usr/libexec/PlistBuddy -c "Print CFBundleVersion" "$APP_PATH/Info.plist")
SOURCE_COMMIT=$(git rev-parse HEAD)
echo "built version=$VERSION build=$BUILD_NUM commit=$SOURCE_COMMIT app=$APP_PATH"
if ! xcrun simctl install "$UDID" "$APP_PATH" > "$EVIDENCE/logs/install.log" 2>&1; then
  fail_manifest "simctl install failed; see logs/install.log"
fi

# --- 3. Run the gate flows ------------------------------------------
MAESTRO_VERSION=$(maestro --version 2>/dev/null || echo "unknown")
FLOWS=(
  "01-onboarding-first-words"
  "02-paywall-plans"
  "03-living-home-words"
  "03b-living-home-words-changed"
  "04-poyo-on-home"
  "05-settings-round-trip"
)
declare -a FLOW_STATUS
OVERALL=0
reboot_sim() {
  # A fresh boot gives the next flow a clean XCTest/driver
  # environment. Successive `maestro test` invocations on one
  # long-lived simulator leave the XCTest runner degraded: in gate
  # run 45744355774 flow 01 passed, then flows 02/03/03b/04 ALL died
  # with IOSDriverTimeoutException before executing a single step.
  # Installed apps and their data survive a reboot, so the suite's
  # cross-flow state (onboarding completed by flows 01/02, relied on
  # by 03/03b/04/05) is preserved.
  echo "== rebooting simulator for a fresh driver environment =="
  xcrun simctl shutdown "$UDID" >/dev/null 2>&1 || true
  xcrun simctl bootstatus "$UDID" -b
  xcrun simctl status_bar "$UDID" override --time '9:41' --batteryState charged --batteryLevel 100
}

run_flow() {
  local name=$1
  local attempt rc
  for attempt in 1 2; do
    echo "== maestro: $name (attempt $attempt) =="
    run_capped 1500 maestro test --device "$UDID" "maestro/gate/$name.yaml" \
      --format junit --output "$EVIDENCE/junit/$name.xml" \
      --test-output-dir "$EVIDENCE/maestro-tests" \
      > "$EVIDENCE/logs/$name.log" 2>&1
    rc=$?
    if [[ $rc == 0 ]]; then FLOW_STATUS+=("$name=passed"); echo "   -> rc=0"; return; fi
    # Maestro's own verdict line is authoritative for the flow's steps:
    # in run 45841118170 flow 03 printed "[Passed] ... (14m 48s)" and
    # then the process wedged in driver teardown until the cap killed
    # it (rc=124). A cap-kill AFTER the pass verdict is a teardown
    # hang, not a flow failure.
    if [[ $rc == 124 ]] && grep -q "^\[Passed\]" "$EVIDENCE/logs/$name.log"; then
      FLOW_STATUS+=("$name=passed"); echo "   -> passed (cap-kill hit teardown after Maestro's [Passed] verdict)"; return
    fi
    # Self-heal the observed cascade: a driver-startup timeout means
    # the flow never executed a step, and a cap-kill means this slow
    # software-GL runner did not finish it in time — both are clean
    # re-runs after a reboot, not masked failures. Any other failure
    # is final. (The per-attempt cap is 1500s: a legitimate flow took
    # 888s in run 45841118170, so the old 900s cap raced real passes
    # and killed flows 01 and 02 before they could finish.)
    if [[ $attempt == 1 ]] && { grep -q "IOSDriverTimeoutException" "$EVIDENCE/logs/$name.log" || [[ $rc == 124 ]]; }; then
      echo "   -> driver startup timeout or cap-kill; rebooting and retrying once"
      mv "$EVIDENCE/logs/$name.log" "$EVIDENCE/logs/$name.attempt1.log"
      reboot_sim
      continue
    fi
    break
  done
  FLOW_STATUS+=("$name=failed"); OVERALL=1
  echo "   -> rc=$rc"
}

run_flow "01-onboarding-first-words"
reboot_sim
run_flow "02-paywall-plans"
reboot_sim
run_flow "03-living-home-words"
# Words-change proof: dump hierarchy now (T0), wait with the app in the
# foreground, then 03b + T1 dump. The deck dwell is ~20s; 35s of wait
# guarantees at least one autonomous advance if the home is alive.
run_capped 120 maestro --device "$UDID" hierarchy > "$EVIDENCE/hierarchy-t0.txt" 2>/dev/null \
  || run_capped 120 maestro hierarchy > "$EVIDENCE/hierarchy-t0.txt" 2>/dev/null || true
echo "== waiting 35s in foreground for autonomous word change =="
sleep 35
run_flow "03b-living-home-words-changed"
run_capped 120 maestro --device "$UDID" hierarchy > "$EVIDENCE/hierarchy-t1.txt" 2>/dev/null \
  || run_capped 120 maestro hierarchy > "$EVIDENCE/hierarchy-t1.txt" 2>/dev/null || true
WORDS_JSON=$(python3 scripts/e2e_gate_quote_check.py "$EVIDENCE/hierarchy-t0.txt" "$EVIDENCE/hierarchy-t1.txt" 2>/dev/null || echo '{"status":"failed","t0":null,"t1":null,"detail":"quote check crashed"}')
echo "words-change: $WORDS_JSON"
echo "$WORDS_JSON" | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['status']=='passed' else 1)" || OVERALL=1
reboot_sim
run_flow "04-poyo-on-home"
reboot_sim
run_flow "05-settings-round-trip"

# --- 4. Verdict ------------------------------------------------------
FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
FLOW_STATUS_CSV=$(IFS=,; echo "${FLOW_STATUS[*]}")
python3 - "$EVIDENCE" "$STARTED_AT" "$FINISHED_AT" "$VERSION" "$BUILD_NUM" \
  "$SOURCE_COMMIT" "$MAESTRO_VERSION" "$RUNTIME" "$DEVICE_TYPE" "$FLOW_STATUS_CSV" "$WORDS_JSON" <<'PY'
import json, os, sys
(ev, started, finished, version, build, commit, maestro_v,
 runtime, device_type, flows_csv, words_json) = sys.argv[1:12]
flows = []
for pair in flows_csv.split(","):
    if not pair:
        continue
    name, status = pair.rsplit("=", 1)
    flows.append({"name": name, "status": status})
try:
    words = json.loads(words_json)
except Exception:
    words = {"status": "failed", "detail": "unparseable quote-check output"}
run_url = None
if os.environ.get("GITHUB_RUN_ID"):
    run_url = "{}/{}/actions/runs/{}".format(
        os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
        os.environ.get("GITHUB_REPOSITORY", ""),
        os.environ["GITHUB_RUN_ID"])
manifest = {
    "app_id": "ai.anicca.app.ios",
    "version": version,
    "build": build,
    "source_commit": commit,
    "maestro_version": maestro_v,
    "simulator": {"runtime": runtime, "device_type": device_type},
    "started_at": started,
    "finished_at": finished,
    "ci_run_url": run_url,
    "flows": flows,
    "extra_checks": [{
        "name": "living-home-words-changed",
        "status": words.get("status", "failed"),
        "detail": words.get("detail", ""),
        "t0_quote": words.get("t0"),
        "t1_quote": words.get("t1"),
    }],
}
with open(f"{ev}/gate-result.json", "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(json.dumps(manifest, indent=2, ensure_ascii=False))
PY
echo "== e2e-gate: finished $FINISHED_AT overall_rc=$OVERALL =="
exit $OVERALL
