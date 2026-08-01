# Connector O1B-22 実装plan

1. coverage continuation state machineをtest先行で定義する。
2. open日が残る全既知結果を次action + next runへ変換する。
3. events packへ唯一のcontinuation入口を接続する。
4. focused/full regressionと証拠を作る。
5. master specをO1B-23へ進めcommit/pushする。
