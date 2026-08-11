# Life Manager 競馬AI financial organ 設計仕様（Mac-native official public web）

## Status、truth、責務

| 項目 | 契約 |
|---|---|
| Status | **REALITY GATE REQUIRED — LIVE PURCHASE DISABLED** |
| 対象 | Life Manager financial organ の第8候補 business_id: horse_racing |
| 現在のactive stage | HRA-3C typed outcome audit B2（ACTIVE）。exact REAL provenance完了、cashはfalse |
| plan / gate / verification owner | Sol |
| edit / code / execution owner | Luna |
| 購入処理 | PurchaseExecutorは常時disabled。HRA-6の全gateなしに有効化しない |

この文書はzero-cost public-web ingestion、source authority、Reality Gate、truth label、受入条件の正本である。HRA-2F、NAR official 46/456/327274 rows、JRA official 12 result rows、HRA-2N acquisition contract、four-lane Reality Gate index、truth-safe append-only store、HRA-3D audit codeはprivate-shadow前提のgateを通過した。actual cutoff-safe normalized recordsは7あるが、対応するcurrent-day settled outcomesは0のためmodelはunlockしない。Sol owns plan/gate/verification; Luna owns edits/code/execution.

### 現在のevidence table

| Evidence | 実測値 |
|---|---:|
| real JRA official public-web result rows | 12 |
| real NAR official race rows | 46 |
| real NAR official horse rows | 456 |
| real NAR official monthly odds rows | 327274 |
| real NAR official payback rows | 0 (pre-settlement) |
| real historical backtests | 0 |
| live SHADOW runs | 0 |
| live Telegram runs | 0 |
| live orders/payments | 0 |
| revenue / real P&L | 0 |

NARの46/456/327274行はdocs/evidence/horse-racing/nar-official-data-probe.mdのredacted observationである。HTTP/DOM successだけ、download開始だけ、schema存在だけではcompletionではない。JRA、backtest、SHADOW、Telegram、orders、revenueは未実施であり、unknownを0へ変換しない。

### Committed proof boundary

0fe627cdはsuperseded boundaryの歴史的記録であり、approved Mac-native official public-web designの実装証拠ではない。現行のNAR観測は6a6cdd135のredacted evidenceだけを根拠にする。

### Evidence classes

- SYNTHETIC_TEST: 人工fixtureでpure mechanicsだけを検証する証拠。
- REAL_PUBLIC_WEB_RECORD: 公式JRAまたは公式NAR公開ページ・公式downloadから、permission basis、robots/terms、rate limit、manifestを記録した非合成record。
- PUBLIC_WEB_SECONDARY: race.netkeiba.comまたはnar.netkeiba.comをofficial fieldのfallbackとして取得した二次record。schema/audit/SHADOWだけに使い、official/licensed/compliantとは呼ばない。
- LIVE_SHADOW: REAL_PUBLIC_WEB_RECORDまたはPUBLIC_WEB_SECONDARYからdecisionしたが注文・決済をしていない証拠。
- LIVE_CASH: HRA-6後のofficial settled result/payout、receipt、reconciliationを通過した証拠。現在は常にdisabled。

SYNTHETIC_TEST、PUBLIC_WEB_SECONDARY、未settled LIVE_SHADOWはreal revenueへ合算しない。NAR officialのpre-settlement payback rows=0はsettled payoutではない。

## 1. 目的とHard non-goals

### 目的

個人利用だけを対象に、Mac-native zero-cost public-web ingestionでJRAとNARの公式公開情報をprimary sourcesとして観測する。JRA official laneはrecord 0から開始し、NAR official laneはdaily race archive、monthly odds archive、公式manualのredacted evidenceを持つ。二次公開ページはofficial fieldが欠けた場合のfallback/shadow-onlyに限定する。

### Hard non-goals

- paid source、subscription、credential、provider login、SaaS、public API、raw redistributionを導入しない。
- browser login、DOM click、注文API、wallet/bank mutation、bet、実購入を実装・実行・有効化しない。
- crwlはnavigation/HTMLに使い、curlはcrwlのPage.goto: Download is starting制限を補う公式binary downloadにだけ使う。robots/termsとcourteous rate limitを守る。
- USER_ATTESTED_PERMISSIONはこのbounded personal probeのbasisに限り、一般的なbot許可、再配布許可、cash execution許可とは解釈しない。permission_document_verified=falseを保持する。
- 収益、勝率、ROI、$10K/monthを保証または推定しない。$10Kはevidence-driven target only。

## 2. Mac-native official-web architecture

### Gateで下流を止めるflow

~~~mermaid
flowchart TD
  A[HRA-0 research/spec] --> B[HRA-1 safety contracts]
  B --> F[HRA-2F Mac ingest boundary]
  P[USER_ATTESTED_PERMISSION / document unverified] -. bounded personal probe only .-> F
  F -- GREEN --> G{HRA-2R per-source manifest gate}
  F -- RED/BLOCKED --> X[DATA BLOCKED]
  G -- JRA official --> J[HRA-2S JRA observed schema]
  G -- NAR official candidate --> N[HRA-2S NAR observed schema]
  G -- secondary fallback --> S[SHADOW-only secondary schema]
  J --> D[HRA-3D actual audit]
  N --> D
  S --> D
  D --> M[HRA-3M baseline/walk-forward/calibration]
  M --> H[HRA-4 SHADOW + official outcome]
  H --> T[HRA-4b Telegram evidence split]
  T --> C[HRA-5 CFO receipt split]
  C --> Q[HRA-6 terms/tax/receipt gate]
  Q --> Z[HRA-7/8 blocked cash/scale review]
  S -. never unlocks LIVE_CASH .-> Q
~~~

JRAとNAR officialは独立laneである。NARのUSER_ATTESTED_PERMISSIONはprobeの根拠を記録するだけで、HRA-6をskipしない。secondary fallbackはschema/audit/SHADOWだけをunlockする。

### Data pipeline

~~~mermaid
flowchart LR
  A[Mac + crwl navigation/HTML] --> J[JRA official HTML]
  A --> N[NAR Today/DataRoom/Monthly HTML]
  N --> C[curl daily race ZIP + monthly odds ZIP]
  J --> F[HRA-2F source/permission boundary]
  C --> F
  F --> R[Mac-local private raw snapshot]
  R --> M[Redacted manifest only]
  M --> V{row_count + schema + sha256}
  V -- PASS --> D[Observed schema/store]
  V -- FAIL --> B[DATA BLOCKED]
  D --> A2[Chronological audit]
  A2 --> W[Model/walk-forward]
  W --> S[SHADOW ledger]
  S --> O[Official outcome reconciliation]
  O --> T[Telegram/CFO split]
  X[nar.netkeiba.com fallback] -. PUBLIC_WEB_SECONDARY / SHADOW-only .-> D
  E[Page.goto: Download is starting] -. curl required for binary .-> C
  P[PurchaseExecutor disabled] -. no side effect .-> S
~~~

raw snapshotはMac-local private append-only boundaryに留める。Git、Telegram、cloud、CFOへ出すのはmanifest、hash、row count、schema names/types、statusだけであり、raw valuesは常にexportしない。

## 3. Source policyとobserved evidence

### Source matrix

| lane | URL / authority | 観測・許可 | gateとtruth |
|---|---|---|---|
| JRA primary | https://www.jra.go.jp/ / official | current home→official result index→2026-08-09 detailを発見。robotsはUser-agent:*とempty Disallow。private raw HTMLから12 actual rows x 14 fieldsを観測 | REAL_PUBLIC_WEB_RECORD、PASS_PRIVATE_SHADOW、cash false |
| NAR official Today | https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop / official | crwl exit 0。2026-08-10 daily venuesとofficial daily-data linkを観測。robotsはCrawl-delay: 10とdynamic path Disallowを保持し、probeはUSER_ATTESTED_PERMISSION basis | REAL_PUBLIC_WEB_RECORD、PASS_PRIVATE_SHADOW、NAR 46 race rows |
| NAR official daily archive | https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily / official | crwlはPage.goto: Download is starting。curl fallback HTTP 200 application/zip、UTF-8 BOM CSV、race 46 / horse 456 / payback 0 pre-settlement | REAL_PUBLIC_WEB_RECORD、PASS_PRIVATE_SHADOW、raw non-export |
| NAR official monthly navigation | https://www.keiba.go.jp/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop / official | crwl exit 0。monthly race/odds endpointsを観測 | official NAR lane |
| NAR official monthly odds | https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8 / official | runtimeは公式pageからyear/monthを導出する。curl HTTP 200 application/zip、first interval 327274 rows | REAL_PUBLIC_WEB_RECORD、PASS_PRIVATE_SHADOW |
| NAR official manual | https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf / official | 8 pages、daily 約2分更新、monthly dataは1日1回・毎日午前2時頃更新、daily intermediate odds、race history 1998-01、odds history 2026-03を観測 | source cadence/coverage evidence |
| Secondary fallback | https://race.netkeiba.com/ または https://nar.netkeiba.com/ / secondary | official fieldが欠ける場合だけcrwl。terms statusを明記し、raw valuesを出さない | PUBLIC_WEB_SECONDARY、SHADOW-only、cash不可 |

NAR robotsはDisallowを隠さない。permission basisはUSER_ATTESTED_PERMISSION（2026-08-10）、permission_document_verified=falseであり、一般的なbot/redistribution許可ではない。NAR official outcome/payoutはpre-settlement payback rows=0で、settled receipt reconciliationまで未確定である。

### HRA-2F accepted source contract

HRA-2FはMac-only source/permission boundaryとして、次のexact combinationを受け付ける。

- www.jra.go.jp + official + JRA
- www.keiba.go.jp + official + NAR
- race.netkeiba.com + secondary + JRA
- nar.netkeiba.com + secondary + NAR

すべてhost_os=macos、storage_scope=mac_local_private、raw_values_exported=false、permission_basis、permission_document_verifiedをmanifestへ保存する。keiba.go.jp dynamic URLのrobots statusを消さず、secondary authorityをofficialへ昇格しない。HRA-2FはGREEN。HRA-2R NARは46/456/327274行で`PASS_PRIVATE_SHADOW`、raw archive absent、cash falseである。

### Reality Gate（sourceごと）

1. JRA laneは公式navigationからcurrent pageをcrwlし、robots/terms、retrieved_at、page/effective timestamp、row count、schema、hashを記録する。現recordは0。
2. NAR official laneはToday/DataRoom/Monthly HTMLをcrwlし、binary race/odds archivesをcurlで取得する。daily ZIPはrace 46、horse 456、payback 0 pre-settlement、monthly oddsは327274 rowsをmanifestへ記録する。
3. crwl binary failure Page.goto: Download is startingはtool limitationとして扱い、curl HTTP 200 archive evidenceを使う。これはsource failureやsettled payoutではない。
4. NAR secondary fallbackはPUBLIC_WEB_SECONDARY、SHADOW-only。official NAR laneの代替primaryにも、LIVE_CASH根拠にもならない。
5. parsed_row_count>=1、observed schema names/types、content_sha256、robots/terms status、permission fields、raw_values_exported=falseが欠ければそのsourceはBLOCKED。syntheticで補完しない。

### Redacted evidence manifest

~~~yaml
evidence_class: REAL_PUBLIC_WEB_RECORD
source_url: https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily
source_authority: official
jurisdiction: NAR
permission_basis: USER_ATTESTED_PERMISSION
permission_document_verified: false
retrieved_at: 2026-08-10T07:22:26+09:00
page_or_effective_timestamp: 2026-08-10T07:22:26+09:00
fetch_exit_code: 0
http_status: 200
parsed_row_count: 46
row_counts:
  races: 46
  horses: 456
  monthly_odds: 327274
  paybacks_pre_settlement: 0
observed_schema:
  type: utf8_csv_field
  racelist: venue/date/race_number/start_time/surface/distance/weather/track_condition/runner_count/prize
  horselist: gate/horse_number/horse_name/sex/age/pedigree/jockey/trainer/weight/result_fields
  payback: win/place/quinella/exacta/wide/trio/trifecta_fields
  odds: venue/date/race_number/bet_type/number1/number2/number3/odds/odds_max/popularity
content_sha256:
  daily_race_zip: f245030f4608055c2fa24e2910d51edcd029f2292c9cfbe66d2911604e1e1c5b
  monthly_odds_zip: ad18c23b4648bef4113c8191cc78d084168a2aa37c9b49431742e64621f0397f
  official_manual_pdf: 56009a444ffb61ddc99097ffdd2d2a84a864073c00052d9f691cfda1770236dd
robots_snapshot_url: https://www.keiba.go.jp/robots.txt
robots_status: "Crawl-delay: 10; TodayRaceInfo/DataRoom/DataDownload disallowed"
terms_url: unavailable
terms_status: USER_ATTESTED_PERMISSION_DOCUMENT_UNVERIFIED
raw_values_exported: false
allowed_scope: private_shadow
~~~

NAR secondary manifestはevidence_class=PUBLIC_WEB_SECONDARY、source_authority=secondary、allowed_scope=shadow_only、permission fields付きで、LIVE_CASH/revenueをauthorizeしない。HTTP/DOM successのみではrecordにならない。

## 4. Boundary、schema、model、risk

### Mac-local private boundary

raw snapshotはMac-local private append-only storeだけに書き込む。保存後のcaller mutation、duplicate、overwrite、stale eventを拒否する。commit、Telegram、cloud、CFOへ送るのはredacted manifest、hash、row count、schema names/types、statusだけで、raw valuesは常にfalseである。

### HRA-2S observed schema

HRA-2SはHRA-2R manifestと実recordからschemaを定義する。REAL_PUBLIC_WEB_RECORDはJRA/NAR official laneを許可し、PUBLIC_WEB_SECONDARYはfallbackのschema/audit/SHADOWだけを許可する。schema_version、race_id、source、jurisdiction、page/effective timestamp、opaque runner id、odds、track condition等はobserved fieldだけを採用し、実馬名やraw rowをschema根拠にしない。

### HRA-3D / HRA-3M

- NAR daily/monthly evidenceはactual public-web coverageだが、historical outcome/backtest datasetではない。actual chronological datasetがない状態ではbacktest、ROI、accuracy、calibrationを実行・主張しない。
- source、jurisdiction、timestamp order、coverage、欠損、duplicate、cutoff leakage、snapshot freshnessを監査する。
- market implied probabilityをbaselineにし、time-series walk-forwardだけを使う。random split、後刻odds、synthetic historical dataを禁止する。
- Brier、logloss、ECE、slippage、later-window evidenceを記録する。accuracyだけで昇格させない。
- EV = p * odds - 1等の推定値はLIVE_SHADOWに留め、real revenueや$10K/month claimに使わない。

### No-betとSHADOW

実public-web dataがあるeligible raceはSHADOWまたはSKIP decisionを生成する。NAR officialでもsettled outcomeがないraceはSHADOWであり、secondary fallbackは常にSHADOW-onlyである。SKIPにもbest candidate、threshold gap、reason、evidence class、freshness、decision_idをappendする。

## 5. Telegram / CFO truth contract

### Sequence

~~~mermaid
sequenceDiagram
  participant S as schedule
  participant W as JRA/NAR official web
  participant F as HRA-2F
  participant R as Reality Gate
  participant D as decision engine
  participant L as SHADOW ledger
  participant T as Telegram
  participant O as official outcome
  participant C as CFO
  S->>W: crwl HTML + curl binary archive
  W->>F: page/archive + permission/robots manifest
  F->>R: redacted evidence
  R-->>D: PASS + evidence class
  R-->>L: blocked/observed evidence
  D->>L: immutable SHADOW/SKIP decision
  L->>T: dedupe outbox + truth label
  O-->>L: settled placing/payout/refund or unavailable
  L->>T: real/shadow P&L split
  L->>C: receipt summary only
~~~

メッセージ先頭はLife Manager::: 競馬AIとし、REAL_PUBLIC_WEB_RECORD official laneまたはPUBLIC_WEB_SECONDARY fallbackを表示する。

- [DATA BLOCKED]: HRA-2F、permission metadata、robots/terms、manifest、quality gateが欠けておりpredictionを出さない。
- [REAL DATA · SHADOW]: official public-web recordでdecisionしたが注文していない。
- [LIVE · ¥100]: HRA-6後にofficial settled receiptがreconcileされた場合だけ許可する。order permissionは`USER_ATTESTED_AUTONOMOUS_ORDER_APPROVAL`。data permission documentの未検証を注文許可と混同しない。

全messageはsource_url、source_authority、jurisdiction、retrieved_at、page/effective timestamp、evidence class、model version、decision_id、action/reason、real P&L、shadow P&Lを表示し、raw values、credential、実馬名は表示しない。

### CFO contractと$10K target

- business_idはhorse_racing、ledgerはhorse_racing_bet_receipts。raw page/rowをledgerへ入れず、receipt summary、hash、evidence classだけを保持する。
- SYNTHETIC_TEST、PUBLIC_WEB_SECONDARY、未settled LIVE_SHADOW、pre-settlement paybackはrevenue 0。unknownは0に変換しない。
- real P&LはHRA-6後のLIVE_CASH official settled receiptだけで確定する。データ取得用の`USER_ATTESTED_PERMISSION`は再配布を許可せず、注文操作は別の`USER_ATTESTED_AUTONOMOUS_ORDER_APPROVAL`による。
- $10K/monthはevidence-driven target only。settled receipt、capacity、slippage、calibration、drawdown、tax evidenceが揃うまでROI/$10K claim、forecast、scalingをしない。

## 6. Reuse matrixとsource boundary

| Source / utility | authority / status | 扱い |
|---|---|---|
| jra.go.jp public pages | official, private-use lane | JRA primaryのREAL_PUBLIC_WEB_RECORD candidate |
| keiba.go.jp Today/DataRoom/Monthly pages | official, USER_ATTESTED bounded probe | crwl navigation/HTML。robots statusを保持し、general bot/redistribution permissionとは呼ばない |
| keiba.go.jp RaceDataDownload / OddsDataDownload | official binary artifacts | crwl download limitation後のcurl取得。headers/counts/hashだけをmanifestへ書く |
| keiba.go.jp data manual | official cadence/coverage documentation | daily approx 2 min、monthly approx 02:00、race 1998-01、odds 2026-03、daily intermediate odds |
| race.netkeiba.com / nar.netkeiba.com | secondary fallback | PUBLIC_WEB_SECONDARY、SHADOW-only。official NAR/JRA recordへ昇格しない |
| crwl + curl | fetch utilities | robots/terms/rate limit、Mac-local raw boundary、raw non-exportを守る |

## 7. Stage gates

| Stage | 内容 | 状態 |
|---|---|---|
| HRA-0 | research/spec、public-web policy、source authority、acceptance | **complete** |
| HRA-1 | registry dependency、PurchaseExecutor disabled、truth labels | **complete** |
| HRA-2a | Mac-local private append-only raw boundary | **superseded design only**。0fe627cdは現行証拠ではない |
| HRA-2F | JRA/NAR official + secondary fallback authority、permission metadata、Mac-local raw non-export、crwl/curl boundary | **complete**。focused 24/full 32 PASS、cash authorization false |
| HRA-2R-JRA | JRA official actual record + manifest | **complete**。12 actual result rows、PASS_PRIVATE_SHADOW、cash false |
| HRA-2R-NAR | NAR official: 46 races / 456 horses / 327274 monthly odds / payback 0 pre-settlement | **complete**。PASS_PRIVATE_SHADOW、raw absent、cash false |
| HRA-2N | NAR official acquisition planner/classifier | **complete**。focused 17/full 49 PASS、bounded URL decode、cash false |
| HRA-2R3 | per-source Reality Gate index | **complete**。official 2 lanes PASS、secondary 2 lanes NOT_OBSERVED、cash false |
| HRA-2S | observed schema/local store | **complete**。synthetic fixtureはtest_only、nullable未観測値、append-only identity |
| HRA-3D | actual chronological coverage/cutoff audit | **code complete / actual BLOCKED**。records 0、model_ready false |
| HRA-3C-monthly | actual NAR materialization probe | **complete / BLOCKED_NO_CUTOFF_TIMESTAMP**。321 joined settled candidates、safe records 0 |
| HRA-3C-daily | one actual NAR daily cutoff snapshot | **complete**。snapshot PASS、exact win complete coverage 7 races/76 runners |
| HRA-3C-market | normalized win/place market identity | **complete**。market混同をstore hash/snapshot keyで防ぐ |
| HRA-3C-materialize | actual daily win parser | **complete**。actual 7 records/76 runners、accepted provenance、names/raw exportなし |
| HRA-3C-outcome | official win result/payback parser | **complete**。actual monthly 321 outcomes/322 payouts、dead heat完全照合 |
| HRA-3D-settlement-guard | caller-declared settlement rejection | **complete**。commit `8d344a97f`、parser evidenceなしのnonzero settlementをAuditRejected |
| HRA-3C-settlement | current-day target settlement capture | **ACTIVE B2**。August monthly 367/368、target 7/7、exact REAL allowlist完了。typed outcomesをauditへ接続する |
| HRA-3M | market baseline、walk-forward、calibration、slippage | **BLOCKED** |
| HRA-4 | live-data SHADOW、official outcome reconciliation | **BLOCKED**。shadow runs 0 |
| HRA-5 | Telegram + CFO real/shadow separation | **BLOCKED**。Telegram runs 0 |
| HRA-6 | terms/order/tax/credential/cap/receipt/reconciliation | **SPAT4 + MUFG SELECTED / WAGERING CREDENTIAL NOT_OBSERVED**。Moneytreeでowner MUFG口座は実測済み、公式SPAT4 signup/loginは未実行 |
| HRA-7 | HRA-6後のone ¥100 max/day review | **BLOCKED。PurchaseExecutor disabled** |
| HRA-8 | evidence-driven target review | **BLOCKED** |

### HRA-6 / HRA-7 policy

2026-08-10T12:48:52+09:00のowner明示により、全対象公式購入サイトの自律操作許可は`order_permission_basis=USER_ATTESTED_AUTONOMOUS_ORDER_APPROVAL`とする。`order_permission_document_verified=false`として証拠強度を誠実に表示しつつ、書面回答は実装・注文の依存にせず、`provider_recontact=false`とする。tax/credential/cap/idempotency/receipt/reconciliation未完了の間はLIVE_CASHをfail-closedする。通過後もstale/manifest/Telegram/reconciliation failureのSKIP、martingale/chasing禁止、公式settled receipt確認、実資金流出直前の確認を必須にする。

2026-08-10T12:52+09:00のread-only inventoryでは、設定済みGmailの過去メール、既存Cloak cookie DBの対象host行、macOS Keychainの対象host完全一致entryのいずれにも投票口座credential証拠を観測していない。`account_credential_state=NOT_OBSERVED`とし、`ACCOUNT_ABSENT`とは断定しない。genericな決済情報は公式投票口座の代替にしない。LIVE_CASH前に、別経路で既存口座を実測するか、公式signup/loginを完了し、credential値を外へ出さず隔離する。

The first live-order route is `SPAT4 + MUFG`. NAR says SPAT4 covers all local races, whereas Rakuten Keiba requires Rakuten Bank, OddsPark excludes South Kanto and Hokkaido, and JRA internet voting has sale-day limitations: https://www.keiba.go.jp/beginner/step4.html. SPAT4 officially accepts MUFG accounts and states that MUFG Direct is not required to apply: https://www.nankankeiba.com/info/spat4/netbank/accountapplication.html. The CFO SSOT has already observed one owner MUFG deposit account through Moneytree, so `bank_eligibility_state=OBSERVED_MUFG_VIA_MONEYTREE`; Moneytree remains read-only evidence and never substitutes for SPAT4 signup, bank authentication, or isolated wagering credentials.

SPAT4 is the clearest published NAR receipt-contract candidate. Its 2026-05-01 official contract fixes ordinary tickets at ¥100 units, defines acceptance/formation, prohibits third-party purchase applications, and retains application records for 30 days; its 2026-06-24 conditions require inquiry after uncertain communication to avoid duplicates. Sources: https://www.nankankeiba.com/info/spat4/pdf/spat4_contract01.pdf?ver=20260501 and https://www.nankankeiba.com/info/spat4/pdf/spat4_contract03.pdf?ver=20260624. Autonomous-operation permission is based on the separate owner attestation, not inferred from this public contract.

Rakuten Keiba likewise fixes tickets at ¥100 multiples, restricts password use to the member, and does not guarantee third-party app/web behavior; OddsPark's published rules require the subscriber's own application and member-only credential use. Sources: https://keiba.rakuten.co.jp/guide/term, https://www.oddspark.com/member/kiyaku/, and https://www.oddspark.com/pdf/kiyaku_dir.pdf. A single Rakuten inquiry was accepted at 2026-08-10T12:39:23+09:00 and has a private inquiry number. This remains historical evidence only: the owner subsequently attested autonomous-operation approval for every target site and instructed no further provider contact. No OddsPark message was sent.

Tax state is fact-dependent, not a model output. NTA states that ordinary horse-racing payouts are generally temporary income, while sustained systematic purchase patterns can be miscellaneous income depending on duration, frequency, scale, and profit facts. CFO therefore persists gross payout, winning-ticket stake, losing-ticket stake, refund/void, and official receipt ID separately and performs no automatic expense-netting or final tax classification. Sources: https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1490.htm and https://www.nta.go.jp/information/other/data/h30/keiba/index.htm.

## 8. Acceptance criteriaとE2E judgment

| 契約 | 検証 | 合格条件 |
|---|---|---|
| JRA evidence | official navigation + crwl | JRA URL、robots/terms、retrieved/effective timestamp、row_count>=1、schema names/types、content_sha256。現状0なのでBLOCKED |
| NAR official evidence | probe evidence + manifest | official URL、USER_ATTESTED_PERMISSION、permission_document_verified=false、robots status、daily races=46、horses=456、monthly odds=327274、paybacks=0 pre-settlement、schema names/types、three hashes、raw_values_exported=false |
| NAR binary acquisition | crwl/curl trace | Page.goto: Download is startingをtool limitationとして記録し、curl HTTP 200 application/zip、filename、bytes、hashをredacted manifestへ入れる |
| source authority | manifest scan | REAL_PUBLIC_WEB_RECORDはofficial JRA/NARのみ。fallbackはPUBLIC_WEB_SECONDARY、allowed_scope=shadow_only、LIVE_CASH/revenue不可 |
| permission honesty | permission fields scan | permission_basis=USER_ATTESTED_PERMISSION、permission_document_verified=false、general bot/redistribution/cash permissionのclaimなし |
| robots boundary | robots snapshot | Crawl-delay: 10とTodayRaceInfo/DataRoom/DataDownload disallowを保持し、permission assertionを隠さない |
| raw boundary | Mac-local path、Git/Telegram/cloud/CFO scan | raw archive/CSV/PDF、secret、credential、実馬名のMac外出力0件 |
| schema derivation | manifestとschema diff | HRA-2F GREEN + source manifest gate前のsynthetic fieldをcompletionへ持ち込まない |
| actual audit/model | HRA-3D/3M evidence | chronological coverage、cutoff audit、Brier/logloss/ECE、slippage、later-window evidence。現backtest 0 |
| all-race SHADOW | HRA-4 source lanes | official recordはSHADOW/SKIP、secondary fallbackはSHADOW-only、blocked laneはpredictionなし |
| official reconciliation | outcome receipt | pre-settlement payback 0をsettled payoutとせず、official settled receiptだけreal P&L |
| purchase safety | disabled executor inspection | credential/network/DOM/wallet/bank side effect 0 |
| one live purchase | official history pre/post + receipt chain | final action-time debit confirmation後、単勝¥100をsubmit call最大1回、official formed purchase差分が完全一致1件、同一receiptのsettlementとTelegram/CFO照合、agent-created duplicate 0。曖昧応答は再送せず履歴照会 |
| target honesty | CFO/report scan | ROI/$10K claimなし、$10Kはevidence-driven target only |

| Item | Value |
|---|---|
| UI変更 | Telegram message UX contractのみ。iOS UI変更なし |
| E2E | Maestro不要。HRA-2FはGREEN。次にNAR manifest、続いてJRA official record、curl archive hashes、Telegram/CFO separationを実測する |

## 9. Best / Base / Worstと反証

| ケース | 想定 | 判断 |
|---|---|---|
| Best | NAR official manifestは受理済み。JRAもactual rowを取得、order permissionはowner-attested | official laneごとにschema/audit/SHADOWを進め、HRA-6の残るgateを別審査する。secondaryはfallback |
| Base | HRA-2FとJRA/NAR private-shadow gateはGREEN。NAR payback pre-settlement 0 | HRA-2N取得contractへ進み、receipt/reconciliation完了までcash/revenue/ROIは0を維持 |
| Worst | robots/terms/permission境界、raw boundary、timestamp/hash、official outcome reconciliationが破綻 | fail-closedし、rawを外へ出さず、PurchaseExecutor disabled、revenue 0 |

棄却案の最強の論拠は、data permissionとorder permissionを1つのbooleanに潰すと、robots/terms、raw boundary、receipt/reconciliationのどの根拠で通過したかを追跡できなくなることである。

自分が間違うとしたら、ownerが取得した許可の範囲が「選択・入力」に限られ「最終送信・履歴照会」を含まない場合である。現在はownerの「全サイトで承認済み」を広義の自律操作として採用し、追加照会を行わない。

## 10. Sources（観測根拠）

1. [NAR official probe evidence](../evidence/horse-racing/nar-official-data-probe.md) — USER_ATTESTED_PERMISSION、permission_document_verified=false、NAR official 46/456/327274 rows、payback 0 pre-settlement、hashes、raw_values_exported=false。
2. [JRA robots.txt](https://www.jra.go.jp/robots.txt) — User-agent:*とempty Disallowを観測。
3. [JRA use policy](https://www.jra.go.jp/use/) — private use/citationを超える利用にはpermissionが必要と説明。
4. [NAR robots.txt](https://www.keiba.go.jp/robots.txt) — 「Crawl-delay: 10」とTodayRaceInfo/DataRoom/DataDownloadのDisallow。
5. [NAR TodayRaceInfoTop](https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop) — crwl exit 0、daily venuesとofficial daily-data linkを観測。
6. [NAR DataRoomTop](https://www.keiba.go.jp/KeibaWeb/DataRoom/DataRoomTop) — crwl exit 0、historical years through 1998を観測。
7. [NAR MonthlyConveneInfoTop](https://www.keiba.go.jp/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop) — crwl exit 0、monthly endpointsを観測。
8. [NAR daily race archive](https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily) — curl HTTP 200 application/zip、daily hash/countを観測。
9. [NAR monthly odds archive](https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8) — curl HTTP 200 application/zip、first interval 327274 rows。
10. [NAR data manual](https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf) — 「更新頻度: 約2分ごとに更新されます。」、「1日1回、毎日夜間（午前2時頃）に更新されます。」、「レース情報は1998年1月以降、オッズ情報は2026年3月以降」。
