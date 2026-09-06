# Transient vs fatal: what a wake is allowed to die on

A loop that drives a browser fails constantly in ways that have nothing to do with its
decision. The page had not hydrated. One competitor URL answered empty. A tab took longer
than thirty seconds under load. Each of those is a condition that will be gone next minute.

The failure this file exists to prevent is treating one of them as a verdict.

On 2026-09-06 the Coconala Storefront loop was fixed eight times in one evening. Every wake
exited `effect 0`, and the reason was different each time — so the loop looked broken in
eight ways when it had one defect wearing eight faces.

## Symptom

Every wake fails. The reason changes each time and never repeats twice in a row. Fixing
one reason makes the loop travel further and die somewhere new. The measured sequence:

| Wake | Reason | Where it died |
|---|---|---|
| 12 wakes | a content guard refused the proposal | sealing the contract |
| next | the category had only two levels | reading the category |
| next | one competitor page came back empty | collecting evidence |
| next | a tab took >30s to open | claiming the draft |
| next | the response schema used `oneOf` | calling the model |
| next | the seller form had not hydrated in 2s | reading the form |

Nine of fourteen competitor sources had already been read when the tenth came back empty.
The wake that died opening a tab had already cleared every earlier stage and created its
draft. Every one of those wakes threw away minutes of real work over one recoverable item.

## The wrong instinct

*The read failed, so the loop cannot proceed — raise.* It reads as rigour. It is the same
instinct that makes a guard correct, so it feels like the same discipline.

It is not. A guard refuses **an answer the world gave you**: this title is ungrammatical,
this copy names a prohibited tool, this contract does not match its precondition. The world
answered and the answer was no. Failing closed is right.

A transient is **the world failing to answer at all**. Nothing was decided. Retrying is not
weakening the guard, because there was no guard finding to weaken.

## The right move

Sort every failure into three piles before writing the raise.

1. **The world answered, and the answer is no.** A prohibited term in copy, a stem that is
   not a verb, a contract whose version no longer matches, being signed out. Fail closed,
   name it precisely, never retry. Retrying an expired session just repeats it.
2. **The world did not answer.** Empty body, unhydrated form, tab timeout, half-rendered
   list. Retry with one shape. If it still will not answer, ask whether this item is the
   whole job or one of many.
3. **The world answered about one item among many.** One competitor of fourteen, one
   service of twelve. Record it as unread, skip it, carry on with the rest. Fail the wake
   only when *nothing* could be read — one unreadable item is a flake, zero readable items
   is a systemic failure.

Use one retry shape everywhere. Divergence is not a tuning decision, it is an accident:

```python
for attempt in range(5):
    ...
    if attempt < 4:
        time.sleep(3)
```

That shape was already in this house in `_read_official_catalog`, with the reasoning
written next to it — *a half-hydrated dashboard is a transient, not a catalogue change, and
failing the whole wake on it costs a decision cycle for nothing*. The knowledge existed in
exactly one function. Every site that had drifted to `range(3)`/`sleep(1)` was a site that
failed in production, and the weakest one — two seconds of settling — was the one that
finally exhausted. **A retry shape that varies by call site tells you nobody chose it.**

Two more rules that cost a wake each when they were missing:

- **A rejection the generator never sees is a rejection it will repeat.** When code refuses
  a model's output, persist the refusal against the thing it was refusing, and put the
  recent ones back into the next prompt. Otherwise the next wake builds the same prompt from
  the same context and gets the same violation. Bound it: after the same guard refuses the
  same target three times, stop asking — but only skip. Do not also mark the target dead,
  because a target that is partway through a multi-wake job has work to lose.
- **A rule the model is never told is a rule it will break.** If a check is mechanical,
  state it in the prompt in the same words the check uses, from one shared constant so the
  two cannot drift. Give the failing example you actually observed, not an invented one.

## The general law

**A failure that names your decision is a verdict. A failure that names your environment is
weather. Only a verdict may end the work.**

Two corollaries worth as much as the law:

- The blast radius of a failure should match its scope. A per-item failure ends that item;
  only a whole-job failure ends the job.
- Local tests cannot see weather. The schema that used `oneOf` was valid JSON Schema and
  passed every test; only the provider rejected it. Where a rule is enforced somewhere you
  cannot run, encode the *enforcer's* restriction in the test, not the standard's.

## One line to remember it by

Nine of fourteen competitor pages had been read when the tenth came back empty, and the
loop threw away all nine.
