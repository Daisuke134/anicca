# CFO provider公式仕様調査 — O3B-00a

確認日: 2026-08-02 JST  
対象: Moneytree LINK / Moneytree Web export / Binance / Base・Ethereum公開wallet / JPY FX  
範囲: 公式一次資料のread-only調査だけ。ログイン、OAuth同意、口座接続、API key作成、秘密値の確認、wallet署名は一切していない。

## 判定基準

- **VERIFIED FACT**: 直リンクした公式資料が明示する事実。各項目に資料名・URL・短い根拠を併記する。
- **INFERENCE**: 公式事実からこのCFO実装に必要な読み方を導いたもの。providerの可用性・契約状態には使わない。
- **UNKNOWN**: 公式資料で確定できないか、Daisの実アカウント・契約・対象addressに依存するもの。推測で補完しない。

## Moneytree

### LINK production / OAuth / API

- **VERIFIED FACT — production credential名・入手条件:** [Moneytree LINK「環境および接続」](https://docs.link.getmoneytree.com/docs/api-domain)は、検証環境と本番環境ごとに`client_id`、`client_secret`、`redirect_uri`の事前登録が必要で、本番接続情報は「原則として契約締結後」に渡すと明記する。したがって、production LINKには少なくともこの3つの登録済み値と契約状態が必要である。

- **VERIFIED FACT — API domain:** 同資料はproduction API domainを`jp-api.getmoneytree.com`、検証環境を`jp-api-staging.getmoneytree.com`とし、HTTPS / port 443 / TLS 1.2+ / SNIを接続要件とする。取得したaccess tokenの`resource_server`は、利用者の所在国により異なり得るとも記載する。

- **VERIFIED FACT — OAuthとredirect URI:** [Moneytree LINK「OAuth 2.0認可の流れ」](https://docs.link.getmoneytree.com/docs/obtaining-an-access-token)は、ゲストデータ取得には`code + PKCE`を対応、plain `code`と`implicit`は非対応とする。`client_id`、`response_type=code`、`scope`、`redirect_uri`が必須で、`redirect_uri`の登録・変更はMoneytreeへの問い合わせが必要とする。`state`も同資料では必須として実装を求める。

- **VERIFIED FACT — production OAuth URL:** 同資料はproductionの認可URLを`https://myaccount.getmoneytree.com/oauth/authorize`、金融サービス登録・管理URLを`https://vault.getmoneytree.com`としている。これはユーザー認可を伴う画面であり、本調査では開いていない。

- **VERIFIED FACT — 最小read scope候補:** [Moneytree LINK「ご利用可能なスコープ」](https://docs.link.getmoneytree.com/docs/api-scopes)は、`guest_read`を基本情報閲覧、`accounts_read`を銀行・card・電子マネーの名称/種別/残高閲覧、`transactions_read`を明細閲覧、`request_refresh`を登録金融サービスの資産情報取得として定義する。これら4 scopeが親仕様のread-only最小セットと一致する。証券を対象に含めるには、同資料が別途定義する`investment_accounts_read`と`investment_transactions_read`の必要性も接続前に確認する。

- **VERIFIED FACT — refresh / 再認可境界:** [Moneytree LINK「アクセストークン、リフレッシュトークンの有効期限」](https://docs.link.getmoneytree.com/docs/faq-access-token-lifetime)はaccess tokenを発行後1時間、refresh tokenを無期限・一回使用のみとする。refresh時には次回用の新しいrefresh tokenが返るため、token rotationの原子保存が必要である。同資料は失効/取消時の再認可トリガーを列挙していない。

- **VERIFIED FACT — rate limit:** [Moneytree LINK「APIレート制限」](https://docs.link.getmoneytree.com/docs/faq-rate-limiting)は、429を返す場合があり、reset時刻は伝えられないため指数backoff（初回3,000 msの例）を推奨する。一律の数値上限は公開していない。大量のユーザー一括取得は営業へ相談するよう案内する。

- **VERIFIED FACT — history availability:** [Moneytree LINK「財務データはどこまでさかのぼることができますか？」](https://docs.link.getmoneytree.com/docs/faq-historical-data)は金融機関により異なり、一部は最大5年前まで取得できるとする。全金融機関・全口座に同じ期間を保証する記載ではない。

- **VERIFIED FACT — data / security restrictions:** [Moneytree LINK「留意点」](https://docs.link.getmoneytree.com/docs/api-notes-api)は、access token、refresh token、client secretをURL queryに載せないこと、利用者が削除したobjectは後続APIから消え得ること、同じ送信元の過度なアクセスで429が返ることを明示する。CFO receiptは取得時刻とsource responseの識別情報を保存し、削除・再集計へ耐える必要がある。

### Moneytree Web export

- **VERIFIED FACT — Web railの存在:** [Moneytree「プランと料金」](https://getmoneytree.com/jp/app/plans-and-pricing)は「Web版から新規登録」「Web版からログイン」を掲載し、`データ出力 (XLSX/CSV)`をプラン比較の機能として表示する。

- **VERIFIED FACT — export期間:** [Moneytree Grow](https://getmoneytree.com/jp/app/grow)は、利用明細をCSV/Excel形式で出力・download/共有でき、「過去1年間」「最長過去2年分」と説明する。これはLINK APIの金融機関依存historyとは別のWeb/app export仕様である。

- **VERIFIED FACT — plan制約の存在:** 同Grow資料はAndroid版・Web版に一部未搭載機能があると注記する。したがって、Web exportをconnection railとして採用する前に、対象アカウントの実planとWeb UIでexportが有効かを実readbackで確認する必要がある。

- **INFERENCE — 実装上の扱い:** LINK未契約時は、上記の公式Web exportをユーザーが生成したimmutable source fileとしてimportするのが妥当である。ただし自動browser export・export頻度・個別planの機能有無は、本資料だけからは自動化仕様に固定しない。

## Binance

> この節のAPI事実はBinance公式GitHubのSpot API documentationと公式connector sourceで確認した**グローバルBinance仕様**である。Binance Japanの口座・endpoint・UIで同じ仕様が使えるとは結論しない。

- **VERIFIED FACT — key / secret / security type:** [Binance Spot API `rest-api.md`](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)は、secure endpointに有効なAPI keyと認証を要求し、API key/secret keyが機密であるとする。`NONE`以外のsecurity typeはSIGNED requestで、`USER_DATA`はprivate account information / trade history用、`TRADE`は注文用である。keyはAPI Managementで作成でき、defaultではTRADE不可と明記する。

- **VERIFIED FACT — read-only permission readback:** [Binance公式Java connectorの`AccountApi`](https://github.com/binance/binance-connector-java/blob/master/clients/wallet/src/main/java/com/binance/connector/client/wallet/rest/api/AccountApi.java)は、`GET /sapi/v1/account/apiRestrictions`を`Get API Key Permission (USER_DATA)`として実装し、対応する[Developers documentation](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account#get-api-key-permission)を直接参照する。接続後はこのendpointでpermissionをreceipt化できる。

- **INFERENCE — 必須権限の最小化:** 親仕様のread-only目的では`USER_DATA`のみを要求し、`TRADE`、withdrawal、transferのいずれも有効化しない。[Binance公式skills hub](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/p2p/SKILL.md)もread-only phaseを`Enable Reading` onlyと記すが、これは日本向けAPI Management UIのavailabilityを保証する資料ではない。

- **VERIFIED FACT — server time / signed request:** [Binance Spot API `rest-api.md`](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)は`GET /api/v3/time`をcurrent server time取得（weight 1）とし、SIGNED requestにはcurrent `timestamp`と署名を要求する。`recvWindow`はdefault 5,000 ms、最大60,000 msである。同期前にserver timeを読むことが必要になる。

- **VERIFIED FACT — account / balances / account permissions:** 同Spot API documentationは`GET /api/v3/account`を`USER_DATA`のcurrent account informationとして定義し、`balances`と`permissions`をresponseに含める。readback対象は残高、account type、permissionであり、注文作成を含まない。

- **VERIFIED FACT — trade history:** 同documentationは`GET /api/v3/myTrades`を特定`symbol`のaccount trade listとして定義する。`symbol`が必須、default limitは500・max 1,000、`startTime`と`endTime`の間隔は最大24時間、`fromId`指定時はそのtrade ID以降を返す。完全backfillを1回で行えるという仕様ではない。

- **VERIFIED FACT — deposit history:** [Binance公式Java connectorの`CapitalApi`](https://github.com/binance/binance-connector-java/blob/master/clients/wallet/src/main/java/com/binance/connector/client/wallet/rest/api/CapitalApi.java)は`GET /sapi/v1/capital/deposit/hisrec`を`USER_DATA`として定義する。`startTime`/`endTime`のwindowは0–90日、両方指定時は90日未満、limitは最大1,000であり、公式[Capital documentation](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital#deposit-history)を参照する。

- **VERIFIED FACT — withdrawal history:** 同`CapitalApi`は`GET /sapi/v1/capital/withdraw/history`を`USER_DATA`として定義する。通常のtime windowは0–90日、`withdrawOrderId`併用時は最大7日、時刻を指定しない場合は直近7日を返す。これは履歴の読取りであり、withdrawal実行endpointではない。対応する[Capital documentation](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital#withdraw-history)がある。

- **VERIFIED FACT — Earn / holdings:** [Binance公式Java connectorの`FlexibleLockedApi`](https://github.com/binance/binance-connector-java/blob/master/clients/simple-earn/src/main/java/com/binance/connector/client/simple_earn/rest/api/FlexibleLockedApi.java)は、`GET /sapi/v1/simple-earn/flexible/position`と`GET /sapi/v1/simple-earn/locked/position`をどちらも`USER_DATA`のposition取得として定義する。Flexible positionはpageを`current`/`size`で取得し、sizeは最大100。対応する[Simple Earn documentation](https://developers.binance.com/en/docs/catalog/investment-and-services-simple-earn/api/rest-api/flexible-locked#get-flexible-product-position)がある。

- **VERIFIED FACT — rate limits:** [Binance Spot API `rest-api.md`](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)は`/api/v3/exchangeInfo`の`rateLimits`で`RAW_REQUESTS`/`REQUEST_WEIGHT`/`ORDERS`を取得可能、429時はbackoff必須、反復違反は418のIP banになり得るとする。limitはAPI keyではなくIP基準で、`X-MBX-USED-WEIGHT-*`と`Retry-After`を監査できる。

- **UNKNOWN — IP allowlist:** 上記の公式資料はrate limitがIP基準であることを示すが、Binance JapanのAPI Management UIでIP allowlistを設定できること、設定方法、固定IP要件は確認できない。実key作成/画面readbackまでは「可能ならallowlist」は要件、availabilityは未確定とする。

- **UNKNOWN — Binance Japan availability:** `api.binance.com`、Spot API、Capital、Simple Earnのグローバル文書はいずれも、Binance Japan accountでこれらのendpoint・`Enable Reading`・deposit/withdraw/Earnが提供されると明記しない。日本向けの契約・account tier・region endpoint・history範囲は接続前に公式Japan support又は実readbackで確定する。

## Wallet

### Base / Ethereum public-address-only readback

- **VERIFIED FACT — Base Mainnet RPC:** [Base「Connecting to Base」](https://docs.base.org/base-chain/quickstart/connecting-to-base)はBase Mainnetをchain ID `8453`、RPC endpoint `https://mainnet.base.org`、native currency `ETH`として掲載する。

- **VERIFIED FACT — public endpointの制約:** 同Base資料はpublic endpointをrate-limitedでproduction trafficに不適切、HTTP only、WebSocketの`eth_subscribe`/`newHeads`/`logs`は非対応とする。連続CFO同期や長いhistory queryはnode providerが必要になる。

- **VERIFIED FACT — native balance:** [Ethereum.org JSON-RPC API](https://ethereum.org/developers/docs/apis/json-rpc/)は`eth_getBalance`を「given addressのaccount balanceを返す」と定義し、引数をaddressとblock tag/numberとする。readbackに必要なのはpublic addressと対象chain/endpointだけである。

- **VERIFIED FACT — ERC-20 token balance:** 同JSON-RPC資料は`eth_call`をchainへtransactionを作らずに実行するread-only contract functionとして説明し、ERC-20の`balanceOf`を例示する。[ERC-20 standard](https://ethereum.org/developers/docs/standards/tokens/erc-20/)はfungible tokenの標準を説明する。token balanceはtoken contract address、public wallet address、block tagで取得する。

- **VERIFIED FACT — token transfer logs / block timestamp:** JSON-RPC資料は`eth_getLogs`をfilterに一致するlogsの配列を返すと定義し、`eth_getBlockByNumber`はblock informationを返す。block objectの`timestamp`はblock作成時のUnix timestampである。したがって、receiptにはchain ID、block number/hash、timestamp、query filterを保存できる。

- **INFERENCE — read-only safety:** 上記read methodsの引数はpublic address、block、filter、call dataであり、private key / seed phrase / wallet password / signing materialを必要としない。本CFO connectorはpublic address以外のwallet credentialを要求・保存・表示しない。

- **UNKNOWN — address history / archive guarantees:** 標準JSON-RPC資料は`eth_getLogs`/block/transaction取得を提供するが、addressを渡すだけで完全な全transaction historyを返す標準endpointは示さない。Baseのpublic endpointはarchive state、広範なlog range、完全な過去historyを保証していない。対象wallet、対象token contract、開始block、providerのarchive/range limitは未確定であり、必要なら承認済みindexer/node providerを別途評価する。

- **UNKNOWN — Ethereum production RPC:** Ethereum.orgはJSON-RPC methodを文書化するが、共有のproduction Ethereum Mainnet RPC URLをこの調査では指定していない。Base endpointをEthereum Mainnet用に流用しない。

## JPY FX

- **VERIFIED FACT — 採用候補とauthority:** [European Central Bank「Euro foreign exchange reference rates」](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)はECBが公表するEUR baseのreference ratesで、JPY（Japanese yen）を掲載する。CFOのJPY評価には、公式中央銀行の再現可能なdaily reference sourceとして使用できる。

- **VERIFIED FACT — 通貨範囲・cadence:** 同資料は全掲載通貨をEURに対するquoteとし、reference rateをTARGET休業日を除く各営業日おおむね16:00 CETに更新するとする。JPYを含む掲載通貨だけをsupport対象とし、任意のcurrency pairやintraday FXを保証しない。

- **VERIFIED FACT — history / machine retrieval:** 同資料はlatest CSV/XMLとtime-series CSV/XML downloadを提供する。[ECB Data Portal API overview](https://data.ecb.europa.eu/help/api/overview)はSDMX 2.1 REST serviceがECB Data Portalのstatistical data/metadataへprogrammatic accessを提供すると明記する。過去rateはtime-series又はSDMXで取得し、source URL、series key、observation dateを保存できる。

- **VERIFIED FACT — terms / attribution:** [ECB「Disclaimer & copyright」](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)は、情報を正確に配布/複製しECBをsourceとして引用する条件でfree useを認め、変更時は明示を求める。同時にFX reference rateをtransaction目的で使うことを強く推奨しないと前掲rate資料は明記する。

- **INFERENCE — deterministic timestamping:** valuation recordには`base=EUR`、quote currency、observation date、ECB publication source URL、retrieved_at、raw value、conversion formulaを保存する。例えば非EUR通貨からJPYへのcross rateは同一observation dateのEUR quotationから計算するが、計算済み値を原典値と混同しない。

- **UNKNOWN — unsupported / intraday rate:** ECB掲載外通貨、休業日のrate選択、intraday・execution価格、provider固有の約定FXはこのsourceから確定できない。これらは別sourceのprovenance policyを先に定義する。

## 未確定事項

1. **Moneytree LINK production契約:** Daisの契約有無、production `client_id` / `client_secret`、登録済み`redirect_uri`、clientに許可されたscope、実resource serverは未確認。本資料はproduction利用可能を主張しない。
2. **Moneytree Web exportの実rail:** 公式ページはWeb導線とXLSX/CSV exportを示すが、Daisのplan、Web UIでのexport可否、export file schema、同一期間の繰返しdownload可否、自動化を許容する利用規約は未確認。実Web sessionを操作する前にofficial UI/readbackで確定する。
3. **Moneytree termsの自動取得制限:** LINK technical documentationのsecurity restrictionsは確認したが、個人Moneytree Webのfull Termsを今回のread-only crawlで本文確認できていない。CSV/XLSXをCFOへimportする用途の自動処理可否はUNKNOWNである。
4. **Binance Japan地域仕様:** 日本口座のAPI key発行可否、`Enable Reading` UI、IP allowlist、global endpoint利用、Spot/Capital/Simple Earnの各endpoint、retention・rate limitは公式Japan固有の根拠を取得できていない。global docsを根拠に接続しない。
5. **wallet対象:** network、public address、token contract、開始block、Ethereum Mainnet providerは未指定。private key、seed phrase、wallet password、署名権限は本connectorの入力ではない。
6. **RPC history保証:** Base public endpointのarchive state、large log query、full address historyは未保証。必要時はread-only node provider/indexerを候補ごとに公式terms・rate limit込みで追加調査する。
7. **FX coverage:** ECBはdaily EUR reference ratesであり、intraday/execution conversionや掲載外通貨は対象外である。

## Sources

### Moneytree

- [Moneytree LINK — 環境および接続](https://docs.link.getmoneytree.com/docs/api-domain)
- [Moneytree LINK — OAuth 2.0認可の流れ](https://docs.link.getmoneytree.com/docs/obtaining-an-access-token)
- [Moneytree LINK — ご利用可能なスコープ](https://docs.link.getmoneytree.com/docs/api-scopes)
- [Moneytree LINK — access / refresh token lifetime](https://docs.link.getmoneytree.com/docs/faq-access-token-lifetime)
- [Moneytree LINK — API rate limiting](https://docs.link.getmoneytree.com/docs/faq-rate-limiting)
- [Moneytree LINK — historical data](https://docs.link.getmoneytree.com/docs/faq-historical-data)
- [Moneytree LINK — API notes](https://docs.link.getmoneytree.com/docs/api-notes-api)
- [Moneytree — プランと料金](https://getmoneytree.com/jp/app/plans-and-pricing)
- [Moneytree Grow — export説明](https://getmoneytree.com/jp/app/grow)

### Binance

- [Binance Spot API official documentation source](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Binance Developers — Account / API key permission](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account#get-api-key-permission)
- [Binance Developers — Capital / deposit & withdrawal history](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital)
- [Binance Developers — Simple Earn positions](https://developers.binance.com/en/docs/catalog/investment-and-services-simple-earn/api/rest-api/flexible-locked)
- [Binance official Java connector — wallet APIs](https://github.com/binance/binance-connector-java/tree/master/clients/wallet)
- [Binance official Java connector — Simple Earn APIs](https://github.com/binance/binance-connector-java/tree/master/clients/simple-earn)
- [Binance official skills hub — read-only permission minimization](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/p2p/SKILL.md)

### Wallet

- [Base — Connecting to Base](https://docs.base.org/base-chain/quickstart/connecting-to-base)
- [Ethereum.org — JSON-RPC API](https://ethereum.org/developers/docs/apis/json-rpc/)
- [Ethereum.org — ERC-20 Token Standard](https://ethereum.org/developers/docs/standards/tokens/erc-20/)

### JPY FX

- [ECB — Euro foreign exchange reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
- [ECB Data Portal — API overview](https://data.ecb.europa.eu/help/api/overview)
- [ECB — Disclaimer & copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
