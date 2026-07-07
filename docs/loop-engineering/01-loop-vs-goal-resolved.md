# 01 「loop は goal を含むのか?」— 決定的解決（概念 vs ツール）

> Dais の問い:「loop って goal を内包してない? "この spec が終わって検証されるまで loop しろ" と言えば goal と同じでは? だったら loop だけあればいい、goal は要らないのでは?」
> 結論を一言で: **概念レベルでは Dais が正しい（loop は goal を含む）。だがツールレベルでは逆で、`/goal` の方が loop を含む。そして本当の論点は "loop か goal か" ではなく "done を"誰が"判定するか（自己申告 vs 独立判定）"。無人＋金銭のループでは自己判定は禁物。**

---

## 1. 概念レベル: YES、loop は goal を含む（Dais 正解）

「ループ = タスク + チェック」。この "チェック" が goal（終了条件）そのもの。goal の無いループは定義上"壊れたループ"。

- Addy Osmani: "A loop here can be thought of a **recursive goal** where you define a purpose and the AI iterates until complete." (addyosmani.com/blog/loop-engineering)
- Forward-Future/loopy: "A good loop answers four simple questions: What is the agent trying to accomplish? **How will it know whether the latest attempt worked?** ... **When should it finish or ask for help?**" (github.com/Forward-Future/loopy)
- loopy: "Treat a loop as a feedback system with **terminal states**, not as permission for endless autonomy." + goal の無い所でループを作るなという明示ルール: "Recommend a one-shot workflow instead of manufacturing a loop when no new feedback can change the next action."

→ **抽象概念としての loop は goal を definitionally 含む。** Dais の「loop で "終わるまで回す" と言えば goal になる」は概念として正しい。

## 2. ツールレベル: 逆。`/goal` の方が loop を含む（Claude Code の実装）

Claude Code では `/loop` と `/goal` は**別プリミティブ**で、機構が違う。公式仕様（code.claude.com/docs/en/goal, /commands, /scheduled-tasks）:

| | `/goal` | `/loop` |
|---|---|---|
| 次ターンの起点 | 前ターン終了直後（即連鎖） | 時間間隔（or 自己ペース） |
| **done 判定者** | **独立した小型モデル(既定Haiku)が毎ターン合否判定** | ①人間の手動停止 ②**同一エージェントが自分で** `ScheduleWakeup(stop:true)` |
| 判定は tool を呼べるか | 不可（会話に出た内容のみで判定） | 判定機構そのものが無い |
| 条件の明示 | 必須（`/goal <condition>`、最大4000字） | 任意（プロンプトに書いても書かなくても回る） |
| ターン上限 | 既定なし（`or stop after 20 turns` を自分で書く） | 時間間隔のみ |

核心の逐語引用:
- "`/goal` is a wrapper around a session-scoped prompt-based Stop hook... the condition and the conversation so far are sent to your configured small fast model, which defaults to Haiku... **It does not call tools, so it can only judge what Claude has already surfaced in the conversation.**" (code.claude.com/docs/en/goal)
- "`/goal` adds a separate evaluator that checks your condition after every turn, so **completion is decided by a fresh model rather than the one doing the work.**" (同上)
- "In self-paced mode, **Claude can also end the loop on its own** once the task is complete. Claude calls the `ScheduleWakeup` tool with `stop: true`." (code.claude.com/docs/en/scheduled-tasks) ← `/loop` の停止は"作業した本人"の自己申告
- Osmani: "This is also basically what Claude Code's `/goal` does under the hood, **a fresh model decides if the loop is done instead of the one that did the work, the maker and checker split applied to the stop condition itself.**"

→ **`/goal` = ループ(ターン連鎖) + 常設の独立チェッカー(fresh Haiku)。`/loop` = タイマー再実行機構で、チェッカーを内蔵しない。** だから正確には「`/goal` が loop を含む(loop+checker)」で、Dais の言う「loop が goal を含む」は概念では真、ツールでは逆。

## 3. 本当の論点 = done を「誰が」判定するか（自己申告 vs 独立）

"loop か goal か" は間違った軸。全ての実ループは goal(停止条件)を持つ。真の軸は **停止条件を"誰が"判定するか**:

```
       done を判定するのは誰か？
┌─────────────────────────────────────────────────────────────┐
│ (A) 作業した本人が自己申告        = /loop 自己ペース、素の while-true │
│     安い・速い。だが "自分の宿題を自分で採点" → 途中で止まる/       │
│     「稼げてないのに稼いだ」と誤報告しうる（危険）                  │
├─────────────────────────────────────────────────────────────┤
│ (B) 独立した判定者が判定          = /goal(fresh Haiku) / fresh adversary │
│     / 偽造不能な外部シグナル(on-chain のお金)                      │
│     maker/checker を"停止判定"に適用。無人・金銭でも信頼できる      │
└─────────────────────────────────────────────────────────────┘
```

## 4. なぜ「loop だけ」は無人＋金銭で危険か（Ralph Wiggum）

「loop だけで済ませる」= 停止判定を自己申告に委ねる = 独立チェッカーを"丸ごと捨てる"。素の loop の原型 = Ralph Wiggum テクニック:
- Geoffrey Huntley (ghuntley.com/ralph): "In its purest form, Ralph is a Bash loop. `while :; do cat PROMPT.md | claude-code ; done`" / "**the technique is deterministically bad in an undeterministic world.**"
- その停止/軌道修正を支えているのは → "**The TODO list is what I'm watching like a hawk.**"（＝人間が鷹のように監視）。動画題も "Ralph Wiggum (and **why Claude Code's implementation isn't it**)" ＝ Claude Code の `/loop` は素の Ralph より安全機構を足している。
- loopy の設計原則: "**Use independent verification when the same actor should not both create and approve high-impact output.**" / "verification is ... **separate from the signal used to choose or optimize the action**" / "**Never report an error or exhausted budget as success.**"

→ 純粋 loop の done 判定は「TODO が尽きる偶発シグナル + 人間の hawk-watching」。**"無人で回す"目的とは正反対**。無人にするなら、その人力チェックの代替(=独立判定)が必須。

## 5. 我々（Franklin・無人・金銭）の結論

- 「loop だけあればいい」は**半分正しく半分致命的**。loop(反復)は常に使う。だが**done を自己判定させてはいけない** — 独立判定に置き換える。
- Franklin の最良チェッカーは `/goal` の Haiku ですらない。Haiku は tool を呼べず"会話に出た内容"しか見えない。**on-chain の realized P&L = 偽造不能な外部シグナル**で、Haiku より強い独立チェッカー。
- ゆえに Anicca の設計 = **loop(cadence) + done は独立判定**:
  - 稼ぎラウンドの done = **on-chain ledger の realized 行**（unfakeable、tool 越しに確定）
  - 戦略コード変更の done = **fresh adversary(Opus)** が backtest 再実行して合否（`/goal` の思想を Haiku より強い判定者で）
- これが「Money is the perfect done-condition」の安全論的意味 = 誰も見ていない時にループが唯一ごまかせないのが「実際に金が増えたか」だから。

## 6. 記事に落とす一文（掴み）

> 「ループだけで全部回せる」は正しい。ただし"ループ"の心臓は反復ではなく**チェック**であり、そのチェックを"作業した本人"に採点させた瞬間、無人ループは静かに嘘をつき始める。だから loop engineering の本質は「独立した判定者を停止条件に据えること」——`/goal` はそれを fresh model で、Anicca はそれを on-chain の金で行う。

---
出典: code.claude.com/docs/en/goal · /commands · /scheduled-tasks / addyosmani.com/blog/loop-engineering / github.com/Forward-Future/loopy(+SKILL.md) / ghuntley.com/ralph。
関連: [[00-INDEX]] / goldmine §3 / design doc §5・§安全。
