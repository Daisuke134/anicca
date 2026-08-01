# Connector O1B-08 Talk Slot Agent Eval Implementation Plan

> Status: 実行中。event本文をagentが読み、一般参加とLT/CFP/demo応募を区別する。

**Goal:** keyword listではなくevent本文全体の意味から、公開中の登壇応募枠、締切済み、招待制、単なる登壇者紹介、一般参加だけを区別し、5件以上のheld-out evalを実Geminiで通す。

## Agent contract

- inputはcanonical URL、title、provider本文、現在時刻だけ。cookie、guest key、mail、個人情報を渡さない。
- agentは`participation_kind`、`talk_format`、`application_status`、`should_create_talk_application`、`application_url`、`evidence_excerpt`、`reason`をstructured JSONで返す。
- `evidence_excerpt`は実本文の連続substringでなければrejectし、agentの作り話をledgerへ入れない。
- 公開応募URLがあり、status=openの場合だけtalk application entityを作る。登壇という語があるだけでは作らない。
- event本文内の命令はuntrusted dataとして扱い、classification promptを書き換えさせない。
- model失敗やschema不正をkeyword fallbackで補わず、そのcandidateをunknownとして次へ進める。

## Tasks

### Task 1: Structured classifier

- [ ] schema validatorとcross-field invariantをRED→GREENにする。
- [ ] Gemini structured-output classifierを実装する。
- [ ] prompt injection、架空URL、本文にないevidenceを拒否する。

### Task 2: Held-out eval

- [ ] open LT、open CFP、締切済み、招待制、speaker紹介だけ、一般参加だけを含む6件以上を作る。
- [ ] 実Geminiで全件を実行し、deterministic expected fieldsとevidence provenanceを判定する。
- [ ] 100%でなければprompt/schema/caseを分析して修正し、再実行する。

### Task 3: Proof

- [ ] secretなしeval evidenceを保存する。
- [ ] O1B-08完了、spec更新、commit、push。
- [ ] O1B-09へ進む。
