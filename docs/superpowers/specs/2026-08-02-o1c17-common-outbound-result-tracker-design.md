# O1C-17 Common Outbound Result Tracker Design

## Goal

`gog` で取得した funder application の confirmation と同一 Gmail thread 内の
reply を、Job Hunter が既に実証した message-level dedup / thread binding /
timestamp / evidence hash / fence の契約へ統合する。Gmail 本文、送受信者、subject、
evidence quote は durable store へ保存しない。

## Chosen architecture

Job Hunter の private SQLite を fundraising 専用 schema へ拡張しない。代わりに
Life Manager に tenant-aware な `lm_outbound_result_ledger` を置き、Job Hunter の
結果契約を `job_hunter` と `fundraising` が共有できる形へ一般化する。

```text
verified source receipt
  └─ exact Gmail thread ID
       └─ gog --gmail-no-send --no-input thread get
            └─ sanitized immutable messages
                 ├─ source confirmation -> deterministic result
                 └─ later inbound reply -> agent_judgment + exact quote proof
                      └─ append-only common result ledger
```

## Invariants

1. Gmail は既に検証・保存された `lm_funder_submission_ledger.mail_thread_id`
   だけを positional ID として読む。全 inbox search は行わず、send/modify command
   は利用しない。
2. `gog` は `--gmail-no-send --no-input --wrap-untrusted --full
   --sanitize-content` で起動する。返却 thread ID、各 message の thread ID、ID形式、
   unique性、時刻を検証する。
3. confirmation は source receipt の exact `mail_message_id`、thread、timestamp、sender、
   subject と一致した場合だけ成立する。reply は confirmation より後、owner 以外の
   sender、同一threadだけを候補にする。
4. reply の意味は `agent_judgment` が所有する。deterministic code は status を keyword
   や regex で推測せず、許可statusと本文内の exact quote だけを検証する。
5. durable row は tenant、organ、workflow、source ID/fence、entity ID、result type/status、
   Gmail message/thread ID、時刻、各 SHA-256 だけを持つ。raw sender/subject/body/quote/
   rationale は保存しない。
6. `(tenant_id, provider_message_id)` は一意。同じ exact row の replay だけ成功し、
   message、source、thread、status、hash の差替えは conflict で失敗する。
7. store は insert 前に source submission row を tenant/source/funder/thread/message で
   再照合する。confirmation は source mail message と一致し、reply は同一threadで
   source submission より後でなければならない。
8. ledger は append-only、RLS enabled、PUBLIC/anon/authenticated deny、service role は
   SELECT/INSERT のみ。current projection は ledger から導出する。
9. source fence は immutable funder submission receipt では revision `1`、Job Hunter
   confirmationでは既存submit intentの実fenceを保存する。Job Hunter bridgeはSQLiteの
   confirmation/intent/application/evidence/time全列をexact queryで再検証してから同じstoreへ書く。
10. 実証は既存 YC Fall 2026 confirmation thread の read-only fresh read を使う。
    現在 reply が無ければ confirmation 1件だけを記録し、reply を創作しない。

## Failure behavior

CLI失敗、malformed JSON、thread mismatch、重複message ID、pre-submission message、
owner outbound、fabricated quote、unknown judgment、source row不在、exact replayでない
conflict はすべて fail closed。Gmail checkpoint は durable insert 成功後にだけ進める。

## Exit proof

- REDを観測した focused tests が全GREEN。
- outbound regression と runtime regression がGREEN。
- migration を実DBへ適用し、RLS・権限・append-only・exact replayをreadback。
- `19fbe6135cf98bd4` を `gog` でfresh readし、confirmationだけを共通台帳へ1回保存。
- raw contentを含まない evidence JSON、正本spec check、remaining count、remote HEAD一致。
