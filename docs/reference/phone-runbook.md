# Phone-only operations runbook

## Claude iOS Code tab

1. In Claude iOS, open the Code tab and connect the GitHub App.
2. Grant the App access only to the required repositories:
   `anicca-products`, `anicca`, and `anicca-dais`.
3. Start the cloud session from the repository needed for the task. The fresh VM
   receives repository-tracked instructions and files; Mac Mini launchd loops stay
   on the Mac Mini and are only edited, instructed, or monitored from the cloud.

## SSH from Termius through Tailscale

1. Connect the phone to the same Tailscale tailnet as the Mac Mini.
2. In Termius, create a host with address `100.99.82.95`, username `anicca`, and
   the SSH key authorized on the Mac Mini.
3. Connect and confirm the host identity before running commands.

```bash
ssh anicca@100.99.82.95
```

## Emergency checks and recovery

```bash
# List loaded Anicca launchd jobs.
launchctl list | grep anicca

# Check root-volume capacity.
df -h /

# Measure colony state and balances from the live script.
bash ~/anicca/skills/self/colony-status.sh

# Restart the Franklin loop after checking its live launchd registration.
launchctl kickstart -k gui/501/ai.anicca.franklin-loop
```

Measured on the Mac Mini on 2026-07-20:

- `launchctl print gui/501/ai.anicca.franklin-loop` resolved to
  `/Users/anicca/Library/LaunchAgents/ai.anicca.franklin-loop.plist` and reported
  `state = running`; the label above is therefore live and verified.
- `launchctl list | grep anicca` produced no matching line in the invoking shell,
  so use `launchctl print gui/501/ai.anicca.franklin-loop` when checking this
  specific per-user service.
- `bash ~/anicca/skills/self/colony-status.sh` completed successfully, but its
  snapshot reported the named colony loops as `STOPPED`. Treat that output as a
  point-in-time measurement and rerun it during an incident.

If the disk is full, identify the large consumer before removing anything. Do not
delete credentials, repositories, or live state as a first response.
