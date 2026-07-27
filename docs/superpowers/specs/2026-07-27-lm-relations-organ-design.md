# H5 ORG-relations Design

## Goal

`done="cloud runtime が本人の実interaction履歴から相手ごとの安定 cadence を測り、いつもの間隔を超えた1人だけを、出典を偽らず・罪悪感を煽らず・第三者PIIを保存せずに提案する"`

H5 は personal CRM でも「友達スコア」でもない。実際に繰り返された1対1の時間が途切れたときだけ、Life Manager が小さな余白を提案する organ である。

## Evidence

| Source | URL | Core evidence |
|---|---|---|
| Monica (open-source personal CRM) | https://github.com/monicahq/monica | Contact、relationship、activity、reminderを別々の実物として扱う。README は「Management of activities with a contact」「Reminders」を機能として掲げる。 |
| Telegram Bot FAQ | https://core.telegram.org/bots/faq#what-messages-will-my-bot-get | bot が受け取る private message は user とその bot の private chat。user と第三者の private chat history を読む API ではない。 |
| Google Calendar Events resource | https://developers.google.com/workspace/calendar/api/v3/reference/events | `attendees[].displayName` は “if available” の optional field、`email` と `self` / `resource` / `responseStatus` が参加者判定に使える。 |
| Production Calendar read | Railway `life-call` / Composio read-only probe | 現 user 18か月711 events、external 1対1=18、displayName付き=0、同一相手4回以上=0。現在は正しく abstain すべきデータ形。 |
| Production Google Contacts probe | Composio `GOOGLECONTACTS_LIST_CONNECTIONS` read-only probe | current Calendar connection は Google Contacts toolkit connection ではなく、HTTP 400 “No connected account”。Calendar OAuthからcontact名を推測してはいけない。 |

## Decision

### 1. Normalized interaction contract

Detector は platform を知らず、次の interaction だけを読む。

| Field | Meaning |
|---|---|
| `interactionId` | source内のdedup key |
| `personKey` | normalized identityをserver secretでHMACしたopaque key |
| `label` | 今回のmessageだけに使う表示名。DBへ保存しない |
| `startMs` | 実interaction時刻 |
| `source` | `calendar_1to1`。将来 `whatsapp_chat` / `telegram_user_session` / `agent_call` を追加 |

v1 source は Calendar の実1対1 eventのみ。

- timed event
- declined / resource / self を除いた external attendee がexactly 1
- attendee `displayName` がproviderから実際に返った
- 10分以上6時間以下
- emailはHMAC入力にだけ使い、出力・log・DBへ出さない

`displayName` がない時にemail local-partやevent titleから名前を作らない。productionの現在値はこの条件で0件なのでabstainが正解。

### 2. Cadence

care detector の実証済み safety rule を再利用する。

| Evidence | Decision |
|---|---|
| 0〜2 interactions | silence |
| 3 interactions / 2 gaps | observe only |
| 4以上でもgap不安定 | observe only |
| 4以上、stable、最終interactionからmedianの1.5倍超 | actionable |

固定の「家族は毎週」rule、社会的価値score、相手の重要度推定は置かない。候補が複数なら `daysSince / personalIntervalDays` が最大の1人だけ。

### 3. Timing and shared budget

提案は user local 18:30〜19:00、7日で最大1通。

- `notifications_enabled=false` → silence
- timezone不明 → silence
- event中 / moving → silence
- MENTAL 3通/24h cap と2h spacingを共有
- history / send budget / relation ledgerが読めない → silence
- `LM_RELATIONS_ENABLED=0|false|off|no` → off、unsetはon

copy:

> 🌿 カレンダーでは、{name}との1対1の時間が{daysSince}日空いています。いつもの間隔は約{intervalDays}日でした。今週、10分だけ連絡する余白があります。

「連絡しろ」「大切にしていない」「孤独になる」と言わない。質問・button・自動outreachはない。

### 4. Privacy and durable state

`lm_relations_log` はappend-only。保存できるのは次だけ。

| kind | Stored |
|---|---|
| `scan` | day、interaction count、opaque person key + interval/days/decision |
| `suggestion_attempt` | opaque person key、attempt timestamp |
| `delivery` | opaque person key、Telegram message id、delivered timestamp |

禁止: name、email、phone、event title、location、message body、free text。

`suggestion_attempt` をsend前にclaimする。sendが不確かな時の再送より、同じ人を二度nudgingしない方を選ぶ。delivery成功時だけ別rowとMENTAL budget rowを書く。

### 5. Honest boundary

「母に42日**電話していない**」は call connector の実receiptがある時だけ言える。Calendar sourceは「カレンダーでは1対1の時間が42日空いた」とだけ言う。

Telegram bot token、Google Calendar OAuth、Google Contactsは個人のphone/WhatsApp/Telegram第三者chat historyではない。H5 v1はこの穴を隠さず、normalized interaction adapterで将来sourceを追加可能にする。

## Architecture

```text
Calendar history (548d, strict complete read)
  → calendar one-to-one adapter
     ├─ raw email → HMAC personKey (ephemeral)
     └─ provider displayName → label (ephemeral)
  → relation detector (personal stable cadence)
  → append-only scan (no third-party PII)
  → time / movement / weekly / shared-MENTAL gates
  → suggestion_attempt claim
  → one Telegram statement
  → delivery receipt + shared MENTAL budget
```

## Files

| File | Change |
|---|---|
| `lib/relation-detector.js` | pure cadence detector |
| `lib/relation-calendar.js` | Calendar → normalized interactions, HMAC identity |
| `lib/relations-runtime.js` | daily scan, timing/budget/cooldown/send |
| `lib/events.js` | preserve attendee/organizer fields in history projection |
| `lib/i18n.js` | source-honest copy |
| `scheduler.js` | last organ in the 60s tick + kill switch |
| migration | append-only relation ledger + MENTAL trigger extension |
| tests/eval | detector, privacy, runtime, wiring, migration, deterministic cases |

## Verification

| Layer | Proof |
|---|---|
| Unit | schema, stability, no-history, no-name, PII non-persistence |
| Integration | actionable event → attempt→Telegram→delivery→MENTAL budget |
| Safety | observe-only / cap / spacing / weekly / event / moving / unknown tz all silence |
| Wiring | real runtime reachable after H4; other organs survive its failure |
| Full | `npm test`, all eval suites |
| Production | migration readback, exact Railway SHA, `/health`, read-only real Calendar scan reports honest abstention |

