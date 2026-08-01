# Connector O1B14 — accepted talk timeline design

## 目的

登壇応募が採択された後、スライド締切、登壇開始・終了、会場、QR、主催者follow-upを一つのtimelineとして追跡する。
一般参加entity、登壇応募state ledger、Google Calendar、現地参加後の関係管理とは混同しない。

## scope

含む:

- 採択receiptに紐づくtimeline生成
- slide deadlineが明記されない場合の`pending`追跡
- 登壇日時、会場、verified QR object reference
- 主催者への締切・会場・QR・資料提出確認のfollow-up
- source reference付きimmutable snapshotとcurrent view

含まない:

- 参加者への連絡、返信、次回面談
- 応募state transition ledger。これはO1B15
- Calendar write。timelineのverified dataをO1B23でCalendarへ接続
- QR bytes、mail本文、氏名、email、secretのDB保存

## architecture

```text
verified accepted talk entity
  + accepted mail/event public text（untrusted）
  + verified event start/end
  + verified QR object ref or pending
             ↓
Gemini timeline interpreter
  slide status/due, venue status/name/address,
  follow-up time/purpose/reason
             ↓
deterministic validator
  exact timestamps, ordering, reference subset,
  accepted state, no raw identity/secret
             ↓
immutable lm_talk_timeline_snapshots
             ↓
lm_talk_timeline_current view
             ↓
Telegram / Calendar projection（後続step）
```

意味判断はGeminiが行う。コードはtimestamp、順序、reference、tenant、state、immutabilityだけを検証する。
keywordやregexで「締切」「会場」「採択」を判定しない。

## timeline contract

- `accepted_at`: verifier由来でmodelに決めさせない
- `appearance_start_at / appearance_end_at`: verified event detail由来
- `slide_status`: `known / pending / not_required`
- `slide_due_at`: `known`の時だけ必須。appearance startより前
- `venue_status`: `known / pending`
- `venue_name / venue_address`: `known`の時だけ必須
- `ticket_status`: `ready / pending / not_required`
- `ticket_ref`: `ready`の時だけverified `object://sha256/...`
- `follow_up_at`: accepted後。event終了30日後より遅くしない
- `follow_up_purpose / follow_up_reason`: agentがsourceと不足情報を読んで決める
- `source_refs`: 入力済みreceipt/evidence refのsubsetのみ

## persistence

`lm_talk_timeline_snapshots`はcontent hashのstable `snapshot_id`を主キーにする。同じsnapshotはidempotent、
異なる観測は新rowになる。UPDATE/DELETEはtriggerで拒否する。保存前に同じtransaction内で
`lm_event_participations`を`FOR SHARE`し、tenant一致、kind=`talk_application`、state=`accepted`を要求する。
`lm_talk_timeline_current`は各participationの最新snapshotだけを返す。

## failure behavior

- talkが未採択: snapshotを作らずgeneric failure
- slide/venue/QR不足: 成功を偽装せず`pending`として保存し、follow-upへ残す
- model invalid/unknown ref/timestamp矛盾: 保存せずretryable interpretation failure
- DB collision/cross-tenant: rollback
- raw identity/secret: validator拒否

## verification

- pure validator TDD
- Gemini request contractとprompt-injection fixture
- temp PostgreSQLでaccepted talk→snapshot→current view→immutability→rollback
- 実runtime DB schema適用
- 現在のreal talkは未採択なので永続timelineを捏造しない。accepted fixtureはtransaction rollbackで実証する

## 完了条件

accepted talkだけがsource-bound timeline snapshotを作れ、5要素を同じcurrent viewから読み出せる。
不足情報はpendingで明示され、実イベント未採択をacceptedとして保存しない。
