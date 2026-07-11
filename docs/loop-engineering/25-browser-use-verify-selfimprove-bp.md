# 25 — Browser-use タスクの検証(verify)+自己改善(self-improve) 業界BP（gig ループへ適用）

**目的**: 自己流で verifier を書かない。「ブラウザ操作エージェントのタスクをどう検証し、失敗からどう自己改善するか」の業界ベストプラクティスを裏取りし copy+tweak する。
**きっかけ (Dais 2026-07-11)**: 「browser操作タスクを人はどう検証してる？録画を取るのか？最高の self-improving browser-use loop を作りたい」。現状の gig auditor は core 自作 jsonl を信じるだけ = report-blind でない = 嘘を見抜けない。

調査ソースは全て一次(公式docs/論文/repo)。各判断に URL + 核心引用付き。

---

## §1 観測/記録 BP — step毎 screenshot+action+state を JSON trajectory に。screenshot が正、DOMリプレイは捨てる

**推奨**: 各ステップ境界で `screenshot(base64) + action + DOM/text state + result` を JSON(trajectory) に追記。動画DOM再構築(rrweb)ではなく **スクリーンショット列**を source of truth にする。

- **Browserbase** "session recordings": 当初 rrweb で DOM を録画・再生していたが「the easiest and most reliable way to show what happened in a browser is to just record what was on the screen」と結論。DOM再構築は iframe/Canvas/WebGL/Shadow DOM で破綻し、環境変化でリプレイが実際と矛盾する → screenshot/動画ベースへ移行。https://www.browserbase.com/blog/session-recordings
- **browser-use 公式**: `generate_gif`(各step screenshot+action 合成) と `AgentHistoryList`(step毎 screenshot/action/result/evaluation_previous_goal)。https://docs.browser-use.com/open-source/development/monitoring/observability ・ https://github.com/browser-use/browser-use
- **witness**(local-first observability wrapper): 「before each step snapshots the page (DOM + screenshot); after each step it records the action taken, the latency, and any error」= step境界記録の型。https://github.com/EricFinland/witness

## §2 検証/eval BP — 「report-blind」でなく「report-skeptical」。summary は渡すが懐疑を指示し screenshot+final-state で裏取り。二値判定

**推奨**: agent の自己申告 summary を判定LLMに **入力として渡す**が、システムプロンプトで **明示的にそれへの懐疑**を指示し、screenshot(最新~10枚, 重複除去)+trajectory+ground-truth で裏取りさせる。**二値(true/false)** verdict。rubric の中間スコアは避ける。fresh model spawn で報告非依存を担保。

- **browser-use/benchmark `judge.py`**(＝コピー元): `construct_judge_messages()` が screenshots(base64)+trajectory+agent summary+task+ground_truth を渡す。system prompt に「evaluate for action — double check whether the action actually happened」「skepticism toward the agent's self reported success」「very high standard」。出力 `JudgementResult{verdict: bool, reasoning, failure_reason, impossible_task, reached_captcha}`。https://github.com/browser-use/benchmark/blob/main/judge.py
- **browser-use 公式ブログ**: 「We use an LLM judge (gemini-2.5-flash) with a simple true/false verdict... agrees with human judgments 87% of the time」「Rubric-based scoring sounds better in theory, but in practice LLMs give middling scores to both successes and failures. Binary verdicts are more reliable.」**自己申告 77.3% vs LLM検証 60.2%** のギャップ = 自己報告は水増しする(不信任の根拠)。https://browser-use.com/posts/ai-browser-agent-benchmark
- **WebJudge**("An Illusion of Progress?", OSU-NLP-Group): 3段階 = (1)タスクを key points に分解 (2)trajectory から重要 screenshot のみ選別(token overload回避) (3)task+key points+key screenshots+action history で二値success判定。人間一致 ~85%。https://arxiv.org/html/2504.01382v4 ・ repo https://github.com/OSU-NLP-Group/Online-Mind2Web
- **AgentRewardBench**: 最終状態のみ／全screenshot／中間screenshot省略 はいずれも人間判定と低一致。「preserves critical intermediate screenshots while mitigating token overload」が正解。https://arxiv.org/pdf/2504.08942

> **本プロジェクトへの調停**: 「Gaming the Judge (arXiv:2601.14691)」= narrative 書換で false-positive +90%。BP の report-skeptical と両立させるルール = judge は claim を **見てよい(何を確認すべきか知るため)** が、**verdict は screenshot/DOM の実観測で正当化**されねばならず、視覚的裏取りが無ければ default-FAIL。稼ぎ(金)の判定だけは特に厳格に(実 販売実績/received_orders 画面 or 入金でのみ PASS)。

## §3 自己改善 BP — AWM(成功を型化)+Reflexion(失敗を言語化)。skill追加は必ず実行検証後

**推奨**: (a) **AWM(Agent Workflow Memory)** online induction = evaluator が correct と認めた **成功 trajectory のみ** を再利用可能 workflow 化して memory に追加。(b) **Reflexion** = 失敗 trajectory は「何が違ったか」を verbal self-reflection でテキスト教訓化し次試行プロンプトに注入。両方併用。

- **AWM**: 「online... iteratively induces workflows from self-generated past predictions that are judged correct by an evaluator module」「surpassing the BrowserGym baseline by 12.0 absolute points」= 判定は必ず外部 evaluator 経由(自己申告で貯めない)。https://arxiv.org/html/2409.07429v1
- **Reflexion**: 「after a failed attempt, the agent generates a textual analysis of what went wrong and uses this analysis to guide the next attempt」
- **Voyager**: 「generates code-based skills, validates them through in-game execution, and incorporates verified skills into a persistent library」= skill追加は execution-verified 後。https://arxiv.org/html/2305.16291

## §4 実装 repo（copy 元）

| repo | copy できる具体要素 |
|---|---|
| `browser-use/benchmark` https://github.com/browser-use/benchmark | `judge.py::construct_judge_messages()` のプロンプト構造(screenshot+trajectory+summary+ground_truth, report-skeptical指示)+`JudgementResult` pydantic — そのまま copy+tweak |
| `browser-use/browser-use` https://github.com/browser-use/browser-use | `AgentHistoryList`/`AgentStepInfo`/`generate_gif` = trajectory 記録データ構造 |
| `OSU-NLP-Group/Online-Mind2Web` https://github.com/OSU-NLP-Group/Online-Mind2Web | WebJudge 3段階(key-point分解→screenshot選別→binary判定) |
| `Skyvern-AI/skyvern` https://github.com/Skyvern-AI/skyvern | step単位の visual reasoning+verification、selector失敗時「remap selectors by trying an alternate selector for the same intention」= self-heal |
| `EricFinland/witness` https://github.com/EricFinland/witness | step()ラップの before/after snapshot(DOM+screenshot,action,latency,error) |

## §5 gig ループへの適用（実装マッピング）

```
core(cdp_*.py, pass毎):
  各 step 実行時 → Page.captureScreenshot(base64)+DOM要約+action+result を
    ~/gig/trajectory/<pass_id>/trajectory.jsonl に追記（AgentHistoryList 型を踏襲）。
    現行の summary-only jsonl をこれに置換/併存。
     ↓
auditor(reality-verifier, 毎時, fresh spawn = report非依存):
  browser-use/benchmark judge.py の construct_judge_messages() を copy+tweak。
  入力 = screenshot列(最新~10, dedup) + trajectory + task + ground_truth(実 received_orders/
    販売実績/出品一覧 の実DOM) + core summary(懐疑指示付き)。
  出力 = 二値 verdict + failure_reason。金(¥)は実 販売実績/入金 画面でのみ PASS。
     ↓ verdict=false or ¥0 継続
self-fix 連携:
  失敗 trajectory → Reflexion でテキスト教訓化 → strategy/skill memory。
  成功 trajectory → AWM で再利用 workflow 化 → skill memory。
  self-fix.sh が failure_reason+教訓を入力に harness/コードを Opus 修正 →
    次 loop で同じ judge 基準で再検証(fix→verify 反復, 上限5=VCSDD既定)。
```

## §6 引用リスト
1. Browserbase, session recordings — https://www.browserbase.com/blog/session-recordings — 「just record what was on the screen」
2. browser-use observability docs — https://docs.browser-use.com/open-source/development/monitoring/observability — `generate_gif`/`AgentHistoryList`
3. browser-use/benchmark judge.py — https://github.com/browser-use/benchmark/blob/main/judge.py — 「skepticism toward the agent's self reported success」
4. browser-use benchmark blog — https://browser-use.com/posts/ai-browser-agent-benchmark — 「Binary verdicts are more reliable」「self-report 77.3% vs LLM-verified 60.2%」
5. WebJudge / Online-Mind2Web — https://arxiv.org/html/2504.01382v4 — 3段階 key-point+screenshot選別 binary
6. AgentRewardBench — https://arxiv.org/pdf/2504.08942 — 「preserves critical intermediate screenshots while mitigating token overload」
7. Agent Workflow Memory — https://arxiv.org/html/2409.07429v1 — 「induces workflows... judged correct by an evaluator module」「+12.0 points」
8. Voyager — https://arxiv.org/html/2305.16291 — 「validates them through in-game execution... persistent library」
9. Witness — https://github.com/EricFinland/witness — step境界 snapshot 型
10. Skyvern — https://github.com/Skyvern-AI/skyvern — step visual verification + selector self-heal

## §7 judge.py 実ソース裏取り（VERIFIED — 実 fetch 済 raw main, 198行）
コピー元 `browser-use/benchmark/judge.py` を実取得し行番号付きで確認（scratchpad/judge_bu.py に保存）。gig judge へ copy+tweak する核心:
- **`JudgementResult`(L14-20)**: `reasoning:str|None, verdict:bool, failure_reason:str|None, impossible_task:bool, reached_captcha:bool` — この pydantic をそのまま採用。
- **`construct_judge_messages(task, final_result, agent_steps, screenshots_b64, ground_truth, max_images=10)`(L28)** — 引数構造を踏襲。
- **screenshot dedup(L55-58)**: 「last N unique screenshots (dedupe while preserving order)」= `unique = [s for s in reversed(screenshots) if s not in seen]; selected = reversed(unique[:max_images])`。
- **report-skeptical(L148)**: 「be initially doubtful of the agent's self reported success, be sure to verify that its methods are valid and fulfill the user's desires to a tee」
- **evaluate-for-action(L143)**: 「double check whether the action that the agent tried to performed actually happened. If the required action did not actually occur, the verdict should be false」
- **報告≠実画面=false(L101)**: 「the agent reports that the action is completed but the screenshot or page shows the action is not actually complete: false」← 我々の核心要件そのもの
- **ground-truth 最優先(L76)**: 「If the ground truth is not satisfied by the agent's execution and final response, the verdict MUST be false」→ gig の ground_truth = 実 received_orders/販売実績/出品一覧 の実DOM。

## 未確認(正直)
- AgentRewardBench/WebJudge の定量値は検索要約からの孫引き、原PDF本文は未直接確認（実装判断には影響しない）。
