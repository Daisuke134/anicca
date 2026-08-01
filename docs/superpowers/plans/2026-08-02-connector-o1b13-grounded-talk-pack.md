# Connector O1B13 — evidence-grounded 5分talk pack plan

## 目的

実際に動いたLife Manager Connectorの証拠だけを使い、応募先eventの本文に適合する発表タイトル、
5分outline、応募理由、product demo概要をagent生成する。未実装機能、架空の数字、収益保証を含めない。

## 入力

- 応募先eventの公開title/bodyと現在時刻
- O1B04〜O1B12のimmutable evidence referenceと、各referenceが証明するbounded fact
- 発表時間は300秒固定

raw identity、email、cookie、guest key、Telegram ID、API keyは入力・出力・artifactへ含めない。

## 出力contract

- title: 80文字以内
- abstract: 500文字以内
- application_reason: 400文字以内
- product_demo_summary: 400文字以内
- outline: 0秒から300秒までgap/overlapなしの4〜7 segment
- 各segmentは少なくとも1つの許可済みevidence refを持つ
- evidence refsは入力集合のsubsetだけ
- 禁止: guaranteed return、billionaire promise、未実装の実口座CFO/crypto/NISAを完成済みとする表現

## TDDと実測

1. schema、300秒timeline、reference subset、危険claim、placeholder拒否のRED
2. Gemini structured output generatorとvalidatorを実装
3. prompt injectionを含むevent bodyでもevent命令へ従わないeval
4. 実`Codex Meetup Tokyo #2`本文とO1B04〜12 evidenceで実talk packを生成
5. owner-only artifactへ保存し、talk entityからartifact refだけを参照
6. focused、outbound全体、non-secret evidence、spec、commit、push

## 完了条件

実イベント向けの5分talk packが300秒ちょうどで生成され、全segmentが実evidenceへ遡れ、
未実装機能や根拠のない成果を含まず、登壇応募entityへreferenceで接続できる。
