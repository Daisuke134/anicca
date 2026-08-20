## ja
# AIエージェントを、完了まで自走させる設計
Loop Engineeringとは、AIエージェントに目標を一度渡し、テスト終了コード0、空のキュー、公開URLの応答など、観測できる完了条件まで実行、検証、修正を繰り返させる設計だ。別のエージェントが結果を再検査し、失敗なら保存した状態から再開する。人間は毎回指示せず、完了か例外だけを受け取る。
## en
# How to Keep an AI Agent Working Until the Job Is Done
Loop Engineering is the design of a system that gives an AI agent a goal once, then keeps it running, checking, and correcting its work until an observable condition is true. That condition might be a test process returning exit code 0, a task queue reaching zero items, or a deployed URL returning the expected response. A separate agent with fresh context reruns every check and treats the worker’s completion claim as unverified. When a check fails, the next attempt reads the saved state and continues from the failure. The developer writes the goal, limits, and evidence rules; the loop handles the repeated prompts and reports only completion or an exception that requires intervention.