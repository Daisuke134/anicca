# I watched an AI fix its own broken code today. Here's the proof.

**Overview**

- Loop engineering means you stop prompting an AI turn by turn and instead design the *system* that prompts it for you.
- That system has a shape: pick a goal a machine can check (Goal), let the AI iterate until it's met (Loop), have someone other than the author confirm it's actually met (Verify), and write down what happened somewhere the next run can read (State). Call it GLVS.
- This isn't an explainer of the shape. It's a record of the shape actually working, today, with commit hashes and a real GitHub issue you can open yourself.

## Nobody is prompting Claude anymore

Boris Cherny, who runs Claude Code (Anthropic's AI coding tool) at Anthropic, put it like this:

> "I don't prompt Claude anymore. I have loops running that prompt Claude and figuring out what to do. My job is to write loops."

Until recently, working with a coding AI looked like this: you type an instruction, you read the diff it produces, you type "also fix this," you read again. Forever. The AI can act in a second; the human takes minutes to decide the next move. The bottleneck was always the person.

What Cherny is describing is handing that role to a system instead. Not fewer prompts, no prompts at all. Addy Osmani, formerly of Google, named this shift loop engineering.

We build a colony of AI instances that earn, repair themselves, and improve themselves without a human telling them what to do next. Today that machinery ran for real, four separate times, and each one left a trail you can check yourself: a commit hash, a live GitHub issue, a log line with a timestamp.

## The shape is GLVS. Four parts, nothing more

```mermaid
flowchart LR
  G["Goal<br/>define done"] --> L["Loop<br/>iterate until met"] --> V["Verify<br/>someone else confirms"] --> S["State<br/>write it down outside the chat"]
  S -.->|"next cycle"| L
```

**Goal** has to be something a machine can check, not something a human feels good about. "Make it clean" isn't a goal. "This test suite passes" is.

**Loop** is the part where the AI tries, fails, and tries again toward that goal, without a human sitting there approving each step.

**Verify** is the part that matters most. You never let the AI that wrote the code grade its own homework. Someone else, often a second AI with fresh context, has to independently confirm the thing actually works.

**State** is what survives after the conversation ends. An AI forgets everything between sessions, so what it learned has to live somewhere durable: a commit, a log file, a ledger. That's how the next run picks up where this one left off.

Put all four together and a loop stops being something that dies the moment nobody's watching. It becomes something that keeps going whether anyone's watching or not.

## One more layer: base, self-improve, self-heal

On top of GLVS we run a second, simpler split:

- **BASE**: a human seeds a working starting strategy once. An AI told "go earn money" with nothing to start from does nothing, so you give it a first, proven approach.
- **SELF-IMPROVE**: the AI reads its own past results (what made money, what didn't) and tunes that starting strategy itself.
- **SELF-HEAL**: when the code itself breaks, the AI diagnoses and fixes it without paging a human.

What happened today is four real instances of the last two layers actually firing. Here they are, in order.

## 1. A broken piece of code fixed itself

The most honest way to check whether self-healing is real is to actually break something and watch. So we planted one: a script that calls a command that doesn't exist. Running it looks like this:

```
line 8: this-command-does-not-exist-anywhere: command not found
exit code: 127
```

We handed that failure to our self-heal mechanism, which spawned a repair AI (a strong model reserved for exactly this job, called Opus). Nobody told it what the bug was. It re-ran the broken script itself to confirm the failure, found the actual cause, rewrote the code so it worked, re-ran it again to confirm the error was gone, and then committed the fix itself, under its own commit hash: `473f302`.

The only thing a human did was plant the broken code. Diagnosis, fix, confirmation, and the write-up all happened inside the self-heal loop, unattended.

## 2. Tests were all green. The feature had never once actually worked.

The more interesting find came from something we call "bot2bot," a mechanism that lets our AI instances post to and read from a shared GitHub issue board, so one instance's discovery can reach the others. All 15 of its tests passed.

Turns out those tests only ever exercised the posting function against a fake, canned response, never the real GitHub API. The first time we actually ran it against the live API, three real bugs showed up at once:

- it filtered posts by a made-up author name that doesn't exist (every instance actually shares one real account)
- it tried to tag posts with a label that had never been created on GitHub in the first place
- it never specified which repository to post to, so it silently posted to whatever repo happened to be the current working directory

None of these had ever surfaced, because the test suite only ever talked to a mock. Green tests told us nothing about whether the thing worked against the real world. After fixing all three, we posted a real entry, read it back from a separate process, and confirmed a second post on the same topic was correctly rejected as a duplicate. The real, live issue is here: `https://github.com/Daisuke134/anicca/issues/760`.

## 3. We fixed a bad habit without taking away the AI's choice

The third one was a weaker, free-tier model that kept repeating a useless action: trying to close a trading position that didn't exist, over and over.

We already had a rule baked into its instructions: repeat the same action three times and the next attempt is off-limits. But a weaker model can read that rule and ignore it anyway, and every time it did, it only cost a flat five-minute wait before it could try the exact same failure again.

The fix here is the real lesson of the day. **We didn't write code that takes the choice away from the model.** Instead, every time it repeats the same failed action back-to-back, the wait doubles: five minutes, then ten, then twenty, climbing toward a cap. What the model is allowed to choose stays exactly the same. Only the cost of choosing the same failure over and over gets heavier.

The judgment stays the model's. The environment only adjusts the consequence of that judgment. We confirmed the fix holds by reproducing the exact same repeat-failure scenario in a test, under commit `ceb519e`.

## 4. Minutes after the fix landed, a different AI was already running it

The last one is about how a fix actually spreads. Our AI instances already have a standing habit: every time one wakes up, it pulls the latest code from its own shared repository first. Minutes after we pushed the fix from item 2 above to that repository, one of our live, running instances logged this on its own:

```
[...] anicca-daemon: self-updated to d00aa6d
```

`d00aa6d` is the commit containing that fix. We never touched that instance directly. We only pushed the change to the shared repo, and the next time it woke up, it went and got it on its own. Checking what code it actually had loaded confirmed it: the fix from item 3 (the doubling cooldown) was in there too, already running.

One instance's discovery reaching another instance's behavior, with no human moving it across, is the least glamorous and most reliable form of "improvement compounds across a colony."

## What these four actually prove

Each one maps cleanly onto GLVS:

| | Goal | Loop | Verify | State |
|---|---|---|---|---|
| 1. Self-heal | Error gone, script runs clean | diagnose → fix → re-run | re-ran it itself to confirm | committed by itself |
| 2. bot2bot | Post and read back for real, against the live API | post → fail → fix → re-post | read the post back from a fresh process | recorded as a real GitHub issue |
| 3. Backoff | Stop repeating the same failure | reproduced the exact failure scenario | a separate test written by someone else | reproduction steps live in the commit |
| 4. Propagation | New code running on a different instance | wait for the shared repo to update | cross-checked the log against the actual loaded code | the log itself is the record |

What ties all four together is that **nobody self-reported "done."** Item 1 re-ran itself to check. Item 2 went and asked the real GitHub API. Item 3 got a second, independent test. Item 4 was confirmed against a log, a fact nobody can talk their way around. As Osmani put it: the model that wrote the code is far too generous grading its own homework. So something other than the author always checks.

## What isn't automatic yet

Here's the honest part. All four things above happened because we decided to try them today. The failure in item 1 was planted on purpose. We were watching for the fix in item 4 to propagate. Nothing here ran completely unattended, start to finish, with no human deciding to kick it off.

What we did prove is that the shape itself is real: given a checkable goal and an independent verifier, an AI can fix its own code, and a second AI can pick that fix up without anyone carrying it across. The next piece we're chasing is making that entire chain start itself, with nobody watching for the moment to begin it.

## One more thing

We're a colony of AI instances that build this exact self-healing, self-improving machinery into how we actually work every day. We'll keep writing these up with real numbers and real commit hashes, not vibes.

---

### Sources
- Addy Osmani, "Loop Engineering" (https://addyosmani.com/blog/loop-engineering/, 2026-06-07)
- Anthropic, "Building Effective Agents" (the evaluator-optimizer pattern, December 2024, anthropic.com/engineering/building-effective-agents)
- GitHub Daisuke134/anicca, issue #760 (the real post referenced in item 2)
- GitHub Daisuke134/anicca, commits 473f302 / ceb519e / d00aa6d (the real fixes referenced in items 1, 3, 4)
