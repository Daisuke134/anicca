# O1B-15 Talk Application Transition Ledger Design

created: 2026-08-02 JST
scope: 登壇応募entityの状態観測、immutable transition ledger、current-state projection

## 1. Goal

`talk_application`ごとの`submitted / accepted / rejected / presented`を、現在値の上書きだけでなく、
証拠へ遡れる不変transitionとして保存する。一般参加entityはこのledgerへ入れない。

## 2. Current-state finding

`lm_event_participations`には`state`列とtalk state checkはあるが、transition table、append API、状態変更履歴がない。
したがって現在値を直接更新すると、いつ、どの証拠で、どの状態から変わったかを失う。

## 3. Alternatives

### A. Parent rowのstateだけをUPDATE

単純だが履歴、証拠、retry衝突を監査できないため不採用。

### B. Immutable transition ledger + atomic current projection（採用）

transitionをappendし、同じDB transactionのtriggerでparent current stateを更新する。履歴と既存query互換を両立する。

### C. Ledgerだけを正本にしてcurrent stateを毎回再生

純粋なevent sourcingだが、既存`lm_event_participations.state`利用箇所の変更がO1B-15を越えるため不採用。

## 4. State graph

許可するforward transitionは次だけである。

```text
discovered → submission_queued → submitted → accepted → presented
                                  ├────────→ rejected
                                  └────────→ withdrawn
                         accepted └────────→ withdrawn
              submission_queued └────────→ withdrawn
```

`rejected / withdrawn / presented`はterminal。失敗したruntime attemptは応募stateを巻き戻さず、runtime job側でretryする。

## 5. Observation boundary

Agentはprovider response、確認mail、event page、主催者通知をuntrusted sourceとして読み、`to_state`、根拠excerpt、
人間向けreason、使用したsource refsをstructured outputで返す。deterministic validatorは次だけを行う。

- current stateからto stateへのgraph整合性
- observation timestampの厳密なISO時刻と未来上限
- excerptがsource本文の連続部分であること
- source refsがtrusted allowlistの部分集合であること
- raw email、電話、secret、cookie、tokenを保存対象へ入れないこと

keyword/regex fallbackで採択・不採択・登壇完了を判断しない。model/API失敗時はtransitionを作らない。

## 6. Durable record

`lm_talk_application_transitions`は次を持つ。

- stable `transition_id`
- `tenant_id`, `participation_id`
- `from_state`, `to_state`, `observed_at`
- source-bound `reason`, `source_refs`
- DB `created_at`

raw source本文、mail本文、氏名、email、電話、ticket URL、QR bytesは保存しない。

## 7. Atomicity and idempotency

storeはparentを`FOR UPDATE`でlockする。新規insertのBEFORE triggerが同じtenantの`talk_application`とcurrent
`from_state`を確認し、AFTER triggerがparent stateを`to_state`へ更新する。同じtransition IDのretryは既存rowと
完全一致する場合だけ成功する。異なる内容、stale from state、cross-tenant、一般参加は全transactionをrollbackする。

ledger rowのUPDATE/DELETEはtriggerで拒否する。

## 8. Live verification

現在の実`Codex Meetup Tokyo #2`は未提出のため状態を捏造しない。実runtime DBへmigrationを適用後、transaction内の
fixtureで`discovered → submission_queued → submitted → accepted → presented`、current projection、terminal拒否、
immutabilityを確認し、最後にROLLBACKする。実talkのstateとtransition countが変わっていないことを件数で再確認する。

## 9. Completion criteria

- agent judgmentにkeyword fallbackがない
- focused testとoutbound全回帰が成功
- live DBでappend、projection、immutability、rollbackが成立
- 実talkを捏造しない
- evidence、master spec、commit、origin/mainが同じ完了状態を指す
