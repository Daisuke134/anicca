# TASKMARKET-READBACK-1

## Result

| Item | Verified result |
|---|---|
| Verdict | **PASS** |
| Code | PR [#1246](https://github.com/Daisuke134/life-manager/pull/1246), merge `0f10a0b47` |
| Task | `0x7c3ab04d35a6b73f1421a9f7876077554f4650e22014188ff2d6d5075c95cbe8` |
| Official submission identity | submit tx `0x47863bf6b297a73d89c1334e3904a556a28986e03d797cd0410ab2defc772558` |
| Existing cost | `$0.065` in wake `00MS4HVBIAF3CF87E6263F49A4` |
| Reconciliation wake | `00MS4OS3L0DA63DDAEA21F4FD6`, exit `0` |
| Additional image cost | `$0.00` |
| Owned submission count | `14 → 14` |

## Failure and repair

The worker submitted successfully, but immediately called `taskmarket task my-submissions` only once.
The official readback had not converged yet, so it appended the real `$0.065` cost with
`submission_id=null` and exited with `submission_readback_missing`.

The repair has two paths:

1. A new submission performs at most five official readbacks, one second apart.
2. A later normal `execute` wake checks owned submissions before selecting or purchasing another task.
   If it finds a null-ID attempt, it appends one zero-cost reconciliation row.

The official `my-submissions` shape exposes `submitTxHash` rather than a separate submission ID, so the
finalized submit transaction is used as the stable submission identity. The original cost row is not
rewritten because the earn ledger is append-only.

## TDD verification

| Check | Result |
|---|---|
| Focused TaskMarket tests | `8/8 PASS` |
| Runtime dependency contract | `1/1 PASS` |
| Delayed readback | empty twice after submit, success on the third bounded read |
| Missing readback | five bounded attempts, then honest failure |
| Existing submission | no wallet load, image generation, download, or submit |
| Exactly once | second reconciliation attempt appends `0` rows |

## Production readback

The existing `ai.anicca.agent-economy-loop` was triggered with `launchctl kickstart`; no replacement
executor was created.

```json
{
  "action": "reconciled_submission",
  "taskId": "0x7c3ab04d35a6b73f1421a9f7876077554f4650e22014188ff2d6d5075c95cbe8",
  "submissionId": "0x47863bf6b297a73d89c1334e3904a556a28986e03d797cd0410ab2defc772558",
  "costUsd": 0
}
```

The append-only pair is:

```text
taskmarket_work_attempt        cost=-0.065  submission_id=null
taskmarket_work_reconciliation cost=0       submission_id=0x47863b…2558
```

The daily image-spend state remained `$0.13`, the earn ledger grew by exactly one row (`437 → 438`),
and the official owned submission count remained `14`.

## Evidence limit

This proves submission delivery readback and cost provenance. It does not prove acceptance, award, or
external income. The task remains open, and verified external revenue remains `$0.00`. The existing
five-minute TaskMarket award observer continues to wait for an external award plus finalized Base USDC
transfer before recording revenue.
