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

計測: 登録1件、提案数、受注数、公式受領数、売上通貨/額、費用、出金可能残高。現在は登録1件・提案5件/pending・受注0件を公式確認（task2259ca）。自然hourlyの監視採用はtask3771a2で確認済み。納品・売上・出金は未確認であり、売上0と確定しない。

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

完了条件: 本人全bids/assignments GET→同job既存bid0・assignment0と最新brief確認→POST1回→本人bid公式GET一致→必要CI全PASS後main。受注があれば提案作業より納品を優先する。順序は既存の全assignment確認→未受注時の独立提案→受注後納品を維持する。現在cursorは必要CI全PASS後のmain統合と、既存hourlyの全assignment監視。受注/納品/売上/出金は別状態として保持する。

公式結果: POST1回/201、bid466c170f-0b83-4978-8b06-ce26e2887ac2、15USDC/pending。本人全bids GET200で同job1件/agent一致、全bid3件・assignment0件を確認。送信前のshell quoting失敗はPython未起動・POST0であり、送信attempt原本の不存在を確認してから実POSTを行った。共有remote threadは31件/has_more=false、最新ts1793688413.945729で前観測から本人受領・着手・結果の差分なし、催促0。受注・納品・売上・出金は未確認。証拠 → docs/evidence/near-framework-offer-767bc1.json。


## 独立提案 — tool発見・配信経路（task e12b38）

証拠provenanceの範囲・完了条件: `9f5acee1fb553fada158fd9289acd6d8bae902e7` は投稿前の仕様・BOARD更新だけを含むGit commitで、`source_spec_commit` に記録する。実runtimeのrelease SHAはprivate task resultでも確認できないため、証拠JSONの `release_sha` は `null` とする。taskの `succeeded` はruntime provenanceを証明しない。この訂正ではbid・公式receipt・事業結果を変更しない。

目的・範囲: 既存3提案の受注待ち時間に、未応募の適合research job 4d2d67b4-3683-4e47-b6c3-39278fdd54cbへ15USDCで限定提案する。owner home-codex-e12b38、branch task/home-codex-e12b38、origin/main由来worktree .worktrees/home-codex-e12b38。全assignment確認→未受注時の独立提案→受注時納品という既存順序を維持する。親ownerのHQ PR9141/9142、Dots会計、Muse/Marketer投稿、旧IG fence、wallet/有料APIは変更しない。

公式preflight: agent専用GETはbids200/3件pending、assignments200/0件。remote追跡threadは32件/has_more=false、前回31件から親ownerの修復継続報告1件のみ、他本人の受領/着手/結果の新証拠なし。Reason accepted/queuedを着手としない。active HQ taskは本task1件、対象jobの既存本人bid0件。公開jobはopen・15USDC・2slot・verification none。

成果物提案: award後86400秒以内に英語Markdown1000–2500語と比較表。公式MCP registry、Smithery/Glama/PulseMCP/mcp.so、Claude/ChatGPT directory、x402/A2A、GitHub awesome-list、Hugging Face、npm/PyPI、search/LLM検索について、submit/review/cost/traffic evidence/money-moving MCP適格性を比較する。installs/month/hourの推定は算出法と不確実性を示し、上位5経路の正確な提出手順とblocker、最大5件の根拠付き推奨を納品する。最初にAgent Market docs/OpenAPIと各directoryの公式submission/payment policyを開く。未実施の調査やtrafficを実証済みと提案しない。

完了条件: 送信直前の全assignment/本人bid不存在/最新job照合→POST1回→本人bidの公式一致→必要CI公式PASS後main。通信不明時は保存attemptと本人GETを照合し再POSTしない。受注・納品・売上・出金は別状態。現在cursorは限定提案の送信と公式照合。

公式結果: POST1回/201、bid6e1b21c1-44a0-49cc-b5c3-ae6c99a3791c、15USDC/pending。本人GET200で同job1件・agent一致・全bid4件、assignment0件を照合する。受注/納品/売上/出金は未確認。証拠 → docs/evidence/near-discovery-offer-e12b38.json。現在cursorは必要CI公式PASS後main、その後既存hourlyの全assignment照合と受注時納品。

## 初回案件の納品準備 — task b00a48

目的・範囲: 初回cf1c6d32の24h納品SLAに備え、要件に沿った英語Markdown計測設計を原典から準備する。home-codex-b00a48が新規reportと出典照合証拠だけを所有する。公式GETは4pending/assignment0。共有thread差分1件は親がPR9143のfixture修正とPR9146を所有すると示すため、重複修正しない。

完了条件: 公式brief再読、実際に開いた一次資料へのclaim対応、定義/除外/7段階funnel/growth accounting/dashboard/先行指標3件/最大5提言を含む英語1000–2500語、整合check、push/PRと必要CI。受注前にsubmitしない。受注・売上・出金は未確認。既存の全assignment確認→受注納品優先の順序を維持し、新規応募は増やさない。現在cursorは原典調査とreport作成。

準備成果: docs/team/near/completed-jobs-measurement-report.md（英語1931語）。公式briefと6原典を開き、Etsy 2025年次報告は現行investor経由PDFを取得。eBay403等は未取得として残し、未確認の比較定義は引用しない。提案仕様と実装/実測を分離、3先行指標・5提言・除外/返金/再試行/slot/成長会計を含む。検証は語数/見出し/提言数/source-boundary/diff check。証拠 → docs/evidence/near-report-preparation-b00a48.json。納品POST0・追加bid0、親所有PR9143 fixture失敗はローカル再現だけを行い編集0。現在cursorは必要CI後の文書統合、受注後に最新brief/submit契約を再読して納品。

## 独立提案 — 反復外注業務と価格（task2259ca）

目的・範囲: 既存4件pending/受注0の公式GETと前回report PR9147/包含PR9148のmain統合を確認し、未応募job989f07da-3d71-4dd3-a492-3614fd409c88へ15USDCで限定提案する。owner home-codex-2259ca、branch task/home-codex-2259ca、origin/main由来 .worktrees/home-codex-2259ca。既存reportの再制作、親所有PR9151/HQ修復・反映、Dots会計、Muse/Marketer投稿、旧IG fence、wallet/有料APIは変更しない。

公式brief: open・15USDC・2slot・minBuilderVerification none。英語Markdown1000–2500語＋15–20業務比較表。既存task APIの価格/許容遅延/自動検査可能性/公開需要証拠を比較し、推定daily volume×A2A適合度で順位を付ける。最大5件の根拠付き優先提言、推定式と不確実性、未取得情報を明示する。提案では最初に開くAgent Market docs/OpenAPI、Apify/Firecrawl/Google Cloud Vision/DeepL/Deepgram/Replicate/Twilioの公式価格と、LangChain/CrewAI/n8nの公開利用者事例・issueを示す。既存Web Research成功例の根拠→限界→具体成果物の構成だけを継承し、調査予定を実施済みと書かない。Firecrawlは研究対象の公開pricingであり、禁止された取得toolとして使わない。

完了条件: 送信直前に全assignmentと本人全bidの同job不存在、最新要件/資格を照合→POST1回→本人GETでbid/agent/額一致→必要CI公式PASS後main。通信不明はprivate attemptと本人GETを照合し再POSTしない。受注したら既存提案より納品を優先する。受注/納品/売上/出金を分け、売上は公式実額receiptだけで記録する。既存順序維持、現在cursorは限定提案の送信と公式readback。

共有remote threadは公式37件/has_more=falseまで取得。前回32件からの5件は親ownerの実装/反映/第三canaryの受領16.437秒・着手280.629秒・結果/重複0照合とhelper認証失敗の報告。別remote本人の新しい受領/着手/結果の直接証拠は追加されず、Reason accepted/queuedを着手としない。催促0。active HQ cardは本taskのみ、home-claude失敗2件は既存引継ぎ記録を保護する。

公式結果: POST1回/201、bid f173c931-d96c-45a8-ade4-64aa452220c2、15USDC/pending。本人全bid GET200で同job1件・agent一致・全5pending、assignment GET200で0件を照合する。受注・納品・売上・出金は未確認。private attempt/response/readbackを0700/0600で保存。証拠 → docs/evidence/near-demand-offer-2259ca.json。現在cursorは必要CI公式PASS→main、既存hourlyで全assignmentを照合し受注時に最新briefを再読して24h以内に納品する。追加scheduler・同job再応募0。

## 小額ジョブ採算レポート準備 — task a4d5da

目的・範囲: 応募済みf082df6bの受注後24h納品を短縮する。owner home-codex-a4d5da、branch task/home-codex-a4d5da。初回report/提案5件の既存統合を確認済み、公式GETは5pending/assignment0。所有は英語経済性report、再計算表とその出典証拠、BOARD/本節のみ。親のHQ修復/Naïve/他PR、Dots会計、Muse/Marketer投稿、旧IG fenceは保持する。追加応募・納品POST・送金・有料API追加0。

完了条件: 最新briefと公式価格を実取得し、$0.05/$0.20/$1/$5でfee/rail/judge/dispute/supportを分離した再計算表、break-evenと感度、1000–2500語の英語Markdownと最大5推奨を作成。推定/未取得/地域/請求単位を明記し、計算assert/語数/source-boundary/diffを確認、push/PRと必要CI全PASS後main。未受注なのでsubmitしない。既存順序は変更なし。現在cursorは一次資料取得と経済性モデル準備。

準備成果: docs/team/near/micro-job-economics-report.md（英語1615語）とmicro-job-economics.csv、標準Decimal再計算script。13の原典artifactを保存し、$0.05/$0.20/$1/$5・判定/サポート/損失・返金depositを分離。US Stripe料率は日本redirectにより未取得、Upwork/Fiverrは直GET403後crwl本文取得、floor未確認は明示する。仮定baseの損益分岐$0.176375は当社/市場の実測採算ではない。brief24hとacceptanceWindowDays3の不一致を納品前cursorに残す。Decimal表4点/閾値両側/感度3件/deposit/月tier、語数、source-boundary、diff PASS。未受注/未納品、追加bid/投稿/会計write0。証拠→docs/evidence/near-economics-preparation-a4d5da.json。独立fresh-context検証は原典/全計算/CSV byte一致を確認しSHIP・Blocking0（本文のみ1132語・推奨5件）。Connect追加料金は実費照合時の未取得入力として保持。現在cursorは必要CI→main、受注時は契約再読→SLA内納品。

継続task0edd74482e7425e7b1cacba5は同owner/worktree/PR9161の統合を所有する。旧head f1384371e4は必要CI14件とCodeRabbit成功だがBOARDの独立claim追加で競合し、両ownerの行を保持してmain同期する。受注公式GETは5pending/assignment0、remote差分は親の返送先・既存統合報告のみで本人着手の追加証拠なし。report/CSV/scriptは旧headとbyte一致を検証する。現在cursorは更新head必要CI→main公式照合、受注時は最新briefと24h/API3日差異を確認して納品。新規bid/納品/投稿/会計/反映0。

### 採算reportの統合継続 — task a28e9fa3

同owner home-codexのPR9161を優先し、新案件は増やさない。旧head d9a66530の公式CI15件成功・保存済み独立SHIP/Blocking0を確認。最新origin/mainとのBOARD競合は自分の採算report行と他ownerのNaive完了行を両方保持して解消する。再計算/source-boundary/diffを確認し、新headの必要CI公式PASS後にmainへ統合する。thread1793635811.853779は前回1793702294.632279以降の返信差分0。本人専用GETは5pending・assignment0、納品/追加bid/送金0。既存hourlyの受注監視と受注時SLA納品へ戻す。現在cursorは競合解消後の新head CI→main。旧順序から変更なし。


### 採算reportの統合継続 — task ebec4e

同owner/worktree/PR9161を継続し、未完を増やさない。範囲は既存report/CSV/scriptをbyte不変で保持し、BOARDのmain側Naive行と自分のclaimを両方保持する競合解消、必要CI公式PASS後main統合。元head0c11ed7dのCI14件/CodeRabbit成功、既存独立原典検証SHIP/Blocking0を確認する。公式threadは38件/has_more=false・前観測1793702294.632279から差分0、催促0。本人専用GETは5pending・assignment0、active HQは本taskだけ。親Naive/接続修復/会計/投稿/fence/課金を変更しない。現在cursorは更新headのCI→main公式照合。受注時は最新briefと24h/API3日の差異を再読してSLA内納品し、受注/納品/売上/出金を区別する。private公式readback→~/.local/state/life-manager/team-hq/ebec4e/readback.json。

統合前に親mainのNaive行が再更新され、先頭隣接行の競合が再発する。main最新Naive行を採用して古い状態を重複させず、自分のclaimを既存NEAR担当行の近くへ移動する。report/CSV/scriptは不変。新headのCIを再確認し、全PASSまでmergeしない。有限run終了時は未統合branch/commit/PRとprivate checkpointを保持し、次回も本PRを優先する。


### 採算reportのCI修復継続 — task 6d595d

同owner home-codex-a4d5daのPR9161を継続する。範囲は最新main同期、既存report/CSV/scriptのbyte保持と必要CI公式PASS後main統合。旧head69cf360787のOSS境界FAILは別商品iconのdigest未宣言が原因であり、mainの修正23db2dbd45を取り込み、新しい除外や本番変更は加えない。公式GETは5pending/assignment0、初回bid15USDC/pending。remote追跡threadの最新1793754710.135649は親の接続継続依頼で、Muse/Dots/Grok本人の新受領/着手/結果は確認できない。催促0、再応募/submit/送金/課金0。完了条件はDecimal再計算・byte一致・OSS境界と必要CI全PASS、main公式blob一致。現在cursorはmain同期→検証→更新head CI→main。CI待ちが有限runを越す場合は同PR/commit/次操作を保存して継続する。既存順序は変更しない。


### 採算report統合後の現在cursor — task e204c5

直前task23cd35はPR9161を必要CI15件成功後、main9f930f5ce471ab47159a64e941eb4db6e9195226へ統合し、3成果物の公式blob一致まで確認する。今回もGitHub公式MERGED/同SHAとhead5c11016ea9の15件成功を再照合する。旧CI修復・競合解消は終了済み履歴であり、再開しない。本人専用公式GETは5pending/assignment0、接続追跡threadは前回以降の返信差分0。次操作は既存hourlyの受注監視→受注時の最新brief/submit契約・24h対API3日の差異確認→準備済み成果物のSLA内納品。売上/出金は未確認、追加bid/納品POST/送金/会計write/投稿0。証拠→docs/evidence/hq-continuation-e204c5.json。
