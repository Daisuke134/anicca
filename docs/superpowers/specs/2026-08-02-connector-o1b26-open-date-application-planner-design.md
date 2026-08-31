# Connector O1B-26 Open-date Application Planner Design

## Goal

rolling 21日coverageの最も早い`open`日について、既存のLuma inventory、agent ranking、
Calendar/移動gate、支出policyを再利用し、同日の候補を一件ずつdurable
`outbound.event.apply` jobへ渡す。coverage workerは応募画面を操作しない。

## Non-goals

- Connector以外のagent、job hunter、fundraising、CFOを変更しない。
- connpassから予約しない。key未配備の間はLumaだけを予約sourceにする。
- 有料eventを許可しない。O1B-26のlive policyは0円である。
- 同日の複数候補を並列enqueueしない。
- AI/crypto等のkeywordをeligibility条件にしない。

## Runtime profile

Daisが明示したpreferences/goalsを、secret-freeでversionedなConnector profileに保存する。
loaderはexact schema、tenant、timezone、reference-only identity/browser/calendar、自然言語長、
secret-like text不在を検証する。runtimeは明示pathからだけ読み、missing/invalid時はfail closedする。

初期profileの意味:

- 東京の対面eventで毎日人に会うことが最優先。
- AI、crypto、startup、founder、VC、product、finance、英語は順位を上げる例であり除外条件ではない。
- 予想外の人・分野とのserendipityを残す。
- Mr.botのuser、協力者、採用、投資、登壇、事業機会へつながる可能性を評価する。
- 自動支出は0円。無料候補だけを応募jobへ送る。

## State machine

```text
latest verified coverage + fresh exhaustive inventory + all-calendar busy inventory
  -> earliest open date
  -> preference ranking (all candidates exactly once)
  -> goal/serendipity ranking (grounded five factors)
  -> Calendar + inbound/outbound travel gate
  -> zero-yen spend sequence
  -> read prior outbound jobs for this date
       completed       -> next refresh will consume receipt; enqueue nothing
       queued/running/retry/reconciling -> wait; enqueue nothing
       terminal failure -> skip that candidate and select next ranked candidate
       absent           -> enqueue exactly one outbound.event.apply job
  -> save refreshed coverage
  -> enqueue next coverage continuation
```

候補なし、全候補Calendar衝突、有料/価格不明、または同日の全候補がterminal failureでも
日付を`unavailable`へ変換しない。`open`のまま次runへ渡す。`unavailable`は全日固定予定の
verified evidenceだけが作れる。

## Idempotency and concurrency

- 応募job IDは既存`buildEventApplicationJob`でtenant/event/start/identityから決定する。
- plannerはDB内の既存jobをtenant-boundで読み、同じeventを再enqueueしてもstore collisionで増えない。
- 一つのcoverage runがenqueueする応募jobは最大1件。
- active応募jobが一件でもあれば、同日の次候補をenqueueしない。
- terminal failureだけが次候補への進行を許可する。
- publish effectの結果が不明な場合は`reconciling`を待ち、次候補へ進まない。

## Result and observability

coverage refresh resultへsecret-freeなplanning outcomeを追加する。

```text
date, status(enqueued|waiting|exhausted|no_candidates), event_ref|null, job_ref|null
```

raw job ID、provider本文、個人情報、API keyはTelegramへ出さない。runtime receiptは件数と
opaque referenceだけを持つ。failureは既存`CONNECTOR_COVERAGE_*`のbounded codeを使う。

## Acceptance

1. 最も早いopen日だけを処理する。
2. 全候補をagent評価し、hard filterを作らない。
3. Calendar/移動非衝突かつ無料の最上位候補だけをenqueueする。
4. active/unknown effect中は次候補をenqueueしない。
5. terminal failure後は同日の次候補へ進む。
6. 実local runtimeで応募jobが1件queuedになり、workerがverified receiptを作る。
7. 次coverage runでCalendar 1件、`covered_new`、open減少を確認する。

