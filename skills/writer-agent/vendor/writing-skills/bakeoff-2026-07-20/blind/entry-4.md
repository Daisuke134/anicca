## ja
# AIに毎回指示するのをやめる。自走させる仕組みを設計する
プロンプトを一度うまく書くだけでは、AIは放っておくと止まる。必要なのは、目標を与え、結果を検証し、失敗なら直して再実行し、完了条件まで回り続ける仕組みだ。この反復系を設計する仕事がLoop Engineeringである。人は毎回の指示役から、止まり方と安全策を決める設計者へ移る。

## en
# Stop Prompting Your AI. Design the System That Keeps It Working
One good prompt can produce one good answer, but it cannot keep an AI agent useful while you are away. The missing piece is a system that gives the agent a goal, checks real evidence, sends failed work back for repair, and stops only when a measurable condition is true. Designing that repeating system is loop engineering. It moves the human from writing every instruction to setting the destination, the proof of completion, and the safety limits. Prompt engineering improves a turn; loop engineering improves the machinery around many turns. The practical payoff is not a more eloquent chatbot, but an agent that can run, verify, recover, and improve without constant babysitting.