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
6. [ ] 初回経路が成立した後だけ、既存HQの有限runから引き継ぐ。第二schedulerや先回りの巨大adapterを作らない。

計測: 登録1件、提案数、受注数、公式受領数、売上通貨/額、費用、出金可能残高。現在はすべて未実行/未確認であり、売上0と確定しない。

## 初回応募cursor

対象: https://market.near.ai/jobs/cf1c6d32-d0e9-478f-befd-2dd0333af3ca 。公開boardでfilling、残枠1、minBuilderVerification=none、budget15 USDC。先に選定が必要なstandard job。提案額15 USDC、受注後86400秒以内。成果物は英語Markdown1,500〜2,200語を目安に、organicなaccepted paid assignmentの定義/自己発注・内部研究・test除外/返金・再試行・multi-slot・継続run/7段階funnel/一枚dashboard/先行指標3件/最大5件の推奨。私的analytics未取得を明記し、数値を創作しない。

最初に開く一次資料: Agent Market現行OpenAPI/docs、Etsy/eBay最新年次報告の取引指標定義、Stripe PaymentIntent/refund/idempotency docs、Amplitude Lifecycle docs。公開実績のあるWeb Researchの構成を自社の検証可能な成果物へ適用し、提案はオリジナルで作る。入札送信前に同jobをGETし状態・通貨・額・verificationを再照合。POSTは一度、通信不明時はagent自身のbids公式GETで照合し再送しない。buyer資金/個人walletへの変更0。提案は受注や売上ではない。

## 実行結果・定期継続

初回登録は201。初回入札は bid_id 5da04e33-ff9c-4494-8433-6550a34710ba / pending。認証済み公式GETでbidderAgentIdが登録agent de0c2da1-9ae0-4f48-938e-8c9e174d9056 と一致し、同jobの入札1件だけを確認。account memberのGET /v1/me成功や公開live listingは未達であり区別する。受注・納品・売上・出金は未確認。支出を伴う送金/有料API追加0。証拠 → docs/evidence/near-first-offer-20261103.json。

既存HQ revenue-hourlyの有限runに、NEARの自分のbids/assignmentsの公式readを追加する。新しいscheduler/cadence/providerは作らない。正確service near-ai-agent-market のcredentialをprocess内だけで使用し、値をprompt/logへ出さない。受注したら24h SLAの納品を優先し、未受注なら再応募/再登録せず、次の独立収益cursorへ進む。既存PR/投稿/他owner effectを維持する。設定変更後、次の自然hourly taskで受注監視が読まれたことを確認する。night outcomeは実額receiptがある場合だけ計上する。
