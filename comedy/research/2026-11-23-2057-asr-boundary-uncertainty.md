# Comedy AI research: 音声ターン境界の注釈誤差に対する感度監査

2026-11-23 JST / INTERNAL RESEARCH / PUBLISH=OFF / FIXED_BENCHMARK=NOT_USED

## 目的と今回の仮説

『痛い痛い！』で最重要なのはダイスの開始合図を妨げず、電話先のAI救急指令センターとして第一声・第二声を守り、アドリブを具体的な行動につなぎ、相手にリアクションの間を残すこと。金子さんの指摘には電話先AIという正体の明示、客席後方の可聴性、身体演技、偶発的な笑い、再現性が含まれる。

既存のASR注釈の時間監査は、例えば「AIが50ms早く喋り始めた」という**入力注釈が完全に正確であるとの条件下**でFAILにできる。しかし現実の音声注釈には境界誤差がある可能性があり、文字列タイミングのFAILをそのまま実機の確定事実として発信すると過大主張になる。今回は**閾値に依存する結論の感度分析**を追加した。

## 正本と保護

ベースmain: `098ce6666854aae2ff7bfbba3420c61101c088db`（PR作成時の正本）。

読み取った必須資料: `comedy/AGENTS.md` blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`; `skills/comedy-agent/SKILL.md` blob `fe21da855d08d5d01feff89be7244176087d4044`（v0.2.1）; `comedy/COMEDY-AGENT-LOOP.md` blob `a3325b5851155311a09805d443ea352a239347e6`; `comedy/benchmarks/README.md` blob `bc8a938429fb972060091f4897bd32cc744f9034`; `comedy/IMPROV-PLAYBOOK.md` blob `5f494c648ac6a630fe932342b53c575f4349e3db`; `comedy/feedback/KANEKO-2026-11-15.md` blob `6c26deba72a978b29da3cfb1975a96d6993451ca`。

次のファイルは読み取りのみで**編集しない**：長尺v8 `comedy/sagi-injury-help.md` blob `099ab68381e23f838299a9706c64f82bfc2dce1d`; 9月6日確定稿 `comedy/sagi-denwa-2026-09-06-live.md` blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`; 選択中の2分稿 `comedy/sagi-injury-help-2min-live.md` blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`; Comedy Skill本文も無変更。

## 追加した監査器

`comedy/benchmarks/audit_endpoint_uncertainty.py` は既存 `normalize_asr_turns.py` の**JSON評価結果**を受け、既存の `timing_audit.reply_gap_ms` と終幕のAI最終発声を対象に、任意の**仮定上の各時刻端点誤差** `u` ms を指定して評価する。

時刻差を `g = AI開始 - ダイス終了` とすると、独立した二端点がそれぞれ `±u` msずれる仮定では、取り得る区間は `[g-2u, g+2u]`。終幕後残留は `g = ダイス終幕終了 - AI最終発声終了` として同じ判定をする。

- 区間下限が0以上：`ROBUST_NONOVERLAP`（**与えた誤差上限の仮定の中だけ**）
- 区間上限が0未満：`ROBUST_OVERLAP`（同条件）
- それ以外：`BOUNDARY_SENSITIVE`。正確な被りの有無はこの仮定だけでは決まらない
- 終幕合図が欠損／AI発声が欠損：`NOT_ASSESSABLE`

**既存の舞台text/timingハードゲートは一切変更しない。** その独立した判定を `reported_stage_gate_unchanged` に保持。実音声、話者認証、金子さんの設定理解、観客の笑いを成功として報告しない。

## 実際に実行したテストと結果

Mac mini上のPython 3を**ファイル保存せずメモリ内実行**。空き容量不足のため通常の作業ディレクトリ新設は失敗したが、GitHub mainから取得したコードをメモリ内にロードし、保存予定のPython監査器と同じソースを実行した。

- 新規`test_audit_endpoint_uncertainty.py`の**15件の境界条件アサーション：15/15 PASS**。0ms、±50ms、±200ms、±400ms、終幕残留、欠損、負の誤差・真偽値等の異常入力を確認。
- GitHub main由来の既存 `normalize_asr_turns.evaluate` で**合成11断片→7イベント、名目text+timing PASS** を再実行。二つのAI応答の注釈ギャップはともに **+50ms**。
- その同じ結果を新監査器へ渡すと `u=0ms` では`ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES`、`u=100ms`では `BOUNDARY_SENSITIVE`。
- AIの開始をダイスの終了より50ms前にずらした合成負例は既存timingゲートでFAIL。新監査では `u=10ms` で `ROBUST_OVERLAP_PRESENT`、`u=100ms` で `BOUNDARY_SENSITIVE`。
- AIが終幕より50ms長く発話した合成負例も既存timingゲートでFAILし、`u=100ms`では `BOUNDARY_SENSITIVE`。
- 実行結果：[`runs/2026-11-23-2057-boundary-integration.json`](../benchmarks/runs/2026-11-23-2057-boundary-integration.json)。

**u=100msは感度分析に選んだ仮定であり、iPhone・会場・日本語ASRの実測誤差でも推奨安全幅でもない。** どちらの判定も本番の実証ではない。

## 新規大喜利と即興、比較可能性

使用セットは**新規オリジナル内部開発題8題**（一般大喜利4題／電話先AI即興4題）。固定ベンチ **未使用**。8題×2テキスト候補＝16出力をGPT-6製品ラベルの**単一ChatGPTセッション**で作り、既存GitHub mainの `validate_run.py` をPythonメモリ内で本当に実行。形式・文字数・舞台アンカー・禁止語の**16/16 PASS**、各候補グループ欠落0。回答全件・お題・出自情報とスコア根拠をファイルとして保存した。形式が適合したことは**面白いと判定されたことではない**。

- [8題全文](../benchmarks/runs/2026-11-23-2057-original-tasks.jsonl)
- [16回答全文とモデル出自](../benchmarks/runs/2026-11-23-2057-chat-responses.jsonl)
- [実行済みハードゲートの要約](../benchmarks/runs/2026-11-23-2057-validation-summary.json)

正確なGPT-6ビルド、API実行レシート、temperature、effortは取得できない。Grok・MuseはReason Networkの**3接続すべてHTTP 409 `agent_network_offline`**で未実行、独立同条件モデル比較は **`NOT_COMPARABLE`**。本番Voice・後方可聴性・客席の電話先AI認識・身体演技・観客の笑いは **`NOT_MEASURED`**。

## 先行知見との区別

Kelterer & Schuppler (2025) は発話単位と完了可能位置を区別した会話注釈を提案（https://arxiv.org/abs/2504.09980）。He et al. (2026-10-02) は自動的な会話ターン抽出の開始/終了境界に誤差があることを報告（https://arxiv.org/abs/2610.03078）。それぞれ本実験の研究設計に参考になるが、研究対象が異なるためその数値を本番の誤差上限に流用しない。

## 次の実測準備とセーフティ

録音条件を固定してiPhone/Voiceの音声を取得できた場合に限り、独立アノテータの境界差から実測誤差分布を求め、想定したuを再検討する。ダイスの「痛い！」開始合図後の厳密な第一声・第二声、電話先AIという設定、既出人物の行動の具体的回収、ツッコミへの間、終幕無音、観客/スタッフの声への誤反応を**個別に**記録する。実録音声ゼロならすべて未測定のままとする。

外部X投稿・自動リプ・大喜利サイト応募・第三者規約外アクセス：**ゼロ**。専用アカウント・適法な使用権限・プラットフォーム規約が未確認のため`publish=false`、`DRAFT_ONLY`を保持する。
