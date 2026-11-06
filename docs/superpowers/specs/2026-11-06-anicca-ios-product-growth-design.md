# Anicca iOS — 初回改善から全アプリの継続成長までの仕様

## 正本・今回の境界

目的は、英語市場を中心にAniccaの獲得・初回価値体験・課金・継続を改善し、配信から製品へ学習が戻る運営を作ること。世界最大・$10K MRRは目標であり、達成済みの事実や今回リリースの保証とは扱わない。

**順序・TODO・状態の唯一の正本:** [統合SSOTの ANICCA-PRODUCT-GROWTH](2026-09-25-life-manager-unified-ssot.md#anicca-product-growth--ios初回改善から全アプリ継続改善まで)。この文書は詳細な要求・契約、[実装計画](../plans/2026-11-06-anicca-ios-product-growth.md)は実行手順。進捗を別台帳へ二重管理しない。

現在の依頼は**G1〜G5のAnicca初回改善を実装し、Maestro実製品動画と審査提出まで進めること**。全体仕様の保存・共有は完了しており、ユーザーが実行開始を指示する。G6以降のダッシュボード拡張・自動化・他アプリ展開は、その後に進める範囲として残す。スコープの分割は後続要求の削除ではない。

## 出所と現在の観測

コード正本は `Daisuke134/life-manager` の `apps/mobile/anicca-ios`。参照時のmainは `897be0e51bd9d9839477fd7c53c2b4768a78b4aa`。実装着手時は最新mainとの差と公式状態を再確認する。

| 対象 | 観測した事実 | 未確認・注意 |
|---|---|---|
| Apple | アプリID `6755129214`、bundle `ai.anicca.app.ios`。今回の事前調査で1.9.6 / build816は `READY_FOR_DISTRIBUTION` | 次版の番号・審査状態・対象buildは提出前に公式再取得 |
| 計測 | `AnalyticsManager` は主にMixpanelへ送信。PostHogは別capture経路、設定が無ければ初期化しない | SDK導入は本番イベント受信・全画面計測の証拠ではない |
| Onboarding | 9つの列挙stepと別の2段paywallが存在 | コメントの「10/20-step」と実際の画面数を混同しない |
| 課金 | 閉じると無料利用へ進めるsoft paywall。`variant: "b"` 呼び出し | フラグの存在だけでA/B稼働としない |
| 価格 | 事前調査の米国公開IAP一覧は月$14.99・年$59.99・買切$59.99。週$6.99も登録 | 公開一覧・現行Offering・対象国・無料体験資格を別に照合。モック値を本番へ固定しない |
| フィード | 縦 `UIPageViewController`、固定カタログEN/JA/ES各200件、8背景、いいねはローカル保存 | swipeの戻りはユーザー報告。原因未確定、端末・操作条件・実版で再現する |
| 通知 | APNs起動処理、通知本文/IDの遷移coordinator、cold-start保留処理と既存回帰が存在 | 1.9.6の公開履歴にも同文言修正あり。再現確認なく同じ修正を作り直さない |
| 設定 | 通知画面の `dailyCount = 4` は固定値 | 実配信頻度、free/pro別上限、serverの稼働経路とは未接続 |
| 売上計測 | 購入時の価格未取得fallbackに `9.99` が存在 | 推定値を実売上へ混入させない。currency・receipt・更新・返金と照合 |
| 共有指標 | 公開Open feedにはAnicca、Dhamma、Thankful、Sleep Reset、Honneの5アプリ分析が存在 | 全出荷アプリの網羅ではない。Cherie等を公式アプリ一覧と照合する |
| 継続処理 | `marketing-product-summary.js`、ASC獲得・RevenueCat集計、日次/週次callerが存在 | コード存在は自然実行や製品改善ownerの稼働証拠ではない |

公開feedの観測例: `https://aniccaai.com/open/data.json` の期間10/29〜11/04、Aniccaは新規3件、JP2/CO1、取得行はApp Store検索。download coverageは7日中4日。米国0・SNS0や「全期間3件」とは断定しない。取得期間と欠測を保持し、別collectorの「行無し→0」と不整合があれば集計境界を直す。

## 勝ち筋の参照と採用範囲

| 一次資料 | 観測・模倣する仕組み | 当社で測る指標 |
|---|---|---|
| [Monkey Taps](https://monkeytaps.app/) / [I am](https://iamaffirmations.app/) | 運営元はI amの年600万downloadを自己申告。カテゴリ・テーマ・reminderによる日常の価値体験 | 初回文言表示までの時間、保存、通知からの再訪、D7継続 |
| [TikTokのMonkey Taps事例](https://ads.tiktok.com/business/es/inspiration/monkeytaps) | 複数creativeを試し、Start Trialまで最適化。有料広告の事例 | 当社の無料配信では到達→クリック→install→trial/paid。広告の成果を無料配信へ外挿しない |
| [RevenueCat調査](https://www.revenuecat.com/state-of-subscription-apps-2026/) | 初回価値体験、地域別比較、売上/インストール、課金と継続の両方を見る | 英語圏別RPI、課金率、成熟コホート継続、返金 |
| [PostHog iOS](https://posthog.com/docs/libraries/ios) / [Experiments](https://posthog.com/docs/experiments) | 既存SDK・安定した割付・露出イベント・同じevent上の実験 | 割付整合、露出人数、主指標とguardrail |
| [RevenueCat Experiments](https://www.revenuecat.com/docs/tools/experiments-v1) | Offering/価格/提示を比較する既製機能。現行契約で利用できるか確認 | 価格別net RPI、refund/renewal。利用料・無料枠は導入前に再確認 |

勝者の構造を当社の素材・事実へ置き換える。競合の文章・画像・商標、裏付けのない健康効果、捏造social proofは流用しない。公開download・ratings・自己申告売上とverified profitを区別する。特定onboardingの因果効果を証明する同条件の資料が無い箇所は、**当社仮説**として小さく検証する。

## G1 — 初回利用・onboarding・課金画面

対象は英語市場を主軸にし、現行対応言語の操作・購入を壊さない。新規状態は隔離simulator/Sandboxで作り、Daisの本番契約や既存ユーザーデータをresetしない。

新規flowは「目的選択 → 関連する言葉を読む/保存 → reminderの説明/任意設定 → Proの実価値と価格 → 購入または無料feed」。最初の言葉を読むまでにaccount作成・通知許可・不要な質問・待ち時間演出を挟まない。冗長な比較/processing画面は現在の契約を確認して整理する。通知拒否でも進める。途中復帰は有効なstepへ戻り、既存の完了/有料ユーザーへ初回質問を再強制しない。

feedは全文を中心にし、保存・共有・カテゴリ・背景・reminderを読みやすい位置に置く。大きい文字、VoiceOver、Reduce Motionを確認する。背景は既存素材とnative表現を先に再利用する。動画背景の追加を今回の必須条件にはしない。

soft paywallを初回版の基準にする。閉じる・無料継続・復元・規約/Privacyへの導線、総請求額・請求周期・更新・無料体験資格を正確に表示する。国/通貨が変わる場合は最新StoreKitとOfferingを再取得し、不一致商品を購入できない。買切をMRRや自動更新契約として数えない。既存購入者の権限を維持する。

Pro特典・free/proの通知上限は、実際に権限で分かれる動作を調べて文言へ反映する。mockにある「全カテゴリ」「テーマ」等は未確定の表示案であり、未実装特典の販売・独断のfree機能削除を許可しない。価格変更・hard paywall・trial変更はG8で別実験とする。

## G2 — swipeと通知を確実にする

swipeはユーザー報告の約10回に1回の戻りを、連続上下・短/長/高速操作・逆方向・保存/テーマ更新・通知遷移の重なりで再現する。pagerの対話遷移とprogrammatic更新、index、catalog mutation、hosting stateを観測して根本原因を限定する。完了したswipeの後に古いindexへ戻らず、隣の全文を一度だけ表示する。短く戻す意図的gesture cancellationは不具合と数えない。

通知は、タップされた本文を表示の根拠とし、安定した `quote_id` と本文・言語・catalog version・notification IDを照合する。未知ID・欠落ID・本文のみ・古いcatalog・同じ通知の再tapでも別文言へ置換しない。payload不正で空なら無関係なquoteへ飛ばさず通常feedへ戻す。アプリ終了/背景/前面、onboarding中、catalog準備前で要求を保持し、準備後に一度だけ解決する。

配信の現在owner・caller・APNs token・timezone・時刻選択・authorization・有料権限・配信receiptを調べ、予定件数と実件数を分ける。設定の固定4件を実設定へ接続する。ローカル通知かremoteかは既存設計で毎日安定供給できる最小案を採り、同じoccurrenceを二重配信しない。OS通知許可、端末offline、Focus等のため「必ず毎日表示」を保証しない。APNs受付は端末表示・開封の証拠ではない。

### 配信経路の実確認による決定

Railway公式readbackで本番APIは `Daisuke134/anicca-products` / `apps/api`、deployment `a4699e00-907b-45be-8d8a-3a46fba90282` / commit `4e7885b` を確認する。同commitのsenderはfree=`09:00/14:00/20:00`、Pro=`08:00/12:30/17:30/21:30`（登録timezone）。今回のアプリはこれを予定として表示し、OS許可と配信済み件数を区別する。iOSの既存時間帯選択は保存されず、現在のAPIに任意時刻変更の接続がないため、反映されない選択を除いて予定確認＋任意通知許可にする。任意時刻の編集を提供する際はbackend契約も変更する。remote-onlyを維持し、二重local配信を追加しない。別repoの稼働backendや既存cronはこのUI修正で置換しない。

## G3 — 文言・いいね・個人化

既存200件/言語を無条件に捨てない。英語は初回版の暫定受入目標を**重複しない600件以上、12カテゴリ以上**とし、数量目標は業界の最適値とは主張しない。カテゴリ・タグ・出所/編集version・言語をstable IDへ結び、意味の重複・不自然な英語・危険な断定を確認する。JA/ESは利用可能な文言を維持し、未翻訳文を翻訳済みとして数えない。

目的選択を最初の推薦へ反映する。いいねは保存と次の推薦候補のカテゴリ重みに反映し、既に見ているページや次ページの内容をgesture中に並べ替えない。最近の20件は十分な候補があれば再表示を避け、探索候補も残す。カテゴリ変更、好みのreset、少数catalog、全件閲覧済みでも空feedにしない。個人化はまず既存モデル/ローカル規則を使い、新しいML基盤を作らない。

通知から受け取ったcatalog外文言も保存後に読める。like解除は保存と推薦重みへ反映し、他の保存内容を消さない。onboarding目的・表示・like・notificationのIDを揃える。健康・悩みの自由入力や本文を無差別に分析/リプレイへ送らない。

## G4 — 初回版に入れる計測

SDKの存在を完了にしない。既存Mixpanelを保持しながらPostHogの分析・実験へ必要eventを接続し、二重発火とユーザーIDの混在を防ぐ。RevenueCat匿名ID等の適切な安定IDで購入と行動を結び、emailや全ユーザー共通literalをdistinct IDにしない。匿名→account移行・logoutがある場合のresetを確認する。

| 意思決定 | 必要event/属性 |
|---|---|
| 各画面の到達/離脱 | screen_viewed、screen_id、flow_version、session_id、app_version/build、language、platform |
| 初回価値までの距離 | onboarding_started、step_viewed/completed、first_affirmation_viewed、onboarding_completed、開始からの所要時間 |
| 継続体験 | affirmation_viewed/liked/unliked/shared、quote_id、category、recommendation_version |
| 通知の一致/復帰 | notification_opened、notification_id/quote_id、navigation_result、reminder設定/許可結果。deliveryは公式取得可能な境界だけ |
| 課金 | paywall_viewed/closed、offering/product、storefront/currency、価格、trial eligibility、purchase_result/cancel/restore |
| 実験 | experiment_id、variant、assignment_version、実際に見たexposure、割付単位 |
| 配信接続 | 取得できるcampaign/content/platform/account/locale。未判定はunknownとして残す |

既存event名を再利用し、意味が変わる場合にschema/flow_versionを付ける。画面描画ごとの重複発火、バックグラウンド復帰、offline queue、再送、内部テスト/TestFlightを区別する。計測受信・property・identityをサービス側でreadbackする。free text、token、秘密値を含めず、感情/健康領域のreplayは許諾とmaskingを確認して最小化する。

売上はreceipt/backendを基準にし、クライアントcallbackの重複・restore・trial開始を新規有料売上へ加算しない。不明価格を9.99等へ置換しない。各通貨を保持し、換算日/レートを明記する。gross・refund・Apple proceeds・運用実費・profitは別field。個人のMRRと全社MRRを混同しない。

## G5 — 検証・実製品動画・提出

1. 変更に対応する最小の回帰を先に失敗させ、実装修正後にpassを確認する。既存のnavigation・onboarding・paywall・tokenテストを再利用する。
2. Release相当のsimulator buildでMaestroを動かす。fresh EN/JA、初回flow、soft close、settingsからの再購入、価格/Offering失敗、購入cancel/restore、連続上下swipe、like/保存/テーマ保持、cold/warm notification本文一致を確認する。
3. 成功した同一runを `xcrun simctl io <UDID> recordVideo` 等の既存録画機能でMP4保存し、Maestro log・screenshots・flow version・device/OS・commit/build・実行結果・動画内の主要時刻を付ける。モック動画や失敗runの編集で成功を装わない。Daisへ再生できるMP4と実画面を提示する。
4. notification injectionのrouting成功、APNs受付、実機表示/タップは別証拠にする。Maestroだけでフレームの滑らかさや実購入を証明しない。変更した購入権限はSandbox購入/paid restore、APNs経路は実配信で確認し、未検証を明示する。
5. 正本main由来の署名済みartifact、privacy/metadata/review notesと実商品を照合し、既存ASC経路で提出する。`VALID`/upload/CIだけでは終了せず、対象version/build/submissionの公式 `WAITING_FOR_REVIEW` を読む。
6. Appleの承認・公開は提出完了とは別に追う。却下時は指摘と対象buildを取得→原因修正→影響する検証/必要なら再録画→一意な次build→再提出。同じ不明submissionを再送しない。

動画・provider receipt・生ログはGit外のprivate evidence storeへ置く。source/specには秘密を含まないartifact refと結果だけ残す。録画は自分のtest simulatorを対象にし、他人の端末状態・本番account情報を含めない。

## G6 — 全出荷アプリ・国別・課金の観測を揃える

公式ASCアプリ一覧と製品registry、RevenueCat project/app、公開URL、source path、ownerを照合する。少なくともAnicca/Honne/Dhamma/Thankful/Sleep Reset/Cherieを対象候補として確認し、未出荷・廃止・未接続を区別する。5アプリfeedを全出荷アプリ扱いしない。

国はASC storefront/territory、言語はapp localeとして別軸。install/new SDK customer/active customer/paid subscriberは別metric。ASCのprivacy threshold・report delay・部分日を保持する。downloadのauto/manual update・再download・restoreをfirst-time installへ混ぜない。アプリごとにsource failureを隔離し、Honneの欠測がAniccaの集計を止めない。

まず取得可能な公式ASC・RevenueCatを修復し、product analyticsのactivation/retention/funnelを接続する。新しいpaid分析toolや追加hostingを前提にしない。SDK設定・API権限・既存契約はprivate SSOT/公式readbackから確認し、不足を具体化する。

## G7 — Openダッシュボード・日次履歴

新しいdashboardを並立させず、既存 `https://aniccaai.com/open/` のsourceへ統合する。公開exportは現在別repo/ownerで運用される可能性があるため、loaded deployment・repository・collector ownerを照合し、Life Manager内に第二実装を作らない。他ownerへは具体的な参照と受入条件を渡す。

アプリ/国・言語/流入元/期間7日・30日/実験variantで絞れる。上段は新規install・onboarding完了・D7継続・MRR。日次線と7日移動平均、release/experiment注記を表示する。funnelは人数と率・分母を併記し、最大離脱、国別、流入元、実験の結果/未判定、free/pro通知設定と実配信のcoverageを確認できる。

| 指標 | 定義 |
|---|---|
| 完了率 | 対象flowを開始したunique userのうち同flowを完了した割合 |
| 画面離脱 | screen_view後、同session内30分以内に定義した次stepを完了しない割合。強制終了の瞬間を完全観測したとは言わない |
| activation | 最初の関連文言を表示し、保存または次の文言閲覧まで到達。価値との関係は後の継続で検証 |
| D1/D7/D30 | 初回cohort日から1/7/30日後に再利用した割合。UTC日付基準、成熟cohortのみ、地域別表示も分母を維持 |
| paid conversion | 初回cohort後35日以内の初回有料購入人数/first-time install。trialとは分け、同一取得範囲で照合できる場合のみ率を出す |
| RPI | 同一獲得cohortのD14/D35実収益/取得install。未成熟値は暫定表示、返金・fees控除前後を分ける |
| MRR | active recurringの月換算額。年額/12、月額そのまま、週額は公式provider定義に従い出所を示す。買切・trial・累計売上は除外 |
| profit | 実売上からrefund・platform fee・production/distribution/inference/VM等実費を控除。欠費用があればunknown/partial |

日次snapshotは上書きだけにせず履歴保存し、後日修正は原値・revision・理由を保持する。`observed_at/data_from/data_to/source/status/coverage`、numerator/denominator/cohortを付ける。null+reasonを0へ置換しない。public pageのheader更新だけでsource鮮度を主張しない。グラフ・最終取得時刻・日付境界・狭幅描画まで公開readbackで確認する。

## G8 — 配信と製品を一つの実験へ結ぶ

投稿/SEO記事/landingの `content_id/category/campaign_id/platform/account/locale` を登録し、当社所有のquote catalogへ結び付ける。SNSで反応したテーマをonboarding選択・app collection・通知の編集候補へ戻す。ユーザーの同意や文脈と無関係な単一SNS人気順へ置換しない。

既存のApple campaign tokenやUniversal Linkを優先する。インストール済みなら該当quote/collectionを開く。未インストールなら対応landing/storeへ送り、post-install同一quote復帰はsupported経路で検証できた範囲のみ約束する。UTM・投稿時刻だけで人ごとのinstall/paid attributionを捏造しない。iOSのprivacy制約/未判定sourceを残す。

実験は「onboarding順序→paywall表現/位置→地域別価格・trial/hard対soft→推薦/通知」の候補から、最大損失と十分な流入に基づき一つを選ぶ。順序はSSOTで理由付き更新。価格・配置・文言を同時に変えて単一要因の効果とは呼ばない。

割付は安定user単位で保持し、experiment/versionと実露出を記録。既存購読価格を上書きしない。開始前に仮説・主指標・最小検出効果・baseline・有意水準/検出力または採用Bayesian規則・必要人数・最短期間・停止条件を記録する。原則、一つの対象cohortで一つの主実験。標本不足の週は「未判定」であり勝者を作らない。

日次閲覧で繰り返し有意判定をしない。予定した固定終了判定か、選んだ統計方式の正式な逐次規則を使う。少なくとも曜日一巡と対象metricの成熟を待つ。SRM・重複・欠測・急な流入構成差を検出し、crash・権限破損・返金悪化等のguardrailは統計的勝者判定と別に安全停止する。

## G9 — 日次分析・週次改善・審査回復loop

新しいharnessを先に作らない。既存 `config/loop-registry.json`、日次集計、週次review、release経路を読み、固定の一製品ownerと既存schedulerのsupported設定を再利用する。OpenFaaS/Hermes等は既存経路の具体的不足がある場合だけ、公式機能・費用・認証・動画を含むiOS実行適性を比較して採用する。独自browser/scheduler/vault/万能API proxyを穴埋めで新作しない。

| 頻度/trigger | 実行すること | 成果物 |
|---|---|---|
| 日次 | 公式獲得/課金、product event、SNS指標の取得、欠測・異常・guardrail診断、履歴保存、Open更新 | source別freshness/coverageと日次差分、原因と次の1手 |
| 週次 | 英語市場の勝者/一次資料を更新、cohortと実験を評価、最大の改善候補を一つ選ぶ | 仮説、対象ファイル、期待metric、実験/通常bugfixの区分、SSOT cursor |
| 修正着手 | 最新main→専用worktree→spec更新→失敗回帰→最小実装→focused検証→独立review→CI/main | SHAと受入証拠、依存や他ownerへ影響しない差分 |
| リリース可能 | 同一成果物のMaestro録画、署名、metadata照合、ASC提出 | MP4、build/version/submission ID、公式状態 |
| Apple却下 | 正式理由と対象buildを取得、原因を修正、影響する検証後に再提出 | 指摘→修正→検証→新submissionの対応関係 |
| Apple承認/公開 | 状態/公開版を照合し、次の変更がreadyなら次版へ | 公開版・release注記と次cursor。変更無しの空updateは出さない |

毎日調べること、毎週改善すること、毎週実験が確定すること、毎日App Store承認されることは別。Apple審査時間を制御できるとは扱わない。審査待ち中に次候補の準備は進め、同じversionのsubmission/不明effectを重複しない。

運営ownerは「Mobile Product Growth Owner」、primaryはSSOT/受入/統合を所有する。Muse/Grok等の既存teamは同じspec・台帳を参照し、配信ownerは配信、製品ownerはapp source、dashboard ownerは公開exportを所有する。共有browser/profile/stateのleaseを尊重し、登録memberやsendだけを着手証拠にしない。

最初のlive実行でwake→receipt→start→分析結果→変更/提出または根拠付きno-change→dashboardを測る。自然な2回目の実行で同じ投稿・購入・提出・集計の二重effectが無いことを確認する。継続計測はprocess/PIDでなくprovider結果とfreshnessを監視する。業務の自然レポートは既存経路を維持し、対話agentがTelegramへ自発送信しない。

各runは `run_id/owner_id/occurrence_id/release_sha/loaded argv-env(秘密値除外)/phase/command/exit_code/effect/readback/provider_receipt_id/evidence_refs/error_class/retryable/next_action` を既存形式で記録する。原因不明を0・成功に置換しない。再試行は同一effectの公式照合後に行い、自己所有の修正可能な原因を先に直す。

spend-capは既存の範囲を維持。追加広告・有料tool・新規資金移動を自動で有効化しない。秘密はprivate SSOTに置き、dashboard/public動画へ個人単位の行動やcredentialを出さない。無人運営のために認証/権限を迂回しない。

## G10 — 他アプリ展開と終点

Anicca初回版がMaestro動画・審査提出まで通ってから、共通metric schema・collector・dashboard・release経路をHonne等へ再利用する。全アプリで同じonboarding文言や同じactivationを強制せず、製品ごとの初回価値とpaid eventを定義する。日次集計で一製品の失敗を他製品へ伝播させない。

全体完了は、全出荷アプリのinventoryとcoverageが明確、Openの日次履歴が実データから更新され、実験が有効な統計とguardrailで運用され、自然実行で改善→検証→動画→審査/却下回復→公開照合を一巡し、次の巡回にも同じ台帳と二重effect防止が効くこと。売上成長・$10K MRR・profitはその後も公式収益で追い、pipeline稼働を収益達成と呼ばない。

## 共有する画面案

- [ダッシュボード案](../../design/anicca-product-growth/growth-dashboard.html)
- [英語アプリ5画面案](../../design/anicca-product-growth/affirmation-app.html)

両方とも会話で提示した操作可能なmockのsource。全指標、価格の提示、特典、通知許可はデモであり、稼働済み機能や実収益の証明ではない。実装はnative SwiftUI/既存UIKitで行う。動画による完成確認はG5の実製品runで置き換える。

## 保管・復旧

spec/plan/designはrepoの永続pathへcommit/pushし、remote objectまで確認する。容量不足は診断開始点とし、対象・owner・稼働利用・再生成可能性を確認して自分の不要build/cache/録画の重複などを整理し、保存/pushを再試行する。他者の進行中worktree、不可侵store、秘密・固有成果物を一括削除しない。認証不足は既存private SSOTと公式経路を確認し、通常判断や容量整理をDaisへの承認質問へしない。

### 初回計測先の実確認

private build configにはMixpanel tokenが存在し、PostHogのproject key/hostは存在しない。PostHog SDKの同梱だけでは稼働扱いにしない。初回は既存Mixpanelへscreen/actionを送る。PostHogは設定済みの場合だけ同じeventを送る。分析サービス上のevent受信確認は未完であり、ローカル送信と区別する。購入callbackはtransaction IDで重複を排除し、表示価格は決済済み売上と区別する。CustomerInfo更新やrestoreから新規売上を作らない。PostHogの実験設定と全アプリdashboardは後続G6以降で扱う。

### 通知許可の回復導線

初回で通知をスキップした場合、Remindersから初回OS許可を要求できる。既に拒否済みならOS設定を開く。許可後は既存remote登録経路へ戻り、local配信を追加しない。Maestroでskip→設定→許可→通知本文表示を確認する。

許可要求の直後はアプリ内へ戻し、OS設定を自動で開かない。要求前のOS状態を読んで分岐し、要求後の実状態を読み直す。処理中の再タップを防ぎ、後から明示的に管理ボタンを押した場合だけOS設定を開く。
