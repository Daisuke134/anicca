## ja
# AIに毎回指示するのをやめる。自走させる仕組みを設計する
プロンプトを一度うまく書くだけでは、AIは放っておくと止まる。必要なのは、目標を与え、結果を検証し、失敗なら直して再実行し、完了条件まで回り続ける仕組みだ。この反復系を設計する仕事がLoop Engineeringである。人は毎回の指示役から、止まり方と安全策を決める設計者へ移る。

## en
# Stop Prompting Your AI. Design the System That Keeps It Working
One good prompt can produce one good answer, but it cannot keep an AI agent useful while you are away. The missing piece is a system that gives the agent a goal, checks real evidence, sends failed work back for repair, and stops only when a measurable condition is true. Designing that repeating system is loop engineering. It moves the human from writing every instruction to setting the destination, the proof of completion, and the safety limits. Prompt engineering improves a turn; loop engineering improves the machinery around many turns. The practical payoff is not a more eloquent chatbot, but an agent that can run, verify, recover, and improve without constant babysitting.

## process
### Step 1: 読者視点
1. AIエージェントを夜間や休日も放置運用したい開発者
2. API代、暴走、誤完了を警戒するコスト・安全性重視の運用者
3. プロンプトを毎回調整する作業に疲れ、次の設計対象を探す実務家

### Step 2: 各視点が最初に聞く質問
1. 放置運用したい開発者
   - 人が毎回指示しなくても、AIはどうやって次の作業を決めるのか。
   - 本当に終わったかを、AIの自己申告ではなく何で判定するのか。
2. コスト・安全性重視の運用者
   - 無限反復やトークン浪費をどこで止めるのか。
   - 間違った変更や「できたつもり」をどう検出し、被害を限定するのか。
3. プロンプト調整に疲れた実務家
   - Loop EngineeringはPrompt Engineeringと何が違うのか。
   - 明日から何を設計すれば、単発の良い回答ではなく継続的な成果になるのか。

### Step 3: 選んだangle
「良いプロンプトの書き方」ではなく、人間が担っていた指示・検証・再実行・停止判定を、観測可能な完了条件と安全策を備えた反復システムへ移す設計転換として説明する。読者への約束は、賢い一回答ではなく、放置しても検証・修復しながら成果まで進むAIを作るための基本構造が分かること。
