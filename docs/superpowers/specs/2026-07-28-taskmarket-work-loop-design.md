# TaskMarket WORK loop design

## Goal

Make the existing `ai.anicca.agent-economy-loop` capable of earning through
TaskMarket without a human creating or submitting the deliverable. The first
vertical slice handles one active, unstaked, still-image bounty per wake and
closes the chain:

`poll → select → buy frontier image generation with x402 → build files → submit → read back → record cost`.

An award is not claimed as income here. The existing
`ai.anicca.life-manager-taskmarket-ledger` remains the only award/payment
observer and writes income only after an external finalized Base USDC payment.

## Observed boundary

- TaskMarket official CLI readback shows 13 existing submissions and 10 active,
  unsubmitted bounties.
- The persistent agent loop only exposes `x402_sell`; it has no TaskMarket
  execution slot.
- The installed TaskMarket launchd job only observes awards and payments.
- The highest-quality currently supported target asks for one 1:1 still image,
  `concept-note.md`, and `sources.md`, and explicitly requires GPT Image 2 or
  better.
- BlockRun's live model catalog exposes `openai/gpt-image-2`. A real unpaid
  generation probe returned an x402 quote of `65000` Base USDC atomic units
  (`$0.065`), so the agent can buy the required model with its own Base wallet
  and no human API credential.

## Chosen design

Add one focused earn slot, `earn/taskmarket`.

| Unit | Responsibility |
|---|---|
| `taskmarket-work.mjs` | Pure selection, prompt construction, file manifest validation, and effect orchestration through injected boundaries |
| `x402-image-client.mjs` | Fetch quote, enforce exact model and price cap, sign x402 payment with the agent wallet, return one HTTPS image URL |
| `run.sh` | Translate loop environment into one bounded pass and emit one JSON result |
| `taskmarket-work.test.mjs` | Contract tests for selection, idempotency, quote cap, generated files, submit, readback, and cost ledger |
| `registry.json` | Declare `earn/taskmarket` as a live safe earn slot |

The slot defaults to `action=execute`. One wake handles at most one submission.
The loop may pass `{"action":"poll"}` for a read-only inventory or
`{"action":"execute","taskId":"0x..."}` to pin an eligible task.

## Selection policy

A task is eligible only when all are true:

1. `status=open`, `phase=active`, and `submissionWindowOpen=true`.
2. The owned wallet has no existing submission for the task.
3. `stakeRequired=false`.
4. The description requires one still/square/hero image and names GPT Image 2
   or a frontier image model.
5. Net reward is at least 20 times the configured maximum image cost.

Supported tasks are ranked by:

1. earliest expiry;
2. fewer existing submissions;
3. higher net reward.

This first slice deliberately rejects short-film, archive, multi-image, and web
app tasks. Unsupported tasks remain visible in the poll result but are never
submitted as fake work.

## Image generation and money safety

- Endpoint: `https://blockrun.ai/api/v1/images/generations`
- Model: exactly `openai/gpt-image-2`
- Size: exactly `1024x1024`
- Images per pass: exactly one
- Quote cap: `$0.07`
- Daily TaskMarket image cap: `$0.14`
- Minimum wallet float after reserved spend: `$0.25`
- Key source: existing per-instance `loadEvmKey()` resolver; no key is logged or
  passed in model arguments.
- The paid response must contain one HTTPS URL. The downloaded artifact must be
  a PNG with equal width and height.

The pass reserves the quoted cost before sending the paid request. A failed
generation records the reserved cost as an attempted expense and does not
submit anything. The TaskMarket worker wallet may differ from the image-paying
agent wallet; both remain registered internal wallets and no internal transfer
is income.

## Deliverables

The task description is the locked factual source. The generated image prompt
contains the complete task brief and explicit instructions to make the
typography native to the artwork.

The pass creates:

- `hero.png` — downloaded GPT Image 2 output;
- `concept-note.md` — task ID, model, composition decision, and factual lock;
- `sources.md` — TaskMarket task URL plus the requester-supplied locked facts.

The CLI call is:

```text
taskmarket task submit <taskId>
  --file hero.png
  --file concept-note.md
  --file sources.md
  --role final
```

The pass is successful only after `taskmarket task my-submissions` returns a
submission for the same task ID and the returned submission includes a stable
submission ID.

## State and accounting

Per-task artifacts live under:

`$ANICCA_HOME/skills/earn/taskmarket/state/submissions/<taskId>/`

The official TaskMarket submission feed is the primary idempotency source.
Local state is evidence, not authority.

Every pass appends one wake-correlated row to `EARN_LEDGER`:

- poll/no eligible task: `earn_usdc=0`, `cost_usdc=0`;
- generated and submitted: `earn_usdc=0`, `cost_usdc=<quoted amount>`;
- external award: never written by this slot; the existing Life Manager
  TaskMarket ledger owns that transition.

## Failure handling

All external boundaries are fail-closed:

- malformed CLI/API JSON: exit non-zero;
- quote above cap or wrong network/token: no payment;
- low float or daily cap: no payment;
- image download/type/dimensions invalid: no submission;
- CLI submit succeeds but readback is absent: report
  `submission_readback_missing`, never success;
- existing submission: return `already_submitted` without spending.

No retry reuses an x402 authorization. A later wake begins from official
TaskMarket readback and creates a fresh generation only when no submission
exists.

## Verification

Completion requires:

1. focused unit/integration tests pass;
2. real loop E2E selects `earn/taskmarket` and carries `ANICCA_ARGS`, `WAKE_ID`,
   and `EARN_LEDGER`;
3. production loop is reloaded with `earn/taskmarket` in the allowlist;
4. one real GPT Image 2 x402 payment completes;
5. TaskMarket official readback returns the new submission;
6. the award observer remains exit 0 and records no income before an external
   award.
