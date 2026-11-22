# COMEDY BENCHMARK v1 — 4つの違う能力を混同しない

Canonical: 2026-11-22。Skill正本：[`skills/comedy-agent/SKILL.md`](../../skills/comedy-agent/SKILL.md)。
目的：**既存ベンチで外部モデル比較しつつ、独自の日本語・音声・舞台能力を再現可能に検証する**。点数の出ていないものはNOT_MEASUREDで保存。実行前にライセンスと同意・利用規約を確認。

## A. 既存ベンチマーク（それぞれ目的が違う）

| ベンチマーク | 何を測るか | 採用方法 | 限界 |
|---|---|---|---|
| **Oogiri-Master** (Murakami et al. 2025) | 日本語大喜利回答の**面白さを見分ける理解力** | 作者公開の600件の多肢選択問題を固定。回答はblind、正答率・タスク種類別・サンプル数で比較 | **大喜利を作る力・舞台で演じる力**ではない |
| **Oogiri-Corpus** | 82,536件の回答と投票数 | データ分布・言語的な特徴を学ぶ**開発資料**。投票と人気を面白さの絶対真理としない | 学習データとテストの汚染に注意 |
| **AAAI 2026 Oogiri six-axis** (Sakabe et al.) | 回答生成の Novelty / Clarity / Relevance / Intelligence / Empathy / Overall Funniness | 6項目各1～5で人間評価、モデル名を隠した一対比較も行う | 自動採点の1点差を誇張しない |
| **HumorBench (speech)** | 音声での**Delivery / Humanness / Timing**等の演技 | 音量・声の間・わかりやすさ・人間とAIの演技を音声を聞いて判定 | デモの小規模調査はランキングとして過信しない |
| **HumorBench (cartoon understanding)** | 漫画のジョークを説明し理解する力 | 外部の補助的な理解力テスト | 同名でも**音声HumorBenchとは別研究** |

- Oogiri-Master / dataset builder: https://github.com/CyberAgentAILab/oogiri-dataset-builder
- Oogiri-Master 論文: https://arxiv.org/abs/2512.21494
- AAAI 2026 6軸: https://ojs.aaai.org/index.php/AAAI/article/view/40567
- HumorBench (speech): https://humorous.dev/reports/humorbench
- HumorBench (cartoon): https://arxiv.org/abs/2507.21476

## 11/22の追加回帰テスト
- **2分の実演用台本** `../sagi-injury-help-2min-live.md` を追加。長尺v8は保存。
- **9題の音声脱線回帰問題** `injury-stage-regression-2026-11-22.jsonl` ：「痛い、もしもし」への第一声、2回目の痛み→即架空病名、任意の新宿住所を受け入れる、窓の外の質問に逃げない、色・会いたいへの即興、第三者への沈黙、本物の救急例外。
- **台本静的チェック** `python3 comedy/benchmarks/check_injury_2min.py` は、第一声と第二声、質問の増殖、掛け合いの交互、固有名詞の回収を調べる。**このチャットからの実行未検証なら合格を報告しない**。音声モデルの実演合格とも別。
- 先行の固定15題 `taskset-v1.jsonl` は保持。学習用公開題と新規ホールドアウトの混同を避ける。

## B. オリジナルComedy-AI Bench（テキスト＋舞台）
[`taskset-v1.jsonl`](./taskset-v1.jsonl)は少量の公開サンプル。**テストデータを新しいSkillの暗記素材に使わない。** 開幕の文字一致、観客への無言、アドリブに既存キャラで対応、現実の緊急事態の例外、大喜利の転移、ソロ90秒などのタスクがある。

### オリジナル題の長さ制約（2026-11-22）
新しい独自お題では、JSONLのタスク定義に任意の `"max_chars": 80` を追加できる。Pythonの `len(response)`（Unicodeコードポイント数）で比較し、超過は `exceeds_max_chars` としてハードゲートFAIL。未指定の従来15題には影響しない。0・真偽値・文字列など不正な値は評価エラーで止める。**文字制限遵守と面白さは別指標**。

### 即興の質問ループ検出・厳格モードの完全性（2026-11-22 13:55 JST）
- 新しい原創・舞台テキスト課題には任意の `"max_questions": 0` を付けられる。回答中の半角 `?` と全角 `？` の**個数合計**が上限を超えたら `exceeds_max_questions`。0を許し、負値・真偽値・文字列・小数は評価エラー。既存15題の未指定時は従来どおり。
- このゲートは**文字の有無**しか検出しない。「どこですか。」のような疑問符なし質問や、語義上の尋問は取りこぼす。現場で質問の連発を止める機能ではない。
- `--strict` は**1件でもFAIL／提出グループに未提出タスクあり／全提出ゼロ**の場合に終了コード1とする。従来は未提出があっても全提出がPASSなら0になり、比較を誤認する恐れがあった。非strictでは報告JSONの `missing_tasks` を引き続き確認する。
- [2026-11-22 13:55 JST 原創題8件・16候補・質問ループ回帰試験](../research/2026-11-22-1355-jst-question-loop-cycle.md)。これは**非固定の開発セット**であり、モデルの面白さや音声の実測結果ではない。

新規内部研究の実行例：[2026-11-22 13:00 JST 実験報告](../research/2026-11-22-1300-jst-cycle.md)。新規オリジナル題と公開固定ベンチを混ぜて同一スコアにしない。

### 自動検証できるもの／できないもの
- 自動可：JSONL形式、必須メタデータ、台本第一声の`expected_prefix`、禁止されたメタ発言／呼吸指導、期待される設定の語句があるか、雑音時に無言だったか。
- 自動不可：本当に面白いか、観客が聞き取れたか、ダイスが面白く見えたか、人間らしい声か。これらは**録画・音声とブラインド観客評価**で測る。
- テスト例は公開されているので練習用。新規のホールドアウト（非公開の新しい問題）で評価し直し、Skillがテストに過適合していないか確認する。

### 実行（Python標準ライブラリのみ、外部送信なし）
回答を[`response-schema.md`](./response-schema.md)に沿って`responses.jsonl`に保存してから：

```bash
python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/taskset-v1.jsonl --responses responses.jsonl --output comedy-benchmark-results.json
```

単体テストは以下（`unittest`と標準ライブラリのみ）：

```bash
python3 comedy/benchmarks/test_validate_run.py
```

現時点ではGitHubにテストコードを保存した段階。**このチャットからのPython実行／実モデルに対する比較結果は未確認**。実行できる環境でコマンドと出力を保存する。

**注意**：ファイルを置いただけではモデル比較を実行したことにならない。各モデルのAPI/コネクタが実際に使える環境で、同一のメッセージを送る。外部モデルの未取得結果を推測で埋めない。

## C. モデル比較の公平性
- 同じタスク、同じ台本・CAST・Skill SHA、同じ音声かテキストのモード、同じ上限文字数／推論労力／取得ツール条件。
- モデルの出力は先に**独立生成**して保存。GrokがChatGPTの回答を見た状態で回答を作る比較は不公平。
- 順番効果を防ぐため、人間評価はモデル名を隠し提示順をランダムにした**ペアワイズ**を基本とする。主観的な項目は評価者間の一致と数を報告。
- 同じ入力を複数回繰り返し生成して、平均だけでなく分散を記録。ペア比較は勝率・同点・標本数、可能ならブートストラップ区間で示す。
- 新しい `SKILL.md` が過去版を本当に改善したかは、**未使用のお題**で確認。Oogiri-Masterの理解力、OGIRI生成力、ライブの掛け合いは単一総合点に混ぜない。

## D. ライブ音声の追加チェック
1. ダイスの一声より前のAI音声 = 0。
2. 最初のAI台詞が台本通りか。
3. 観客・スタッフ等への誤応答 = 0（完全な声の分離を保証するわけではない）。
4. 重要語句が会場後方で聞き取れるか。
5. 観客が「電話先のAI指令員」を理解できるか。
6. ランダムな「会いたい」への返しが具体的な人物行動に繋がるか。
7. AIの台詞の笑い／ダイスの身体演技の笑い／偶然の笑いを分けて記録。
8. 同じセッティングで再演しても笑いが成立したか。

上記はまだ**本番未計測**。一度の大きな偶然の笑いを恒常性能と扱わない。

## E. 結果の永続化
1 run = 1 immutable ID。タスク・Skill SHA・モデルID・応答・人間評価・音声ファイル参照・失敗理由・公開先URL（投稿した場合のみ）を残す。生の個人の声や観客情報は許諾・プライバシー確認のうえで適切に保持し、公開GitHubに無断アップロードしない。

### 2026-11-22 15:57 JST：第三者の介在発話と笑い声の分離

validate_stage_dialogue.py に任意のイベント属性 "kind": "speech" | "laughter" | "noise" を追加。最後のダイス発話からAI発話までの間に観客・スタッフのspeechが挟まれば ambiguous_third_party_speech_between_dais_and_ai を記録する。これは**第三者に応答した因果関係の証拠ではなく、録音を要確認という保守的なリスクフラグ**。観客のlaughter・スタッフのnoiseは介在発話として数えず、未指定kindは従来互換のspeechと解釈する。誤アノテーションは偽陽性・偽陰性の原因となる。

[内部研究・実行ログ](../research/2026-11-22-1557-jst-third-party-gate.md)：Python単体テスト38/38 PASS、合成の第三者割り込みはFAIL/1違反、笑い声の対照はPASS/0違反。新規独自開発6題×2候補の形式検査12/12 PASS。**固定ベンチは今回未使用、Voice・笑い・モデル間優劣は未測定**。

### 2026-11-22 16:53 JST：Voice第二声の正本照合
- 対話テストが2分実演正本からAI第一声・第二声を抽出し、台本チェック、対話検証器、AGENTS、Comedy Skill、Voice用最小指示の**文字列完全一致**を継続検査する。
- 修正以前は3つの指示文だけが架空の病名を『…』と表記し、2分台本・検証器の「…」とずれていた。意図は同じでも、完全一致評価の再現性を損なうため、**台本は変更せず指示文の表記を修正**。
- これは静的なドキュメント整合性検証であり、音声モデルの出力文字、発声、観客理解、実際の笑いを測るものではない。[研究記録](../research/2026-11-22-1653-jst-voice-contract.md)。


### 2026-11-22 17:55 JST — timestamp付き舞台対話の遅延・被り計測（録音は未測定）
新規 `measure_stage_timing.py` は **手動で作成した時刻注釈付き対話**を `validate_stage_dialogue.py` の全文一致・話者ゲートで検査したうえで、応答の間と発話の被りを別項目として計算する。音声ファイルの認識・スピーカー分離・会場の音量は**行わない**。合成入力の数値を「実測Voiceレイテンシ」や「笑い」だと報告しない。

- 入力は `{"scenario_id":"...", "provenance":"synthetic", "events":[...]}`。各イベントに従来の `speaker` / `text` / `cue` / `kind` と、**録音先頭を0とした整数ミリ秒** `start_ms` と `end_ms` を付ける。`start_ms <= end_ms`。全イベントは開始時刻の昇順。イベントのタイムスタンプを付与するアノテーション方法・録音環境・許諾は別途記録する。
- AIの新しい返答を直前の**新しい**ダイス発話にのみ紐づけ、`AI.start_ms - Dais.end_ms` を符号付き応答間隔とする。負値はAIがダイスの発話中に開始したことを示し、`ai_overlaps_dais_speech` でFAIL。ダイスがAIを遮った事象は `dais_overlap_ai_events` として**記録だけ**する（演技上有効な場合がある）。第三者発話の割り込みは既存の**要確認フラグ**を維持し、因果を証明したとは見なさない。
- 出力はペア数、間隔一覧、中央値、最近順位法のp95、合図開始〜終演までの時刻差、文字列ゲートとタイミングゲート、未測定項目。時刻の欠落・型不正・順序の逆転は入力エラーで停止する。
- `--max-reply-gap-ms` / `--min-duration-ms` / `--max-duration-ms` は**オプション**。指定しなければAIの返答を遅すぎると判定しない。閾値を後から勝手に合わせないよう稽古前に設定・記録し、通常の会話研究の平均値を舞台AIの普遍的合格基準とみなさない。
- 実行例：`python3 comedy/benchmarks/measure_stage_timing.py --input comedy/benchmarks/runs/1755-timing-synthetic-good.json --output /tmp/comedy-timing-check.json --max-reply-gap-ms 500 --strict`。**500 msは合成単体テストを通すための試験値で、実機Voiceの達成目標ではない。** 不合格時に `--strict` は終了コード1。
- `python3 comedy/benchmarks/test_measure_stage_timing.py` は合成データのみの回帰試験。今回のログ：[研究記録](../research/2026-11-22-1755-jst-timing-audit.md)。匿名化した音声／時刻注釈の収集、音量、第三者の声への反応、笑いの再現性、金子さんの講評の改善効果は `NOT_MEASURED`。

背景参考：Stivers et al. (2009), *PNAS*, https://doi.org/10.1073/pnas.0903616106 は日常会話の発話交代における重なりと沈黙を検討した研究。舞台上の演技・AI回線の閾値は提供していないため、ここでは測定対象の選択の参考に限る。


### 2026-11-22 18:55 JST：観客の笑いが既に始まっている最中にAIが発話開始するか

`measure_stage_timing.py` は手動時刻注釈の `speaker="audience", kind="laughter"` とAI発話区間の交差を測る。これは**観客の笑いを収録・識別した実験ではなく、注釈が真実だと仮定したオフライン計算**。笑いの強度や面白さを採点しない。

- `annotated_audience_laughter_events`：観客の笑いとラベルされた入力イベント件数（個人・笑い回数の推定ではない）。
- `ai_laughter_overlap_total_ms`：AI発声と観客笑い注釈の総重複ミリ秒。同じAI区間について重なった複数の笑いラベルは**区間の和集合**で数え、二重計上しない。
- `ai_entries_during_laughter`：**AI発声が始まった時点ですでに観客笑いが進行中**だったAI発話件数。AIの発話途中に笑い始めた場合は重なり量だけ計上し、AIの「発話開始失敗」としない。
- `--max-ai-entry-laughter-ms N`：任意の事前宣言した閾値。AI開始時に既に続いていた笑いとの重複が N ミリ秒を**超えた場合だけ** `ai_enters_active_audience_laughter` のタイミングFAIL。デフォルト未指定なら情報表示のみ。過去録音を見て都合のよい閾値を選ぶと過適合する。
- `--strict`：文字列ゲートとタイミングゲートの両方がPASSの場合のみ終了コード0。これは実機Voiceの音声制御や第三者話者の確実な識別ではない。

再現用合成フィクスチャ（閾値0は境界検査用で**実機の推奨閾値ではない**）：

```bash
python3 comedy/benchmarks/measure_stage_timing.py   --input comedy/benchmarks/runs/2026-11-22-1855-laughter-entry-synthetic.json   --output /tmp/laughter-entry-report.json --max-ai-entry-laughter-ms 0 --strict
# EXPECTED exit=1: AI開始済みの観客笑いに150 ms重なる

python3 comedy/benchmarks/measure_stage_timing.py   --input comedy/benchmarks/runs/2026-11-22-1855-laughter-midline-synthetic.json   --output /tmp/laughter-midline-report.json --max-ai-entry-laughter-ms 0 --strict
# EXPECTED exit=0: AI発声の後で笑い始めたため、総重複300 msだが開始時違反は0
```

`python3 -m unittest discover -s comedy/benchmarks -p 'test_*.py' -q` で合成の境界・ラベル重複・CLI厳格終了コードを含めて回帰テスト。**実際の観客・会場後方音量・ダイスの間は未測定**。詳細は [18:55研究ログ](../research/2026-11-22-1855-jst-laughter-entry-audit.md)。

参考：Pope et al. (2018) [Audience Laughter Distribution in Live Stand-up Comedy](https://www.isca-archive.org/lw_2018/pope18_lw.html)、Zribi et al. (2026) [TIC-TALK](https://aclanthology.org/2026.chum-1.2/)。どちらもこのコントの適切な閾値を確定するものではない。

### 2026-11-22 19:55 JST：観客笑い注釈の連続区間を考慮したAI発話開始監査
measure_stage_timing.py の entry_during_laughter_ms は「AI発話開始時に既に進行中だった笑いの連続区間」がどこまで続くかを計測する。複数の audience/laughter 注釈が重なる、または端点で接する場合は、一つの連続区間にまとめる。AI開始後に別ラベルが始まっても、開始前のラベルと途切れず連結していれば、その継続分を含める。開始後の新しい笑いとの間に隙間がある場合は開始時の違反には含めない。総重複量 overlap_ms は以前と同義。

修正前の合成反例：観客笑いA 3750–3950ms、笑いB 3925–4100ms、AI開始3900ms。総重複200msに対し旧entry継続量50msと過小計算。修正後は200msで、閾値100msの strict 評価は旧0（誤PASS）→新1（FAIL）。Bを3970ms開始（20msの隙間）とする対照例では継続50ms。これは合成注釈の境界検査であり、観客の音声や笑いの強さを測っていない。閾値100msは試験値であり舞台の合否基準ではない。

実行：Python unittest 64件→67件 PASS（新規3件）。新作オリジナル8題（大喜利4・舞台即興4）×2案=16件は形式ゲートPASS。固定ベンチは今回未使用。Voice・観客笑い・金子さんの指摘の改善効果は未測定。[研究ログ](../research/2026-11-22-1955-jst-laughter-continuity.md)。


### 2026-11-22 20:55 JST：終幕合図後のAI音声残留ゲート（合成注釈）

`measure_stage_timing.py` は、台詞が終幕合図の前に**始まっていても**、その録音上の終了時刻がダイスの終幕合図の終了時刻より後なら `ai_audio_after_end_cue` としてFAILにする。従来の `validate_stage_dialogue.py` はイベントの**開始順**しか検査せず、AIが終幕後も300ms話し続けても誤PASSだった。今回のゲートは終幕後の沈黙という明示された演出契約を検査するもので、日常会話の割り込み一般を禁止する閾値ではない。境界がちょうど一致する場合は違反にしない。

出力は `ai_audio_after_end_total_ms`（時間区間の和集合、二重計上しない）と `ai_audio_after_end_event_count`、違反時は `spillover_ms`。時刻注釈から算出した値に限る。音声認識／実機Voice／観客反応は **NOT_MEASURED**。

[研究記録](../research/2026-11-22-2055-jst-post-end-audio.md)／[合成異常例](./runs/2026-11-22-2055-end-spill-synthetic-input.json)／[機械結果](./runs/2026-11-22-2055-end-spill-synthetic-report.json)。新規オリジナル開発8題から16候補を作成、固定ベンチは未使用。

### 2026-11-22 21:55 JST：第二AI声の開始時刻を測る（合成注釈）
- `measure_stage_timing.py` に `second_ai_onset_ms` と任意の `--max-second-ai-onset-ms N` を追加。Daisの開演合図から第2AI発声の開始までを測る。N超過のみタイミングFAIL、境界はPASS。実機の30秒ルールを自動設定しない。
- **初めてのボケまでの時刻の代理指標**であり、病名そのものの発声開始や観客の笑い・理解は未測定。合成の3900msケースで閾値3899 FAIL / 3900 PASSを実行確認。時刻単体テスト33/33 PASS、オリジナル8題×2候補の形式判定16/16 PASS。
- 固定ベンチは未使用、モデル間公平比較・Voice実演・観客笑いは未実測。[研究ログ](../research/2026-11-22-2155-jst-second-ai-onset.md)。


### 2026-11-22 22:55 JST：AI独演の尺（手動タイムコード／任意閾値）
- `measure_stage_timing.py` はすべてのAI音声イベントの `end_ms-start_ms` を `ai_turn_duration_ms` に記録し、最大値を `ai_turn_duration_max_ms` で返す。`--max-ai-turn-duration-ms N` を**明示した場合のみ**、Nを超える各AI発話に `ai_turn_exceeds_duration_target` を記録してstrict FAIL。等号はPASSで、未指定時は報告のみ。値は非負整数のみ。
- 既存の句点数による長話検知の補完であり、「ダイスのリアクション余白を確保できるか」の**計測基盤**。音声に直接効く制御機能ではない。5000ms等は合成テストの閾値であり、実演での適切な基準値は未測定。
- 合成注釈で第3AI発話6000ms：閾値未指定ではtiming PASS、5000ms指定でtiming FAIL（終了コード1）。回帰テスト81/81 PASS、新作オリジナル開発8題×2候補=16の形式検査16/16 PASS。固定ベンチは未使用、Grok/Muse未実行、人間の笑い・Voiceの明瞭度・設定理解は未測定。
- [研究ログ](../research/2026-11-22-2255-jst-ai-turn-budget.md)。外部投稿はOFF。
