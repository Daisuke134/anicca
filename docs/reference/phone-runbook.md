# Phone-only operations runbook

## Claude iOS Code tab

1. In Claude iOS, open the Code tab and connect the GitHub App.
2. Grant the App access only to the required repositories:
   `anicca-products`, `anicca`, and `anicca-dais`.
3. Start the cloud session from the repository needed for the task. The fresh VM
   receives repository-tracked instructions and files; Mac Mini launchd loops stay
   on the Mac Mini and are only edited, instructed, or monitored from the cloud.

### One-time cloud authorization and proof run (Dais physical action)

The local CLI cannot complete this authorization while it is using the current
third-party provider. On 2026-07-20, `claude --cloud` reached cloud creation but
returned HTTP 403; `claude doctor` reported that claude.ai subscription auth was
inactive and the `user:profile` scope was missing. Complete this one-time flow on
the phone:

1. Sign in to the Dais claude.ai subscription in Claude iOS, open **Code**, and
   choose **Connect GitHub**. If the App authorization page opens, approve the
   `Daisuke134` account and restrict repository access to `anicca-products`,
   `anicca`, and `anicca-dais`.
2. Create the default cloud environment with **Trusted** network access and no
   secrets or setup script. Select `anicca-products`, then select the branch that
   contains this migration spec.
3. Start a **Plan** mode session with this exact read-only prompt:

   ```text
   Do not edit, commit, or push. Report the current git commit; prove that
   AGENTS.md, CLAUDE.md, .claude/settings.json, and .claude/rules were loaded;
   quote the names of two applicable repository rules; run
   echo "$CLAUDE_CODE_REMOTE_SESSION_ID"; and return the session URL.
   ```

4. Keep the session URL and its output as the evidence for spec task #4. The
   expected repository evidence is root `AGENTS.md`, root `CLAUDE.md`, project
   `.claude/settings.json`, and the tracked Markdown files under `.claude/rules/`.

After this authorization, a direct subscription-authenticated terminal can also
run `/web-setup` inside interactive `claude`, then create a session with
`claude --cloud "<task>"`. `claude --remote` is only a deprecated alias for
`--cloud`; `claude --teleport` pulls an existing cloud session into a terminal.

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
