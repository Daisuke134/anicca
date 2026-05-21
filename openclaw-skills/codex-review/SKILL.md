# Codex Review（Anicca 用・VPS スキル）

Anicca が **spec または実装** を Codex でレビューするときに使うスキル。VPS 上で Anicca がこのスキルを呼び出す。

## いつ使うか

- **spec レビュー**: anicca-auto-development の流れで spec を書いたあと。ok: true になるまで修正してから実装に回す。
- **実装レビュー**: Codex が実装したあと。コード・品質を再度検証して ok: true になってから E2E に進む。

## やり方（VPS）

1. **Codex CLI が VPS で使える場合**  
   workspace に対象リポがあり、`codex` が PATH にあるときは、対象（spec のパスまたは diff 範囲）を指定して `codex exec --sandbox read-only` でレビュープロンプトを実行する。出力は JSON（ok, blocking, advisory, summary）に従って解釈する。

2. **Codex が VPS にない場合**  
   レビュー依頼を **Slack** に投稿する。「次の spec/実装を Codex Review してほしい。パス: …。結果（ok: true/false と blocking の有無）を返して。」ユーザーがローカルで codex-review を実行し、結果を Slack で返す。Anicca はその結果を受け取って次へ進む。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 出力の扱い

- `ok: true` → 次ステップへ（実装依頼または E2E 検証）。
- `ok: false` → blocking を解消するまで修正し、再度 codex-review を実行する（このスキルを再度使う）。

## 他スキルとの関係

- **anicca-auto-development** が spec レビューと実装レビューのタイミングでこのスキル（codex-review）を呼び出す。Anicca は Cursor やローカル環境を参照しない。使うのは **VPS のスキル** だけ。
