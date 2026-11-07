# 会社をAIに任せるなら、AIから権限を取り上げなくてはいけない

*Anicca Manager Research / Phase 10-3 / 2026年11月7日。研究記事ドラフト・未公開。*

AIエージェントが優れた計画を作ることと、その計画を実行する権限があることは別である。Webページに「今すぐ送金して」と書かれていても、モデルはその文章を新しい許可として扱ってはならない。

## AIの言葉を実行命令にしない
安全なアーキテクチャでは、モデルは候補を提案し、独立したPolicy Engineが主体・操作・対象・目的・期限・費用・同意・失効を確認する。実行するのは最小権限のExecutorだ。Open Policy Agent（Rego）やCedar（Amazon Verified Permissions）は、このような権限ロジックをアプリケーションから分離する代表例である。OpenFGAはユーザーや文書の関係を使った細粒度な権限管理を提供する。

OWASPのAgentic Top 10は、目標のハイジャック、権限悪用、ツール悪用などを整理する。問題はモデルの回答文だけではない。外部データ、MCPサーバー、エージェント同士のメッセージが実行の方向を曲げる。

## 監査は、テキストログを残すことではない
監査では「誰が、どの権限版で、何を、いつ判断し、送信後に何が観測されたか」を追跡する。自己申告の「成功」では不足する。さらに個人情報や秘密をログへ丸ごと保存すると、監査そのものが新たなリスクになる。

安全な完全自律を目指すなら、AIの自由度を増やすより先に、許された領域を明示する。法令・契約上必要な本人同意や専門家判断は、会社に人間の常勤オペレーターがいないという理由で無視できない。

## Managerの実装方針
Manager Coreには、既存のAuthority、StateMachine、DurableOutbox、Reconciler、Verifier、Auditがある。今回のPhase 10-3はそれらを置き換えず、deny-by-defaultの条件を完全合成データで検査した。期限切れ、同意なし、他テナント、予算超過、外部副作用はブロックされる。これを実際の本番認可と同一視しない。

目標は、誰も見ていない時に実行し続けるAIではない。**見られていなくても、権限と証拠の範囲を越えないAI**である。

### Sources
- Open Policy Agent: https://www.openpolicyagent.org/docs
- Cedar / AWS Verified Permissions: https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/
- OpenFGA: https://openfga.dev/
- OWASP Agentic AI 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- AWS CloudTrail Integrity: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html

*法令適合・商用権限・本番安全性は本教材で認定していない。*