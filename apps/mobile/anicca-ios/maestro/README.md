# Anicca iOS Maestro journeys

Run from `apps/mobile/anicca-ios`. The current soft-paywall journey is
`v1.9.14/01-soft-paywall.yaml`: clean launch, goal, first affirmation/save,
optional reminder/notification setup, free feed and swipe, saved words, locked
Premium theme, actual purchase plans, close, free theme and continued reading,
then relaunch into the feed.

## Real simulator run and recording

Use a Mac with full Xcode, an installed iPhone simulator runtime, Java 17 and
Maestro CLI (`brew install mobile-dev-inc/tap/maestro`). CommandLineTools alone
does not include the iOS simulator. Supply the existing private Production and
Staging xcconfig files; real RevenueCat SDK settings are required to load plans.
Never commit configuration values.

```bash
bash scripts/run-soft-paywall-maestro.sh /absolute/path/to/private-evidence
```

The helper selects an available iPhone simulator, builds and installs this
checkout, records the actual screen while Maestro runs, and saves JUnit, debug
output, source commit, simulator metadata and MP4. Recording startup/termination,
duration and a decoded frame must pass independently of the Maestro result.
Inspect the real video before calling the experience verified. This helper
replaces the old README's nonexistent `run-maestro-e2e.sh` command.

To drive an already installed build without recording:

```bash
maestro --device SIMULATOR_UDID test --format JUNIT --output result.xml \
  maestro/v1.9.14/01-soft-paywall.yaml
```

## GitHub Actions

The real journey is an explicit manual job in
`.github/workflows/anicca-ios-build.yml`, using a free local Maestro CLI on the
GitHub macOS runner. It does not call paid Maestro Cloud. The repository secret
`ANICCA_E2E_XCCONFIG_B64` supplies the private SDK configuration.

```bash
gh workflow run anicca-ios-build.yml --ref YOUR_BRANCH -f run_maestro=true
```

Download the `soft-paywall-evidence-COMMIT` artifact. Build logs and xcconfig files
are excluded from the artifact. Failed runs are retained as failures, not
accepted experience recordings. PRs run unsigned build/unit tests; they do not
automatically run the real journey. There is no `maestro-e2e.yml` workflow.

## Versioned and specialized flows

`v1.8.0/`, `onboarding/` and `e2e/` contain older or specialized flows. Their
entry states and product assumptions differ; running the entire directory is
not the current acceptance command. Many flows use accessibility IDs. Required
product assertions must not be made optional to hide a failure.

`v1.8.0/14-notification-message.yaml` expects an already injected notification.
Simulator injection verifies routing, not real APNs delivery.

[Maestro CLI reference](https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options)

## Final 1.9.14 verification budget

The real job uses standard `macos-15-intel`, Xcode26.2/iOS26.2 and a120-minute
job limit. The prior40-minute limit cancelled run43268640984 after the real
build reached recording; its MP4 is incomplete and not acceptance evidence.
For the final delegated verification, dispatch once only. If that run fails or
is cancelled, preserve its actual result and report the blocker; do not rerun
it or weaken assertions. This includes a host-admission failure.
