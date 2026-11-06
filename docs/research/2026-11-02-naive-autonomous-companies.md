# Naïve・自律企業・評価基盤の調査記録

観測日: 2026-11-03。実行順と状態の正本は unified SSOT。本資料は根拠と提案であり、別の実行キューではない。

## 要点と訂正

旧調査の会社状態メモは10/28の記録で止まり、Grok側の後続作業を捉えていなかった。今回 `Daisuke134/sanbou-ops` の `team/naive-sdk/NOTES.md`、`team/opportunities/naive-hackathon/DEMO-PROOF.md`、demo source/README/recordings、LM-ON-NAIVE-EVALを取得し訂正する。**SDK導入と実inferenceは10月末の記録で確認できる。後続で公式APIのlive readbackを取得した。下記の最新節を現在判定に使い、過去の未取得状態と区別する。**

評価は旧LM-EABの拡張だけで済ませず、公開名 **BusinessRun Bench** の実行suiteを作る。既存record scorerは「経済記録の契約検証」と表示し、モデルの事業遂行能力と混同しない。既存Business Processが継続業務と通信障害を既に扱うため、同等の自社simulatorを再実装しない。

## 社内状況の根拠

| 対象 | 新たに確認した記録 | 現在の限界 |
|---|---|---|
| SDK | Grok VMのVetta SDK0.10.0/CLI0.10.1導入記録 | npmの現在最新や全VM導入の確認ではない |
| 実inference | 10/30頃の修復後に約20 session、10/31のsales応答OK、約$0.007986という記録 | 当該履歴。今のsession成功を保証しない |
| 組織 | Anicca、CEO/growth/builder/sales/CFOの5役割とboard・cronの配置記録 | 登録済みと現在稼働中を区別 |
| 予算 | 10/31の残高約$0.68–0.72、CEO cap到達と後続cap変更の履歴 | fresh balance/capは未取得。新規支出や他サービスkey流用をしない |
| デモ | local rehearsal記録。live版はMIN_BALANCE_USD=2で止める設計 | localは定型文、real board APIを使ってもmodel推論の証明にならない。Capafyはread-only、公開/投稿を完了としない |
| domain | agents.aniccaai.comのpending_dns記録 | 現在のDNS・inbox・tenant提供は未確認 |
| 顧客向け | LM-ON-NAIVE-EVALの軽量顧客$1–3/月等の見積り | 推定。実費・ToS/resale・tenant分離・継続運用を未検証 |
| credential | remoteの既存保管場所をowner記録で特定。Macの正本全件にservice naive/vetta完全一致は発見せず | 会社にaccountが無いという意味ではない。秘密値を取得/複製/公開しない |

Grok・MuseへReason Networkで直接照会し、さらにSlack #agents-hqで両者をmentionしてlive readbackを依頼した。[照会thread](https://dais-45u3124.slack.com/archives/C0CBLBGSBJN/p1793631334314609)。最新の確認時点で返信なし。ReasonのqueuedとSlack送信成功は、担当の受領や作業開始ではない。

## SDKの新旧

旧starterは `@usenaive-sdk/node` / forUser / Account Kit、現在のManaged Agentsは `@usenaive-sdk/vetta`、api.vetta.sh、vetta CLI。会社層はblueprintとnaive.config.ts/naive up。[旧starter](https://github.com/usenaive/naive-starter-template)、[公式docs](https://usenaive.ai/docs)。旧keyの互換性は推測しない。今回の実装範囲はbenchmark runnerで、既存Naïve org・配信loop・production設定は変更しない。

## ベンチマークの使い分け

| 評価 | 確認した仕組み | 私たちへの用途と限界 |
|---|---|---|
| Clipping Bench | 約30日、初期$300、決定的シミュレータ、終端精算。ルール準拠のscript baselineとhidden stateを読むoracleも表示 | 長期運用・待ち・予算・記憶・投稿規律の比較。ゲーム内$は実収益ではない。5時間cooldown等は実SNSの普遍仕様ではない |
| Short Form Bench | 7日のbrand運営、現金・在庫原価・債権債務による価値、各モデル3 seasons。simulated viewers | 営業・販売・返金・誤入金対応等。実人間の行動予測精度や因果効果は未検証 |
| Harness studies | モデルを固定してharnessを比較。terminal/business/workplace/PRD等 | モデル差と基盤差を分ける手本。小さいtask slice・seed数・不完全な費用cellを総合SOTAに拡張しない |
| LM-EAB | synthetic recordから費用・自律性・経済算術を採点 | 現状は採点器の契約確認。agentが仕事をする共通環境、独立adapter、未見課題、反復比較、実経済traceが必要 |

根拠: [Clipping](https://usenaive.ai/benchmark/clipping-bench)、[Short Form](https://usenaive.ai/benchmark/short-form-bench)、[一覧](https://usenaive.ai/benchmarks)、[Managed Agents説明](https://usenaive.ai/blogs/introducing-naive-managed-agents)。Managed Agents記事はtrial rowsを内部DBに保持し未公開と明記。Short Formは自分のagentを走らせたい場合の連絡先を掲載する。今回公開GitHubに両media simulatorの実行コードを確認できず、公開ページがあるだけで手元で再現可能としない。

推奨する評価は三層。①外部の既存benchで比較する。②未見の自社業務を比較する。③限定本番運用で実売上・費用・介入を確認する。これらは別の証拠として報告する。

独自課題の候補は、既存販売事業の「依頼→受入条件→納品→請求照合」。同じ入力・予算・制限で、固定script、現行Life Manager、Naïve経由を比較する。課題成功率、成功1件あたり費用、完走時間、介入回数/秒、重複・不明effect、費用控除後成果を分けて出す。提案であり実装済みではない。平均だけでなく試行数・分散・失敗例を公開する。反復回数はpilot分散と費用から定め、3回を統計的十分性としない。

## ハッカソンまでの残作業案

公式eventは11/7–8 SF、全teamのNaïve SDK使用、承認された参加者のみ、実稼働のlive demoを要求する。Naïve側LPの賞品TBDに対し、YCイベント本文は賞品詳細を掲載する。現金賞金と現物・creditの総額を混同しない。[YC公式イベント](https://events.ycombinator.com/naive-autonomous-companies-hackathon)、[Naïve公式LP](https://usenaive.ai/hackathon)

公開本文には、事前開発済み全成果物の持込みを許可する明文を確認できない。事前の調査・環境準備・評価設計は進め、既存部分と会期中の変更をcommitで分けて開示する。持込み適格性は運営規約/本人宛案内の確認事項として残す。参加承認・渡航の確認も今回していない。

1. remote goalの設計書・最新ログ・配置先を取得し、現行担当と実行環境を特定する。
2. 既存credentialの保管先・org・残高・spend cap・SDK世代を照合し、現行APIのread-only疎通を確認する。
3. 一事業の一業務を選び、Naïveで実際にagent/sessionが動く最小adapterを作る。既存の配信ownerや本番scheduleを二重起動しない。
4. 顧客獲得→制作/納品→請求/費用照合のうち実際に完走した範囲を記録し、人間・外部AIによる修復も介入として記録する。
5. 同条件baselineを取り、2–4分のlive demoを「依頼・判断・成果・介入・費用」で構成する。事前/会期中の成果を分ける。

これは既存全体TODOの無断reorderではなく、Naïve laneを受け入れる際の依存順。優勝・売上の保証ではない。

## 分野の学習地図

- Naïve: 会社をtemplateとして配布し、runtimeと評価を接続する。[会社の定義](https://usenaive.ai/blogs/what-is-an-autonomous-company)
- Andon Labs: シミュレーション→実店舗運営→Pion。自社記事はシミュレーションと現実の隔たり、記事時点で店舗/caféが未黒字であることも説明する。[Pionの背景](https://andonlabs.com/blog/why-we-built-pion)
- Paperclip: self-hosted OSSで組織図・予算・governanceを扱う。人間による方向付け・承認を明記。[公式about](https://paperclip.ing/about/)
- Conway: agentの暗号学的identityとcreatorの登録。identityやwalletの存在は採算性の証明ではない。[公式docs](https://docs.conway.tech/automatons)
- Simile: 人間/集団の反応を扱うsimulation領域。事業を動かすagentと、顧客行動を予測するモデルは別の評価対象。[公式](https://www.simile.com/)

専門性の柱は、①長期の意思決定と状態管理 ②権限・identity・予算 ③再現可能な環境と採点 ④実利益と顧客価値 ⑤行動予測と因果介入。what-ifの予測精度と「その介入で人の生活が改善するか」を同一視しない。未見の人・期間・環境での予測評価と、同意を得た現実の介入評価を分ける。

## 記事の制作方針

参照する構成はNaïveのManaged Agents記事とAndonのPion記事。前者は結論→費用分解→比較表/構成図→実装→限界、後者は研究上の問い→実験→失敗trace→現実との隔たり→製品をつなぐ。本稿はこの構成を使い、本文・画像を転用しない。両記事の閲覧数・conversion・販売貢献は取得していないため「成果実証済みの勝者記事」とは呼べない。この穴を残した編集上の参照である。

草稿は独自のMermaid構成図と比較表を含む。画像生成・第三者画像の転載はしない。公開試験では読了率、出典クリック、評価再現手順への遷移、適格な問い合わせを測る。現在それらの測定値はない。

## 取得と検証の限界

Firecrawl skillを読んでconnector検索を試みるが、空link_id拒否後、非空IDによる実行は `Unknown tool(firecrawl.firecrawl_search)`。成功や収集credits=0を主張しない。代替の公式ページ取得、crwlによるYC event本文取得、ghによる公式repo/現行mainを使う。Grokの別repoの実装/証跡は取得済み。live Naïve orgは下記の公式readbackで取得済み。

今回の追加指示により製品runner・catalog・Actionsと実行証跡を追加する。投稿・決済・既存production loopは変更しない。詳細は下記の実測資料を参照する。

## 全9評価の詳細と実測

全ての公式ページを取得してscore/期間/seed/選択条件/分母/欠測費用まで読み、機械可読一覧20項目にした。各評価の詳しい解釈と引用は[記事](../articles/2026-11-02-naive-autonomous-company-ja.md)、pinと全一覧は[catalog](../../products/businessrun-bench/catalog.json)、実行は[RESULTS](../../products/businessrun-bench/RESULTS.md)に集約する。

取得したBusiness sourceには9つのprocess task.yamlが存在する。READMEの7件という概要より、固定commitの実ファイルとall実行の9件を採用する。35件という旧予定の数字ではなく、9task×5seedなら45条件。strict validatorは13条件の成功後にmargin-bridge seed3で生成器のゼロ除算が発生し、一括検証は未完である。公式graderの変更や失敗seedの隠蔽はしない。

設計上の最優先学習は、①modelとharness比較を分ける ②期間/seed/背景actorを揃える ③成功単価にhost/背景費用を含むか示す ④tuningと未見課題を分ける ⑤選択した比較だけで全順位を名乗らない ⑥インフラ障害を分類し全attemptを残す、である。

## 一般提供の追加確認

公式terms §4.2はサービスアクセスの共有/再販/再許諾に書面同意を要求する。[原典](https://usenaive.ai/terms)。LM-on-Naïveの顧客向け構成の適用範囲と既存契約許諾を確認する必要がある。既存許諾が無いと断定せず、Grok/Museへ存在と適用範囲のみ照会する。これは自社コードのbenchmark OSS公開とは別の境界。Computerは公式docsからLinux micro-VM・turn間pause/resumeを確認し、V8 isolate予定と提供済みを分ける。[Computer](https://usenaive.ai/docs/capabilities/computer)。

## 初回の公式API readback

取得時点: 2026-11-03 JST。Codex自身の1Password接続のnaive項目からloginを回収し、private SSOT exact service naiveへmode600で登録。現行API keyではなくメール/passwordの記録だった。公式POST /v1/auth/sessionで同じAniccaへ通常login成功し、得たvt_ sessionも正本へ保存する。秘密値・raw会話・promptはrepoへ入れない。以下はread-only GETのallowlist。[取得証拠](evidence/naive-live-20261103/)。

- OrganizationはAnicca、balance $11.590718、setting_up=false。Standard active。古い残高約$0.7は現在値ではない。API URLはapi.vetta.sh/v1、date version2026-09-30を指定する。
- 6agent: CEO/growth/builder/sales/CFOの5役割とn1-verification。5役割のmodelはGLM-5.2-FP8、verificationはDeepSeek flash。登録と実稼働を分ける。
- 現在のComputer inventoryは0、has_more=false。直近sessionもcomputer_id=null。platformがmicro-VMを提供することから、自社agentのVM割当済みとは言えない。過去のcomputer支出$0.600419も現在VM存在の証明ではない。
- CEO deploymentはenabled=true、cron0 9 * * *、Asia/Tokyo、schedule_status=scheduled。次は11/3 09:00 JST。予定があることを業務成功としない。
- 直近10session中、budget_paused7件/end_turn3件。11/2 09:00JSTのCEO sessionはend_turnで$0.405272消費、その後はCEO/builderのpauseを確認する。end_turnは会話終了であり納品/売上ではない。
- 現在のCEO budgetは月$1、max_task$0.25。他4役割は月$2/max_task$0.25。deployment budgetは$1。異なる層の値を混ぜない。
- builderはsession capのbudget.exceededで停止する。session budget250000、consumed29517なので残220483 microUSD。最後に観測できた成功callのquote222884はこの残額より2401大きく、予約見積による拒否という説明と整合する。ただし拒否された次callのquote自体は記録に無く、2401を当該拒否の確定差額とは扱わない。CEOのbudget.exceededは別のagent cap境界。実消費$0.029517だけを見て『$0.25未満なのに不具合』とも、残高を見て『資金不足』とも結論しない。公式budget.exceededの境界を使って次の修正を決める。
- CEOの公式version履歴は、v14が月$10/max_task$10、v15が月$10/max_task$0.50、v16が月$1/max_task$0.25。DEMO-PROOF.mdの$10記録はv14と一致し、その後に設定変更がある。古い値を意図せぬdriftと断定して復元しない。現在deploymentのagent_versionはnull、current_versionは16。11/1 00:00Z以降のCEO費用は$0.835543。これは問い合わせ区間の実費であり、組織timezone基準のbudget内部台帳や次call予約額そのものとは区別する。
- この初回調査では既存agent/model/budget/cron/computerを変更せず、新しい推論支出を発生させない。後続の専用browser担当の有料実行は次節へ分ける。RESTのloginと読み取りであり、SDK経由benchmarkや顧客向けtenant運用が完了したわけではない。

Reason/SlackのGrok/Muse返信は未取得。Reasonはpull/idle、ローカルAGMSGのlm/anicca-dev/capafyには対象名を発見せず、remote bindingもnone。新sessionを相手本人として捏造/起動しない。公式API readbackで現在値は自力確認し、Grok/Muse自身のVM/provider・source owner・demoの後続証拠は別途残す。

## 専用ブラウザ担当の現在位置

既存6agentに加えて専用担当を作成し、main265bab69由来のv3を適用する。画像観測、actによる動画検索30件の確認、同Computerのメモwrite/別session read、自然idleのpausedを確認する。公式spendは405957 microUSD。業務shell/APIは与えない。Google認証はservice/hostを修復しても専用login/provider操作の境界が残り、未完。成功文章と実画面の矛盾を記録し、売上や完全自律運転へ昇格しない。詳細は[実測証拠](evidence/naive-browser-20261103/hosted-readback.json)と[記事](../articles/2026-11-02-naive-autonomous-company-ja.md)。Muse Relayは最小inferenceのみ返答し、Grok/Muse/Dots本人の実ブラウザ業務手順は未取得。
