# 自然な日本語Telegram UX設計

## 目的

Marketing Engine内部の正規化キー、provider名、experiment IDは英語のまま維持する。一方、オーナーがTelegramで読む本文はプロフィールの`owner_report_language=ja`に従い、自然な日本語で「何が起きたか」「数字が何を意味するか」「次に何をするか」を説明する。

## 採用方式

数字、状態、attribution、勝敗、次の操作は決定論的コードが台帳から確定する。文章は用途別の日本語テンプレートが組み立てる。LLMに数字や勝敗を自由生成させない。商品コンテンツの言語とオーナー報告言語は分離するため、英語ebookの結果も日本語で報告する。

## メッセージ

1. 実操作直後の「公開・変更完了」
2. 6時間・24時間・72時間・7日の「途中経過」
3. 商品ごとの「今日の結果」
4. 成熟cohortの「実験結果」
5. 二重操作、認証、計測、lease、timeoutの「問題報告」
6. 全商品の「今週のまとめ」

本文は自然文を先に置く。run ID、receipt ID、hash、provider URLは末尾の「確認情報」にまとめる。`not_mature`は「まだ判断できる時間ではありません」、`unavailable`は「取得できませんでした」、`unknown`は「現在の証拠では分かりません」と表現する。成功したscoped queryだけが0を表示できる。

## 完了条件

- 任意のapp/ebook/product manifestから同じ日本語UXを生成できる。
- Telegram本文の全数値がcanonical ledgerと一致する。
- 同じrun/message keyを二重送信しない。
- 若い実験を勝ち負けにせず、利益不明を売上やMRRで代用しない。
- owner-facing fixtureが自然な日本語としてレビューを通る。
