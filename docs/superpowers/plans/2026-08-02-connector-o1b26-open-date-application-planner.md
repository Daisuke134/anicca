# Connector O1B-26 Implementation Plan

1. RED: Connector profile loaderのexact schema、secret拒否、tenant mismatch、missing path testを追加する。
2. GREEN: versioned Dais Connector profileとfail-closed loaderを実装する。
3. RED: earliest open date、active wait、terminal skip、one enqueue、zero-candidate outcomeのplanner testを追加する。
4. GREEN: 既存packのranking/goal/Calendar/spendとjob storeを組み合わせるplannerを実装する。
5. RED: coverage refreshがplanning outcomeを返し、adapterがopaque receiptへ保存するcontract testを追加する。
6. GREEN: refresh/runtime factory/composeへprofile、Gemini、job-state reader、enqueue境界を配線する。
7. 全Connector/runtime回帰を実行しmaster specを更新、commit/pushする。
8. new imageをdeployし、earliest open日の応募jobが実DBへ最大1件enqueueされることを確認する。
9. 応募workerのverified receipt、Calendar、次coverage snapshotを実測し証拠を保存する。

