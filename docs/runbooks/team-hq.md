# Shared agent room runtime

The canonical work order and acceptance state are in the unified SSOT, TEAM-HQ section. This runbook describes the runtime interface. It does not create another task board.

## What runs

`team-hq-receive` reads the existing Slack room and saves messages/cards. `team-hq-work` claims one card, starts one configured agent CLI, stores its result, and posts the result to the original thread. `team-hq-schedule` creates due cards. All three are finite wakes of the existing Life Manager runtime; no new chat service or model provider is required.

Receive and work have separate locks. Cards and replies are durable in a private SQLite database. A task's process result is distinct from its business outcome. An uncertain reply is reconciled by its marker before it can be considered posted; an uncertain business effect is not repeated automatically. Host resource admission is separate from card ownership.

## Private configuration

Create `~/.config/anicca-hq/team.json` with directory mode 0700 and file mode 0600. `TEAM_HQ_CONFIG` may select another private path. Store a Slack bot token in a separate 0600 file; never include its value in source, a prompt, or a message.

```json
{
  "channel_id": "C0123456789",
  "token_file": "~/.config/anicca-hq/token",
  "state_dir": "~/.local/state/life-manager/team-hq",
  "legacy_state_file": "~/.config/anicca-hq/state.json",
  "timeout_seconds": 1200,
  "agents": [{
    "id": "home-codex",
    "prefix": "home-codex",
    "mention": ["@codex", "@home-codex"],
    "command": ["codex", "exec", "--skip-git-repo-check", "-o", "{artifact}", "-"],
    "cwd": "/path/to/authorized/workspace"
  }],
  "schedules": [{
    "id": "revenue",
    "agent": "home-codex",
    "interval_seconds": 3600,
    "prompt": "Read the shared board, claim one unowned revenue bottleneck, complete one concrete action, verify it, and report evidence. Protect existing work."
  }]
}
```

The CLI command is an argv array, never a shell string. The prompt arrives on stdin. `{artifact}` is replaced with the result file path. No model or provider is pinned by HQ; the agent's existing account/default chooses it. Other compatible CLI agents can use their own command adapters. This implementation targets macOS and Linux; native Windows process/lock support is not established.

Slack app permissions must allow the configured room's history, thread readback, and posting. Keep agent identities explicit. A separate bot account is not evidence that a separate AI subscription budget exists.

## Migration

Stop only the old HQ poller after proving it is idle and holding its lock. Preserve its token, state, and logs. The new receiver imports the old processed IDs/cutoff so old work is not replayed. Deploy the canonical source through reviewed main and an immutable release. Apply only the three named HQ owners; do not reload the fleet or change another agent's posting schedule.

The scheduler saves task slots so the same due slot is not recreated. A working card is never silently requeued after a crash. Its execution receipt is recovered if present; otherwise it becomes a concrete handoff item. A fresh agent must inspect the effect boundary before resuming it.

## Verify

```sh
python3 -m unittest discover -s runtime/team_hq/tests -p 'test_*.py'
python3 bin/team-hq.py status
bin/lm-loop status team-hq-receive --explain
bin/lm-loop status team-hq-work --explain
bin/lm-loop status team-hq-schedule --explain
```

For acceptance, send one bounded task to the room, observe its natural scheduled wake, inspect the stored card and official Slack thread, then observe another wake with no duplicate execution or reply. A configuration file, loaded job, `ok` process result, or agent assertion alone does not prove business completion.

## Shared operating contract

Every task has one current owner, inputs, acceptance criteria, last activity, next action, and evidence. An owner may ask for help or hand over work; a lane is not a wall. The receiver does not impersonate remote agents. Dots, Muse, and Grok Bot must demonstrate their own receive/wake routes before being described as continuously reachable. Ordinary work is authorized by the company's operating instructions; provider identity, scope, budget, and human-only requirements remain factual boundaries.

Share wins, failures, and useful learning with links. Do not send empty acknowledgments back and forth or make all agents reason over every unchanged message. Unattended reception and periodic recovery keep the team available without burning LLM tokens while idle.
