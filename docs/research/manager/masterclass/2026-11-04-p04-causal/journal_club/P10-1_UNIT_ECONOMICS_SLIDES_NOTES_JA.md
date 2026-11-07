# P10-1｜研究用補足スライド（既存34枚本番スライドは変更しない）

**用途**：詳細アーカイブ用の新しい8枚の講義補足。既存研究118枚の総数を自動的に119枚以上と宣言しない。別ファイルP10-1補足デッキとして保存し、後で明示的に統合する。全値は架空。

## Slide 01｜予測から事業価値へ
見出し：正しい予測 ≠ 完了した仕事 ≠ 利益 ≠ 本人の便益
本文：P09の問い「未知への汎化」→P10の問い「継続して価値を届けられるか」。単位はAPIコールでなくwork_item。
Speaker notes：何を測るかで製品の方向が変わる。予測器は重要だが、顧客の目標達成は独立に検証する。

## Slide 02｜1件の仕事の経済構造
見出し：WORK ITEM → ATTEMPTS → VERIFIED OUTCOME
本文：推論、ツール、リトライ、人的救済、決済、返金を結びつける。送信レシートと結果の確認を分離。
Speaker notes：失敗したattemptを消さず原価に含める。Trace IDとwork_item_idをjoinする。

## Slide 03｜売上・原価・利益
見出し：CM = Recognized Net Revenue − Variable Costs
本文：認識売上、変動費、固定費、営業利益を区別する。Cash / billing / recognized revenueは同じでない。
Speaker notes：3件の例。Aは+4.10ドル、Bは−2.30ドル、Cは−0.10ドル。合計+1.70ドル。全部架空。

## Slide 04｜成功当たり費用
見出し：安い推論 ≠ 安い成功
本文：A・B・Cの総費用3.30ドル ÷ VERIFIED_SUCCESS 1件 = 3.30ドル/成功。
Speaker notes：成功したAの0.90ドルだけを用いると、失敗や安全停止に使った費用が消える。

## Slide 05｜人の介助とZero-Humanの検証
見出し：介入が「ない」ことは計測して初めて言える
本文：human_touch_count、assist_seconds、rescue_rate、unassisted_verified_success_rate。
Speaker notes：裏側の人手、外部委託、事後修正を計測。安全必須の承認は削る目標ではない。未計測≠0。

## Slide 06｜証拠と計測のアーキテクチャ
見出し：Trace × Provider bill × Revenue ledger × Readback
本文：OTelでトークン/呼出、FOCUSで費用、経理ソースで収益、独立観測で成果。READ-ONLY Projection。
Speaker notes：唯一の権限と事業正本は既存システム。新しい台帳を正本にしない。

## Slide 07｜利益とは別の利用者便益
見出し：利益が正でも、心理的便益は未証明
本文：本人の選択目標、生活機能、悪化・害、対照群を評価。NOT_MEASUREDは成功扱いしない。
Speaker notes：P04・P06・P07の因果・尺度・安全の知識を再利用する。売上を苦の軽減へ換算しない。

## Slide 08｜P10-1受入・次のP10-2
見出し：合成で検証→実業務で照合→比較実験
本文：重複費用、返金、未知の結果、原価配賦、人手の欠測を検査。BFM-01/02、INT-02は並行で未完了。
Speaker notes：講義終了と製品化完了を別管理。次P10-2は資金配分と価値の比較。

一次資料：FinOps Unit Economics / FOCUS 1.3 / OpenTelemetry GenAI / Google Cloud Agent KPIs / Stripe Revenue Recognition / NIST AI RMF。
