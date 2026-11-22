# Comedy AI内部研究：反復ボケの準重複監査（2026-11-23 04:02 JST）

## 結果の要約
- **研究種別**：新規オリジナル開発題。固定ベンチの実行とは区別する。
- **起点正本**：GitHub `Daisuke134/anicca` `main` commit `095035d7ea0fac0573103a69224ebfb26a5506a8`。
- **専用ブランチ**：`comedy/response-repetition-audit-20261123-0402`。
- **参照した正本**：`comedy/AGENTS.md`, `skills/comedy-agent/SKILL.md`, `comedy/COMEDY-AGENT-LOOP.md`, `comedy/benchmarks/README.md`, `comedy/IMPROV-PLAYBOOK.md`, `comedy/feedback/KANEKO-2026-11-15.md`。追加で台本静的検査、直近2回の回答JSONLを確認。
- **仮説**：同じ車両・人物を毎回使うことはコールバックとして有用だが、語彙の繰り返しで回答が定型化すると、短い形式ゲートを通過するだけでは劣化を見逃す。元の舞台台本を変更せず、テキスト準重複だけを客観的に検査する。

## 作成したもの
1. `comedy/benchmarks/audit_response_repetition.py`：日本語をNFKC正規化し空白・記号・句読点を除去、文字3-gram集合のJaccard係数で同一実行内・過去実行との高類似対を抽出。デフォルト閾値0.70は**編集上の要確認フラグ**であり笑い・新規性の合格基準ではない。入力ハッシュ、過去ファイルのハッシュ、最大類似度、フラグ対をJSONに保存。ネット通信なし。語義上の類似や転用を検知しない。
2. `comedy/benchmarks/test_audit_response_repetition.py`：合成入力で正規化、記号差だけの重複、実行内重複、異なる短文、人物名だけの共通、閾値境界、無効閾値、不正JSON、空回答、入力取り違え、未測定表示の**11テスト**。
3. `comedy/benchmarks/runs/2026-11-23-0402-repetition-tasks.jsonl`：このサイクルで創作した**オリジナル開発題8題**（一般大喜利4、電話先AI救急係の即興4）。他人の投稿題をコピーしていない。版固定の評価セットではない。
4. `comedy/benchmarks/runs/2026-11-23-0402-repetition-responses.jsonl`：各2案、計16案を**このGPT-6のChatGPTテキストセッション内で作成**。モデルの独立API生成・音声発声と誤認しない。各案に元台本Skill、生成元、権限、publish OFFを明記。

## 実行環境・実行事実
- Mac mini（Remote Desktop Commander経由）上でGitHubブランチの実ファイルをコミットSHAから再取得し、Python標準ライブラリで実行。
- `python3 -m unittest -v test_audit_response_repetition.py` → **11/11 PASS**。合成データの検証でありモデル能力の測定ではない。
- `python3 validate_run.py --tasks 2026-11-23-0402-repetition-tasks.jsonl --responses 2026-11-23-0402-repetition-responses.jsonl --output 2026-11-23-0402-repetition-format-report.json --strict` → **16/16形式PASS**、各サンプルグループ8/8、未提出0、exit 0。これは面白さではない。
- `python3 audit_response_repetition.py --current 2026-11-23-0402-repetition-responses.jsonl --history 2026-11-23-0255-provenance-responses.jsonl --history 2026-11-23-0155-boundary-responses.jsonl --output 2026-11-23-0402-repetition-audit.json` → 新規16案、過去32案と比較。**実行内の準重複フラグ0、過去とのフラグ0、全対で最大Jaccard=0.157143**（閾値0.70）。これは短文の**文字3-gram類似度**だけであり、意味的独創性の実証ではない。過去の題と今回の題は異なるので、能力差を測ったBefore/After比較でもない。
- `python3 audit_comparison_provenance.py` → **NOT_COMPARABLE**。理由：`fewer_than_two_models`, `invalid_generation_setting`, `missing_generation_setting`, `missing_provider_receipt`, `missing_version_or_skill_sha`, `no_verified_independent_invocation`。
- `python3 comedy/benchmarks/check_injury_2min.py` → **PASS**（22発話・714文字・台本冒頭と交互発話の静的検査）。これは録音での実演成績ではない。
- 実行結果の生JSONは本ディレクトリの `*-format-report.json`, `*-audit.json`, `*-provenance.json` へ保存した。

## モデル、実行境界、出自
- **ChatGPT**：GPT-6（コンシューマーセッション、テキスト）の16回答を記録。正確なデプロイビルド、temperature、effort、max tokens、API request IDは取得・制御していない。実測できたのはPythonの検査結果とローカル実行の出力。独立API反復はゼロ。
- **Grok / Muse**：Reason Networkの3接続で `list_team` を試み、全件HTTP 409 `agent_network_offline`。**未実行**。モデル間勝敗の結論は出さない。
- Skill `v0.2.1`、blob SHA `fe21da855d08d5d01feff89be7244176087d4044`、起点 `main` SHA `095035d7ea0fac0573103a69224ebfb26a5506a8`。生成条件は応答JSONLに記録。
- **全16回答がDRAFT_ONLY**。X、第三者大喜利サイト、自動返信、応募は実行せず。publish=false／auto_reply=false。権利・規約・専用アカウント未確認につき公開不可。

## 舞台保護と未測定事項
- **改変禁止**：長尺『痛い痛い！』v8 blob `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6確定上演稿 blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、2分実演稿 blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`、Skill blob `fe21da855d08d5d01feff89be7244176087d4044`。変更していない。
- 金子さんのフィードバック：電話先の**AI救急指令員**の明確化、ダイスの開演合図、第一声「はい、救急指令センターです。火事ですか、救急ですか？」の完全性、第二声の架空病名、役を外さず既出人物の行動でアドリブを回収、ダイスの身体演技のために余白を残す、後方音量の確認。
- **未測定**：実機Voiceの第一／第二声遵守率、発声遅延、音量、会場後方可聴性、話者誤起動、複数回再演の再現性、観客の笑いと理解率、ダイスの演技の効果、意味的独創性、ブラインド人間評価、モデル間公平比較。評価コードが増えただけでモデルが学習したとは解釈しない。
- Mac miniの空き容量が約189MiBと小さいため、汚れた既存ワークツリーを変更せず、一時領域に必要な小容量ファイルだけ取得してテストした。

## 解釈と次の検証
今回、**テキストの使い回しを機械的に発見・記録する監査手段**が実際に動き、今回16案には定義した閾値以上の類似が無かった。一方、似ていない文が面白いとは限らず、表面上違うだけの同じボケは見逃す。今後は意味的な重複、同一キャラの自然な回収、観客の笑い、ダイスへのリアクション余白を独立して評価する。生成モデル比較には両モデルの独立推論証跡と同条件設定が必要。

研究上の参考：Shaib et al. (2024), *Standardizing the Measurement of Text Diversity*, https://arxiv.org/abs/2403.00553 。文字3-gram Jaccard自体はこのサイクル独自の簡易検査設計であり、同論文によって日本語コメディの評価妥当性が証明されたものではない。
