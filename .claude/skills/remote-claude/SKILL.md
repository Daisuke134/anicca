---
name: remote-claude
description: Start or resume a local Claude Code session in Claude Desktop, seed it with a real message, enable Remote Control, and verify that it is reachable from Claude on a phone or browser. Use when the user asks to open Claude Desktop remotely, continue a Mac Claude session from a phone, create a phone-accessible Claude session, or troubleshoot Claude Code Remote Control.
---

# Remote Claude

Create the session without disturbing unrelated Claude chats. Treat “Desktop session opened” and “Remote Control enabled” as separate states and verify both.

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

5. Send `/remote-control` in the warmed session. Verify a success log containing `Remote control enabled` and a bridge session URL or equivalent positive Remote Control state. Do not infer success from the command being typed.

6. Leave Claude Desktop and the backing session running. Tell the user to open Claude on their phone with the same account and select the active Code session.

## CLI-to-Desktop fallback

Use this when Desktop GUI automation cannot focus or type into the composer.

1. Start a real interactive Remote Control session in a PTY. `script` is important when the calling harness does not expose a true TTY:

   ```bash
   script -q /dev/null claude --remote-control=Phone-Remote
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

## Failure handling

| Evidence | Meaning | Action |
|---|---|---|
| `Remote Control requires an active session` | No active query exists | Send one real message, wait for completion or an explicit API response, retry |
| `OAuth access token has expired` | CLI authentication is stale | Import the transcript into authenticated Desktop, then retry there |
| `session_stale_relogin` | Desktop authentication is stale | Report the exact authentication blocker; never claim phone access is ready |
| No `Remote control enabled` evidence | Command did not run or failed | Keep the result as `desktop_ready / remote_blocked` |
| Computer Use Accessibility denied | GUI targeting cannot be trusted | Use the CLI-to-Desktop fallback and log-based verification |

## Safety and reporting

- Never expose OAuth tokens, cookies, QR payloads, or bridge credentials in logs or chat.
- Never close, overwrite, or archive unrelated sessions.
- Do not report success from a dry run, a prefilled prompt, or a pressed key.
- Report four fields: Desktop session ID, seed-message verification, Remote Control state, and any exact blocker.

Official behavior reference: [Continue local sessions from any device with Remote Control](https://code.claude.com/docs/en/remote-control).
