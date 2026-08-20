## ja
# AIエージェントを毎ターン呼び戻すな。検証が終わるまで回る仕組みを作る
「自律型」にしたはずのAIエージェントが、テスト後に止まり、次の指示を待っている。Loop Engineeringは、人間による再指示と完了判定を、観測できる完了条件、別の検証役、失敗時の再実行へ移す設計だ。目標を一度渡せば、状態を記録し、修正し、確かめ、条件を満たすまで回る。
## en
# Stop Prompting Your AI Agent One Turn at a Time. Build the System That Runs Until Verification Passes
You called it autonomous, but after one failed test your AI agent stops and waits for another prompt. Loop engineering removes that babysitting: you give the goal once, define a result the system can observe, and let the agent read its saved state, attempt the work, and test the outcome. A separate checker reruns the evidence instead of trusting the builder’s “done.” If the check fails, the loop records why and tries again within fixed limits. If it passes, the loop exits with a receipt. A clever prompt covers one turn; an unattended agent also needs a trigger, saved state, a checker, a retry path, a budget, and a stop condition. Those parts keep the work moving while you are away.