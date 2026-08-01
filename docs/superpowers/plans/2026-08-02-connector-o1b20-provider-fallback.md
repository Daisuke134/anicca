# O1B-20 Luma→connpass conditional fallback 実装計画

**Goal:** その日の全Luma候補を既知の非成立理由で尽くした場合だけconnpassへ進み、成功・復旧・不明effect時は二重provider操作を防ぐ。

## Contract

- 既存Luma candidate sequenceを唯一のLuma outcome sourceにする。
- Luma booked / recovery_required / reconciliation_requiredではconnpass call 0。
- `next_provider_required/luma_candidates_exhausted`だけがconnpassを一度呼ぶ。
- connpass key未発行はcoverage_openとして残し、complete/bookedを偽装しない。
- connpass verified bookingだけをbookedへ変換し、unknown effectはreconciliationへ止める。

## Steps

1. booked/recovery/unknown/exhausted/no-keyをtest-firstでREDにする。
2. deterministic provider routerを実装する。
3. 現在のno-key policyでLuma exhaustion→coverage_openをcontrolled実測する。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
