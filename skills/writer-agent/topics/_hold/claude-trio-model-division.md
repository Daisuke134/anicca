---
lane: A
created: "2026-07-17T21:05:55+09:00"
voice: recit
sources:
  - /Users/anicca/anicca-project/docs/reference/fable-luna-sol-harness.md
  - https://aniccaai.com/
angle: Claude Code 1セッション内で plan=Fable、実装=GPT-5.6 Luna、レビュー=GPT-5.6 Sol に分業する構成を作って OSS 化した——settings.json の env が shell env を上書きして subagent を乗っ取っていた真因を突き止め、モデル分岐の4経路が全滅し、`CLAUDE_CODE_SUBAGENT_MODEL` だけが生き残った実測過程の記録。
---

構成(フック→構成→真因→全滅した経路→学び):

1. **導入のフック**: Claude Code 1セッションの中で、采配と plan は Claude Fable 5、実装は GPT-5.6 Luna、review は GPT-5.6 Sol に分けたい。claudexmix で Fable が main を持ち、subagent を Luna にし、Sol は fresh context の one-shot にする構成を作って OSS 化した、という欲望から始める。
2. **構成を実測する**: main セッションは `claudexmix` で起動した Fable、全 subagent は GPT-5.6 Luna、Sol は `solx` の `--effort xhigh` one-shot。wordfreq の実タスクでは Luna が `wordfreq.py` と `test_wordfreq.py` を作り、`uvx pytest` は **4 passed**、Sol の verdict は `{"verdict":"PASS","findings":[]}` だった、という動く形を見せる。
3. **決定的な真因**: subagent が Luna にならず Sonnet に化けた原因を追うと、`~/.claude/settings.json` の `env.CLAUDE_CODE_SUBAGENT_MODEL` が最強で、shell から渡した同名 env を潰していた。settings.json に残った `claude-sonnet-5` を削除し、zshrc 関数側だけで `gpt-5.6-luna` を渡すことで配線を直す。
4. **モデル分岐4経路が全滅する**: agent frontmatter の `model: gpt-5.6-luna` は未知 ID として Sonnet 5 に silent fallback、Agent tool の per-invocation `model` は enum 固定で `gpt-5.6-sol` を渡すと `InputValidationError`、`ANTHROPIC_DEFAULT_SONNET_MODEL` などの alias redirect は subagent に効かず、`--model gpt-5.6-luna-xhigh` は3分 timeout のハングになった。異種モデルを subagent に混ぜる生存経路はなく、`CLAUDE_CODE_SUBAGENT_MODEL` による全 subagent 一律 routing だけが生き残る。
5. **学び**: できる構成を先に語らず、main・subagent・review それぞれの `modelUsage` と実タスク結果を確認する。Sol review は subagent に混ぜず fresh context の one-shot に分ける方が、同じ env に Luna として潰されないうえ、レビューの独立性も守れる。

この記事の看板 = 「モデルを3つ並べただけでは分業にならない。どの設定がどの経路を上書きするかを、実際の `modelUsage` とテスト結果で確かめて初めてハーネスになる」という、Claude Code のモデル配線を OSS 化するまでの実測記録。
