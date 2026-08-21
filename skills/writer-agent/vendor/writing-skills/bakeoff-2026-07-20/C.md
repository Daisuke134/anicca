## ja
# AIエージェントを放置で回す設計――Loop Engineeringとは何か
AIエージェントを放置すると、止まり方を誤り、同じ失敗を繰り返し、やがて人間の確認待ちになります。Loop Engineeringは、目標、観測できる完了条件、検証、自己修復、再実行を一つの制御系にし、人間が毎回プロンプトを書く仕事そのものを置き換える設計です。
## en
# How to Keep AI Agents Running Without You: What Loop Engineering Actually Designs
Leave an AI agent alone and it usually does one of three things: stops too early, repeats the same failure, or waits for a human to decide what “done” means. Loop engineering replaces that babysitting with a control system. You define a goal, an observable completion condition, a verifier that does not trust the builder’s claims, and a recovery path that feeds failures back into the next attempt. The agent can then inspect state, act, test, repair, and repeat until the evidence says the job is finished—not until the model merely says it is. This explainer shows how that differs from prompt and context engineering, and what developers must design before an agent can run unattended without quietly drifting, stalling, or declaring a false success.
