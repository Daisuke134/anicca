# Anthropic一次ソース+gh実例で loop 設計を評価(2026-07-11)

firecrawl scrape + gh search で一次情報を確認し、現行の「BASE戦略+self-improve+self-heal の3層」loop設計と `/loop` セッション内運用を評価した。判断には全て引用を付す。

## テーマ1: 自律 AI agent loop 設計の BP

### 引用一覧

1. Anthropic「Building Effective Agents」(2024-12-19) https://www.anthropic.com/engineering/building-effective-agents
   > 「Agents… are typically just LLMs using tools based on environmental feedback in a loop… during execution, it's crucial for the agents to gain "ground truth" from the environment at each step (such as tool call results or code execution) to assess its progress.」
   > 「When and how to use frameworks」節: 「start by using LLM APIs directly… don't hesitate to reduce abstraction layers」
2. Anthropic「Effective context engineering for AI agents」(2025-09-29) https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
   > 「find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome」
   > compaction / structured note-taking(NOTES.md, progress file)/ sub-agent 隔離コンテキストの3手法を提示。
3. Anthropic「Effective harnesses for long-running agents」(2025-11-26) https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
   > 「a later agent instance would look around, see that progress had been made, and declare the job done」(=偽りの完了報告の実例)
   > 対策: feature_list.json に `passes:false` で全機能を先出し記録→エージェントは `passes` フィールドしか編集できない、「It is unacceptable to remove or edit tests」と明記。JSON採用理由「the model is less likely to inappropriately change or overwrite JSON files compared to Markdown」。
   > 「Claude mostly did well at verifying features end-to-end once explicitly prompted to use browser automation tools and do all testing as a human user would.」(=実side-effect検証)
   > 4失敗モード表: 「Claude marks features as done prematurely」→対策「Self-verify all features. Only mark features as "passing" after careful testing.」
4. Anthropic「Demystifying evals for AI agents」(2026-01-09) https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   > 「it's often better to grade what the agent produced, not the path it took」(=outcome-based grading、process/自己申告よりstate check優先)
   > 「Make your graders resistant to bypasses or hacks. The agent shouldn't be able to easily "cheat" the eval.」
   > 「You won't know if your graders are working well unless you read the transcripts… Reading transcripts is how you verify that your eval is measuring what actually matters」
   > 「We recommend practicing eval-driven development: build evals to define planned capabilities before agents can fulfill them, then iterate until the agent performs well.」
5. AWS builder / dev.to「How to Stop AI Agents from Hallucinating Silently with Multi-Agent Validation」(Elizabeth Fuentes, 2026-03-17) https://dev.to/aws/how-to-stop-ai-agents-from-hallucinating-silently-with-multi-agent-validation-3f7e
   > 一次研究引用: 「Teaming LLMs to Detect and Mitigate Hallucinations」(arXiv 2510.19507) https://arxiv.org/pdf/2510.19507 — single-agentの構造的失敗4種(成功を偽装/誤ツール使用/内容捏造/不正確統計)を提示。
   > 解: Executor(実行)→Validator(検証: 正しいツール使用か/要求と一致するか)→Critic(APPROVED/REJECTED理由付き)の3役割分離。「No agent trusts its own output.」
6. Geoffrey Huntley「Ralph Wiggum as a "software engineer"」(2025-07-14, Ralph技法の原典) https://ghuntley.com/ralph/
   > 「Ralph is a Bash loop. `while :; do cat PROMPT.md | claude-code ; done`」「the technique is deterministically bad in an undeterministic world」
   > 「one item per loop」「deterministically allocate the stack the same way every loop」(=@fix_plan.md + @specs/* を毎ループ固定投入)
   > 「Before making changes search codebase (don't assume an item is not implemented)… Think hard.」(=誤検出=false-negative実装済み判定への対策プロンプト)
   > phase two backpressure: 「After implementing functionality or resolving problems, run the tests for that unit of code that was improved」+ 型システム/静的解析を機械的backpressureとして配線。
7. vercel-labs/ralph-loop-agent(2026-07-10更新、815 stars) https://github.com/vercel-labs/ralph-loop-agent
   > アーキ図: 「Ralph Loop(outer) → AI SDK Tool Loop(inner) → verifyCompletion: "Is the TASK actually complete?" → No: inject feedback → retry / Yes: return」
   > コード例の `verifyCompletion` は構造チェック(`fileExists('vitest.config.ts')`, `noFilesMatch(...)`, `fileContains('package.json', '"vitest"')`)であり、LLMの自己申告テキストではなく**決定的な環境状態**を見て completion 判定している。

### 我々の現状設計の評価

| 現状要素 | 一致するBP | 判定 |
|---|---|---|
| BASE戦略+self-improve+self-heal 3層 | Anthropic「evaluator-optimizer workflow」(Building Effective Agents)= 生成LLM+評価LLMのfeedback loopに相当。self-healはこの evaluator 側の自動修復拡張 | ✅ 正しい方向 |
| healthcheck が report を見る | ソース6「don't assume it's not implemented」= reportをそのまま信じず再検索させる工夫と同じ発想だが、**report自体を信じる設計だとソース3・4・5の「後発agentが進捗を見て勝手にdone宣言する」「単一agentは自分の出力を自分でチェックできない」の失敗パターンにそのまま該当**。healthcheckは report ではなく **state/outcome**(ソース4「grade what the agent produced」)を見るべき | ⚠️ 欠けている点(構造的) |
| cadence contract | ソース3の「incremental progress + clean state」に相当。git commit 単位で進捗を残す設計と一致していれば良好 | 要確認(実装次第) |
| self-fix spawn(Opus) | ソース5の Executor→Validator→Critic に近いが、**fix実行者とverify実行者が別モデル/別contextか**が鍵。同一loop内・同一contextでの自己検証は「no agent trusts its own output」の原則に反する | ⚠️ fresh-context adversary(既存 VCSDD 運用)を self-fix にも必須適用すべき |

### loop内 verifier を deep にする具体機構(BP合成)

1. **feature_list.json 型の構造化状態ファイル**(ソース3): 全達成条件を `passes:false` で先出し。agentは `passes` フィールドのみ編集可、削除・上書き禁止を強い言葉で明記。JSON採用(Markdownよりモデルが誤編集しにくい)。
2. **verifyCompletion は決定的な環境チェックのみ**(ソース7): ファイル存在/コマンド終了コード/DBレコード有無など、LLMの自己申告テキストを一切信用しない。`result.text.includes('DONE')` のようなテキストマッチのみのverifyCompletionは反面教師として明記されている(basic exampleは簡易化のためテキストマッチだが、migration exampleは全て構造チェック)。
3. **outcomeで採点し、経路(transcript)では採点しない**(ソース4)。同時に「graders resistant to bypass」= agentがcheatできない設計にする。
4. **fresh-context の第三者検証**(ソース5): 実行者=修復者と検証者は別contextであるべき。既存の VCSDD adversary(Opus 4.8、fresh spawn)はまさにこのBPと一致——self-heal/self-fix.sh の verify段にも同じ fresh-adversary 原則を適用すべき。
5. **実side-effect検証を明示的に指示**(ソース3): 「browser automation tools and do all testing as a human user would」。コード変更だけでなく、実際に動く様を人間と同じ経路(HTTPリクエスト、UI操作、on-chain tx確認等)で確認させる一文を loop prompt に必ず含める。
6. **transcriptを定期的に人間/上位agentが読む**(ソース4 Step 6): grader・healthcheckが正しく機能しているかは、失敗ケースのtranscriptを読まないと分からない。「Reading transcripts is how you verify that your eval is measuring what actually matters」。

**評価まとめ**: 現行の3層構成(BASE/self-improve/self-heal)は Anthropic の evaluator-optimizer + 長時間runハーネスの二大パターンに正しく整合している。欠けているのは「検証を誰が・何を見て行うか」の設計原則——(a) verifierは実行者と**別コンテキスト**であるべき、(b) verifierは**report(自己申告)ではなくstate/outcome**を見るべき、(c) done判定は**決定的チェック**でLLMテキストに依存しない。これら3点を healthcheck-lib / self-fix.sh の verify段に機械的に組み込むことが次のアクション。

---

## テーマ2: Claude Code `/loop` をセッション内嘘防止に使う BP

### 引用一覧

- 公式コマンド一覧(2026-07-11 firecrawl再確認、内容2026-06-28時点から不変) https://code.claude.com/docs/en/commands
  > 「`/loop [interval] [prompt]` Skill. Run a prompt repeatedly while the session stays open.」
- 公式 scheduled-tasks docs(2026-07-11 firecrawl確認) https://code.claude.com/docs/en/scheduled-tasks
  > 固定間隔: 「Claude converts it to a cron expression」
  > 自己ペース: 「Claude chooses one dynamically… picks a delay between one minute and one hour based on what it observed: short waits while a build is finishing or a PR is active, longer waits when nothing is pending.」「Claude may use the Monitor tool directly. Monitor runs a background script and streams each output line back, which avoids polling altogether」
  > 停止: 「In self-paced mode, Claude can also end the loop on its own once the task is complete. Claude calls the ScheduleWakeup tool with stop: true」「If an iteration ends without either rescheduling or stopping, Claude Code schedules one fallback wakeup about 20 minutes later and ends the loop when that iteration doesn't reschedule either.」
  > 既定maintenanceプロンプト(引数なし `/loop`): 「continue any unfinished work from the conversation」「tend to the current branch's pull request: review comments, failed CI runs, merge conflicts」「run cleanup passes such as bug hunts or simplification」「irreversible actions such as pushing or deleting only proceed when they continue something the transcript already authorized」
  > `loop.md` はプロジェクト単位でデフォルトプロンプトを差し替え可能(`.claude/loop.md` > `~/.claude/loop.md`)。

### 具体レシピ:セッション内 `/loop` で自己再検証させ「嘘」を構造的に防ぐ

1. **prompt自体に「決定的な検証コマンドを実行して出力を貼れ」を必須項目として書く**。テーマ1のBPと同じ原則(state/outcome check、report禁止)を `/loop` のプロンプト文字列にそのまま埋め込む。例:
   `/loop 5m self-fix.sh の最新runを確認し、ledger/*.jsonl に実際のtx hashが追記されているかを実際にファイルを開いて確認。無ければFAIL報告、報告テキストだけで済ませない`
2. **done条件はテキストではなくファイル/コマンドの終了コードにする**。dynamic modeでは Claude自身が `ScheduleWakeup(stop:true)` を呼んでloopを終える権限を持つが、その判断根拠を「タスク遂行者自身の申告」ではなく「直前iterationで実行した検証コマンドの結果」に強制的に紐づけるようpromptで明示する。
3. **interval選択**: BP=「build/PRがactiveな短時間検証は短interval(1〜5m)」「定常監視・cadence確認は自己ペース(dynamic)で `Monitor` toolに委ねる」。60分以上や daily 系は `/schedule`(クラウド)に切り替える(既存 `references/loop-command.md` の運用ルールと一致、変更なし)。
4. **verify専用の別コンテキストを混ぜる**: `/loop` 単体は同一セッション内=同一コンテキストで回るため、テーマ1の「fresh-context 第三者検証」原則を満たすには、loop prompt内で明示的に `vcsdd-adversary` や独立 subagent(Task/Agent tool)をverify役として毎iteration spawnさせる一文を入れる。同一コンテキストの自己検証だけに頼らない。
5. **loop.md をproject単位の恒久verify契約にする**: 頻繁に回すverifyループ(例: cronの死活監視、ledgerの実残高チェック)は `.claude/loop.md` に「毎回これを実行しFAIL時は自己修復せず報告のみ」の形で固定化しておくと、`/loop` を引数なしで叩くだけで毎回同じ検証契約が走る。

### まとめ表

| 項目 | BP | 出典 |
|---|---|---|
| done条件 | 決定的チェック(ファイル/exit code/on-chain確認)。テキスト自己申告は不可 | ソース7 verifyCompletion例、テーマ1ソース4 |
| interval | 短時間監視=固定(1-5m)、定常監視=dynamic(Monitor併用) | scheduled-tasks docs |
| 60分以上/毎日 | `/schedule`(クラウド)へ誘導 | 既存 references/loop-command.md(不変確認済み) |
| 検証者分離 | loop内で独立subagent/adversaryをverify役にspawn | テーマ1ソース5 Executor/Validator/Critic |
| 恒久契約 | `.claude/loop.md` にverify専用プロンプトを固定 | scheduled-tasks docs |
