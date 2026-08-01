# O1C-20 Funder Weekly Reflection Design

## 目的

確認済みの返信・面談・採否・資金受領だけを毎週一度振り返り、次のfunding outreachで使うtarget順序とpitch方針へ反映する。
観測されていない結果は推測せず、会社factsの正本、過去の送信、過去の判断を上書きしない。

## 現状と不足

O1C-17〜19により、提出、outreach、返信、面談予定、offer/reject/fundedはappend-only台帳へ保存される。
ただし、次回の`buildInvestorOutreachPlan`はagentが渡した`candidate.rank`と本文だけを使い、過去結果を読まない。
そのため現在は、funnelを表示できても学習結果が次の行動へ届かない。

2026-08-02時点の実データはYCのapplication 1件、confirmation 1件、VC outreach 1件であり、
返信・面談・offer・reject・fundedは0件である。confirmationを好意的返信として数えたり、架空の採択結果を作ってはならない。

## 検討した方式

1. registry priorityまたはApplication Kitを直接更新する方式は、会社factsと戦略を混ぜ、履歴とrollbackを失うため採用しない。
2. 週次analyticsだけを保存する方式は、次回plannerが読まないため要件を満たさない。
3. append-onlyの週次strategy revisionを作り、次回plannerが検証済みrevisionを必須参照する方式を採用する。

## 採用アーキテクチャ

```text
submission / outreach ledger
             +
typed result / inbound / meeting ledger
             |
             v
単一tenant・半開区間の週次snapshot
             |
             v
agent-owned reflection judgment
             |
   deterministic closed validation
             |
             v
append-only weekly reflection ledger
       |                    |
       v                    v
target ranking          pitch directive
       \____________________/
                  |
                  v
       次回investor outreach planner
```

### 週次snapshot

- timezoneは`Asia/Tokyo`固定、月曜00:00から日曜20:15までの固定した半開区間とする。
- 同じdatabase statement snapshotから、提出・送信というexposureと、その後のtyped resultを読む。
- resultはledger ID、target ID、status、observed time、送信時のsubject/body hashへ束縛する。
- confirmationはfunnel事実として保持するが、reply/meeting/adoptionの成功材料には含めない。
- 週末より後の結果を過去週へ混ぜるlook-aheadを拒否する。
- cutoff直前のresultがsnapshot後にcommitされても失わないよう、過去週の未反映learnable resultを次の未記録週へcarryする。既にreflectionが引用したresult IDは再利用しない。
- 生のemail address、subject、body、evidence quote、rationaleはreflectionへ保存しない。

### agent判断

意味判断はagentが所有し、固定keywordや手書き点数で採否を解釈しない。agentはclosed objectとして次を返す。

- 使用したresult IDの完全な集合
- 週の要約と判断理由
- 次週候補IDの完全な順位（重複・欠落なし）
- 候補ごとのpitch directiveと、その根拠result ID
- `change | hold`。結果が無い場合は必ず`hold`

順位対象IDはprogram registryから推測しない。VC/angel plannerとprogram registryは異なるdomainだからである。学習可能な結果がある場合、
次回plannerがfreshに生成した同じcandidate ID集合をrunnerへ注入してからrevisionをmaterializeする。候補集合がまだ無ければ週次tickは
成功扱いにせずretryし、次のplanner runが人の承認なしでmaterializeする。

deterministic codeは、参照resultが同じsnapshotに存在すること、status/time/target/hashの一致、候補順位が完全なpermutationで
あること、directiveが単一行・24語/240文字以内のexact sentenceであること、全変更が少なくとも1件のreply/meeting/rejected/offer/fundedへ根拠づけられることだけを検証する。

### 次回outreachへの強制接続

結果を含む最新週次revisionが存在する場合、次回plannerは各candidateに次を要求する。

- 同じ`reflection_id`
- revisionで指定された`ranking_position`
- exact `pitch_directive`
- directiveが引用したresult ID

production plannerは候補ID確定後に未記録週を古い順で全てmaterializeし、同一instantを含む最新の未適用`change` revisionをloadする。
後続週が`hold`でも未適用changeは隠れず、少なくとも1件のoutreach applicationがappendされた後だけ消費済みになる。
`change`なら順位を自動で並べ替え、90語以内の原稿へexact directiveを自動注入してから120語上限を再検証する。
plannerはrevisionの候補集合と入力候補集合の完全一致、順位、directive、result lineageを照合する。
plain objectの偽造、JSON round-tripした未検証revision、古いrevisionと新しい候補の混在を拒否する。
結果0件の`hold` revisionでは現在のagent順位・pitchを変更せず、no-opであった事実だけを保存する。
全schema-v2 Gmail receiptはin-process delivery provenanceを要求し、change適用行はreflection/result lineageと同じtransactionで保存する。
DBのdeferred constraintも、対象候補に最新changeがあるのにapplicationを省いた直接INSERTをcommit時に拒否する。
planは次の週次cutoffの5分前に失効し、Gmail deliveryは外部送信より前に期限を検査する。これによりplan/reservation後に
新しいchangeがmaterializeされ、実送信だけ成功して古いapplicationのDB保存が失敗する境界raceを防ぐ。

### 保存とcadence

- `lm_funder_weekly_reflection_ledger`はtenant/week単位のappend-only台帳とする。
- 同一週・同一snapshot・同一判断はexact replay、異なる内容の衝突は拒否する。
- 日曜20:15 JSTでdueとなり、停止中だった場合は次回起動で最古から全未記録週をcatch-upする。固定cutoffより後の結果と未反映の遅延commitは次の未記録週へ送り、再起動や並列実行はDB uniquenessで重複を止める。
- runnerはagent judgmentをdependencyとして呼び、人の承認を要求しない。agent/providerが使えない場合は成功扱いにせずretryable failureとする。

## live runの境界

現在の実台帳には学習可能な返信・面談・採否結果が無いため、live runは`hold / insufficient_outcomes`を保存する。
target順位やpitchが改善したとは主張しない。fixtureのverified meeting/rejection/offerでは、次回plannerへ順位とdirectiveが実際に強制されることを
RED→GREEN testとPostgreSQL integrationで証明する。
