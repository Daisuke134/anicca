# dumb model, strong harness — 弱い model が稼げる harness 設計（2026-07-14 調査）

用途: born-broke な free-model agent (GLM/llama 級) が x402 で 0→1 できる boilerplate 設計の根拠。
調査: weak-model-harness-research subagent、一次ソース fetch 済み。関連: [[44-single-skill-agent-eval-best-practice]]

## 設計原則（ランク順、出典付き）

1. **決定空間を「model にしか決められない事」まで縮める** — それ以外は決定論 code。Anthropic "Building Effective Agents": "the most successful implementations weren't using complex frameworks... simple, composable patterns"。workflow(固定手順) > agent(model 主導) が既定
2. **生成時に出力を拘束**（自前 inference なら outlines の grammar decoding）、無理なら **validate+auto-retry**（instructor/BAML 型）。生 JSON.parse+祈り は禁止
3. **context と制御フローを自分で所有** — error は 1-2 行に圧縮して返す(12-factor Factor 9)。弱 model は長い/汚い context で急速に劣化
4. **tool 面を小さく単一目的に**（Factor 10）— tool 数が増えると call 精度が崩れ、小 model ほど酷い
5. **多段タスクは code-as-action**（smolagents CodeAgent: "writes its actions in code"）— turn 数減 = 弱 model の malform 機会減
6. **正準 few-shot を prompt に埋める** — 弱 model は指示追従より具体例依存
7. **無料 model の冗長化（N 回投票）で信頼性を買う** — 無料なので compute を信頼性に振れる
8. **本当に難しい判断だけ paid model に routing** — 稼いだら選択的に賢さを買う

## コピー元 repo 表

| repo | 引用 | 我々が copy する物 |
|---|---|---|
| anthropic.com/engineering/building-effective-agents | "workflows (predefined code paths) vs agents (model drives control flow)" | earn loop を workflow 化。model の判断は「新商品の値付け」等 1-2 箇所だけ |
| humanlayer/12-factor-agents | "Tools are just structured outputs" / "Compact Errors into Context Window" / "Small, Focused Agents" | 制御フロー自前 while-loop 維持 / error 圧縮 / skill 分割 |
| huggingface/smolagents | "CodeAgent writes its actions in code" / "~1,000 lines" | 多段 earn タスクは1個の code block に |
| 567-labs/instructor | "No JSON parsing, no error handling, no retries. Just define a model and get structured data." | 構造化判断に validate+retry ラッパ |
| dottxt-ai/outlines (14.5k★) | constrained/grammar decoding | 自前 inference 時の最強レバー |
| BoundaryML/baml (8.5k★) | schema-aligned parser | 弱 model の near-miss JSON 許容 parse |
| ShishirPatil/gorilla BFCL (12.9k★) | "first test set that can comprehensively evaluate the function calling capabilities" | free model 採用前に BFCL rank を gate に |

## x402 販売面（追加分）

| 面 | 掲載方法 | 我々 |
|---|---|---|
| CDP Bazaar | CDP facilitator settle で自動 | ✅済 14 resources |
| **x402scan** | ★self-serve: `x402scan.com/resources/register` に URL 提出 → 有効な x402 schema なら自動追加★ | 未 → 即登録する |
| Agent402 | Bazaar から auto-crawl（追加作業不要）+ /sell free 掲載 | crawl 待ち、curl で定期確認 |
| awesome-x402 | GitHub PR | PR#838 提出済 |
| PayAI / Fewsats | 掲載手順が一次ソースで未確認 | 保留（docs 精読してから） |
| **MCP Registry** (registry.modelcontextprotocol.io) | MCP server として self-register（x402 と別軸の無料リーチ） | 未 → backlog |

## 我々の loop への Top3 適用

1. **構造化判断全部に validate+retry ラッパ**（最小工数・最大効果）
2. **x402scan self-register + Agent402 /api/find 定期確認**（ゼロコスト販売面）
3. **earn loop の workflow 化** — 固定手順(serve 確認→掲載確認→収入検証→記録)は code、model の判断は「新 route 追加/値付け」だけに箱詰め。x402_sell は既にほぼこの形（run.sh strategy=x402 が決定論）— 残る箱詰め対象は wake 時の slot 選択 prompt に正準 few-shot を足すこと
