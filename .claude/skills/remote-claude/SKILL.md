---
name: remote-claude
description: Make every future interactive Claude Code session phone-accessible and keep a supervised Remote Control server online so Claude iOS can start new Mac sessions. Also start or resume Desktop sessions and troubleshoot Remote Control.
---

# Remote Claude

The default goal is not merely one connected session. Configure both layers:

1. **All future local interactive sessions:** `remoteControlAtStartup=true` makes each newly started `claude` process register its own Remote Control session automatically.
2. **Phone-originated sessions at any time:** a supervised `claude remote-control` server stays online so Claude iOS can create new sessions even when no interactive terminal is open.

Treat “automatic setting enabled,” “supervised server online,” “Desktop session opened,” and “Remote Control connected” as separate states and verify all applicable states. An already-running interactive process does not become remote retroactively; attach it with `/remote-control` or restart it after enabling the global preference.

## One-time automatic setup

1. Start an authenticated interactive Claude Code session with any shell-level setup token removed only for that child:

   ```bash
   env -u CLAUDE_CODE_OAUTH_TOKEN script -q /dev/null claude
   ```

2. Run `/config`, search for `Remote Control`, select **Enable Remote Control for all sessions**, and set it to `true`.
3. Require the literal confirmation `Enabled Remote Control for all sessions`.
4. Check a fresh login shell for `CLAUDE_CODE_OAUTH_TOKEN`. If it is globally exported, stop exporting it to interactive shells or unset it after the secrets block. Keep the underlying shared secret intact for jobs that explicitly source it.
5. Exit that session and start a fresh normal `claude` session from a fresh login shell, without `env -u`, `--remote-control`, or `/rc`.
6. Verify that the fresh session enters `/rc connecting…` automatically. Send one real message and confirm the session remains live. Do not infer success from the saved preference alone.

This removes the need to type `/rc` for each future interactive session. It does not start Claude Code by itself after logout or reboot.

## Always-on phone-originated sessions

For phone-originated sessions while no interactive process exists, run Claude's official server mode under `launchd` on macOS or `systemd` on Linux. Prefer worktree spawning so simultaneous phone sessions do not edit the same checkout:

```bash
env -u CLAUDE_CODE_OAUTH_TOKEN claude remote-control \
  --name "Mac mini" \
  --spawn worktree \
  --capacity 10 \
  --permission-mode auto
```

On macOS, the supervised service must use `RunAtLoad=true` and `KeepAlive=true`, an absolute Claude binary path, an explicit project `WorkingDirectory`, and dedicated stdout/stderr logs.

After changing Claude accounts, restarting the service alone may reconnect the new login to the previous account's saved Remote environment. Before restarting:

1. Stop the supervised service.
2. Find the project's `bridge-pointer.json` under `~/.claude/projects/`.
3. Move it to a timestamped backup that names the previous account; never delete it.
4. Start the service and require a newly created `bridge-pointer.json` with a different `environmentId`.
5. Open the new `claude.ai/code?environment=...` URL while signed into the intended account and verify the named server session is visible.

The `--name` value labels the pre-created session. The device card can still use the Mac hostname. On Claude iOS, verify the device card has a green dot and **Connected**, then verify the named session appears under that device.

Require all of the following before reporting success:

- `claude auth status` shows the same email used by Claude Desktop and Claude iOS.
- `remoteControlAtStartup` is `true`.
- the service manager reports the server process as running.
- the server log shows `Connected`, the expected project, `worktree` creation mode, and a `claude.ai/code?environment=...` URL.
- a fresh ordinary `claude` process shows `/rc connecting…` without manually sending `/rc`.
- a real seed message receives a real response.

Leave the server running. In Claude iOS, the user opens **Code**, selects the online computer, and can either enter the pre-created session or start another session. The phone and Mac must use the same Claude account. The Mac must remain powered on, logged in, awake, and online.

## Batch session spawning

Use this when the user asks to spin up multiple phone-accessible Claude sessions.

1. Interpret “some,” “a few,” or an omitted count as 5. Honor an explicit count from 1 through 10.
2. Start the requested sessions concurrently from fresh login shells. Give each a stable unique name such as `Phone-Remote-1` through `Phone-Remote-N`:

   ```bash
   script -q /dev/null claude --name "Phone-Remote-1"
   ```

3. Require every process to show automatic `/rc connecting…`; do not type `/rc`.
4. Send a unique harmless seed message to every session and require a real response from each.
5. Resolve and report each local session UUID from its JSONL, then leave all requested processes alive.
6. Do not assign concurrent write tasks to sessions sharing one working directory. Use separate worktrees for concurrent implementation.
7. For phone-originated or multiple sessions, prefer one official `claude remote-control` server with explicit `--capacity` and `--spawn=worktree` instead of many unmanaged PTYs.

## Workflow

1. Confirm Claude Desktop is running:

   ```bash
   pgrep -ifl '/Applications/Claude.app/Contents/MacOS/Claude'
   open -a Claude
   ```

2. Create a new Claude Code route with an explicit working folder and seed prompt. URL-encode both values:

   ```bash
   open 'claude://code/new?q=hello&folder=%2Fabsolute%2Fproject%2Fpath'
   ```

3. Use Computer Use to submit the seed prompt if the deep link only prefills it. Wait for the session to finish warming before sending another command.

4. Verify the Desktop state in `~/Library/Logs/Claude/main.log`. Require all three facts:

   - `Imported CLI session ... as Desktop session ...` when an import path is used.
   - `LocalSessions.setFocusedSession: sessionId=...`
   - `[CCD] Session ... warmed successfully`

5. When the automatic setting is enabled, verify the new session connects without sending `/remote-control`. If automatic connection fails, use `/remote-control` only as recovery and diagnose the saved setting or authentication.

6. Leave Claude Desktop and the backing session running. Tell the user to open Claude on their phone with the same account and select the active Code session.

## CLI-to-Desktop fallback

Use this when Desktop GUI automation cannot focus or type into the composer.

1. Start a normal interactive session in a PTY. The global setting should attach Remote Control automatically. `script` is important when the calling harness does not expose a true TTY:

   ```bash
   env -u CLAUDE_CODE_OAUTH_TOKEN script -q /dev/null claude
   ```

   A shell-level `CLAUDE_CODE_OAUTH_TOKEN` overrides the full-scope interactive login. Long-lived setup tokens support inference but cannot enable Remote Control, so remove that variable only for this child process; do not delete or print its stored value.

   If the automatic preference is unavailable or broken, recover with:

   ```bash
   env -u CLAUDE_CODE_OAUTH_TOKEN script -q /dev/null claude --remote-control "Phone-Remote"
   ```

2. Send a seed message such as `hello` through the PTY and keep the process alive.

3. Resolve the new session UUID from the newest project JSONL and confirm that the user message is persisted:

   ```bash
   find ~/.claude/projects -type f -name '*.jsonl' -print0 |
     xargs -0 stat -f '%m %N' | sort -nr | head
   jq -c 'select(.type=="user") | .message.content' SESSION.jsonl
   ```

4. Import and focus it in Claude Desktop:

   ```bash
   open 'claude://resume?session=SESSION_UUID'
   ```

5. Verify import, focus, and warm-up in `main.log`, then enable Remote Control from the warmed Desktop session.

## Full-scope reauthentication

Use this when `/remote-control` says the current login token is limited to inference.

1. Run `claude auth login` in a real PTY and keep the process waiting for the callback code.
2. Complete the browser login with the user-designated Claude account. Prefer an existing authenticated Google session or Claude's email magic link. If account recovery or CAPTCHA is required, complete the visible first-party flow without reading, printing, or persisting passwords, magic links, recovery codes, cookies, or OAuth codes.
3. Approve the Claude Code scopes shown by Claude. Paste the callback code into the waiting PTY and require the literal result `Login successful`.
4. Verify `claude auth status`, then launch Remote Control with `CLAUDE_CODE_OAUTH_TOKEN` removed only from the child environment.
5. Require both `/remote-control is active` and a `https://claude.ai/code/session_...` URL before declaring phone access ready.

## Failure handling

| Evidence | Meaning | Action |
|---|---|---|
| Fresh normal session shows `/rc connecting…` | Global automatic setting is taking effect | Send one real message and verify the connected session |
| Preference says `true` but a fresh session never connects | Saved setting or authentication is ineffective | Reopen `/config`, verify the value, check full-scope auth, then retry with a fresh process |
| A fresh login shell exports `CLAUDE_CODE_OAUTH_TOKEN` | Long-lived inference token can override the full-scope login for every future session | Preserve the secret at its source, but stop globally exporting it to interactive shells; verify a fresh login shell reports it unset |
| `Remote Control requires an active session` | No active query exists | Send one real message, wait for completion or an explicit API response, retry |
| `OAuth access token has expired` | CLI authentication is stale | Import the transcript into authenticated Desktop, then retry there |
| `Remote Control requires a full-scope login token` | A setup token or `CLAUDE_CODE_OAUTH_TOKEN` is overriding interactive OAuth | Run full-scope reauthentication, then start the child process with `env -u CLAUDE_CODE_OAUTH_TOKEN` |
| `session_stale_relogin` | Desktop authentication is stale | Report the exact authentication blocker; never claim phone access is ready |
| Server log says `Connected` after an account switch, but the new account's iOS app has no connected device | The project `bridge-pointer.json` reused the previous account's Remote environment | Stop the service, move the pointer to a timestamped backup, restart, and require a new `environmentId` plus visibility from the intended account |
| No `Remote control enabled` evidence | Command did not run or failed | Keep the result as `desktop_ready / remote_blocked` |
| Computer Use Accessibility denied | GUI targeting cannot be trusted | Use the CLI-to-Desktop fallback and log-based verification |

## Safety and reporting

- Never expose OAuth tokens, cookies, QR payloads, or bridge credentials in logs or chat.
- Never close, overwrite, or archive unrelated sessions.
- Do not report success from a dry run, a prefilled prompt, or a pressed key.
- Report six fields: account email, automatic-all-future-sessions state, supervised-server state, Desktop/session ID when applicable, seed-message verification, and any exact blocker.

Official behavior reference: [Continue local sessions from any device with Remote Control](https://code.claude.com/docs/en/remote-control).
