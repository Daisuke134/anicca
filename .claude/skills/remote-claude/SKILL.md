---
name: remote-claude
description: Enable Remote Control for every Claude Code session, start or resume a local session in Claude Desktop, seed it with a real message, and verify phone access. Use when the user asks to make all Claude sessions phone-accessible, open Claude Desktop remotely, continue a Mac Claude session from a phone, create a phone-accessible Claude session, or troubleshoot Claude Code Remote Control.
---

# Remote Claude

Configure automatic Remote Control once, then create sessions without disturbing unrelated Claude chats. Treat “automatic setting enabled,” “Desktop session opened,” and “Remote Control connected” as separate states and verify all applicable states.

## One-time automatic setup

1. Start an authenticated interactive Claude Code session with any shell-level setup token removed only for that child:

   ```bash
   env -u CLAUDE_CODE_OAUTH_TOKEN script -q /dev/null claude
   ```

2. Run `/config`, search for `Remote Control`, select **Enable Remote Control for all sessions**, and set it to `true`.
3. Require the literal confirmation `Enabled Remote Control for all sessions`.
4. Exit that session and start a fresh normal `claude` session without `--remote-control`.
5. Verify that the fresh session enters `/rc connecting…` automatically. Send one real message and confirm the session remains live. Do not infer success from the saved preference alone.

This removes the need to type `/rc` for each future interactive session. It does not start Claude Code by itself after logout or reboot. For phone-originated sessions while no interactive process exists, use Claude's official server mode under a supervised service:

```bash
claude remote-control --name "Mac mini"
```

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
| `Remote Control requires an active session` | No active query exists | Send one real message, wait for completion or an explicit API response, retry |
| `OAuth access token has expired` | CLI authentication is stale | Import the transcript into authenticated Desktop, then retry there |
| `Remote Control requires a full-scope login token` | A setup token or `CLAUDE_CODE_OAUTH_TOKEN` is overriding interactive OAuth | Run full-scope reauthentication, then start the child process with `env -u CLAUDE_CODE_OAUTH_TOKEN` |
| `session_stale_relogin` | Desktop authentication is stale | Report the exact authentication blocker; never claim phone access is ready |
| No `Remote control enabled` evidence | Command did not run or failed | Keep the result as `desktop_ready / remote_blocked` |
| Computer Use Accessibility denied | GUI targeting cannot be trusted | Use the CLI-to-Desktop fallback and log-based verification |

## Safety and reporting

- Never expose OAuth tokens, cookies, QR payloads, or bridge credentials in logs or chat.
- Never close, overwrite, or archive unrelated sessions.
- Do not report success from a dry run, a prefilled prompt, or a pressed key.
- Report four fields: Desktop session ID, seed-message verification, Remote Control state, and any exact blocker.

Official behavior reference: [Continue local sessions from any device with Remote Control](https://code.claude.com/docs/en/remote-control).
