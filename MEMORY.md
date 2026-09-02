# Tacit operating memory

## Codex loop runtime boundary

Use `/goal` for one durable objective. Use Desktop Scheduled Tasks for recurring desktop work, or let an external scheduler invoke one finite `codex exec` run with an explicit working directory, sandbox, completion contract, and JSONL/final-output artifact. The scheduler owns recurrence; the Codex worker terminates after one run.

Never make Codex Desktop/app-server supervise or restart itself with `launchctl submit`, raw `launchctl`, Terminal, AppleScript, self-kill, or reopen commands. For Life Manager, trigger the existing launchd job through `lm-loop`; Codex observes and fixes the owner system but does not replace it with another executor.

Before lifecycle mutation, verify all three conditions: `id -un` returns the named account, `launchctl managername` returns `Aqua`, and `launchctl print gui/$UID` exits 0. A numeric username together with non-Aqua/141 and failed LaunchServices means the current Codex harness is isolated. Treat that as a harness-context fault, not a project or business-loop blocker. Stop side effects, record the exact unfinished atom and official command, then resume it unchanged from a healthy Codex session. Do not attempt a GUI bridge and do not mark the project goal blocked for this condition.

Canonical example: when targeted `lm-loop apply` returns launchd 141, do not hand-write a plist or open Terminal. After the Codex app returns to Aqua, run the same target-only apply, kickstart via `lm-loop`, and verify loaded argv, immutable release, terminal event, official effect, and replay-zero.

Sources: [OpenAI non-interactive mode](https://developers.openai.com/codex/noninteractive), [OpenAI Scheduled tasks](https://developers.openai.com/codex/automations), [OpenAI Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals), and [openai/codex issue #32321](https://github.com/openai/codex/issues/32321).
