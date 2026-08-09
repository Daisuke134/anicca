# Life Manager 競馬AI financial organ 設計仕様（Mac-native public web）

## Status、truth、責務

| 項目 | 契約 |
|---|---|
| Status | **REALITY GATE REQUIRED — LIVE PURCHASE DISABLED** |
| 対象 | Life Manager financial organ の第8候補 business_id: horse_racing |
| 現在のactive stage | HRA-2F TDD refactor（ACTIVE）。HRA-2RはHRA-2F GREENまでBLOCKED、JRA/NAR実recordは0 |
| plan / gate / verification owner | Sol |
| edit / code / execution owner | Luna |
| 購入処理 | PurchaseExecutorは常時disabled。HRA-6の全gateなしに有効化しない |

この文書は無料の公開Web ingestion、source別Reality Gate、実測値のtruth label、受入条件の正本である。horse_racingはCFO-0c exact-seven完了後にregistry v2で候補として扱うだけで、revenue businessとして承認されたことを意味しない。Sol owns plan/gate/verification; Luna owns edits/code/execution.

### 現在のevidence table

| Evidence | 実測値 |
|---|---:|
| real JRA public-web records | 0 |
| real NAR public-web records | 0 |
| NAR secondary route observations (links only) | 1 |
| live shadow runs | 0 |
| live orders/payments | 0 |

route observationやHTTP/DOM successはrecordではない。row、observed schema、hashを含むmanifestがない限り、provider connectivity、data accuracy、model accuracy、ROI、Telegram/CFO revenue、収益を証明しない。unknownを0へ変換せず、未取得はBLOCKEDと表示する。

### Committed proof boundary

0fe627cd proves only the superseded Windows boundary; it is not compatible with the approved Mac-native free-web design and is not HRA-2F/HRA-2R evidence.

### Evidence classes

すべてのreceipt、Telegram、CFO projection、model reportに次のtruth labelを明記する。

- SYNTHETIC_TEST: 人工fixtureでpure mechanicsだけを検証した証拠。
- REAL_PUBLIC_WEB_RECORD: JRA公式公開ページから、robots/termsとrate limitを守って取得した非合成record。
- PUBLIC_WEB_SECONDARY: nar.netkeiba.com等の二次公開ページから得たrecord。NAR laneはSHADOW-onlyであり、official/licensed/compliantとは呼ばない。
- LIVE_SHADOW: REAL_PUBLIC_WEB_RECORDまたはPUBLIC_WEB_SECONDARYでdecisionしたが注文・決済をしていない証拠。
- LIVE_CASH: HRA-6後にofficial settled result/payoutとreceipt reconciliationを通過した証拠。現在は常にdisabled。

SYNTHETIC_TEST、PUBLIC_WEB_SECONDARY、未settled LIVE_SHADOWはreal revenueへ合算しない。HTTP/DOM successだけ、ページの存在だけ、リンクだけではrecordにならない。

### 永久 rejection（歴史的メモ、activeではない）

Physical Windows、VM/Wine/COM、JRA-VAN/Data Lab/JV-Link、UmaConn/NV-Link、JRDB、every paid data sourceは永久にrejectする。これらはarchitecture、source、requirement、manifest、acceptance、reuse candidateのいずれにも登場しない。

## 1. 目的とHard non-goals

### 目的

個人利用だけを対象に、Mac-nativeなzero-cost public-web ingestionでJRAの公式公開ページをprimary sourceとして観測する。NARは当初nar.netkeiba.comを二次公開ページとして観測し、schema/audit/SHADOWに限定する。sourceごとにactual non-synthetic race recordを1件以上得てから、observed schema、append-only store、chronological audit、market baseline、walk-forward model、official outcome reconciliationへ進む。

### Hard non-goals

- paid source、subscription、credential、provider login、SaaS、public APIを導入しない。
- raw page、raw row、実馬名、secret、credentialをGit、Telegram、cloud、CFO、公開ページへ再配布しない。
- browser login、DOM click、注文API、wallet/bank mutation、bet、実購入を実装・実行・有効化しない。
- crwlはサイトごとのrobots/termsの範囲とcourteous rate limit内だけで使う。許可が確認できない自動化は継続しない。
- 収益、勝率、ROI、$10K/monthを保証または推定しない。$10Kはevidence-driven target only。
- 説明層にdecision、probability、odds、EV、stake、action、capを決めさせない。

## 2. Mac-native public-web architecture

### Gateで下流を止めるflow

~~~mermaid
flowchart TD
  A[HRA-0 research/spec] --> B[HRA-1 safety contracts]
  B --> C[HRA-2a Mac-local private boundary]
  C --> F[HRA-2F TDD free-web ingest boundary]
  F -- GREEN --> G{HRA-2R source Reality Gate}
  F -- RED/BLOCKED --> X[DATA BLOCKED: refactor required]
  G -- JRA official PASS --> J[HRA-2S JRA observed schema]
  G -- NAR secondary PASS --> N[HRA-2S NAR secondary schema]
  G -- BLOCKED --> X[DATA BLOCKED report only]
  J --> D[HRA-3D actual data audit]
  N --> D
  D --> M[HRA-3M baseline/walk-forward/calibration]
  M --> S[HRA-4 live-data SHADOW + official outcome]
  S --> T[HRA-5 Telegram/CFO evidence separation]
  T --> P[HRA-6 terms/order/tax/receipt gate]
  P --> Q[HRA-7 micro-live review, still disabled]
  Q --> R[HRA-8 evidence-driven target review]
  N -. secondary never unlocks LIVE_CASH alone .-> P
~~~

JRAとNARは独立したgateである。JRA PASSはNARをPASSにせず、NAR secondary PASSはschema/audit/SHADOWだけをunlockする。NARがBLOCKEDでもJRA laneは独立して進める。

### Data pipeline

~~~mermaid
flowchart LR
  S[Mac host + crwl] --> F[HRA-2F ingest boundary] --> R[Mac-local private append-only raw snapshot]
  R --> M[Redacted manifest only]
  M --> V{row_count >= 1 + schema + hash}
  V -- PASS --> D[Observed schema/local store]
  V -- FAIL --> B[DATA BLOCKED]
  D --> A[Chronological audit]
  A --> F[Walk-forward calibrated model]
  F --> H[SHADOW ledger]
  H --> O[Official result reconciliation]
  O --> T[Telegram/CFO split]
  F --> P[PurchaseExecutor: disabled]
  N[keiba.go.jp dynamic paths] -. robots disallow .-> B
~~~

Raw snapshotはMac-local private append-only boundaryに留める。Git、Telegram、cloud、CFOにはraw snapshotを送らず、redacted manifestだけをcommit可能にする。

## 3. Source policyとobserved evidence

### Source matrix

| lane | URL / authority | 現在の観測・許可 | gateとtruth |
|---|---|---|---|
| JRA primary | https://www.jra.go.jp/ / official | 公式公開ページ。https://www.jra.go.jp/robots.txt は User-agent:* と空のDisallowを観測。https://www.jra.go.jp/use/ はprivate use/citationを超える利用にpermissionが必要と説明する。個人・private useの範囲だけで取得する | 1件以上のactual record + manifestでREAL_PUBLIC_WEB_RECORD |
| NAR official dynamic | https://www.keiba.go.jp/ / official | robots.txtはCrawl-delay: 10と/KeibaWeb/TodayRaceInfo/、/KeibaWeb/DataRoom/、/KeibaWeb/DataDownload/を明示的にDisallow。これらをcrawlしない。推測URL /KeibaWeb/DataRoom/DataDownload は404で、verified ZIP/CSV claimはしない | official NAR laneはBLOCKED。robot disallowを回避しない |
| NAR initial secondary | https://nar.netkeiba.com/ / secondary | crwlで現行race-card/result linksを観測。automation termsは未検証で、official/licensed/compliantとは呼ばない。raw valuesを公開・再配布しない | PUBLIC_WEB_SECONDARY、schema/audit/SHADOW-only。LIVE_CASH前にterms resolution + official result/payout reconciliation |
| JRA fallback | nar.netkeiba.com / secondary | JRA公式ページにfieldがない場合だけfallbackにできる。source labelとsecondary authorityを保持し、JRA official recordへ昇格しない | PUBLIC_WEB_SECONDARY、SHADOW-only |

HRA-2F is the immediate active TDD slice: refactor the ingest boundary to accept JRA official and netkeiba secondary source authority, persist Mac-local private storage, capture robots/terms evidence metadata, and keep raw values non-exported. HRA-2R record probes remain BLOCKED until HRA-2F is GREEN.

crwlによる取得は、対象サイトのrobotsとtermsを毎回確認し、courteous rate limitを守る。NAR secondaryのtermsが未検証のままなら自動化範囲を増やさず、観測をroute evidenceとして扱う。NAR secondaryはHRA-6のterms/order/tax/receipt gateを単独で満たさない。

### Reality Gate（sourceごと）

1. JRA laneは公式公開pageをcrwlで取得し、robots snapshot、terms status、retrieved_at、page/effective timestampを記録する。
2. NAR official dynamic pathはrobots disallowのため取得せず、404 observationからZIP/CSVやAPIの存在を推測しない。
3. NAR secondary laneは公開race-cardまたはresult pageをrate-limitedに取得し、PUBLIC_WEB_SECONDARYと明記する。termsが未検証なのでSHADOW以外の作用を許可しない。
4. JRAとNARはそれぞれ独立に、row_count>=1のactual non-synthetic public-web race recordを1件以上観測する。links、DOM、HTTP 200、synthetic fixtureだけではPASSしない。
5. manifestの必須値欠落、HTTP/parse failure、terms/robots違反、content hash欠落、raw export発生は即BLOCKED。syntheticで補完しない。

### Redacted evidence manifest

sourceごとに次のmanifestだけをcommit可能にする。

~~~yaml
evidence_class: REAL_PUBLIC_WEB_RECORD
source_url: https://www.jra.go.jp/<public-page>
source_authority: official # official|secondary
jurisdiction: JRA # JRA|NAR
retrieved_at: <ISO-8601>
page_or_effective_timestamp: <timestamp or unavailable>
fetch_exit_code: 0
http_status: 200
parsed_row_count: <integer >= 1>
observed_schema:
  - name: <field name only>
    type: <normalized type only>
content_sha256: <sha256 of Mac-local raw snapshot>
robots_snapshot_url: <robots URL>
robots_status: <observed status/directive summary>
terms_url: <terms URL or unavailable>
terms_status: <observed|unverified|blocked>
raw_values_exported: false
~~~

NAR secondary manifestはevidence_class: PUBLIC_WEB_SECONDARY、source_authority: secondary、jurisdiction: NARにする。parsed_row_count>=1、observed schema field names/types、content_sha256、robots_snapshot_url/status、terms_url/status、raw_values_exported=falseが全て必須である。page/effective timestampが取れなければunavailableと明記する。HTTP/DOM successのみはrecordではない。

## 4. Boundary、schema、model、risk

### Mac-local private boundary

raw snapshotはMac-local private append-only storeだけに書き込む。保存後のcaller mutation、duplicate、overwrite、stale eventを拒否する。commit、Telegram、cloud、CFOへ送るのはredacted manifest、hash、row count、schema names/types、statusだけで、raw valuesは常にfalseである。

### HRA-2S observed schema

HRA-2SはReality Gateで観測したmanifestとrecordからのみschemaを定義する。schema_version、race_id、source、jurisdiction、page/effective timestamp、runner opaque id、odds、track condition等は実recordに存在したfieldだけを採用する。synthetic-only field、実馬名、raw row、credential、subscription id、receiptはschema根拠にしない。

### HRA-3D / HRA-3M

- actual chronological datasetがない状態ではbacktest、ROI、accuracy、calibrationを実行・主張しない。
- source、jurisdiction、timestamp order、coverage、欠損、duplicate、cutoff leakage、snapshot freshnessを監査する。
- market implied probabilityをbaselineにし、time-series walk-forwardだけを使う。random split、後刻odds、synthetic historical dataを禁止する。
- Brier、logloss、ECE、slippage、later-window evidenceを記録する。accuracyだけで昇格させない。
- EV = p * odds - 1等の推定値はLIVE_SHADOWに留め、real revenueや$10K/month claimに使わない。

### No-betとSHADOW

実public-web dataがあるeligible raceはSHADOWまたはSKIP decisionを生成する。SKIPでもbest candidate、threshold gap、reason、evidence class、freshness、decision_idをappendする。NAR secondaryはSHADOW-onlyで、NAR official outcome/payoutがreconcileされるまでLIVE_CASHを生成しない。

## 5. Telegram / CFO truth contract

### Sequence

~~~mermaid
sequenceDiagram
  participant S as schedule
  participant W as public web
  participant R as Reality Gate
  participant D as decision engine
  participant L as shadow ledger
  participant T as Telegram
  participant O as official outcome
  participant C as CFO
  S->>W: source + robots/terms + rate limit
  W->>R: page + redacted manifest
  R-->>D: PASS + evidence class
  R-->>L: immutable blocked/observed evidence
  D->>L: immutable SHADOW/SKIP decision
  L->>T: dedupe outbox + truth label
  O-->>L: placing/payout/refund or unavailable
  L->>T: result with real/shadow split
  L->>C: receipt summary only
  C->>T: nightly evidence-separated report
~~~

メッセージ先頭は正確にLife Manager::: 競馬AIとし、その直後にlabelを置く。

- [DATA BLOCKED]: source、robots/terms、manifest、quality gateが欠けておりpredictionを出さない。
- [REAL DATA · SHADOW]: JRA REAL_PUBLIC_WEB_RECORDまたはNAR PUBLIC_WEB_SECONDARYでdecisionしたが注文していない。
- [LIVE · ¥100]: HRA-6以降にofficial settled receiptがreconcileされた場合だけ許可する（現在disabled）。

全messageはsource_url、source_authority、jurisdiction、retrieved_at、page/effective timestamp、evidence class、odds snapshot、model version、decision_id、action/reason、real P&L、shadow P&Lを表示する。raw values、credential、実馬名は表示しない。TelegramとCFOはsynthetic、secondary、shadow、cashを混ぜない。

### Message schema

~~~text
Life Manager::: 競馬AI
[DATA BLOCKED|REAL DATA · SHADOW|LIVE · ¥100]
日時: <ISO-8601 JST>
source_url: <public page>
source_authority: <official|secondary>
jurisdiction: <JRA|NAR>
retrieved_at: <timestamp>
page_or_effective_timestamp: <timestamp or unavailable>
evidence_class: <SYNTHETIC_TEST|REAL_PUBLIC_WEB_RECORD|PUBLIC_WEB_SECONDARY|LIVE_SHADOW|LIVE_CASH>
action: <SHADOW|SKIP|LIVE|NONE>
reason: <reason>
decision_id: <immutable id>
model: <version or null>
data_freshness: <status and age or null>
real_P&L: <settled value or null>
shadow_P&L: <shadow value or null>
~~~

### CFO contractと$10K target

- business_idはhorse_racing、ledgerはhorse_racing_bet_receipts。raw page/rowをledgerへ入れず、receipt summary、hash、evidence classだけを保持する。
- SYNTHETIC_TEST、PUBLIC_WEB_SECONDARY、未settled LIVE_SHADOWはrevenue 0。unknownは0に変換しない。
- real P&LはHRA-6後のLIVE_CASH official settled receiptだけで確定する。bank/internal settlementとの二重計上を拒否する。
- $10K/monthはevidence-driven target only。settled receipt、capacity、slippage、calibration、drawdown、tax evidenceが揃うまでROI/$10K claim、forecast、scalingをしない。

## 6. Reuse matrixとreject boundary

| Repository / source family | authority / status | 扱い |
|---|---|---|
| jra.go.jp public pages | official, private-use lane | robots/terms/rate limitを満たすREAL_PUBLIC_WEB_RECORDのprimary source |
| nar.netkeiba.com public pages | secondary, terms unverified | PUBLIC_WEB_SECONDARYのschema/audit/SHADOWだけ。official/licensed/compliantと呼ばない |
| keiba.go.jp dynamic TodayRaceInfo/DataRoom/DataDownload | official, robots disallow | crawl、ZIP/CSV推測、API claimをreject |
| crwl | fetch utility | siteごとのrobots/termsとcourteous rate limit内だけ。raw publication・redistribution・SaaS化はreject |

このmatrixはsource authorityとevidence classを混同しないための再利用SSOTである。二次ページのschemaは公式sourceの証明にならず、NAR secondaryはLIVE_CASHをunlockしない。

## 7. Stage gates

| Stage | 内容 | 状態 |
|---|---|---|
| HRA-0 | research/spec、public-web policy、source rejection、acceptance | **complete** |
| HRA-1 | registry dependency、PurchaseExecutor disabled、truth labels | **complete** |
| HRA-2a | Mac-local private append-only raw boundary | **superseded design only**。0fe627cdは旧Windows boundaryの証明で、approved free-web designと非互換 |
| HRA-2F | TDD refactor ingest boundary: JRA official + netkeiba secondary, Mac-local storage, robots/terms metadata, raw non-export | **ACTIVE**。GREENまでHRA-2Rをblocked |
| HRA-2R | JRA/NAR各1 actual public-web record、robots/terms、redacted manifest | **BLOCKED until HRA-2F GREEN**。JRA 0、NAR 0 |
| HRA-2S | verified manifestからobserved schema/local store | **BLOCKED**。sourceごとのHRA-2R PASSまで不可 |
| HRA-3D | actual chronological coverage/cutoff audit | **BLOCKED**。historical evidence 0 |
| HRA-3M | market baseline、walk-forward、calibration、slippage | **BLOCKED**。real backtest 0 |
| HRA-4 | live-data SHADOW、official outcome reconciliation | **BLOCKED**。shadow run 0 |
| HRA-5 | Telegram + CFO real/secondary/shadow separation | **BLOCKED**。live run 0 |
| HRA-6 | terms/order/tax/credential/cap/receipt gate | **BLOCKED** |
| HRA-7 | HRA-6後のone ¥100 max/day review | **BLOCKED。PurchaseExecutorはdisabled** |
| HRA-8 | evidence-driven target review | **BLOCKED** |

### HRA-6 / HRA-7 policy

HRA-6のterms resolution、official result/payout receipt、tax review、credential separation、cap、reconciliationが揃うまで実装・有効化しない。通過後もfail-closed、stale/manifest/Telegram/reconciliation failureのSKIP、martingale/chasing禁止、公式receipt確認を必須にする。NAR secondaryだけではHRA-6を通過できない。

## 8. Acceptance criteriaとE2E judgment

| 契約 | 検証 | 合格条件 |
|---|---|---|
| JRA Reality evidence | crwlの実public page + manifest | official URL、robots/terms、retrieved_at、page/effective timestamp、fetch exit/HTTP status、parsed row_count>=1、observed schema names/types、content_sha256 |
| NAR secondary Reality evidence | nar.netkeiba.comの実public race-card/result page + manifest | PUBLIC_WEB_SECONDARY、source_authority=secondary、row_count>=1、terms status、SHADOW-only |
| official NAR crawl safety | robots snapshot + 404 observation | disallowed pathsをcrawlせず、verified ZIP/CSV/API claimをしない |
| evidence truth | Telegram/CFO payload scan | REAL_PUBLIC_WEB_RECORD等のlabelを表示し、secondary/shadow/syntheticをreal revenueへ合算しない |
| raw boundary | Mac-local path、manifest、Git/Telegram/cloud/CFO scan | raw page/row、secret、credential、実馬名のMac外出力0件 |
| schema derivation | manifestとschema diff | HRA-2R PASS前のsynthetic fieldをcompletionへ持ち込まない |
| append-only/replay | duplicate/overwrite/alias/stale tests | duplicate reject、caller mutation無効、同一semantic recordのhash一致 |
| actual audit/model | HRA-3D/3M public-web evidence | chronological coverage、cutoff audit、Brier/logloss/ECE、slippage、later-window evidenceが全て存在 |
| all-race SHADOW | HRA-4 source lane | eligible raceにSHADOW/SKIP、BLOCKED laneはpredictionなし |
| official reconciliation | outcome receipt | placing/payout/refund/voidをdecisionと分離し、official settled receiptだけreal P&L |
| purchase safety | disabled executor inspection | credential/network/DOM/wallet/bank side effect 0 |
| target honesty | CFO/report scan | ROI/$10K claimなし、$10Kはevidence-driven target only |

| Item | Value |
|---|---|
| UI変更 | Telegram message UX contractのみ。iOS UI変更なし |
| E2E | Maestro不要。Reality Gate後に実crwl public-web evidence、manifest、Telegram/CFO分離を実測する |

## 9. Best / Base / Worstと反証

| ケース | 想定 | 判断 |
|---|---|---|
| Best | JRA officialとNAR secondaryが各1件以上のrecordを得てmanifestを満たし、JRAはprimary、NARはsecondaryとしてSHADOWが継続 | source authorityを混ぜず、later-window evidenceを積み、HRA-6を審査する |
| Base | JRA public pageは観測できるがNAR termsまたはofficial outcome/payoutが未解決 | JRA laneだけ進め、NARはDATA BLOCKEDまたはSHADOW-only、cashはdisabled |
| Worst | robots/terms違反、record不足、timestamp/hash欠落、outcome reconciliation破綻 | fail-closedし、rawを外へ出さず、revenue 0、PurchaseExecutor disabled |

棄却案の最強の論拠は、paid source、OS依存route、未許可scraping、DOM注文がpersonal-use、robots/terms、receipt/reconciliation、raw-data boundaryを同時に満たせず、静かなデータ漏洩または誤決済を招くことである。

自分が間違うとしたら、公式公開ページに未発見のmachine-readable fieldまたは書面許可済みtermsがあり、現在の一次/二次分類を更新できる場合である。その場合もrobots/terms snapshot、actual record、manifest、HRA-6 receipt evidenceを先に確認し、labelを遡及変更しない。

## 10. Sources（観測根拠）

1. [JRA robots.txt](https://www.jra.go.jp/robots.txt) — User-agent:*と空のDisallowを観測。空でもrate limitとtermsを守る。
2. [JRA use policy](https://www.jra.go.jp/use/) — private use/citationを超える利用にはpermissionが必要と説明。個人・private useの範囲に限定する。
3. [NAR robots.txt](https://www.keiba.go.jp/robots.txt) — Crawl-delay: 10とTodayRaceInfo/DataRoom/DataDownloadのDisallowを観測。該当dynamic pathsをcrawlしない。
4. [NAR official terms](https://www.keiba.go.jp/terms.html) — 公開情報の転載・複製を事前許諾なく行わない境界。
5. [NAR public site](https://www.keiba.go.jp/) — guessed /KeibaWeb/DataRoom/DataDownloadは404。verified ZIP/CSVを主張しない。
6. [NAR secondary pages](https://nar.netkeiba.com/) — crwlで現行race-card/result linksを観測したroute evidence。automation termsは未検証で、official/licensed/compliantとは呼ばない。
