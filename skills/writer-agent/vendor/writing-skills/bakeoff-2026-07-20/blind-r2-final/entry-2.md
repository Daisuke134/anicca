## ja
# AIエージェントを毎日自走させるには、何を組み込めばよいか
夜に走らせたAIエージェントを朝に開くと、テスト失敗で止まり、次の指示を待っていた。長いプロンプトを足しても、この停止は直らない。起動時刻と作業状態を記録し、別の検証役が完了条件を確かめ、失敗なら再実行する。そう組んで初めて、毎回の再指示が消えると気づいた。この反復の組み方をループ工学と呼ぶ。
## en
# What Must You Build for an AI Agent to Run Every Day Without Supervision?
You leave an AI agent running overnight and return to find it stopped at the first failed test, waiting for another prompt. A longer instruction does not fix that pause. The agent needs a trigger that starts the job, a saved record of prior attempts, and a completion condition that software can check. A separate checker reruns the test and accepts only observed evidence. When the check fails, the runner records the result and starts another attempt. When it passes, the runner writes a receipt and stops. Budgets and attempt limits keep the agent from consuming time without bounds. This arrangement is loop engineering: connecting triggers, state, verification, retries, and exit rules so an agent can resume work each day without a person returning for every turn.
