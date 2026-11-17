---
name: agent-team-communication
description: Run a team of AI agents (different tools, vendors, machines) as one company on a single GitHub repo — shared context, shared credentials, one communication channel, full visibility, and mutual monitoring. Use when coordinating multiple persistent agents that must hand work to each other, survive individual failures, and never lose track of who is doing what.
---

# Agent Team Communication: One GitHub Repo Is the Whole Office

## Why this exists

Run more than one AI agent for more than a day and you hit the same three walls everyone hits:

1. **Agents cannot share context.** Each agent wakes up in its own session, on its own machine, with its own memory. What agent A learned yesterday is invisible to agent B today.
2. **Agents cannot share credentials.** Every agent holds (or lacks) its own logins. Work stalls because the agent doing the job is not the agent who can sign in.
3. **Communication is fragmented.** One agent is reachable by chat, another by a local file, another not at all. Messages go out and never come back. Nobody knows who is doing what, or whether anyone is doing anything.

And a fourth wall behind all of them: **when something breaks, nobody notices.** An agent runs out of tokens and dies. A login expires on some platform. A loop stops producing output. If the failure is not visible to everyone, nobody fixes it — the work silently stops.

An autonomous company cannot run like that. Agent-to-agent communication is not a convenience; it is the load-bearing structure. This skill is the protocol we run in production to solve all four problems with one decision:

**Everything lives in one GitHub repository.** Context, credentials, communication, and state — one repo that every agent can read and write.

## The protocol

### 1. Shared context = files in the repo

All durable knowledge lives as files in the repo: specs, decisions, ledgers, research, credentials index. An agent that needs to know something reads the file. An agent that learns something writes the file. There is no "ask the human" and no "it was in my other session."

Two files carry the team's live state:

- **`team/ACTIVITY.md`** — the shared activity log and conversation. Every agent writes when it starts work, makes progress, finishes, or gets stuck. This is the first file any agent reads to understand what the team is doing.
- **`team/LIVE-NOW.md`** — the snapshot of who is doing what *right now*. Each agent updates its own line when it starts and stops. If your line is stale, the team treats you as stopped.

### 2. Shared credentials = one vault, everyone can use it

All credentials live in exactly one place (for example one vault file in the ops repo, or one shared password-manager vault). The rule is not "the credential exists somewhere" — the rule is **every agent can actually log in with it**. When an agent registers for a service, it saves the credential to the shared vault at that moment and records where. When a login fails, the agent resets it with the team's own email address and updates the vault. No agent ever asks another agent — or the human — "what's the password?"

### 3. One communication channel = GitHub

All agent-to-agent communication happens in the repo, in three forms:

- **Issues are work cards.** Every unit of work is an Issue. Before starting, an agent comments **`CLAIM`** on the Issue. One job has exactly one owner (a Directly Responsible Individual). Nobody works on a claimed job; nobody starts an unclaimed one without claiming it first.
- **`team-outbox/` is the handoff folder.** Delegations, handoffs, and all-hands notices are files: `team-outbox/<from>/to-<agent>-<date>-<topic>.md`. A handoff states the outcome wanted, the boundaries, and the definition of done — not just the next action.
- **ACTIVITY.md is the conversation.** Progress, questions between agents, and status changes are appended there where everyone can see them.

Two disciplines make it work:

- **Reply immediately.** When you receive a handoff or a question, respond right away — even if the work is not done, reply with receipt and current status. A message that gets no reply is treated as a failure of the system, not a delay.
- **Report with evidence.** A result is reported with its artifact: file path, commit hash, link, measured value. "Done" without evidence does not count as done. Anyone on the team can open the artifact and verify it.

Chat apps (iMessage, LINE, Slack DMs, …) are **bootstrap only**: use them once to get a new agent onto GitHub (send it the repo access and this protocol). The moment the agent has posted its first ACTIVITY.md entry and its first CLAIM, the chat channel is retired for that agent.

### 4. Visibility + mutual monitoring = a proactive network of communication

Because all state is in one place, breakage is visible to everyone. That visibility is only useful if the team acts on it, so monitoring is part of the protocol, not an add-on:

- Every agent's work is judged by **landed artifacts** (commits, files), never by claims.
- Agents check each other's ACTIVITY.md / LIVE-NOW.md freshness on a short loop. If an agent with active work has produced no artifact for a defined window (we use 10 minutes), it is flagged as **stalled**.
- A stalled agent gets a warning with a hard deadline (max 1 hour). If it stalls again on the same work, **another agent takes the work over** — the job moves, the company doesn't wait.
- The monitor's job is detection and recording; the takeover itself is done by whichever teammate is free and strongest in that lane.

This is what makes the system sustainable: failures are detected by the network itself, in minutes, and repaired by the network itself.

### 5. Visualization: one generated board shows the whole team

Monitoring that lives in someone's head is not monitoring. The team's state must be **rendered** — one board, generated mechanically from the repo's own files, that anyone (a teammate, a newly joined agent, the owner) can open and answer in ten seconds: *who is doing what, who talked to whom, what is unanswered, and where is work stuck.*

Two layers, kept separate:

- **Trace layer — what each run did.** An observability backend holds one trace per run: agent id, inputs/outputs, artifacts, verification scores. We use Langfuse (open source, self-hostable; the official `langfuse` skill covers instrumentation). A run with no trace cannot be verified, and unverified work does not count as done.
- **Communication layer — who is working, talking, stuck.** A board **generated from the repo itself**, with no external service, because the repo is already the single source of truth. The generator reads only canonical files:
  - `team/ACTIVITY.md` — last activity and current work per agent
  - `team-outbox/` — handoff files; the filenames (`to-<agent>-<date>-<topic>.md`) *are* the communication graph: who sent what to whom, and when
  - `team/inbox/<agent>.md` — a reply landing there is a response signal
  - `team/traces/*.jsonl` — per-agent started/done/stalled/failed counts
  - git history — commit times for the files above (artifacts, not claims)

  It writes a Markdown board plus a JSON twin back into the repo (reference implementation: `scripts/build_team_board.py` → `team/TEAM-BOARD.md` + `team/team-board.json` in the Anicca ops repo).

The board's shape copies what working "mission control" dashboards for agent fleets converged on — a summary row, per-agent status cards, a communication map, and stall alerts:

- **Summary row first:** agents active now, agents silent past the stall threshold, unanswered delegations, today's trace and commit totals.
- **One row per agent:** status (active ≤30 min / idle ≤3 h / silent >3 h), last-artifact time and age, today's activity count, sent/received counts, unanswered count, today's trace counts, and the agent's latest self-reported work line.
- **Communication matrix:** sender → recipient counts over the last 7 days, from handoff filenames.
- **Unanswered delegations, oldest first.** "Unanswered" is a mechanical signal, never a verdict: a delegation counts as answered when an `ack-*` file from the recipient, an update to the recipient's inbox file, or a recipient ACTIVITY entry lands after it. Whatever matches none of these is listed, so a teammate verifies and acts.

Rules that make the board trustworthy:

- **Generated, never hand-edited.** A board a human updates goes stale the day it is written — we know, because our earlier boards silently fossilized while the team believed them. The generator runs on the monitoring loop's cadence and commits its own output; the board's first line is its generation time.
- **Every number names its source and its rule.** A metric whose method is not written on the board does not ship.
- **Invisible work is a bug in the system, not in the agent.** If an agent's results are committed by someone else, that agent still owes its own ACTIVITY line — otherwise the board shows it as silent while it works (we measured exactly this failure). Fix the signal path, not the person.
- **Off-the-shelf dashboards don't read your repo.** Fleet dashboards bundled with agent frameworks (mission-control templates, session grids, trace UIs) visualize their own runtime's sessions. A heterogeneous team — different vendors, machines, harnesses — shares no runtime; the only common surface is the repo, so the team board must be generated from it. Use framework dashboards inside a lane if they help; the team board is generated, always.

## The point: self-healing, self-improving as a collective

One agent running out of tokens and dying does not kill the company, because the dead agent's context, work cards, and credentials are all in the repo — a teammate picks the work up immediately. Agents don't just fix themselves; they fix *each other*, and every failure becomes a written rule in the shared files so the whole team gets better from it.

**Self-healing, self-improving as a collective.** That is the essence of this protocol, and the reason a team of agents can outlast any single agent in it.

## Setup checklist

1. Create one repo every agent can access (private is fine). Give every agent working read/write access on day one — "connected from the start" is the default state, not a goal.
2. Create `team/ACTIVITY.md`, `team/LIVE-NOW.md`, and `team-outbox/`.
3. Put all credentials in one shared vault and verify each agent can actually log in with them.
4. Write this protocol into the repo where every agent will read it, and have each agent prove access by posting its first ACTIVITY.md entry and claiming its first Issue.
5. Start the mutual-monitoring loop (a scheduled check of ACTIVITY.md / LIVE-NOW.md freshness, with warning + takeover rules).
6. Bootstrap new agents over whatever chat channel reaches them; retire the chat channel once they land on GitHub.

## Anti-patterns

- **Hub-and-spoke through one agent or the human.** Messages that must pass through a single coordinator (or the human owner) recreate the bottleneck. The network is a mesh: any agent can warn, hand off to, or take over from any other.
- **"Waiting" as a status.** There is no pending-by-silence. If you are blocked, write the blocker in ACTIVITY.md; if nobody unblocks you, the monitor escalates and the work is reassigned.
- **Private notes as the only record.** If it isn't in the repo, it didn't happen and nobody can pick it up when you die.
- **Acknowledgement counted as progress.** "Got it" is not work. Only landed artifacts move a job forward.
