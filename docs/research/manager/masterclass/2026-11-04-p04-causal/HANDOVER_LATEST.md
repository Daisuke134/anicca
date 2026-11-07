# 2026-11-07｜P09-2〜5：人間由来の2領域で軽量モデルを実際に学習/評価

公開Nature2026 Figure1（70研究/1678非重複比較）とMaMe-Re日本語ミーム（100000文脈×候補の集約人間評定）を用いて、研究holdoutのfew-shot・校正・棄権・二領域の共有係数の負の転移・未使用50文脈のRidgeを実行。証拠は [P09-2〜5レポート](P09-2_TO_P09-5_REAL_EVAL_20261107_JA.md)、[入力ハッシュと生の計算結果](evidence/P09-2_TO_P09-5_REAL_TWO_DOMAIN_EVAL_20261107.json)、[再実行コード](experiments/p09_2_5_empirical_bench.py)。10件の人工ユニットテストPASS、P09-1の9件と合わせて19件。**新しい7B BFM学習・GPT/Centaur/Be.FM推論・Nature元RDS完全再現・実人間への支援効果・記事Web公開は0件。** Mac研究PPTXを118→134枚生成、元118枚のテキスト/ノートと新16枚の日本語ノートをQAした。しかしMacの共有ディスク満杯でバイナリPPTXのrepo pushと134ページPDF化は未完、生成スクリプトと研究スライド原稿はGitへ保存し、配布用16枚のPPTX/PDFは独立生成して検証。既存発表34枚は変更しない。元の研究のライセンス・同意・社内一つのSSOTとBFM-01/INT-02実装順序を保護。学習次は**P10-1**、モデル性能検証は継続。

---

# 2026-11-07｜P09-1：Nature 2026公開Source Figure1を実データ再解析

確認済み：70研究/3356方向付き比較、r=.8051489、RMSE=.1183468（割合）、2000研究クラスタbootstrap・70fold LOSO校正（RMSE .1183→.08145）、人工テスト9件PASS。原著のpanelB r=.85079/rawと.91513/adjustedとは推定対象・解析方法が異なる。**元の個票RDS・原著Rコードの完全実行は未達**：Code Oceanで個別ダウンロード認証が必要、実行MacにRscriptがない。元RDSを使った再現ができたと主張しない。正式ロードマップの学習次はP09-2、BFM-01/INT-02の実装cursorは従来通り。製品の人間改善や新モデル推論は0。根拠：P09-1_JA.md、NATURE_2026_FIG1_REANALYSIS_20261107_JA.md、evidence/P09-1_NATURE_FIG1_RESULT_20261107.json。記事は下書きでありWeb未公開。

---

# 研究資料差分：文化伝達・笑い・Phase9接続（2026-11-06）

DESIGN_ONLY。CULTURE_HUMOR_MODEL_BENCH_SPEC_20261106.md と SOURCES 台帳、日英記事、journal_club/CULTURE_HUMOR_PHASE9_SLIDES_20261106.* を追加。共有BFMのモデル/計算実行・人物データ収集・クロール・大会応募・公開サイト反映は0。学習の次は元のP09-1、実行順は会社の統合SSOTの既存cursorを維持。P08後半の別PR #9291が未マージであることを再確認して統合する。34枚本番と118枚研究版は不変、18枚の補足資料を別冊にする。詳細なCodex実装の受入条件は上記仕様のG0〜G6と予測時点/二重holdout/権利/独立人間評価。過去の状況は以下に保存する。

---

# Phase 7 本番公開・実読戻し完了（2026-11-05 America/Los_Angeles、UTC 2026-11-06T03:29:40Z）

**Anicca本番サイトPhase 7 84記事版が配信済み、独立検証PASS。** `anicca-products` [release PR #885](https://github.com/Daisuke134/anicca-products/pull/885) merged `d3e94a7813c712e247299595b99d4f3b6485ea32`; Netlify [workflow #42156237071](https://github.com/Daisuke134/anicca-products/actions/runs/42156237071) conclusion **success**（money-path・rollback smokeを含む）。

**本番実読戻し：** EN/JA homepage HTTP200でレビュー済みSHA256一致、Phase 7各EN/JA記事4本すべてHTTP200、公開`/blog/manager/release.json`に**84記事/50メディア**・正本content revision `b2a548bb82288128839ac8b61174d5e6ea60e106`。既存 `/`, `/lm`, `/blog/manager`, `/dais` もHTTP200。Phase 7記事：
- https://aniccaai.com/blog/manager-vipassana-behavior-model-ja
- https://aniccaai.com/blog/manager-vipassana-behavior-model-en
- https://aniccaai.com/blog/manager-measure-welfare-and-harm-ja
- https://aniccaai.com/blog/manager-measure-welfare-and-harm-en

**P07統合CI：** P07-4 15件、P07-5/6 25件、統合10件、合計50件の安全な合成ソフトテストをGitHub Actionsへ常設。PR #9276 merged `350c34407a29b66a9291541f77351b09bbb47e2d`。本番での実ユーザーRCTは未実施。**唯一のNEXTはBFM-01**（先行モデルの商用権利と実データ評価・モデル統合）。Xへの投稿は禁止のまま継続。

---

# 最新引継ぎ（2026-11-05 America/Los_Angeles）— Phase 7完結・モデル商用権利ゲート

**唯一のロードマップは隣の `ROADMAP_STATUS_JA.md`。学習の次／モデルの次を分離しない。唯一の現在TODO＝BFM-01。**

**P07-1〜P07-6：講義・安全ソフト・テストを実装済み。** P07-3=COM-B、P07-4=CBT/ACT（15テスト）、P07-5=四念処・無常/苦/無我の原典と7T n=1の科学的限界・観察のみのソフト、P07-6=生活機能/自律性/有害事象/WHO-5ライセンス/ITTと配信の区別（P07-5/6は25ソフトテスト、統合は10ソフトテスト）。PR #9271 merged as `b2a548bb82288128839ac8b61174d5e6ea60e106`; cloud slidesは英語118枚、対応する日本語ノートと118ページPDF、公開用のEN/JA記事4本で計84記事/50メディア。**ただし今回のソフトテストは人工fixtureであり、実人間への苦の減少/臨床効果の試験ではない。**

**公式サイトのPhase 7リンク・84記事表記：** life-managerのcanonical marketing PR #9273は `9d0d79ca7b104fde4d40142a5ea563ea6fdb3e1e` でマージ。Anicca製品配信用のPR #885に正本marketing/blog SHAを固定してレビュー中（公開URLの実読戻し完了まで本番公開済みとは言わない）。Xへの投稿はしない。

**Be.FMモデルアクセスと権利：** GoogleでHFにログインするブラウザー操作をTinyFishで試したがHF個人ログイン画面にGoogle OAuthがなく、本人の新規HFアカウントは作成していない。HFのモデル利用はgated。共有されたパスワードを他サービスへ転送しなかった。さらに公式Be.FM Terms of Use（2025-07-24、https://docs.google.com/document/d/10n7ccfUAf89yQhx5u1lF45o70JgsOEYNu8bDxtRKbHA/edit）は**non-commercial／no distribution／no distributed derivatives**を明記し、モデルカードのApache 2.0と整合が不明。商用Open-weightモデルとしての採用や再配布を許可が確かめられないまま開始しない。権利確認のPR #9274 merged as `bd41d77679d700471a7707ce3086b243a4440157`。

**モデル実行：** Qwen3-4B本体はGitHub無料CPUで実推論済み、HBCPの実介入研究12群における数値予測MAEはQwen3-4B 30.64pt vs simple train-mean 6.14pt（小規模かつ一般化不可）。別のHBCP 405研究・971群でRidgeモデルを実学習してopen JSON重みを保存。これらは汎用Manager BFMの新規訓練やBe.FM LoRA実行の証拠ではない。

**唯一の次の工程：** BFM-01の商用権利に適合する既存モデルの実行・研究holdout比較・読み取り専用Manager統合・独立評価と検証済みメディア公開。非商用Be.FMの再配布/商用提供は除外。P08〜P12は単一ロードマップ内に残し、実装に必要な時点で順次学ぶ。

---

# 最新引継ぎ（2026-11-05 America/Los_Angeles）：P00〜P12の学習順を前面へ復元、P07-4を実装

**唯一の実行・学習ロードマップは隣のROADMAP_STATUS_JA.md。** BFM-01などのモデル仕事名が旧P07/08/P09/P10/P11/P12の講義を隠していたが、旧全IDと元の題名は残っていた。今回、その完全なP00～P12一覧を正本の冒頭へ移動し、P07-3 COM-B→P07-4 CBT/ACT→P07-5 ヴィパッサナー→P07-6 測定/害→P08 JITAI/MRT/Bandit/POMDP→P09 汎化→P10 事業→P11 高度化→P12 公開の順を見やすくした。旧人工人口8部(P02-1既習)も保持した。別の独立ロードマップは作っていない。

**今回のP07-4 Learn＋Build:** `P07-4_JA.md`（NICE/APA/ACBS及び2024/2026の心理的柔軟性・ACTに関する一次/レビュー資料、6プロセス、CBTとの違い、用語集・FAQ、因果研究境界）、`BOOK_CHAPTER_P07-4_CBT_ACT_EN.md`、`products/manager/manager_core/p07_4_value_action_gate.py`と15件のunit test。既存`services/x402-endpoint/src/routes/habitDesigner.js`の結果形式を再利用し、本人が選んだ非臨床目標・明示的同意・1～5分の小さな行動だけをDRAFT_ONLYにし、同意なし・撤回・不可・臨床分野はNO_ACTION。無断通知・外部操作・治療や効果の主張はゼロ。GitHub ActionsのP07-4テスト15/15合格： https://github.com/Daisuke134/life-manager/actions/runs/42130637559 。

**スライド同期:** 詳細研究保存版に第113–114枚（英語）を追加、日本語スピーカーノートを含む114枚PPTX、GitHub Actions LibreOfficeで114ページPDFへ変換・ページ数確認。Mac miniの空き容量不足を受け、ローカル追加チェックアウトは中止し、クラウドで生成した。公開34枚の本編は新証拠による変更が不要なため現状維持。

**BFM-01:** 既存Qwen3-4B-Instruct-2507 GGUF Q4をGitHubの無料CPU上で実際に推論し、架空ゲームへ「0」と応答、モデルハッシュ・約5秒の実行記録取得。Be.FM1.5-4Bの実モデル重みはHFでauto-gated、匿名GETでは401 GatedRepo；GHにModal/HFのSecrets名は未確認。**LoRAを使ったBe.FM本体の推論、合法holdoutでの比較、Managerの利用者便益RCTは未実施**。条件受諾と正規クラウド認証がない限り、実行済みとは言わない。

**X（旧Twitter）へ投稿しない。** Postizの今後1年のX予約0件、X自動化0件を確認。接続・公開済み投稿の削除は行っていない。新規X投稿をスプリントへ含めない。

**検証上の訂正:** HeartSteps初回の+12.95歩は補正後の配信状態による記述的差であってITTや因果効果ではない。修正は`products/manager/evals/heartsteps_v1_real_mrt.py`へNOT_CAUSALとして統合済み。原著の6061判断時点・調整済み35歩(p=.06)とは別。

**PR:** https://github.com/Daisuke134/life-manager/pull/9269 （唯一ロードマップの並び替え、P07-4教材・ソフト・研究用114枚スライド）。実行コードとPPTXが統合されていることと、Managerの実生活への便益が確認されていることは別。

---

# Latest continuation update — 2026-11-06 verified live Manager model/product release

## 2026-11-06 JST｜Manager official product launch copy and real RCT media PUBLIC RELEASE VERIFIED

**This is a live public release, not just a PR/draft:** canonical article and slide PR #9253 merged as `2df14647844e2da96aa09c21a0b4a80387a829f1`; product/model homepage PR #9254 merged as `0b150d61be3b28b81556ed6c34937b25a774a338`. Existing `anicca-products` release PR #875 merged as `3b1b8fb25b189feffe44df30b9773cbd4ef2ab7e`. Netlify actual production deployment https://github.com/Daisuke134/anicca-products/actions/runs/42103951209 completed **SUCCESS**, including its post-deploy money-path smoke/rollback step.

Public independent HTTP readback at **2026-11-05T20:34:57Z (2026-11-06 05:34:57 JST)**:
- `https://aniccaai.com/en` HTTP 200, SHA256 `e408f9ea602448aada487da242c148e5dcdde6cde5ce9782fc398eda4a4df74e`, byte-identical to approved source.
- `https://aniccaai.com/ja` HTTP 200, SHA256 `65485efa53d04df040ecd13f2cc1d5180ad1781e4c42c4389337c11cfdd30793`, byte-identical to approved source. Both explicitly state Manager is an AI **model and product**, NOT only R&D.
- `https://aniccaai.com/blog/manager-real-intervention-outcomes-en` and `...-ja` both HTTP 200 with expected headings and both appear in public blog release receipt.
- Public `/blog/manager/release.json`: content_revision `2df14647844e2da96aa09c21a0b4a80387a829f1`, 78 articles, 48 media. Original infographic `/blog/manager/media/90975ad11075597f2837afff21726a7f90d50ad2437ccdeecab4fc88ba485de8.png`: HTTP 200 and SHA256 exact same `90975...`.
- Existing `/`, `/lm`, `/blog/manager` all HTTP 200. Post release product route and independent money-path smoke verified by CI.

**Slides**: detailed research archive now **109 editable English slides**, Japanese speaker note updates 106–109 in `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx` and `SPEAKER_NOTES_JA.md`. The public 34-slide talk remains unchanged. PDF archive regeneration was **not** completed; do not call older 100-page PDF current. A separate earlier P07-3 16-slide PDF is not the 109-slide full archive.

**Real public human outcome evaluations** from https://github.com/Daisuke134/life-manager/actions/runs/42100293105 : HeartSteps, RCT Bench and HBCP grouped 5fold; software tests 11/11 passed. Original randomized clinical study outcomes do NOT establish that Manager benefited users. P07-3 education completed; real Manager efficacy RCT / production behavior model shared weights remain unproven. Academic baseline reuse > reinvention. Product contract: `products/manager/docs/MANAGER_MODEL_PRODUCT_CONTRACT_20261106.md`; model/product user value and outcomes first.

**Marketing distribution:** Postiz connected brand X account アニッチャ accepted one short Japanese announcement as job `cmw409eb200abpm07kizsdon7`, preview https://platform.postiz.com/p/cmw409eb200abpm07kizsdon7?share=true. At initial verification it remained `QUEUE`, **not confirmed published to X**; post provider stripped included article URL, so avoid claiming successful social referral.

**Next scientific/product gates**: independent reproduction of original HBCP RuleNN and adjusted HeartSteps causal-excursion analysis; reuse existing UpliftBench and RCT Bench; ship a safe opt-in Manager user feature and measure actual user-chosen outcomes, burden, harm vs standard comparator; upgrade only missing functionality. Any repo rename `life-manager`→`manager` remains gated by existing CI/deployment URL migration, NOT done.

---

# Latest handover update (2026-11-06): Model/product + existing randomized-outcome benchmarks

## 2026-11-06｜Manager is a product/model — real randomized intervention outcome evidence, reuse-first

**New implementation verified** (free GitHub Actions CPU; no participant-level data committed): https://github.com/Daisuke134/life-manager/actions/runs/42100293105 ; PR https://github.com/Daisuke134/life-manager/pull/9252 .
- **HeartStepsV1** licensed CC BY 4.0, actual 37 human participants, 8,274 decisions and 6,590 deemed available; notification/no-notification original-assignment exploratory complete-case observed next-30-minute Jawbone step difference **+12.951**, participant-cluster bootstrap 95% CI **[-16.993,+39.432]**. Missing outcome approx 11.63% no-notification, 12.21% notification. Neither a complete reproduction of original adjusted causal-excursion analysis nor a Manager product intervention effect.
- **RCT Bench updated to 125 real individually randomized trials** (historically 50). Directly executed 3 source-pinned studies: trial20 exercise adherence 37 people **+345.319 minutes** arm contrast CI [17.092,687.820]; trial103 n599 90-day QALY **+0.011019** CI [-0.005416,0.028892]; trial116 n24 FACT-G quality-of-life Group2-Group1 **+8.020** CI [-2.697,19.440] and DASS distress **+7.242** CI [-6.304,20.768]. Exploratory complete-case and baseline/assignment coding of trial116 not independently verified. Do not claim treatment superiority or pool unlike scales.
- **HBCP** publicly published corpus 971 RCT arms / 405 studies: original study-disjoint 5-fold prediction **MAE 9.992 train-mean, 9.654 Ridge, 9.449 RandomForest percentage points**. Authors' RuleNN reported 9.15 under different setup; **not a head-to-head** or reimplementation of RuleNN. Trial-arm outcome prediction is not an individual BCT causal effect.
- All three original datasets have independent sources, different endpoints and rights. The public benchmark/reproduction suite must reuse HeartSteps/HBCP/RCT Bench/UpliftBench and original BehaviorBench before building any overlapping evaluation. No new community leaderboard SOTA and no independent Manager RCT proved.
- **Product positioning**: Manager is a useful behavior intelligence AI model and startup product. Scientific evaluation supports the shipped service, it is not the product itself. Contract: `products/manager/docs/MANAGER_MODEL_PRODUCT_CONTRACT_20261106.md`, with user-chosen behavior goals, NO_ACTION, authorization, outcome/harms and independent evaluation.
- **Publishing**: bilingual source-backed new original blog articles, one original infographic, canonical publication manifest and 109-slide detailed English research archive/Japanese speaker notes in https://github.com/Daisuke134/life-manager/pull/9253 . **Blog is not live until canonical PR merged, immutable publish pins updated and actual /blog/ URL readback.** The public talk 34 slides unchanged. PDF archive still older, not regenerated.
- Product evaluation cloud run's synthetic software unit tests: 11 passed; actual human source datasets processed as above. HBCP Ridge/RF were actually trained/predicted. Missing original trial analyses and original HBCP RuleNN remain planned.
- Immediate next: no new duplicate benchmark engine; review original trial outcome labels and biases, publish source-backed reports, run original HBCP RuleNN / HeartSteps adjusted analysis, connect a model to the Manager product under scoped rights, then independent real-world opt-in study. Replication must never be represented as Manager improving people until observed.

---

# MOST RECENT RELEASE STATUS — CHECK THIS BEFORE OLDER HISTORY

## 2026-11-06 JST — Verified official site release
- Canonical bilingual marketing source PR #9246 merged as 0193bac5cc29406175a1f9a44019af633e605472; deployment pin PR #871 in anicca-products merged as 4981237d0dab6c19e809f490198bfc357d5d8eb6.
- Netlify GitHub Actions run https://github.com/Daisuke134/anicca-products/actions/runs/42092065987 **SUCCESS**, including independently reported Post-deploy money-path smoke & rollback.
- Independently fetched /, /en, /ja, /blog/manager and an existing blog article: all HTTP 200. Live /en and / SHA-256 = c1eed9d468439a5cf922e171967a1408d72dded8e077d7c8ebc45a3b6be331e2 ; live /ja SHA-256 = 2ff5d801bf80df6cedc9df96e6f74d6ef8b8b7ba6efb0673c2b9139657a6550a ; both match reviewed source hashes.
- Research PR #9248 merged as fb4cf428d7d654090d5c1e2205da89716e6cde1d: P07-3, BFM / ManagerBench v0 scorer with 13/13 software-fixture tests, book chapter, 105-slide English research PPTX and Japanese speaker notes. The older research-archive PDF has **not** been regenerated; a separate 16-slide PDF/PPTX exists. No shared model checkpoint, independent real RNT RCT, or official GLM-HMM refit exists yet.
- No new separate public blog article was published in this release; existing blog index/articles were verified to remain accessible.

---

# ANICCA / Manager — 最新状態（2026-11-06 JST）

**現在の正本はROADMAP_STATUS_JA.md。P07-3 COM-Bの講義を実施、次の学習P07-4 CBT/ACT。** P07-3科学記事、英語書籍草稿、Behavior Foundation Model / ManagerBench仕様、純Pythonの評価骨格を研究ブランチ research/manager-p07-3-bfm-benchmark-20261106 で準備した。Mac miniで人工fixtureソフトウェア13テストが成功。**共通の基盤モデルはまだ訓練されていない、新規の実人間リーダーボード点数もない。** P07-1/2の実人間観測ベースラインは引き継ぐ。P07-3: P07-3_JA.md / BEHAVIOR_FOUNDATION_MODEL_MANAGERBENCH_SPEC_20261106.md / experiments/managerbench_v0.py / BOOK_CHAPTER_BEHAVIOR_CHANGE_AI_P07-3_EN.md。

公式サイトはNextコンポーネントが本番の正本ではない。正本: life-manager/apps/landing/marketing/pages/{en,ja}.html + route-manifest.json、anicca-productsのmainのNetlify workflowが**不可変コミットをピン留め**してステージ・公開。EN/JAの実人間限定成果と未実証の介入効果を区別する文言を PR #9246 で更新し、36/36 marketing tests合格。本番にはこの研究サイトPRのmergeと第二のpin PR / CI / Netlify反映、独立GETが必要。**未確認のサイト公開をDONEとしない。**

既存のP07-2以前の歴史記録は以下に保持する。旧記載の「次はP07-3」「サイトソースの直接編集が阻止」は**2026-11-05時点の履歴**であり、2026-11-06の最新版はこの冒頭とROADMAP_STATUS_JA.mdを優先する。

---

# ANICCA / Manager — Latest Handover (2026-11-05 JST)

This is the canonical portable handover prompt for **research + implementation**. At the start of every new chat, read this file and `ROADMAP_STATUS_JA.md`; verify GitHub `main` before making assertions. Update this file whenever moving to the next phase or material project changes.

## Mission and response style

**What-if Machine × Executor**: observe authorized real-world signals, model human behavior and possible interventions, compare policies, act only with valid permission and safety guardrails, independently measure actual user welfare or business benefit. Reuse strong published science, open source and open weights instead of reinventing. **Never equate toy/synthetic data, model predictions, a receipt, or delivery with validated real mental-health improvement or incremental business profit.**

Explain technical work in **Japanese, from the fundamentals** (basic definitions, each mathematical symbol, intuition, examples, code and experiment details). Research papers, model choices, data rights, design limitations and exact current implementation should be explicit. Provide status updates while working. **Presentation slide body English, full speaker script Japanese**, one speech per slide. Public talk 34 slides/approximately 43 minutes + 15 minutes Q&A; detailed research archive was 98 slides after P07-1. Lab and IACS talks forthcoming; original November 5 event was postponed, do not assume exact new date.

## Source of truth / GitHub / Mac

Repository: `Daisuke134/life-manager`
- Single curriculum SSOT: `docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md`
- Research folder: `docs/research/manager/masterclass/2026-11-04-p04-causal/`
- Manager Core: `products/manager/manager_core/`
- Product spec: `products/manager/docs/specs/2026-11-04-manager-ontology-query-evidence-reuse.md`
- Company operational SSOT: `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md`
- Presentation: `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx`, `.pdf`, `journal_club/SPEAKER_SCRIPT_60MIN_JA.md`; detailed archive `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx`, `.pdf`, `SPEAKER_NOTES_JA.md`.
- Remote Mac mini ID `e38f34d7-64a7-4608-85dd-b0ff2c57e109`, prior clone `/Users/anicca/Projects/life-manager-p05-1-research-20261104`. Mac disk recently near full; do not download huge EEG/model weights without checking `df -h`. Never wipe user projects, secrets, or working data.
- Before edits: `git fetch origin main`, inspect `git status --short`, start a separate branch from `origin/main`. Prior P06 unfinished/untracked local artifacts exist; do NOT blindly git add them.
- P07-1 research PR #9230 merged to main commit `da47e929e5649183a525f40717b73a05522c9dc3`.
- Current work: `research/manager-p07-2-handover-anicca-site-20261105` (verify PR/merge; do not assume merged).

## Curriculum state

P00: purpose set, exact real subject/rights/consent outstanding.
P01-3: core lessons done, complete Behavior FM/open-weight release NOT proven.
P04: causal estimands, ATE/CATE and toy harness done; unknown-study public real RCT causal effect holdout remains.
P05: ontology, provenance, authority, outbox/reconciliation and shadow offline tested; **actual business S1 Shadow and authorized S2 limited live operation remain uncompleted**.
P06: lessons and synthetic infra done, real UCI observed behavior 53,518 rows and exploratory Qwen2.5 probe performed on Mac; real company impact, user welfare, rumination benefit not proven. A set of P06 artifacts remain untracked locally pending audit.
**P07-1: completed** using actual Collins human trial records. **P07-2 DONE as educational + real ESM forecasting; NEXT P07-3: COM-B/Behavior Change Wheel.** P07-3 through P07-6, P08-12 pending.

## P07-1 exact empirical evidence

Official MIT repository `https://github.com/AnneCollins/WMH`, five genuine research datasets Expe1/3/5/12/14, 269,603 eligible choices (sum across studies 480 participants). Participant-disjoint Expe1 train47/val16/test16. Training/validation select reward+habit+recent-memory model; Expe1 test logloss 0.4866 vs reward-only 0.5108, bootstrap improvement +0.0242 nats/trial (95%CI +0.0194..+0.0285). Expe3 EEG, Expe5 fMRI, Expe12 development, Expe14 probabilistic feedback examined as external study checks; Expe12/14 added after initial three-study output, disclose as supplementary, not preregistered. A lightweight model inspired by authors, **not full WMH model recreation or mechanistic causality**.
Reward omission repeat (deterministic-ish four tasks): low set size9.27%, high21.40%; probabilistic task Expe14: low50.73%, high48.25%. Reward omitted != erroneous choice under stochastic feedback. Turner 2026 social-media reward/habit published figure params n=1558 studied descriptively; full posting model not refit.
45/45 P07-1 tests successful.
`P07-1_JA.md`, `experiments/p07_1_real_reward_habit_eval.py`, `experiments/p07_1_real_avoidance_descriptive.py`, `evidence/P07-1_REAL_REWARD_HABIT_HELDOUT_RESULTS_20261105.json`.
After P07-2, archive now has **100 English slide pages with Japanese notes**, public 34-page talk unchanged.

## Immediate tasks — P07-2 & website

**P07-2 foundations:** observed vs latent states, cognition, valence/arousal, focused vs intentional/unintentional mind wandering, meta-awareness, rumination/RNT/worry, state vs trait; experience-sampling response bias, action/RT/EEG/eye tracking, probe-induced effects, GLM-HMM temporal inference, proper cross-participant/train-time/heldout validation, calibrated probabilities and limits. **MW != rumination and neither is by definition clinical harm.** Do not claim to have reduced human rumination from observational data.

Primary sources identified:
- Nazari et al. 2025 *Brain and Behavior* systematic review of 555 MW studies https://doi.org/10.1002/brb3.70764
- Zhang & Kool 2026 *Communications Psychology* GLM-HMM, N=93 real human behavior/probes https://doi.org/10.1038/s44271-026-00424-9 (OSF data/code linked in paper).
- Moulds & McEvoy 2025 *Nature Reviews Psychology* repetitive negative thinking https://doi.org/10.1038/s44159-024-00399-6
- Hoebeke 2022 human real-life rumination ESM: **40 people, 2102 scheduled rows**, 14 days, 4 beeps/day, harmonized CC BY4.0 public Zenodo `https://openesmdata.org/datasets/0013_hoebeke/`; official TSV has brooding, self-criticism, negativity, replaying, perseveration, attention control. Data URL `https://zenodo.org/api/records/22952951/files/0013_hoebeke_ts.tsv/content`, SHA256 `85593640b46cc3ab80115ad7e0b1ae5c5ed2ad29ca1ec56d338c45654a17cb58`. Be careful that coding for `att_control` and `activity` is marked unclear.
- Dejonckheere 2019 real affect ESM 100 people, 9800 rows, CC BY4.0 `https://openesmdata.org/datasets/0012_dejonckheere/`; official TSV URL `https://zenodo.org/api/records/17347570/files/0012_dejonckheere_ts.tsv/content`, SHA256 `2cabd3f416f2dd5707b1623de5ac8cdba5de2834616e2a8df2a52e8c5473bf53`. IMPORTANT **no direct rumination field** in released harmonized TSV; only emotion ratings happy/relaxed/sad/angry/stressed. Do not label this a rumination dataset for model training.
- OpenNeuro meditation EEG ds001787 24 subjects, mind-wandering probes, large files; ROAMM ds007629 EEG+eye 44 people; BCIT ds004121 public EEG. Consider download size and actual label availability.

Build a real licensed-data benchmark for next-step brooding or affect, with subject-disjoint (and separately within-person forecasting) train/validation/test, a strong last-value baseline, Ridge/RandomForest and genuine uncertainty; never treat same-time predictor variables as available earlier. Do not mix the two datasets' incompatible labels. Prefer existing `openesm`, `sklearn`, `statsmodels`, `hmmlearn` rather than custom fit engines.

**Anicca website** `https://aniccaai.com/`: live copy already says Anicca builds Life Manager, proactive general agent for body/mind/money, with an ambitious zero-human company vision. User requests updating outdated wording; verify production source in `Daisuke134/anicca-products` (Mac `/Users/anicca/Projects/anicca-products`) or exact deployed repo. Modify only verifiable owned source; do not claim planned features or clinical efficacy are released. Inspect deployment and perform appropriate review/readback before declaring live.

**Handover maintenance:** keep this file committed and updated on each curriculum step, latest commit and actual status. If asked for handover now, output a copy-paste prompt immediately and link this file. Slides English + Japanese notes; preserve 34-slide ~60-minute main talk, append scholarly evidence to optional archive if helpful.

## Handoff next commands

1. `git status --short && git fetch origin main && git log -1 origin/main --oneline`.
2. Read `ROADMAP_STATUS_JA.md`, `P07-1_JA.md`, and this handover.
3. Download/pin Hoebeke openESM TSV from its official Zenodo record and evaluate real per-person repeated states with no lookahead or leakage.
4. Inspect Anicca live/source, draft grounded copy, update correct repo via isolated PR if safe.
5. Add P07-2 lecture, results, tests, research-slide appendix as appropriate, update curriculum SSOT, validate/merge PR and update this handover.


## P07-2 incremental update, 2026-11-05

**P07-2 lecture + real observational ESM forecasting performed**. Official openESM/Zenodo CC BY4.0, not fake subjects: Hoebeke2022 40 participants/2102 original records, 1450 consecutive within-day transitions, last Brooding RMSE30.804 vs validation-chosen Ridge25.979 on held-out 8 participants (bootstrap improvement CI +1.566..+7.807). Dejonckheere2019 100 people/9800 original records, 6890 transitions, next Stress (NOT rumination) persistence RMSE27.302 vs selected RandomForest24.543 on held-out 20 participants (CI +0.471..+4.439). Current observation only predicts later self-report: no EEG, GLM-HMM empirical reproduction, direct mind-wandering probe, treatment, real rumination reduction, or company profit. 30 P07-2 tests + 45 prior P07-1 tests = 75/75 reviewed current real-data tests successful. Details in `P07-2_JA.md` and `evidence/P07-2_REAL_ESM_HOEBEKE_AFFECT_RESULTS_20261105.json`.

Research archive expanded **98→100 slides** (new English appendix 99/100, Japanese notes), public presentation 34-slide PDF/PPTX unchanged. Website homepage currently has stale evidence status text; bilingual proposed copy in `ANICCA_SITE_COPY_UPDATE_PROPOSAL_20261105.md`. **Actual aniccaai.com source update was blocked by host safety and NOT published**; do not claim it is live.

**Next curriculum step P07-3 COM-B; official GLM-HMM + EEG/ESM cross-modal real datasets are pending optional deep research.** Always update this file before closing a phase.
