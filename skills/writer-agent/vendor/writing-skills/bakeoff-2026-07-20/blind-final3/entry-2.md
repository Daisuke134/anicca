## ja
# 朝いちでAIのログを開いているなら、あなたがまだ制御装置だ
午前2時、テストが1件落ちる。実行はそこで切れ、「自律型」のAIは誰かが起きてログを開くまで何もしない。長いプロンプトを足しても、この待ち時間は消えない。人が握っている次回起動と合否判定を、観測できる完了条件と実装者とは別の検証役へ渡す。これがLoop Engineeringだ。ただし、再試行は最大3回、使える予算も固定する。合格なら止まり、失敗なら理由を記録して戻る。最後に残るのはAIの「できました」ではなく、test exit 0や公開URLを入れたreceipt（証拠記録）だ。
## en
# If You Open Your AI's Log First Thing Every Morning, You Are Still the Control System
At 2 a.m., one test fails. The run ends, and the "autonomous" agent does nothing until someone wakes up and opens the log. A longer prompt will not remove that wait. Loop engineering hands the next trigger and pass/fail decision to an observable done condition and a checker who did not build the work. It also sets a hard ceiling: three retries and a fixed budget. A passing run stops. A failing one records the reason and returns within those limits. Completion means a receipt containing evidence such as test exit 0 or a live URL, not the agent saying, "Done."
