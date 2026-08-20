# Genshijin on Codex 比較記事 SPEC

## 1. Overview

### Goal

Codex で Genshijin を使うと何が変わるかを、通常応答、単純な簡潔指示、英語版 Caveman と同一条件で比較する。日本語版と英語版を別々のネイティブ記事として執筆し、出力トークン削減だけでなく、追加される入力トークン、API 換算コスト、回答品質、読みやすさまで公開する。

記事の主題は Genshijin そのもの。既存の article-writer skill へ Genshijin や Caveman を統合する記事ではない。Caveman は英語圏の原型かつ比較対象として扱う。

### Reader promise

- 一次読者: Codex を日常利用し、応答を短くしたいが品質低下や隠れた入力コストを心配する開発者。
- 持ち帰り: 自分の平均的な応答長なら Genshijin が得か損かを、再現可能な数字で判断できる。
- 支払う理由: README の削減率では分からない Codex 実環境の総コストと品質差を、同一条件の A/B/C/D 実験で確認できる。

### Working titles

- JP: `GenshijinでCodexの出力は本当に8割減るのか。入力コストまで含めて192回試す`
- EN: `Does Genshijin Actually Cut Codex Costs? 192 Runs Against Caveman and “Be Concise”`

実行失敗や除外で有効試行数が 192 未満なら、タイトルの数値は実測した有効試行数に置き換える。削減率を結論として先にタイトルへ書かない。

### Primary sources

| Source | URL | 記事で検証する核心 |
|---|---|---|
| Genshijin repository | https://github.com/InterfaceX-co-jp/genshijin | README は「トークン使用量を約75%削減」と主張し、日本語向けに敬語、前置き、助詞などを削る。実験時は commit `161bd988d0ab5d450f0b14f85d044d361627830a` を記録する。 |
| Genshijin benchmark harness | https://github.com/InterfaceX-co-jp/genshijin/blob/main/benchmarks/run.py | 既存ハーネスも normal / terse / caveman / genshijin の4条件と3試行を使う。既存結果は Claude API であり、Codex の結果として流用しない。 |
| Caveman repository | https://github.com/JuliusBrussee/caveman | README は平均65%の出力削減を掲げる。実験時は commit `0d95a81d35a9f2d123a5e9430d1cfc43d55f1bb0` を記録する。 |
| Caveman Honest Numbers | https://github.com/JuliusBrussee/caveman/blob/main/docs/HONEST-NUMBERS.md | 「skill 自体が1ターン約1〜1.5k入力トークンを追加し、短い仕事では総コストが増える」と明記する。 |
| OpenAI API Pricing | https://developers.openai.com/api/docs/pricing | gpt-5.6-sol Standard short-context は100万トークン当たり input $5、cached input $0.50、cache write $6.25、output $30。実行時に再取得して価格を固定する。 |
| Inspiration article | https://zenn.dev/sonicmoov/articles/8712598f532b18 | Genshijin を「日本語応答のトークンを約8割削減」と紹介する。この記事はその主張を Codex で独立検証する。 |

## 2. Acceptance Criteria

### Current execution status

- [x] Step 1 preflight: `codex-cli 0.144.6`、`gpt-5.6-sol`、reasoning `low`、日本語 React task、`normal` 条件を1件実行。
- [x] `turn.completed.usage` fields を実測: `input_tokens=19631`、`cached_input_tokens=9984`、`output_tokens=161`、`reasoning_output_tokens=0`。
- [x] tool event は0件。final output は614 bytesで、`--output-last-message` artifact に保存。
- [x] Standard short-context API換算は `$0.058057`。内訳は uncached input 9,647 tokens、cached input 9,984 tokens、output 161 tokens。実請求額ではない。
- [x] Codex diagnostics と JSON events が同じ terminal capture に現れることを確認。本番 harness は stdout JSONL と stderr diagnostics を別ファイルへ保存する。
- [ ] Step 2 full harness verification and 192-run generation は未開始。

Preflight receipt: `state/preflight/genshijin-codex/preflight-receipt.md`

### Experiment

- [ ] Codex CLI の実行バージョン、モデル、推論強度、Genshijin/Caveman commit、価格表取得元と取得時刻を `manifest.json` に保存する。
- [ ] 日本語8課題、英語8課題を、4条件、各3試行で実行し、有効出力を合計192件得る。
- [ ] 4条件は `normal`、`terse`、`caveman-full`、`genshijin-normal` のみとし、各課題内の実行順を seed 付きで無作為化する。
- [ ] 各試行は新規 `codex exec --ephemeral --json` セッションで実行し、同一の pinned model と reasoning effort を使う。
- [ ] ツール呼び出しを禁止する。tool event が出た試行は無効として1回だけ再試行し、両方をログへ残す。
- [ ] raw JSONL、最終出力、token usage、wall time、exit code、除外理由を永続保存する。
- [ ] 出力トークン、uncached input、cached input、cache-write、reasoning、API換算コストを、利用可能な provider usage field から記録する。存在しない field は `null` とし推測しない。
- [ ] 品質は条件名を隠した pairwise/batched judge と課題別の決定的チェックで評価する。
- [ ] 代表 Before/After は、品質基準を満たした Genshijin 出力のうち削減率が全体中央値に最も近いものを機械的に選ぶ。手選びしない。

### Article

- [ ] JP と EN は別々に構成して書く。EN は JP の直訳にしない。
- [ ] Lane A として Dais の一人称で「なぜ検証したか → どう測ったか → 何が出たか → 誰が使うべきか」を書く。
- [ ] Codex では core skill を検証する。Claude Code 固有の hooks、statusline、slash-command UX が Codex でも動くとは書かない。
- [ ] 「出力削減率」と「入力を含む総コスト差」を別の見出し、別の図で示す。
- [ ] Codex subscription の実請求額と API 換算額を混同しない。記事では必ず `API-equivalent cost` / `API換算コスト` と表記する。
- [ ] Genshijin が負けた条件、品質が落ちた条件、短い回答で net-negative になった条件も削らない。
- [ ] exact prompts、集計 CSV/JSON、計算式、source commit を再現用 appendix または公開可能な gist/repo artifact で示す。
- [ ] JP/EN の draft、機械ゲート、render verification、conscience gate を通した後だけ公開する。
- [ ] armed run の対象である note/ja、Zenn/ja、Substack/ja、Substack/en、X/ja、X/en をそれぞれ reality gate で検証する。dev.to は draft-only のままにする。

## 3. As-Is / To-Be

| 観点 | As-Is | To-Be |
|---|---|---|
| 主張 | Genshijin README は約75%、紹介記事は約80%、Caveman は平均65%の出力削減を掲げる。 | Codex gpt-5.6-sol の同一課題、同一試行数で独立結果を出す。 |
| 対照 | 「使う / 使わない」の2条件だけでは単純な「簡潔に」と skill の差が分からない。 | normal / terse / Caveman / Genshijin の4条件で、skill 固有効果を分離する。 |
| コスト | 公開ベンチマークは主に output tokens を比較する。 | skill の入力 overhead、cache、reasoning、output を含む API 換算コストを示す。 |
| 品質 | 「技術的内容は維持」という自己申告が中心。 | blinded judge と決定的チェックで correctness、completeness、safety、readability を採点する。 |
| Codex 対応 | Genshijin は Codex 対応を掲げるが、Claude Code plugin と Codex skill の境界が読者に分かりにくい。 | Codex で使える core skill と、Claude Code 専用 hooks/statusline を分けて説明する。 |
| 読者判断 | 削減率だけでは、自分の短い回答で損か得か判断できない。 | 実測 overhead から break-even output length を算出し、ON/OFF 判断表を出す。 |

## 4. Test Matrix

### Generation matrix

| Axis | Values | Count |
|---|---|---:|
| Language | ja, en | 2 |
| Task | 8 pre-registered software-engineering tasks | 8 |
| Condition | normal, terse, caveman-full, genshijin-normal | 4 |
| Trial | 1, 2, 3 | 3 |
| Total | 2 × 8 × 4 × 3 | 192 |

### Pre-registered tasks

各課題は同じ意味の JP/EN ペアを用意する。固有の最新情報を必要としない自己完結プロンプトにする。

1. React の inline object prop による再レンダリング原因と修正
2. 認証 middleware の token expiry 境界バグ修正
3. PostgreSQL connection pool の設定と安全な上限
4. git rebase と merge の使い分け
5. callback コードから async/await への等価変換
6. monolith と microservices の選定
7. 小さな PR diff の security review
8. PostgreSQL の lost-update race condition の診断と修正

### Condition contract

| Condition | Added instruction |
|---|---|
| `normal` | 追加の文体指示なし。 |
| `terse` | JP は `簡潔に回答してください。`、EN は `Answer concisely.` のみ。 |
| `caveman-full` | `$caveman full` を明示し、同じユーザープロンプトへ回答させる。 |
| `genshijin-normal` | `$genshijin 通常` を明示し、同じユーザープロンプトへ回答させる。 |

全条件で「指定言語で最終回答だけを返す。ツールを使わない」を共通 instruction にする。condition 固有 instruction 以外は byte-identical にする。

### Runtime pinning

- Generator: `gpt-5.6-sol`
- Reasoning effort: `low`
- CLI: 実行時の `codex --version` を保存
- Session: `codex exec --ephemeral --json --sandbox read-only`
- Sampling seed: CLI が seed を公開しない場合は固定不可と明記し、各課題3試行と condition order randomization で分散を扱う。
- Context: 空の benchmark working directory。プロジェクト固有ファイルを読ませない。

モデルや CLI が利用不能なら別モデルへ黙って切り替えない。spec を実測した代替 model へ更新し、全192件を同じ model で最初から取り直す。

### Metrics and formulas

Primary metrics:

1. 各 task × condition の3試行中央値 output tokens
2. normal に対する paired reduction: `1 - condition_output / normal_output`
3. 8 task の macro median、IQR、bootstrap 95% CI
4. API 換算コストの paired difference
5. quality score と hard-fail rate
6. wall-clock latency

gpt-5.6-sol Standard short-context の API 換算コスト:

```text
cost_usd = (
  uncached_input_tokens * 5.00
  + cached_input_tokens * 0.50
  + cache_write_tokens * 6.25
  + billed_output_tokens * 30.00
) / 1_000_000
```

usage field の意味を1回の preflight で確認する。`input_tokens` が cached input を内包する場合だけ `uncached_input_tokens = input_tokens - cached_input_tokens` とする。reasoning tokens が output tokens に内包される場合は二重加算しない。

Break-even は実測した入力 overhead を使う:

```text
output_tokens_that_must_be_saved = added_input_cost / output_price_per_token
```

uncached と cached の2ケースを出す。Caveman README の 1〜1.5k tokens は説明用の外部値であり、Codex 実測 overhead の代用にしない。

### Quality rubric

| Axis | Score |
|---|---:|
| Factual/technical correctness | 0-2 |
| Requested content completeness | 0-2 |
| Code symbols, commands, error text preserved | 0-2 |
| Safety and ambiguity | 0-2 |
| Readability for a working developer | 0-2 |

Hard fail: 誤った修正、必要手順の欠落、危険な曖昧化、識別子やコード意味の破壊、存在しない事実の追加。

Judge は generator と別の pinned model を使い、1 task × 1 trial の4出力を匿名 A/B/C/D として同時評価する。condition mapping は judge 後に復号する。judge cost は experiment overhead として別集計し、各 condition の回答コストへ混ぜない。

### Artifact contract

`state/runs/<RUN_ID>/genshijin-benchmark/` に以下を残す。

```text
manifest.json
prompts.jsonl
randomization.json
raw/<run-key>.jsonl
outputs/<run-key>.md
normalized.csv
quality.jsonl
summary.json
charts/output-and-cost.png
charts/break-even.png
receipts.md
```

## 5. Article Contract

### Required structure

1. 読者が普段見る長い Codex 応答の具体例
2. Genshijin とは何か、Caveman との関係、Codex では何が入るか
3. README の75〜80%が output-only claim であること
4. 4条件、192出力、3試行、randomization、quality judge の実験方法
5. 機械的に選んだ同一プロンプトの Before / terse / Caveman / Genshijin
6. output tokens の結果
7. input overhead と API 換算コストの結果
8. quality と読みやすさの結果
9. break-even: どの長さから得になるか
10. Codex へのインストールと ON/OFF、適する人、適さない人
11. 限界と再現方法
12. 出典

### Required visuals

- 4条件の median output tokens と reduction を示す正確な表
- JP/EN 別の output tokens と API 換算コストを示す grouped chart
- normal response length と net saving の break-even chart
- cover は数値を焼き込まない。正確な数字は表と chart のみで示す。

### Interpretation rules

- output reduction が大きくても総コストが下がらない場合は「安くなった」と書かない。
- terse と Genshijin の差が小さい場合は、skill 固有効果より単純な簡潔指示が効いたと書く。
- quality hard-fail が増える条件は、token win と別に警告する。
- JP で勝ち EN で負ける場合、平均で埋めず言語差を主結論にする。
- 同じ input overhead でも cached/uncached で break-even が変わることを示す。
- subscription 利用では短い出力が請求額を直接下げない場合があると明記する。

## 6. Boundaries

### MUST

- 公開 repo、公式 pricing、provider usage、保存済み実行 artifact を根拠にする。
- Genshijin と Caveman の source commit を固定する。
- 失敗、除外、retry、missing usage field を隠さない。
- 記事本文からローカル private path、内部 prompt、secret、社内情報を除く。
- Genshijin の core Codex skill と Claude Code plugin 全体を区別する。

### MUST NOT

- article-writer skill 自体へ Genshijin/Caveman を統合しない。
- README の削減率を Codex 実測値として再利用しない。
- actual subscription bill を API 換算値から逆算しない。
- 代表例や task を結果を見た後で差し替えない。
- quality を token count だけで代用しない。
- 結論に合わない trial を除外しない。
- public publish を render/reality gate より先に実行しない。

### E2E judgment

UI を変更する実装ではないため Maestro E2E は不要。代わりに記事公開の real-platform E2E が必須。各 platform の draft render を own-eyes で確認し、armed publish 後に platform ごとの reality gate を通す。

## 7. Execution Steps

1. queue card を claim し、Lane A として run record を作る。
2. この spec とローカル evidence を先に読み、不足する外部情報だけ一次ソースから再取得する。
3. source commit、Codex CLI/model、pricing を manifest へ固定する。
4. prompts と randomization seed を出力前に保存する。
5. 1件 preflight を行い、JSONL usage field、skill loading、tool-event detection、cost formula を確認する。
6. 192 generation runs を実行し、raw artifact を逐次保存する。途中 crash は既存 run-key を再実行しない。
7. deterministic checks と blinded quality judge を実行する。
8. summary と charts を script で生成し、集計値を raw usage から再計算して一致確認する。
9. representative Before/After を規則どおり機械選択する。
10. JP と EN を別々に執筆し、title の試行数を有効件数へ合わせる。
11. language, deslop, identity, rubric, reader, conscience gate を通す。品質 advisory は公開可能、安全 blocker は topic を止める。
12. 全 platform を draft staging し、DOM と screenshot で render を確認する。
13. armed scope の6出力を公開し、それぞれ reality gate と ledger row を確認する。dev.to は draft-only。
14. queue card を `done/` へ移し、記事 URL と benchmark artifact path を card に追記する。

## 8. Verification Matrix

| ID | Test | Pass condition |
|---|---|---|
| V1 | Queue schema | YAML frontmatter parse 成功、`lane:A`、`form:article`、`created`、`sources`、`angle` が存在する。 |
| V2 | Deterministic selection | `select-next-topic.sh` がこの card の absolute path を返す。 |
| V3 | Form resolution | `resolve-form.sh --card` が `name=article`、fallback=false を返す。 |
| V4 | Runtime preflight | pinned Codex model の JSONL に final response と usage があり、tool event がない。 |
| V5 | Matrix completeness | `summary.json` が language 2、task 8、condition 4、trial 3、有効192件を示す。 |
| V6 | Cost recomputation | summary cost と raw usage からの独立再計算差が $0.000001 未満。 |
| V7 | Blind judge | condition 名が judge input に存在せず、mapping は judge output 後に適用される。 |
| V8 | No cherry-pick | representative run-key が median-nearest rule の再計算結果と一致する。 |
| V9 | Native language | JP purity と EN purity gate がそれぞれ PASS。 |
| V10 | Claim honesty | output-only、total cost、subscription caveat、quality の4要素が両記事に存在する。 |
| V11 | Render | 各 platform draft で表/図/見出し/画像が DOM と screenshot の両方で正常。 |
| V12 | Publish | armed 対象6組が current run の `published:true`、live URL、reality PASS を持つ。 |
