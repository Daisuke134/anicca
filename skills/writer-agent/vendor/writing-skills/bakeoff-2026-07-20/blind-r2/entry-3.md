## ja
# 毎朝「続けて」と言う人が必要なら、そのAIエージェントは自走していない
放置したAIエージェントは、たいてい一度失敗すると止まる。足りないのは賢いプロンプトではない。次の実行を起こす時計、途中から戻る記録、結果を疑う別の検証役、機械が読める完了条件だ。これらをつなぐLoop Engineeringなら、人が寝ている間も修正と再検証が回り続ける。
## en
# Your AI Agent Is Not Autonomous If It Needs You to Say "Continue" Every Morning
Most agents look autonomous during the happy path. Then a test fails at 2 a.m., the run ends, and the "autonomous" system waits for its developer to wake up and type another instruction. The missing piece is not a sharper prompt. It is a control loop: a trigger that starts the next run, durable state that tells it where to resume, an observable finish line, and an independent checker that distrusts the builder's claim of success. When the evidence fails, the system records why and tries again within a fixed budget. When it passes, the agent stops and leaves a receipt. That is loop engineering: the control system that lets the agent work each day without waiting for you.
