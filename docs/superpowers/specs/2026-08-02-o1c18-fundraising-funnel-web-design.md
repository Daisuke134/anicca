# O1C-18 Fundraising Funnel Web Projection Design

## 目的

既存Life Manager panelに、資金調達の
`application → confirmation → interview → offer / reject → funded`を、tenant別・証拠由来・read-onlyで表示する。
未観測stageを推測で到達扱いにせず、現在の実データではYC Fall 2026のapplicationとconfirmationだけを表示する。

## 比較した方式

1. **既存ledgerから単一snapshotを導出する（採用）**
   - PostgreSQL RPCが一つのMVCC snapshot内でsubmission/resultを読み、Panel APIがclosed DTOへ検証・投影する。
   - 新しいfunnel正本を持たないため、二重書込みとdriftがない。
2. funnel snapshot tableを定期更新する
   - 読取りは単純だが、元ledgerとの整合性、再構築、更新失敗の扱いが増える。
3. browserが複数REST tableを直接読む
   - 実装は小さいがservice credentialをbrowserへ出せず、複数request間でsnapshotも揃わない。

## 証拠とstage

| 表示stage | 到達を証明する既存event | 表示 |
|---|---|---|
| application | `lm_funder_submission_ledger.status=submitted` | 応募済み |
| confirmation | 同じsource/threadに束縛されたcommon result `confirmed` | 確認済み |
| interview | agent判断済みcommon result `meeting_requested` | 面談依頼 |
| offer | agent判断済みcommon result `offer_received` | オファー |
| reject | agent判断済みcommon result `rejected` | 不採択 |
| funded | agent判断済みcommon result `funded` | 資金受領確認 |

`offer_received`と`funded`はO1C-17の同じreply evidence契約へ追加する。モデルがexact quoteとrationaleを所有し、
deterministic codeはallowed schema、source/thread、timestamp、hash、append-only保存だけを検証する。

## データ契約

DB RPC `lm_panel_fundraising_funnel(p_uid text)`はservice roleだけが実行できる。`p_uid`と一致する行だけを読み、
provider message ID、thread ID、本文、sender、subject、digestを返さない。各source rowは次だけを返す。

- `funder_id`
- `source_id`
- `event_kind`: `application | confirmation | interview | offer | rejected | funded`
- `occurred_at`

Panel coreはsource ID一致、stage順序、terminal矛盾、重複をfail closedで検証し、次のclosed DTOへ変換する。

```json
{
  "schema_version": 1,
  "summary": {
    "application": 1,
    "confirmation": 1,
    "interview": 0,
    "offer": 0,
    "rejected": 0,
    "funded": 0
  },
  "applications": [{
    "program": "YC Fall 2026",
    "current_stage": "confirmation",
    "terminal_outcome": null,
    "last_event_at": "2026-08-01T17:31:05.000Z",
    "stages": [
      { "id": "application", "state": "reached", "occurred_at": "2026-08-01T17:31:05.000Z" },
      { "id": "confirmation", "state": "reached", "occurred_at": "2026-08-01T17:31:05.000Z" },
      { "id": "interview", "state": "pending", "occurred_at": null },
      { "id": "decision", "state": "pending", "outcome": null, "occurred_at": null },
      { "id": "funded", "state": "pending", "occurred_at": null }
    ]
  }]
}
```

## 整合性規則

- confirmation以降は同じsubmission `source_id`へ束縛される。
- `application ≤ confirmation ≤ interview ≤ offer ≤ funded`の観測時刻順を守る。
- rejectはconfirmation後のterminal branchであり、offer/fundedと同居できない。
- fundedはoffer観測後だけ許可する。stageを逆算して捏造しない。
- 同じapplication/stageの複数event、未知stage、extra field、secret-like valueはsection unavailableにする。
- source table/RPCが無い時は偽の全0件を返さず、section unavailableにする。

## Web UX

既存panelの上段に「資金調達 funnel」を追加する。summaryは6つのcountを横並びにし、各applicationは
一本のrailとして表示する。到達stageは濃色、次stageは輪郭、terminal rejectは赤、fundedは緑にする。
スマートフォンでは横スクロールを使わず縦railへ切り替える。日時は日本語の短い表示にし、provider IDやdigestは表示しない。

## 検証

- focused Node tests: current YC 2-stage、全stage、reject branch、empty、cross-source、逆順、矛盾、extra/secret拒否。
- Panel API/UI tests: authenticated endpoint、closed DTO、browser validator、mobile layout、section単独failure。
- PostgreSQL integration: migration replay、service-only RPC、tenant isolation、single snapshot output、anon/authenticated拒否。
- live local readback: current YCがapplication=1、confirmation=1、他=0で、Web renderも同じ値になる。
- full panel/outbound/runtime regressionとindependent reviewを通す。

## claim boundary

この項目が証明するのは、既存の検証済みeventをWebへ正しく投影できることだけである。現在存在しない
interview、offer、reject、fundedを成果として主張しない。
