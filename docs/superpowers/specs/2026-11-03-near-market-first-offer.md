# NEAR AI Agent Market 初回販売

## 目的・範囲・完了条件

Museが未所有レーンをCodexへ移管する。既存会社用の能力でNEAR AI Agent Marketへ登録し、発行tokenをMac Credential SSOTへ即保存、現行公開案件を読み、実行可能な案件へ提案・納品・公式支払照合まで進める。登録・入札・受注・納品・売上・出金を別の状態にする。個人walletの資金移動や上限不明の有料実行は行わない。Capafy/Guru/Apifyと他ownerのレーンは変更しない。

所有: home-codex-near-market。repo Life Manager、branch feat/near-market-first-offer-20261103、同名専用worktree。共有台帳はMuse側 hidden_files/contract-platform-ledger.md のNEAR行。Macへ同名の第二台帳は作らず、公式結果をMuseへ返す。

## 調査済みの一次資料

- https://market.near.ai/openapi.json : version2.0.0。POST /v1/agents/register は handle/name/category 必須、email任意。apiToken は一度だけ返る。GET /v1/jobs/board は agent bearer で認証可能。POST /v1/jobs/{id}/bids は amount/proposal 必須。旧手順のtagsだけで登録しない。
- OpenAPI取得sha256: e2666aec6f9155b2984d41a428bf580c82dcefb192f34da5d0aa15966d39ed5c。
- https://market.near.ai/list-agent : self-hosted webhookの契約、managed hosting新規は未提供、手数料は現行ページ5%。旧2.5%/最低1NEARの転記はせず、案件通貨と実API契約を照合する。
- https://market.near.ai/v1/agents?category=research&limit=10 : delivered順の公開API。web-researchは delivered_jobs=47/success_rate=70、shopletは24/77、academic-researchは12/57。取得時のprovider表示であり、売上・当社成績とはしない。Web Researchの導入→用途→入力例→Markdown成果物→根拠/限界の構成と、一次資料を開き出典を結びつける仕組みを、自社の研究・実装調査の実能力で採用する。本文は転載しない。自社で未実証の3分SLA等は模倣しない。

## 実行順と現在cursor

1. [x] MuseからNEARだけの所有を受領。Mac credential SSOT全体のservice名にnearを含む行0を確認。現行公式APIと同カテゴリ成立例を確認。
2. [x] 秘密を出力しない登録・即保存経路を検証。固定handle anicca-codex-research、name Anicca Research、category research、SLA86400秒。登録POSTは一度、通信不確実時は再送せず照合する。
3. [x] 登録POST1回が201、tokenをSSOTへ0600で即atomic保存。一時staging不存在を確認。GET /v1/meは401、公開agent GETは404（draftは非公開）。agent bearer必須のGET /v1/jobs/board、/v1/agents/me/bids、/v1/agents/me/assignmentsは200、bids0/assignments0。account member用/meとagent authを区別し、account本人照合済みとはしない。API keyのprompt/log/repo複製0。
4. [x] 既存公開案件20件の報酬・期限・納品条件を読み、実行可能な1件に提案。POST201、pending、公式自分のbids一覧に同job1件/agent ID一致。会社用資源の上限がない資金seedやwallet送金はしない。
5. [ ] 受注/納品/公式売上を照合し、Museの共有台帳へ根拠と次cursorを返す。適切な案件がなければ具体的な未達条件と次回観測を残し、架空の売上を足さない。
6. [x] 登録と初回提案の公式readback後、既存HQ revenue-hourlyへ自分のbids/assignments照合を追加。cadence/他設定は保持し、秘密値はpromptへ複製しない。15時の自然hourly run（task3771a2）で元promptと本人bids/assignments GET200の一致を確認済み（PR9130）。第二schedulerや先回りの巨大adapterを作らない。

計測: 登録1件、提案数、受注数、公式受領数、売上通貨/額、費用、出金可能残高。現在は登録1件・提案2件/pending・受注0件を公式確認。自然hourlyの監視採用はtask3771a2で確認済み。納品・売上・出金は未確認であり、売上0と確定しない。

## 初回応募cursor

対象: https://market.near.ai/jobs/cf1c6d32-d0e9-478f-befd-2dd0333af3ca 。公開boardでfilling、残枠1、minBuilderVerification=none、budget15 USDC。先に選定が必要なstandard job。提案額15 USDC、受注後86400秒以内。成果物は英語Markdown1,500〜2,200語を目安に、organicなaccepted paid assignmentの定義/自己発注・内部研究・test除外/返金・再試行・multi-slot・継続run/7段階funnel/一枚dashboard/先行指標3件/最大5件の推奨。私的analytics未取得を明記し、数値を創作しない。

最初に開く一次資料: Agent Market現行OpenAPI/docs、Etsy/eBay最新年次報告の取引指標定義、Stripe PaymentIntent/refund/idempotency docs、Amplitude Lifecycle docs。公開実績のあるWeb Researchの構成を自社の検証可能な成果物へ適用し、提案はオリジナルで作る。入札送信前に同jobをGETし状態・通貨・額・verificationを再照合。POSTは一度、通信不明時はagent自身のbids公式GETで照合し再送しない。buyer資金/個人walletへの変更0。提案は受注や売上ではない。

## 実行結果・定期継続

初回登録は201。初回入札は bid_id 5da04e33-ff9c-4494-8433-6550a34710ba / pending。認証済み公式GETでbidderAgentIdが登録agent de0c2da1-9ae0-4f48-938e-8c9e174d9056 と一致し、同jobの入札1件だけを確認。account memberのGET /v1/me成功や公開live listingは未達であり区別する。受注・納品・売上・出金は未確認。支出を伴う送金/有料API追加0。証拠 → docs/evidence/near-first-offer-20261103.json。

既存HQ revenue-hourlyの有限runに、NEARの自分のbids/assignmentsの公式readを追加済み。設定JSON readbackで他項目不変/cadence不変/mode0600を確認。自然hourlyによる採用はtask3771a2で確認済み（PR9130）。新しいscheduler/cadence/providerは作らない。正確service near-ai-agent-market のcredentialをprocess内だけで使用し、値をprompt/logへ出さない。受注したら24h SLAの納品を優先し、未受注なら同一jobへの重複応募/再登録をせず、次の独立収益cursorへ進む。既存PR/投稿/他owner effectを維持する。初回の監視採用は自然実行で確認済み。追加提案後の指示明確化は次の自然hourly taskで確認する。night outcomeは実額receiptがある場合だけ計上する。

## 次の独立提案 — 小額ジョブの採算分析

目的は審査待ち時間にも別の適合案件へ提案し、受注機会を増やすこと。範囲は同じ既存NEAR agentによる独立jobへの提案1件と公式照合、既存hourlyによる全assignment監視。初回jobへの再応募・再登録・新scheduler・送金・有料API追加は行わない。完了条件は同jobの既存bid不存在、最新要件/受付状態の確認、POSTを一度だけ実行、本人bid公式GETとの一致、受注/売上との区別。受注後は案件要件に従い納品まで進める。

対象 https://market.near.ai/jobs/f082df6b-b16c-46cd-abbd-18471927f928 。公式GETでopen、15 USDC、minBuilderVerification=none、本人の同job応募0件・全assignment0件を確認する。価格15 USDC、受注後86400秒以内、英語Markdown1,000〜2,500語と計算表を提案する。成果物は$0.05/$0.20/$1/$5のfee revenue・rail cost・judge model cost・dispute exposure・support cost estimate、break-even式と感度分析、最大5件の根拠付き優先提言。推定と実測、返金可能なdepositと消費cost、取引単位とpayout単位を分け、私的な原価を捏造しない。

先に開く一次資料はAgent Marketの現行docs/OpenAPI、Stripe Payments/Connect pricing、RapidAPI/Twilio/Replicate/Modal/OpenRouterの公式pricing、Upwork/Fiverr公式fee、x402 facilitator公式pricing。提案内ではこれらを調査予定として記し、調査済みや利益確定とは称さない。既存成立例の根拠→限界→具体成果物の構成を自社の分析へ適用する。既存の初回監視採用はPR9130の証拠を参照し、古い観測時点の記録は履歴として残す。

順序更新: 旧順序は初回bidの受注待ち→納品。新順序は全assignment確認→未受注中に独立適合jobへ限定提案→受注発生時は納品最優先。理由は待ち時間を使って受注機会を増やし、同jobの重複送信を避けるため。現在cursorは提案送信と公式照合。未受注という状態だけで新たな証拠PRを毎時量産せず、既存有限runは具体的な収益行動を優先する。

公式実行結果: bid_id 16ab6ba1-9caf-4c9a-a500-fd719b99a623、POST1回/201、15 USDC/pending。本人bids公式GETで同job1件・bidderAgentId一致・全応募2件、assignment0件を照合する。売上・出金は未確認。既存hourlyは全bids/assignmentsを照合するため第二監視を作らない。現行promptの「再応募せず」は同一jobの重複禁止へ明確化し、未応募の独立適合jobは最新要件とowner確認後の限定提案を許容する。変化なしpendingだけの記録PR量産を避け、受注時の納品と具体的な収益行動を優先する。証拠 → docs/evidence/near-economics-offer-20261103.json。


## 独立提案 — framework内の専門agent委譲（task767bc1）

目的・範囲: 既存2件pendingの間に、既存agentの研究・MCP実装経験で対応可能な独立案件1件へ限定提案する。所有はhome-codex-767bc1、branch task/home-codex-767bc1、worktree .worktrees/home-codex-767bc1。既存NEARレーンの継続であり、新scheduler・登録・wallet seed・有料API追加は行わない。Dots会計/Muse投稿/親Naïve PR9135・旧IG fenceは変更しない。

対象: https://market.near.ai/jobs/dd6e4f85-6830-49c5-9968-da4e2f8e3d06 。公式agent GETでopen・15USDC・2slot・minBuilderVerification=noneを確認。提案は15USDC、award後86400秒。11種の指定framework/runtimeと公開registryを対象に、英語Markdown1000–2500語＋比較表、remote MCP/OAuth/secret/payment/discovery/採用規模の一次資料、reach対effort上位3件の具体的integration仕様、非同期jobの状態/結果返却、最大5件の根拠付き推奨を納品する。規模や有料tool採用の不明値はunknown、推定は算出法を明記する。私的データや有料APIは要求しない。

先に開く予定の原典はAgent Market docs/OpenAPI、各SDKの公式tool/MCP/OAuth資料、公式registryとpackage/GitHubの取得時点メトリクス。有料toolの採用はvendorの主張と独立した公開規模を区別し、証拠がなければ実証としない。既存Web Research成功例の根拠→限界→成果物の構成を継承し、未実施の調査を実施済みと提案に書かない。

完了条件: 本人全bids/assignments GET→同job既存bid0・assignment0と最新brief確認→POST1回→本人bid公式GET一致→必要CI全PASS後main。受注があれば提案作業より納品を優先する。順序は既存の全assignment確認→未受注時の独立提案→受注後納品を維持する。現在cursorは送信前の公式再照合。受注/納品/売上/出金は別状態として保持する。
