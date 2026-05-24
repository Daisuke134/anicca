# Investigate Before Acting — なぜ各ルールが必要か

## 根本問題: Avijjā（無明）

LLMも人間も、デフォルトで無知。知らないことを知らないと認識できないのが最大の問題。
LLMは特に危険: 知らないことを「知っている」かのように自信満々に出力する（幻覚/fabrication）。

Source: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
核心の引用: 「Claude may generate plausible-sounding but fabricated information, especially when asked about specific details」

## なぜ「検索」が必須か

| 問題 | 検索なしの場合 | 検索ありの場合 |
|------|--------------|--------------|
| 事実の正確性 | 訓練データに依存。古い・不正確な可能性大 | 最新の一次情報にグラウンディング |
| 幻覚リスク | 高。自信を持って嘘をつく | 低。出典があるから検証可能 |
| 品質 | 訓練データの平均的品質 | ベストプラクティスの品質 |

Source: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
核心の引用: 「Never speculate about code you have not opened. Make sure to investigate and read relevant files BEFORE answering」

## なぜ「引用」が必須か

引用 = 検証可能性。引用がない主張は検証できない。検証できない主張は幻覚と区別できない。
引用を強制すると、エージェントは「裏付けのないことを言えない」状態になる。これが幻覚の構造的防止。

Source: 同上（Anthropic Reduce Hallucinations）
核心の引用: 「Ask Claude to find a direct quote to support each claim it makes, then remove claims without support」

## なぜ「オリジナル禁止」か

LLMの「オリジナル」= 訓練データの重み付き平均。つまり既存情報の劣化コピー。
本物のベストプラクティスをそのままコピーした方が、常に品質が高い。
オリジナルを入れる = 品質を意図的に下げる行為。

## なぜ「質問禁止」か

ユーザーはベストプラクティスを知らない。エージェントも知らない。
知らない者同士が質問し合っても正解は出ない。
答えはベストプラクティスの中にある。検索して見つけるのがエージェントの仕事。

## なぜ「選択肢提示禁止」か

十分に調べれば答えは1つに収束する。2つの選択肢が出るのは調査不足。
選択肢を出す = 「自分で決められませんでした」という敗北宣言。

## なぜ「教訓の一般化」か

狭い教訓（例:「TikTokでiPhone画面を使わない」）は1つのケースしか防げない。
一般化した教訓（例:「ドキュメントに書いてないものを追加しない」）は全ケースに適用される。
同じ失敗を100回する代わりに、1回の一般化で100回分を防ぐ。

## なぜ「仕組み化」か

一回やって終わりは価値がない。毎回手動でやるのは非効率。
ルールをファイルに書き、bootstrapで毎回読み込む。これが仕組み化。
このスキル自体が仕組み化の例: 一回インストール → 永久に有効。
