# Connector O1B-20 許諾済みsource handoff設計

status: APPROVED
owner: Connector
date: 2026-08-02 JST

## 2026-08-02実測

- connpass API申請は2026-08-02 JST提出済み。案内された審査目安は約5営業日。
- `CONNPASS_API_KEY`はlocal secret providerに未配備。
- 提出日以後のconnpass公式API返信mailは0件、credential-like valueも0件。
- connpass公式v2は全endpointでAPI key必須。API以外のcrawler/scraper/other accessは禁止。
- Meetupの新規OAuth consumerはactive Meetup Proと審査が必要。現在その権限はない。
- Eventbrite公式APIはorganization/event/order管理とcheckout integrationを提供するが、第三者eventへ
  participantとして自動注文する公開endpointは公式documentから確認できない。
- GitHubのevent aggregator repoは情報importが中心で、本人RSVPとverified receiptを提供しない。

公式source:

- https://connpass.com/about/api/v2/
- https://help.connpass.com/api/api-term
- https://www.meetup.com/graphql/
- https://help.meetup.com/hc/en-us/articles/41453576628749
- https://www.eventbrite.com/platform/docs/introduction
- https://www.eventbrite.com/platform/docs/orders

## capability matrix

| provider | discovery | registration | coverage credit | 現在 |
|---|---|---|---|---|
| Luma | 既存CloakBrowser daily-driver | E1/E2/E3付きbrowser RSVP | 可 | active |
| connpass | key受領後の公式v2 GETのみ | 禁止 | 不可 | blocked_missing_key |
| Meetup | Pro OAuth承認後に再評価 | 未検証 | 不可 | not_adopted |
| Eventbrite | official API scope取得後に再評価 | 第三者eventは未検証 | 不可 | not_adopted |

## handoff契約

1. O1B-20はverifiedな`luma_candidates_exhausted` outcomeだけを受ける。
2. keyありならconnpass公式API read-only discoveryを一度実行する。
3. keyなしならconnpass network accessを0件にし、key watcherとLuma再探索を次actionにする。
4. connpass候補は`advisory_only`で、registrationやcoverage resolutionへ渡さない。
5. fallback候補0件、key未取得、source errorのいずれでもdateを`open`のまま保持する。
6. unknown provider、browser scrape、POST、coverage credit昇格はfail closedする。

O1B-20は「次sourceへ安全に継続する」責務であり、同日候補を成功まで試すO1B-21、検索一巡を
終了条件にしないO1B-22、Calendar conflictを判定するO1B-23を先取りしない。

## 完了条件

- capability policyとverified handoffをTDDで実装する。
- connpass keyなしでnetwork 0、date open、retry actionを実証する。
- fixture keyありで公式API GET discoveryだけが動き、coverage credit 0を実証する。
- 実Gmail/secret stateをread-onlyで証拠化する。
- outbound全回帰、spec、evidence、commit、pushを完了する。

