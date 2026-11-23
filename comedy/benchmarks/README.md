# COMEDY BENCHMARK v1 — 4つの違う能力を混同しない

## 2026-11-24 01:00 JST：独立モデルの比較資格を保守的に監査
- 新規 `audit_run_comparability.py` は共通タスク・各候補・Skill blob SHA・モデル版・モダリティ・推論設定・独立APIレシートの申告を検査。レシートの実在性はオフラインでは未検証なので、条件を満たす人工正例でも `CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED` に留める。
- 新規回帰12/12 PASS、Python全309/309 PASS。固定ベンチは使用せず、新作オリジナル開発8題×2回答の静的形式16/16 PASS。
- 実際の独立モデル比較は `NOT_COMPARABLE`。ChatGPT GPT-6製品ラベルのみ・正確なbuild不明・外部APIレシートなし。Reason Network 3接続HTTP409でGrok/Muse未実行。Voice・笑い・後方可聴性・金子さん指摘の役割理解は `NOT_MEASURED`。外部publish・自動返信はOFF。
- [研究全文](../research/2026-11-24-0100-jst-comparison-eligibility.md) / [オリジナル題](./runs/2026-11-24-0055-original-tasks.jsonl) / [回答全文](./runs/2026-11-24-0055-chat-responses.jsonl) / [比較資格監査](./runs/2026-11-24-0055-comparability.json)。

## 2026-11-23 23:57 JST：有効な無音WAVを「発話した稽古」と誤認しない
- `audit_voice_wav_evidence.py` はWAVバイト整合性と、`claimed_real_rehearsal` が会話を含む証拠として使えるかを別ゲートに分離。有効な**完全無音WAV**は `wav_byte_integrity=PASS` だが `claimed_rehearsal_audio_evidence=FAIL` としてCLI終了1。非ゼロ波形は `NEEDS_SPEECH_VERIFICATION` であり話し声を証明しない。新たにPCM非ゼロサンプル割合を診断値として記録。
- 新規7テストは旧mainで1 FAIL/6 ERROR、修正後は既存17件を含め **24/24 PASS**。合成WAVのみ。金子さんの指摘した電話先AIの設定理解、客席後方の可聴性、ダイスの演技、観客の笑い、Voice実機再現率は **NOT_MEASURED**。
- 新規オリジナル開発8題（一般4、舞台4）×2候補＝16回答の文字列ハードゲート **16/16 PASS**。固定ベンチ未使用。単一GPT-6チャット内テキストのみで独立モデル間比較 **NOT_COMPARABLE**。Grok/MuseはReason Network接続HTTP409で未実行。外部publish・自動返信OFF。
- [研究報告](../research/2026-11-23-2357-jst-silent-voice-evidence.md) / [合成試験・出自結果](./runs/2026-11-23-2357-silence-evidence-evaluation.json) / [オリジナル16候補](./runs/2026-11-23-2357-chat-responses.jsonl)。

## 2026-11-23 22:55 JST：RIFFヘッダ差し替えによる同一PCM再利用の検出
- `audit_voice_wav_evidence.py` は既存のファイル全体SHA-256に加え、読み出したPCMの逐次SHA-256を比較する。同じサンプル列を異なる合法WAVヘッダに格納しても、二つの独立試行として誤受理しない。
- 同条件の新規5テストで旧版 **1 PASS / 2 FAIL / 2 ERROR**、修正版では既存12件を含め **17/17 PASS**。合成WAVだけの監査。実機Voiceの再現性・笑い・客席後方での聞き取りは **NOT_MEASURED**。
- 新規オリジナル開発8題（一般4/舞台4）×2案＝16テキストの形式16/16 PASS。固定ベンチ未使用。単一ChatGPTチャットのみで正確なモデルビルド不明。Grok/Muse未実行、独立比較`NOT_COMPARABLE`。publish/auto-replyはOFF。
- [研究記録](../research/2026-11-23-2255-jst-pcm-fingerprint.md) / [合成回帰](./runs/2026-11-23-2255-pcm-regression.json) / [回答全文](./runs/2026-11-23-2255-chat-responses.jsonl)。


## 2026-11-23 20:57 JST：音声発話境界の注釈誤差に対する感度監査

- 新規 `audit_endpoint_uncertainty.py` は `normalize_asr_turns.py` の既存JSON評価結果を入力し、**仮定上の各時刻端点誤差±u ms**に対して、発話被りと終幕後残留の判定が頑健かを分析する。元の舞台ハードゲートは変更しない。**u=100msは実機の誤差実測ではない**。
- Python回帰アサーション15/15 PASS。main由来の既存合成ASR 11断片→7イベントの+50ms応答は、誤差ゼロ仮定なら非重複、各端点±100ms仮定なら `BOUNDARY_SENSITIVE`。50ms早い発声も±100ms仮定では被りを断定できない。
- **新規オリジナル開発8題**（一般4/舞台4）×2テキスト候補の既存 `validate_run.py` ハードゲート16/16 PASS。固定ベンチ未使用、GPT-6チャット内生成のみ。Grok/Museは接続HTTP409で未実行、モデル間比較`NOT_COMPARABLE`。実機音声・観客笑い・後方可聴性は`NOT_MEASURED`、外部publishはOFF。
- [研究報告](../research/2026-11-23-2057-asr-boundary-uncertainty.md) / [合成注釈統合実測](./runs/2026-11-23-2057-boundary-integration.json) / [16回答原文](./runs/2026-11-23-2057-chat-responses.jsonl)。


## 2026-11-23 18:55 JST：ASR復元後に隠れた時間的舞台違反を検出
- `normalize_asr_turns.evaluate` は従来の文字列ゲートに加え、復元後の手動時刻注釈を `measure_stage_timing.measure` で監査。台本第一声が完全一致しても、ダイスの合図終了前のAI発話開始、終幕後まで続くAI音声なら総合FAIL。`stage_gate` と `timing_gate` を分離して記録。
- 合成の2負例：旧テキストゲート誤PASS → 新時間ゲートFAIL（開演の50ms被り／終幕後50ms残留）。通常の11断片→7イベントと境界一致の正例はPASS。**実音声ではなく人工タイムコード**。
- Python全回帰テスト **267/267 PASS（新規4件）**、現行2分稿の静的検査PASS（22発話・714文字）。**固定ベンチ未使用**、新作オリジナル8題（一般4・電話先AI4）×2案、形式 **16/16 PASS**。GPT-6製品ラベルのチャット内生成だけ、Grok/MuseはReason Network 409で未実行、複数モデル比較 `NOT_COMPARABLE`。Voice・観客の笑い・後方可聴性・金子さんの設定理解率は `NOT_MEASURED`。外部投稿・自動返信OFF。
- [研究報告](../research/2026-11-23-1855-jst-asr-timing-composite.md)、[旧→新の合成監査](./runs/2026-11-23-1855-asr-timing-regression.json)。

## 2026-11-23 18:02 JST：ASRチャンク分割を舞台の誤FAILにしないターン復元
- 新規 `normalize_asr_turns.py` は、明示的な `turn_id`・話者・時間境界が一致する連続断片だけを連結する。観客やスタッフの発言を跨ぐ結合、話者混同、曖昧な時間差は拒否。既存の `validate_stage_dialogue` に完全発話を渡して開始合図・第一/第二声・アドリブの反応機会・終幕を判定。
- **合成11断片 → 7イベント（4連結）で静的舞台ゲートPASS**。原断片を直接渡した場合はFAIL。別の脚本改変・第三者発話の人工負例は正しくFAILまたは入力エラー。新規17件を含め **Python 263/263 PASS**（ローカルのGitHub main由来ソースで実行）。音声録音・ASR品質の実測ではない。
- 固定ベンチ**未使用**、新規オリジナル8題（一般4、舞台4）×各2候補をチャット内で生成、形式**16/16 PASS**。ChatGPT GPT-6製品ラベルのみ、正確なモデルビルド・独立APIレシートは未取得。Reason Network 3接続HTTP 409によりGrok/Muse未実行、比較は `NOT_COMPARABLE`。
- 電話先AIの観客理解・後方可聴性・実機Voice・観客の笑いは `NOT_MEASURED`。v8、9/6確定稿、選択中2分稿、Skill本文は無変更。publish/auto-replyはOFF。
- [研究報告](../research/2026-11-23-1755-jst-asr-turn-boundaries.md) / [新規17テスト](./test_normalize_asr_turns.py) / [合成実行結果](./runs/2026-11-23-1755-asr-normalization-report.json)。


## 2026-11-23 17:04 JST：長い一文でダイスの反応時間を奪うリスクの静的検査
- `validate_stage_dialogue.validate` に任意の `max_ai_turn_chars` を追加。総合舞台監査では冒頭の固定2声を除くAI発話を**96文字以下**で保守的に検査。句点1つの122文字という従来PASSした人工発話を `ai_turn_exceeds_char_budget_proxy` でFAIL。
- **Python 100/100 PASS**（新規6、既存94）、現行2分稿の静的検査PASS（22発話、714文字、AI最大68文字）。新規**独自内部開発8題×2案=16テキスト**の形式検査16/16 PASS。固定ベンチ未使用。
- ChatGPT GPT-6製品ラベルのチャット内案のみ。Grok/MuseはReason Network 409で未実行、比較 `NOT_COMPARABLE`。**音声秒数・笑い・電話先AI設定認識・後方可聴性は未測定**。96文字は発話時間の代替ではない。外部publishはOFF。
- [研究報告](../research/2026-11-23-1657-jst-human-reply-budget.md) / [モデル接続出自](./runs/2026-11-23-1657-provenance.json)。



## 2026-11-23 16:00 JST：舞台の個別評価をAND合成する総合静的ゲート
- New `audit_stage_composite.py` は既存の `validate_stage_dialogue`（ダイス合図・第一/第二声・第三者・終幕）、`audit_callback_continuity`（仕込み→リアクション→回収）、注釈ありの場合 `audit_adlib_anchors`（直前の行動回収）を全て実行する。**どれかがFAILなら総合FAIL**。アドリブ未注釈は `NOT_REQUESTED` と区別。
- 新規テスト13件＋既存45件＝**58/58 PASS**。合成の正例/負例**8/8期待判定一致**。新規**オリジナル開発題8題×2テキスト候補**の形式検査**16/16 PASS**。固定ベンチは未使用。
- ChatGPT GPT-6製品ラベルの単一チャット内生成だけで、独立モデル比較 `NOT_COMPARABLE`。Reason Networkの3接続はHTTP409、Grok/Museは未実行。**Voice・金子さん指摘の観客理解・後方可聴性・身体演技・笑いは未測定**。
- [研究報告](../research/2026-11-23-1600-jst-composite-stage-gate.md)、[合成結果](./runs/2026-11-23-1600-composite-report.json)。台本v8・9/6確定稿・2分稿・Skill本文は変更せず、外部投稿・自動返信はOFF。

## 2026-11-23 14:55 JST：仕込み→ダイスのリアクション→後半回収の複数ターン監査

- 新規 `audit_callback_continuity.py`: 人手注釈の完全発話列に限定し、同一人物の前振り／後半の展開／間にダイス発話があるか／事前指定の矛盾文字列／開始・終幕の逸脱を検査。**実際の間の秒数や意味理解は評価しない**。
- Python新規**19/19 PASS**、既存アドリブ検査**26/26 PASS**、人工8ケースの期待判定**8/8一致**（正例2・負例6）。初回人工入力は笑いをダイスの台詞と置換したため7/8、入力訂正後8/8。
- **オリジナル内部開発題8題**×2案=16テキスト、固定ベンチ未使用。形式検査**16/16 PASS**。GPT-6製品ラベルで同一チャット内生成のみ、比較は**NOT_COMPARABLE**。Grok/Muse未実行、Voice・観客の笑い・客席後方可聴性は**NOT_MEASURED**。
- [研究報告](../research/2026-11-23-1455-jst-multi-turn-callback-continuity.md)。台本v8・9/6確定稿・2分稿・Skill本文は不変。外部投稿・返信・応募OFF。


## 2026-11-23 13:55 JST：アドリブ回収の「質問・提案・依頼＝実行済み」誤PASS回帰

- `audit_adlib_anchors.py` の新しい `uncommitted_action_mentions` は「会田へ連絡しましたか？」「連絡しましょうか？」「連絡してください」「連絡する予定です」など**限定された文字列パターン**を実行済み行動と区別する。独立した肯定的な「手配しました」があれば維持。意味理解・行動実行の証明ではない。
- Python単体テスト**修正前26件中7件FAIL→修正後26/26 PASS**（既存18、新規8）。人工舞台8ケースで期待判定8/8。**新規オリジナル開発題8題・テキスト16候補**の形式ゲート16/16 PASS、固定ベンチ未使用。
- ChatGPT GPT-6製品ラベルの単一チャット内作成のみ。Grok/MuseはReason Network HTTP 409で未実行、比較 `NOT_COMPARABLE`。実機Voice・観客笑い・客席後方可聴性・金子さん指摘の実測効果は**NOT_MEASURED**。
- [研究ログ](../research/2026-11-23-1355-jst-uncommitted-action-uptake.md)。外部投稿・自動返信OFF。

## 2026-11-23 12:55 JST：アドリブ回収の「否定された行動」誤PASS回帰

- `audit_adlib_anchors.py` が「会田アイタロウへ**連絡しません**」を「会田」＋「連絡」の文字一致だけでPASSした誤判定を修正。動作語直後の限定的な否定形を `negated_action_mentions` として分け、否定だけなら `immediate_reply_only_negated_action` でFAIL。別の肯定行動がある場合は除外しない。
- 事前追加した新規4件によって**修正前15/18（3 FAIL）→修正後18/18 PASS**。既存舞台対話6件を含む24/24 PythonテストPASS。新規**オリジナル開発題8題**×2案（固定ベンチ不使用）の形式検査16/16 PASS。人工舞台会話12ケースの期待判定12/12一致、舞台対話静的検査12/12 PASS。
- ChatGPT GPT-6製品ラベルの単一チャット内生成のみ。モデル比較 `NOT_COMPARABLE`、Grok/MuseはReason Network 3接続すべて409。これは否定語の**字面の検査**であり意味理解・面白さ・実機Voiceの測定ではない。笑い・声・客席後方の明瞭さ・金子さんの設定理解率は `NOT_MEASURED`。
- [研究報告](../research/2026-11-23-1255-jst-negated-action.md)、[合成監査](./runs/2026-11-23-1255-negation-anchor-audit.json)、[16候補全文](./runs/2026-11-23-1255-negation-responses.jsonl)。X・外部応募・自動返信はOFF。


## 2026-11-23 11:57 JST：即興回収の「単語＋行動」オプトイン監査

- New `audit_adlib_anchors.py`: ダイスの**完全なアドリブ発話**に事前注釈した `anchor_any` と `action_any` を、次のダイス発話前の**最初の非空AI回答**で照合。単なる返答の有無だけでは見逃す「人物名は出したが何も進めない」ケースを静的なレビュー対象にする。注釈が0件ならFAIL。
- GitHub main由来の既存舞台対話28テストと新規14テスト、計**42/42 PASS**。**新作オリジナル開発8題**（固定ベンチ不使用）×2チャット内テキスト候補は既存形式**16/16 PASS**。舞台4題×2回答を合成会話に組み込んだ文字列回収代理指標は**7/8 PASS・1/8 FAIL**（`st02-2`の行動語不足）。合成の期待判定は8/8一致。
- これは人手注釈語に依存する**文字列マッチ**。意味理解、観客の笑い、実機Voice、設定理解、後方音量は**NOT_MEASURED**。モデル比較は`NOT_COMPARABLE`（単一ChatGPT製品ラベル GPT-6、Grok/MuseはReason Network 409）。
- [研究ログ](../research/2026-11-23-1157-jst-immediate-adlib-anchors.md)。X投稿・外部応募・無差別自動返信はOFF。


## 2026-11-23 10:56 JST：ダイスの一手を取りこぼさない厳格テキスト監査

- `validate_stage_dialogue.py --require-turn-coverage` は**任意の厳格モード**。完全発話単位に注釈したダイスの一手へAIが返さず次のダイスの発話／終幕へ進んだ場合を検知する。ASRの分割チャンクには使用しない。既定動作は保持。
- 旧ソースで見逃した合成ケースが新モードでは `unanswered_dais_turn` FAILに。既存22件＋新規6件の単体テスト**28/28 PASS**（Mac miniのPython上でGitHubソースをインメモリ実行）。本物の音声による未回収率や笑いの改善を意味しない。
- **オリジナル開発題**8題 ×2案、ChatGPT GPT-6の単一チャット内の16テキストを既存`validate_run.score`で**16/16形式PASS**。固定ベンチ未使用。モデル比較監査は`NOT_COMPARABLE`。Grok/MuseはReason Network 409で未実行、Voice・観客笑いは未測定。
- [研究報告](../research/2026-11-23-1056-jst-turn-uptake.md)。X投稿／外部自動返信はOFF。

Canonical: 2026-11-22。Skill正本：[`skills/comedy-agent/SKILL.md`](../../skills/comedy-agent/SKILL.md)。
目的：**既存ベンチで外部モデル比較しつつ、独自の日本語・音声・舞台能力を再現可能に検証する**。点数の出ていないものはNOT_MEASUREDで保存。実行前にライセンスと同意・利用規約を確認。

## 2026-11-23 09:55 JST：盲検A/B回答の「票の真正性」監査

- New: audit_blind_ballots.py and test_audit_blind_ballots.py. Offline A/B packet results are **NOT automatically human judgments**. Audits mirrored A/B text, packet SHA-256, pseudonymous reviewer, one review variant per reviewer, duplicate votes, missing/invalid votes, and publication OFF.
- New **original development prompts**, not the fixed benchmark: 8 tasks (4 oogiri, 4 telephone-dispatcher improv), 2 GPT-6-chat text candidates each; existing format gate **16/16 PASS**. New integrity unittest **14/14 PASS**. 8 reversed-order packets, 16 deliberately **synthetic** ballot fixtures, **zero human** ballots. Human laughter and Voice are **NOT_MEASURED**.
- Provenance comparison remains **NOT_COMPARABLE**; one chat product label is not a multi-model API run. Models Grok and Muse were not run. No external posts or automated replies.
- Run: python3 comedy/benchmarks/audit_blind_ballots.py --packets comedy/benchmarks/runs/2026-11-23-0955-packets.json --ballots comedy/benchmarks/runs/2026-11-23-0955-empty-ballots.jsonl --output /tmp/comedy-ballots-audit.json
- [Research report](../research/2026-11-23-0955-jst-blind-ballot-integrity.md). Both selected and protected historic stage scripts were left untouched.

## 2026-11-23 08:53 JST：大喜利・電話先AI即興のA/B順序バイアスを制御する内部レビュー準備

- 新しい `prepare_blind_pairs.py` は**オリジナル開発題のみ**（固定ベンチではない）の2候補について、問題の表示順を決定論的にシャッフルし、候補1/2がA欄へ表示される回数を均衡化する。反対順の`v1`/`v2`を作るが、同じ評価者に両方を見せない。
- 13件のPythonテスト**13/13 PASS**、新作8題×2回答の既存文字・禁止表現ゲート**16/16 PASS**、両バリアントのA欄が4/4で均衡。**人間評価0件、笑い`NOT_MEASURED`**。出自監査`NOT_COMPARABLE`（GPT-6ラベルの同一チャットのみ、独立APIレシートなし、Grok/Muse未実行）。
- 実行例：`python3 comedy/benchmarks/prepare_blind_pairs.py --tasks comedy/benchmarks/runs/2026-11-23-0853-blind-pair-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-23-0853-blind-pair-responses.jsonl --output /tmp/comedy-blind-packets.json --seed comedy-20261123-0853`。
- パケットはモデル名・run_idを表示しないが、生回答が同じ公開リポジトリにあるため、アクセスできる人への**完全な盲検化ではない**。未実測のVoice・会場後方の聞こえ方・電話先AIの理解度・ダイスの演技効果をPASSと解釈しない。
- [研究記録](../research/2026-11-23-0853-jst-counterbalanced-human-review.md)。外部投稿・自動返信はOFF。

## 2026-11-23 07:55 JST：録音IDの重複を「別々の稽古」と誤集計しない

- `audit_stage_repeatability.py` に `recording_ref` の再使用検出と、任意の `recording_sha256`（64桁の16進数）の再使用検出を追加。別の`run_id`でも同じ録音参照なら `NOT_COMPARABLE` とし、台詞のPASS/FAILと録音の出自不備を別欄で示す。
- 合成メタデータの負例では台詞ゲート2/2 PASSでも、重複録音参照で比較は `NOT_COMPARABLE`、厳格CLIは期待どおり終了1。正例の異なる架空IDでは `SAME_DECLARED_CONDITIONS_ONLY`、ただし**音声・実録の真正性や独立性は未確認**。Python単体テスト19/19 PASS（新規5件）。
- 新規**オリジナル開発題**8件（固定ベンチではない）×2テキスト回答。文字・設定のハードゲート **15/16 PASS、1/16 FAIL**（`st03`の1案で必須の「絹ごし3号」を欠落、元出力を保存）。モデル間出自監査は `NOT_COMPARABLE`。GPT-6製品ラベルの同一チャット内のみ、Grok・Muse未実行。観客笑いと実機Voiceは未測定。
- [研究報告](../research/2026-11-23-0755-jst-recording-uniqueness.md)。外部投稿・自動返信OFF。

## 2026-11-23 07:00 JST：同一条件の稽古反復を監査する（合成のみ実行）

- 新規 `audit_stage_repeatability.py` は、`validate_stage_dialogue.validate` を各回の**時刻なし注釈テキスト**に適用し、同一条件を申告した複数回のPASS/FAILを集約する。主目的はモデル版、Skill / 台本 Git blob SHA、入力・音声プロファイル、データ出自が異なる回を**一つの再現率に混ぜない**こと。1回だけでは反復比較を成立させない。
- `source_type=synthetic` はテスト用の人工会話で、どの実モデルの発話とも扱わない。`audio_annotated` では録音参照と注釈者IDを必須にするが、**コードは録音を開かず照合しない**。宣言値を検査するだけなので、録音された本人・音量・笑い・観客が「電話先AI」と理解した割合・実機音声の再現性は未検証として返す。
- 合成fixture `runs/2026-11-23-0700-stage-repeatability-synthetic.json` の4回では2件PASS、正しい第一声に余計な問診を足した1件と、第三者音声が介在した1件をFAILと検出。これは**意図して作った正負の入力**であり、Voice合格率50%などと解釈しない。厳格モードは期待どおり終了コード1。
- 新規14件と既存舞台対話22件の単体テストは36/36 PASS。同回の**新しいオリジナル開発題8件（固定ベンチではない）×2案=16テキスト**の形式ゲートは16/16 PASS。ChatGPT製品ラベル GPT-6 の同一チャット内案だけで、独立API実行やGrok・Muse比較はない。
- 実行：`python3 comedy/benchmarks/audit_stage_repeatability.py --input comedy/benchmarks/runs/2026-11-23-0700-stage-repeatability-synthetic.json --output /tmp/repeatability-report.json`。根拠：[研究ノート](../research/2026-11-23-0700-jst-repeatability-provenance.md)、[実行済みレポート](./runs/2026-11-23-0700-repeatability-report.json)。外部投稿OFF。

## 2026-11-23 05:55 JST：2分舞台の第一声・第二声を「完全一致」で検査

- 既存の `expected_prefix` は先頭一致のみで、正しい第一声の後ろに「住所を教えてください」を付け足す誤答でもPASSし得る。**完全固定の舞台発話**だけに `expected_exact`（任意フィールド）を指定し、余計な語・途中切断・語尾違いも `script_exact_response_mismatch` とする。旧タスクは従来どおり先頭一致を維持。
- 新規の**舞台回帰セット** `injury-stage-exact-2026-11-23.jsonl` は第一声完全一致・第二声完全一致・観客だけが叫んだ場合の沈黙の3件。これらは**新規大喜利題ではない**。固定15題 `taskset-v1.jsonl`、既存9題の2026-11-22回帰セット、長尺v8と9/6確定稿は変更していない。
- 検証：`python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/injury-stage-exact-2026-11-23.jsonl --responses comedy/benchmarks/runs/2026-11-23-0555-exact-positive-synthetic.jsonl --output /tmp/exact-positive-report.json --strict` は3/3 PASS。negative fixtureでは3/3の**期待どおりのFAIL**、終了コード1。合成テキストによる実装検査であり、実際のVoice音声がその台詞を話した証拠ではない。
- 同日の**新規オリジナル開発題**8題×2候補=16テキストは別ファイル `runs/2026-11-23-0555-tasks.jsonl`、`runs/2026-11-23-0555-responses.jsonl` に保存。形式16/16 PASS、モデル比較 `NOT_COMPARABLE`、観客の笑い・声の再現性 `NOT_MEASURED`。外部投稿OFF。
- [実行結果と限界](../research/2026-11-23-0555-jst-exact-stage-utterance.md)。

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


### 2026-11-22 23:57 JST：AI累積発声占有率の任意ゲート（合成時刻のみ）
- `measure_stage_timing.py` で **AI+Daisの発声時間に占めるAI割合**を報告する。Stage start/end内に区間をクリップし、同じ話者の重複ラベルをマージしてから計算する。観客の笑い・無声の身体演技・沈黙は分母に含めない。
- 新オプション `--max-ai-talk-share-percent 0..100` は指定時だけ厳格ゲートに追加する。未指定は従来互換。数値の合否に丸め誤差を使わない。欠損・分母0はnullで示す。**60%などの値は舞台の確定推奨値ではない。**
- 合成テスト：AI 6100ms、ダイス3400ms → AI 64.211%。単発最大4000msは5000ms上限内だが、累積64%上限ならFAIL・65%ならPASS。Python単体テスト **43/43 PASS**、新規8題×2テキスト候補のハードゲート **16/16 PASS**。これは**声や笑いの実測ではない**。
- 研究記録：[23:57 JST AI talk share](../research/2026-11-22-2357-jst-ai-talk-share.md)。GPT-6はチャット内候補生成のみ、Grok/Muse未実行、固定ベンチ未使用。

### 2026-11-23 00:51 JST：ダイスの再発話までの時間を報告（合成注釈）

`measure_stage_timing.py`で、AI発話終了から次のダイスの**通常の音声発話開始**までの時間 `dais_reentry_gap_ms` と中央値 `dais_reentry_gap_median_ms` を報告する。負値は被り。開演・終幕の合図は集計せず、笑い声もダイスの発話として扱わない。これは身体演技の量や観客の笑いを示す値ではない。任意オプション `--min-dais-reentry-gap-ms N` は**明示された稽古ターゲットがある場合のみ**最小閾値を強制する（NぴったりはPASS、未指定は報告のみ）。舞台に普遍的な100msの「正解」を適用しない。

合成データで100ms・200ms、中央値150ms。最小100msはPASS、101msはFAIL／strict終了コード1を実行確認。単体テスト50/50、対話テスト22/22、2分台本静的チェックPASS。新規オリジナル開発8題からテキスト16回答・形式16/16 PASS、**固定ベンチ未使用**。Grok/Muse未実行、Voice・笑い・身体演技は未計測。詳細：[2026-11-23 00:51 ダイス再発話の間](../research/2026-11-23-0051-jst-dais-reentry-gap.md)。外部投稿はOFF。

### 2026-11-23 01:55 JST：終幕後の稽古講評をダイス再発話の「舞台の間」から除外
- `measure_stage_timing.py` の `dais_reentry_gap_ms` は「舞台中のAIボケ→ダイスの次の**通常発話**」の間を表すが、以前は終幕合図の後にダイスが稽古講評を話した場合まで集計し、余分な区間と任意の閾値違反を作っていた。
- `active`（開演合図から終幕合図まで）で再発話検出を限定。終幕後の講評は**舞台指標から除外**し、終幕後のAI音声残留の別ハードゲートは維持。生音声、身体演技、客席の笑いは依然として未測定。
- **赤→緑の実行テスト**：新規3件追加直後、53件中3件FAIL（終幕後の講評を3番目の再発話として誤算入）。修正後53/53 PASS、対話検査22/22 PASS、2分稿静的検査PASS。合成入力の再発話の間は100ms・200ms／中央値150msでPASS。これは人工注釈のコード検証であり実機Voiceの性能ではない。
- **新規オリジナル開発題**8題・16案、`validate_run.py --strict`で16/16形式PASS。固定ベンチ未使用。ChatGPTの単一チャット内で作成し、独立API反復ではない。Grok/Muse未実行、Reason Network接続はリンク未認証。観客笑い・Voice再現性・モデル間優劣は未測定。
- [今回の研究ログ](../research/2026-11-23-0155-jst-post-end-debrief.md)。外部投稿と自動返信はOFF。


### 2026-11-23 02:55 JST：モデル比較の出自監査（今回の新規実装）
- `audit_comparison_provenance.py` は、回答のモデル版、Skill commit/blob SHA、タスク×試行番号のカバレッジ、生成条件、呼び出し種別、証跡フィールドをチェックする。**面白さ、モデル実行の真正性、提供元レシートの真正性は検証しない。**
- 同じチャットで作った2案を独立API実行やGrok/Muse比較と誤認しないため、`invocation_source=chat_session`、未制御の生成条件、プロバイダ実行レシート不在は `comparison_setup=NOT_COMPARABLE` を返す。`COMPARISON_INPUTS_AUDITED` はメタデータ上の整合性だけを意味し、勝敗や本物のAPI実行の保証ではない。
- 実行コマンド：`python3 comedy/benchmarks/audit_comparison_provenance.py --tasks <tasks.jsonl> --responses <responses.jsonl> --output <audit.json>`。比較可能性の判定を形式チェック `validate_run.py` と別に実行する。
- 新しいオリジナル開発題8件（大喜利4、電話先AI即興4）×2案=16回答について、形式検査16/16 PASS、出自監査は **NOT_COMPARABLE**。新規ユニットテスト10/10 PASS。固定ベンチ未使用。実機Voiceと観客笑いは未測定。
- [出自監査レポート](./runs/2026-11-23-0255-provenance-audit.json)、[今回の研究記録](../research/2026-11-23-0255-jst-provenance-audit.md)。X投稿・第三者サイトへの自動投稿はOFF。

### 2026-11-23 03:52 JST：比較出自監査の欠測対称性バグ修正
- `audit_comparison_provenance.py` は、モデル間の`(task_id, sample_index)`の集合一致だけでなく、**各モデル内で全タスクの試行数が同数か**と、**試行番号が1から連続しているか**も監査する。両モデルが同じ試行を欠測すると従来の集合一致だけでは見落とした。
- `temperature` の真偽値・非数値、`max_output_tokens=0` のような無効な生成設定は `invalid_generation_setting` として検出する。ただし検査はメタデータの自己申告だけで、実際のモデル版やAPIレシートの真正性を保証しない。
- 合成の4負例で**修正前14件中4件FAIL、修正後14/14 PASS**。新規オリジナル開発8題×2案=16件の形式検査16/16 PASS、比較出自は**NOT_COMPARABLE**。今回の固定ベンチは未使用、Grok/Muse未実行、実録Voice・観客笑いは未測定。
- [研究報告](../research/2026-11-23-0352-jst-provenance-sample-integrity.md)、[形式結果](./runs/2026-11-23-0352-format-report.json)、[出自監査結果](./runs/2026-11-23-0352-provenance-report.json)。外部への自動投稿・返信はOFF。

### 2026-11-23 04:55 JST：出自監査の空回答・沈黙課題ゲート
- `audit_comparison_provenance.py` はタスクの `kind` を読み、`silence` に発話がある場合 `unexpected_silence_response`、それ以外に空白だけの回答がある場合 `empty_non_silence_response` を記録し、`NOT_COMPARABLE` とする。舞台前の第三者への沈黙と、実際の応答取得を区別するための比較入力監査で、音声認識や面白さを判定するものではない。
- 合成メタデータ18テストは修正前15/18（新規3 FAIL）→修正後18/18 PASS。新規4件のうち沈黙正解の正常系も検証した。
- 新規オリジナル開発8題（大喜利4、電話先AIアドリブ4）×2案=16テキスト候補：形式ゲート16/16 PASS、出自監査 `NOT_COMPARABLE`、文字3-gram監査は過去16回答に対し要確認フラグ0。固定ベンチ未使用。
- ChatGPT GPT-6のチャット内生成のみ。Grok/MuseはReason Networkの3接続が409 `agent_network_offline`、独立API比較は未実施。実録Voice・客席笑い・金子さんの導入効果は未測定。外部投稿 `publish_enabled=false`、自動返信 `auto_reply_enabled=false`。
- [今回の研究ログ](../research/2026-11-23-0455-jst-silence-provenance.md) と [監査結果](./runs/2026-11-23-0455-provenance-report.json)。

### 2026-11-23 20:00 JST：ASR断片の0ms音声・同一話者の異ID時間重複を入力拒否

- `normalize_asr_turns.py` は同一の`turn_id`を結合する際のギャップ検査に加え、文字のあるダイス／AI断片で `end_ms == start_ms` を拒否。同じ話者の別`turn_id`の時間重複も拒否する。ターン境界の接触は許容し、**ダイスとAIの別話者間のかぶりは従来どおり時間監査へ渡す**。
- 新規6テスト：修正前は4件FAIL、修正後は全Python **273/273 PASS**。旧・新に同じ合成7ケースを実行し、旧版で総合PASSの不正注釈3件を新版が入力拒否。入力拒否と、正規化された舞台対話のFAILは別。
- 新規オリジナル開発8題×2=16テキスト回答は形式16/16 PASS。**固定ベンチ未使用**。Grok/MuseのReason Network接続3件は409、`NOT_RUN`。ChatGPT GPT-6は単一チャット内生成のみで`NOT_COMPARABLE`。実機Voice・観客の笑い・後方可聴性は`NOT_MEASURED`。
- [研究記録](../research/2026-11-23-2000-jst-asr-annotation-integrity.md) と [旧新版の合成監査](./runs/2026-11-23-2000-asr-annotation-regression.json)。外部投稿／返信はOFF。
