# Connector O1B-17 Luma日付別inventory 実装plan

1. `luma-discovery`と`luma-event-detail`へin-process provenance検証を追加する。
2. 日付別snapshotの失敗条件を先にtestで固定する。
3. verified coverage、verified inventory、全verified detailから21日snapshotを構築する。
4. Connector events packへ全candidate detail読取と日付投影を接続する。
5. read-only scriptで実Luma Tokyoを終端まで読み、公開event内容を出力せず件数だけ証拠化する。
6. focused test、outbound全回帰、実readbackを実行する。
7. master spec、evidenceを更新し、commit/pushする。

