# 壊れないAI企業ではなく、壊れても二重実行しないAI企業を作る

*Anicca Manager Research / Phase 10-4 / 2026年11月7日。研究記事ドラフト・未公開。*

AIが文章を1回生成したなら成功した、と判断するのは簡単だ。しかし現実の顧客業務は、ネットワーク切断、課金、外部サービスの遅延、重複した実行、返金、ログ欠落などにさらされる。

## 最も危険なのは「成功したかわからない」
たとえば支払APIへ送信した直後にネットワークが落ちた場合、支払は成功しているかもしれない。ここで同じ操作をやり直すと、二重の支払が発生し得る。

TemporalなどのDurable Executionシステムは、履歴と再生、リトライによってワークフローを続けやすくする。ただしTemporalの公式資料も、Activityは再実行され得るため冪等性が重要だと強調する。Durableだから外部副作用が必ず1回だけ起こる、ではない。

Manager Coreが持つOutboxとReconcilerは、この不確定性を明示的に扱う。外部効果がUNKNOWNなら自動再送せず、提供元の状態を読み取り専用で照合し、結果が確認されるまで成功扱いしない。

## SLOを事業の意思決定へ
GoogleのSREでは、成功率などのService Level Indicator（SLI）を測り、Service Level Objective（SLO）と比較し、許容できる失敗予算を使ってリリースと安定化の優先順位を決める。

重要なのは「99.9%の数字が良い」ということではない。失敗の種類と害を理解し、エラーバジェットが尽きれば新規変更より信頼性改善を優先することだ。

## キャッシュフローとユーザー価値も必要
経済的な自律運用には、本当の入金・出金、認識売上、変動費、固定費、資金繰り、実顧客の成果を継続して照合する必要がある。トークン利用が無料でも、顧客が利益を得たという証明にはならない。利益が正でも人の苦しみが減った証明にはならない。

Phase 10-4の合成コードは、外部UNKNOWNの再送禁止、読み取り専用リトライ、失敗予算、Runway、未配賦費用を検査した。現実のゼロヒューマン会社が完成したという主張ではない。

私たちが作りたいのは、**壊れないと宣伝するAIではなく、壊れた時に何が起きたかを証明でき、誤った再実行を防ぎ、持続的に成果を出せるAI**である。

### Sources
- Temporal Durable Execution: https://docs.temporal.io/evaluate/understanding-temporal
- Temporal Activity Idempotency: https://docs.temporal.io/develop/python/best-practices/error-handling
- Google SRE SLOs: https://sre.google/workbook/implementing-slos/
- Google SRE Alerting: https://sre.google/workbook/alerting-on-slos/
- FinOps for AI: https://www.finops.org/wg/finops-for-ai-overview/

*本稿は安全・信頼性・財務成績を実測で主張するものではなく、研究・設計原則を述べる。*