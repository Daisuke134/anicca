# O1C-19 VC / Angel Personalized Outreach Design

## 目的

acceleratorではないVCまたはangelだけを、公式投資thesisとAniccaの正本company factsが一致するとagentが判断した時だけ、
東京日付ごとの全送信合計3〜5件の範囲でpersonalized outreachする。O1C-09の送信台帳を唯一の送信正本として維持する。

## 現状と不足

2026-08-02（東京）はO1C-09で3件送信済みだが、既存契約には次の不足がある。

1. VC / angel / acceleratorの対象種別と、その公式根拠が保存されない。
2. thesis一致はsummary hashだけで、公式ページのexact quoteへ束縛されない。
3. 3〜5件の制約がbatch単位で、同日batchの合計を5件以内へ直列化しない。
4. 個別化したtarget/company claimが、それぞれ公式ページ/application-kitのexact quoteへ束縛されない。

## 採用方式

既存`lm_funder_outreach_ledger`を送信正本として拡張し、VC/angel送信には次のproof列をall-or-noneで必須化する。
O1C-09 schema v1は既存receiptのexact replayだけを維持し、予約を持たない旧外部送信は停止する。

- `investor_kind`: `vc | angel`
- `thesis_evidence_sha256`
- `company_evidence_sha256`
- `personalization_sha256`
- `daily_slot`: 1〜5

同時実行で5件を超えないよう、送信前にappend-only reservation tableへslotを確保する。DB functionはtenant/東京日付の
advisory transaction lockを取り、既存送信数と既存reservation数を同じtransactionで数え、1〜5の空きslotだけを返す。
予約後の送信失敗はslotを消費したままにして安全側へ倒す。送信台帳を複製する表ではなく、外部副作用前の上限fenceである。

## 判断境界

agentがclosed assessmentを所有する。

```json
{
  "kind": "agent_judgment",
  "investor_kind": "vc",
  "thesis_match": true,
  "summary": "...",
  "target_evidence_quotes": ["..."],
  "message_claims": [
    {"claim":"...", "evidence_source":"target", "evidence_quote":"..."},
    {"claim":"...", "evidence_source":"company", "evidence_quote":"..."}
  ]
}
```

決定論コードは意味をkeyword/regexで推測しない。`investor_kind`が`vc|angel`、`thesis_match=true`、target quoteがfreshな
公式HTTPS本文に完全一致、company quoteがcurrent `application-kit://KIT.md`に完全一致、全claimがemail本文に完全一致することだけを
検証する。`accelerator`または不一致は送信候補にならない。

## 日次契約

- `daily_target`は3〜5。
- DBの同日既送信数を必ず読み、必要件数は`daily_target - existing_count`だけ。
- 既送信数がtarget以上なら正直なno-op。5件以上なら常にno-op。
- 外部送信直前に各outreachの`daily_slot`をDBで確保する。未予約messageは送信境界が拒否する。
- recipientは全期間dedupし、同じrecipientへ再送しない。

## 今回のlive run

同日既送信3件を正本DBで確認し、Scion Ventures公式ページのseed/pre-seed、agentic systems、Pitch Us、公式emailをfresh取得する。
agentがVCかつthesis一致と判断し、current application-kitの会社事実へ束縛した1通だけを送る。合計4件となり3〜5件を満たす。

## claim boundary

本項目が証明するのは、公式情報でVC/angelかつthesis一致と判断した相手だけを、current company factsで個別化し、
東京日付の全送信合計を5件以内へ直列化して送れることである。投資関心、返信、面談、採択、資金受領は主張しない。
