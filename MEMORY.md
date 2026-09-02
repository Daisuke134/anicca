# Tacit operating memory

## Codex loop runtime boundary

Use `/goal` for one durable objective. Use Desktop Scheduled Tasks for recurring desktop work, or let an external scheduler invoke one finite `codex exec` run with an explicit working directory, sandbox, completion contract, and JSONL/final-output artifact. The scheduler owns recurrence; the Codex worker terminates after one run.

Never make Codex Desktop/app-server supervise or restart itself with `launchctl submit`, raw `launchctl`, Terminal, AppleScript, self-kill, or reopen commands. From Remote, never call `launchctl`, `lm-loop apply/start/stop/restart`, app-server daemon lifecycle, or remote-control lifecycle. Life Manager runs through existing natural wakes, and release application belongs to the independent release watcher. Codex observes process, ledger, and artifacts read-only; it does not replace or manually trigger the owner system.

Do not run lifecycle preflight from Remote merely to reproduce a historical 141. A numeric username together with non-Aqua/141 and failed LaunchServices in existing logs means the prior Codex harness was isolated. Treat that as a harness-context fault, not a project or business-loop blocker. Keep Remote alive, stop lifecycle side effects, record the exact unfinished atom, and observe the independent release watcher and natural business-loop wake. Do not attempt a GUI bridge, signal or restart any app-server/updater, restart the Mac, or mark the project goal blocked for this condition.

Canonical example: when historical output shows targeted `lm-loop apply` returned launchd 141, do not rerun it from Remote, hand-write a plist, open Terminal, or request a restart. Wait for the independent release watcher and natural loop owner, then verify loaded argv, immutable release, terminal event, official effect, and replay-zero from read-only artifacts.

Sources: [OpenAI non-interactive mode](https://developers.openai.com/codex/noninteractive), [OpenAI Scheduled tasks](https://developers.openai.com/codex/automations), [OpenAI Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals), and [openai/codex issue #32321](https://github.com/openai/codex/issues/32321).

## Delegated cleanup authority

Symptom: an agent repeatedly asks for permission after Dais has already delegated cleanup or refactor authority. Wrong instinct: transfer ordinary owner/recovery decisions back to Dais because a file might matter. Correct move: measure owner, active/open state, uniqueness, remote or regeneration path, then act and record an exact receipt without asking again. General rule: explicit standing authority covers later reversible or deliberately accepted cleanup in the same scope; ask only when a higher safety boundary requires new authority or the target is outside that scope. Example: preserve OpenClaw working files, verify remote/open state, and remove obsolete Git metadata without repeating the permission question.
