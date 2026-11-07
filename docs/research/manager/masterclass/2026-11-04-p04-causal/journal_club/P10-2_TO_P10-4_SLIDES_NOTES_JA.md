# P10-2〜P10-4｜Managerの研究用スライド25枚追加の構成／日本語講演ノート

**2026-11-07**。P10-1既存8枚と組み合わせた、合計33枚のPowerPoint/PDFを別添成果物として作成するための講義設計。既存の本番34枚と詳細研究アーカイブ118枚は置換しない。すべての経済値と権限判断は合成・教育用で、実企業の利益や実人間の便益の証拠ではない。

| Slide | Heading | Speaker intent |
|---:|---|---|
| 09 | P10-2 資本配分 | モデルの精度だけで研究費を決定しない |
| 10 | 予算の制約 | cash、reserve、project cap、rights、riskを分離 |
| 11 | Explore / Exploit | 研究と実製品の配分を明示的に選ぶ |
| 12 | Value of Information | EVPI/EVSIと研究費用の差を理解 |
| 13 | 完全架空の配分計算 | 1,000¢現金、450¢reserve、500¢cap、投資480¢ |
| 14 | FinOps実務の標準 | 企業は費用配賦と業務単位の成果を比較する |
| 15 | P10-2の実装 | 予算計画と実行権限を分離し、費用を事後照合 |
| 16 | P10-3 ガバナンス | 「提案した」ことと「許可された」ことは違う |
| 17 | Policy Decision Point | model → policy gate → privileged executor |
| 18 | OPA / OpenFGA / Cedar | 既存権限を維持し、必要ならOSSを再利用 |
| 19 | 権限のフィールド | tenant/consent/scope/expiry/budget/policy version |
| 20 | OWASP Agentic | prompt injection、goal hijack、tool misuse等の脅威 |
| 21 | Privacy & Audit | 情報最小化、独立ログ、SHA鎖の限界 |
| 22 | Kill Switch / STOP | UNKNOWN、撤回、超過はSTOP/NO_ACTION |
| 23 | P10-3合成ゲート | 正しい読取要求はSIMULATIONのみ。外部効果禁止 |
| 24 | P10-4 継続運用 | 一発成功ではなく長期間の安全な成果 |
| 25 | Durable Execution | replayは便利だが外部副作用exactly-onceでない |
| 26 | UNKNOWN Effect | 曖昧な送信後は絶対に盲目的に再送しない |
| 27 | SLO & Error Budget | 1,000仕事/99.5%目標→許容失敗5 |
| 28 | Runway & Cost | 現金と費用を別途照合し、未配賦を隠さない |
| 29 | Operational Loop | admit/reserve/dispatch/reconcile/verify/learn |
| 30 | Safe Delivery Stages | read-only→shadow→bounded canary→独立評価 |
| 31 | Manager Architecture | 予測、認可、実行、検証、経済、学習の関係 |
| 32 | 教育完了と実証未完 | 合成41テストは本番の権限・利益・信頼性を証明しない |
| 33 | Primary sources | FinOps, ISPOR, OPA, OWASP, Temporal, Google SRE |

## Design
16:9、Noto Sans CJK JP、濃紺背景、ティール/青/紫/アンバーの情報階層、ネイティブ編集可能テキストと図形。全ページに日本語発表者ノート。既存P10-1の8枚は本文を維持し、合計枚数のフッターのみ更新。

## Source list
- https://www.finops.org/wg/finops-for-ai-overview/
- https://www.finops.org/framework/capabilities/budgeting/
- https://proceedings.mlr.press/v35/badanidiyuru14.html
- https://pmc.ncbi.nlm.nih.gov/articles/PMC7373630/
- https://www.openpolicyagent.org/docs
- https://openfga.dev/
- https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- https://docs.temporal.io/develop/python/best-practices/error-handling
- https://sre.google/workbook/implementing-slos/
