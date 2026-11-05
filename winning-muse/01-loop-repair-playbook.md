# Loop Repair Playbook

How to diagnose and repair a stalled scheduled loop (cron job, agent loop,
pipeline) from fixed procedures instead of improvisation.

Sources: Airflow Summit 2026, "From Broken DAGs to Self-Healing Pipelines"
(AIRA: agents select approved playbooks, they do not invent production
actions; bounded retries; validation before resolution); PlainSightIL,
"AI Principal Engineer Agent Playbook" (validation gates at every state
transition, diagnostic capture); Anthropic's Project Vend phase 2, via
winner-operator research (fixed procedures, not more autonomy, are what
turned the numbers).

## Prove the stall from records, not from the schedule

- Check the job's run history and the output ledger (or published artifacts)
  for the window. A schedule existing, a job starting, a queue entry, or a
  `succeeded` status is not output.
- Name the broken stage in the four-stage chain:
  1. **Trigger** — did the time or event occur?
  2. **Execution** — was a run created, and what state did it report?
  3. **Handoff** — did the result reach an agent who can act on it?
  4. **Arrival** — did the expected artifact actually appear (post URL,
     listing, reply, sale, ledger row)?
- Repair the stage that broke. Re-kicking the whole job when the break is at
  arrival only repeats the failure.

## Pick the playbook for the failure pattern

Do not invent a new production action mid-incident. Select the matching
playbook:

- **Run missing, coalesced, or cancelled:** hand-run the owning job once,
  then verify the expected artifact for the window. If it is still absent,
  the failure is inside the run, not the schedule.
- **Partial output (some surfaces done, the rest untouched):** fill the
  missing surfaces in the same pass. Never leave the remainder for the next
  scheduled run; an overloaded run that ends partial is split by surface
  instead of re-run whole.
- **Missed slot whose time has passed:** publish immediately to fill it; do
  not wait for the next slot.
- **Session or credential expired:** agent-side recovery only, in this
  order: saved session → vault index → password reset with the account's own
  agent email (save the new credential at once) → re-register with agent
  email. Never route the step to a human.
- **Approval card or gate pending:** treat as an internal jam. Switch to the
  route that does not surface a card (CLI or API) and record the jam; do not
  present the card as someone else's work.
- **Verification gate failed (quality, destination, diff count, readback):**
  hold the output, repair the artifact, re-run the gate. Never publish
  around a failed gate.
- **External API intermittently failing (truncated reads, dropped
  connections):** this is a script defect until proven otherwise — do not
  file it under "the provider is unstable". Harden the client: more retries
  with exponential backoff, a longer timeout, and a documented fallback
  route (for example a simpler GET endpoint), recording in the data itself
  which route answered. **Proven**: this exact repair took a brand-mention
  measurement from recurring 5/8–7/8 completions to verified 8/8 with zero
  error rows, one answer arriving via the fallback route.

## Bounds on repair

- One hand-run per stall per check. If the same failure survives two
  consecutive checks, stop re-kicking it the same way: split the job, switch
  the route, or take the surface over by hand, and record the jam with its
  unblocking step. (House rule, stricter: begin the repair at the *first*
  detection — see the working principles.)
- If repair attempts alternate between two conflicting fixes, stop (circuit
  breaker) and record both attempts instead of thrashing.
- Bounded retries with backoff for temporary outages; unknown or
  high-impact failures preserve evidence and escalate inside the team, never
  silently.

## A repair is done only when the artifact is verified

- Confirm the expected artifact itself: the public URL loads with the right
  content, the ledger row exists, the counterpart-side state changed.
- Record one log line per incident in the loop's log: the window, the
  expected artifact, the broken stage, the playbook used, and the verified
  result.
- Report repairs as published URLs and changed numbers only. "Ran the job"
  and "started the fix" are not results.
