---
description: 現在の spec と最小 handover を参照する、次セッション用の Start prompt と Go prompt を生成する。
---

# セッション引き継ぎ

## 実行手順

1. 現在の作業の spec ファイルを特定する。会話で扱っている `docs/superpowers/specs/*.md` を優先し、特定できない場合は同ディレクトリで最新の spec を使う。必ずファイルを読み、残 TODO 表が現在の状態を表していることを確認する。
2. `.claude/handovers/` に handover ファイルを書く。既存の当該 handover があれば更新し、無ければ `YYYY-MM-DD_HHmm.md` を作る。中身は次の情報だけにする。
   - spec の絶対パス
   - 残 TODO の正本が spec の TODO 表であること
   - 未 commit の変更に関する注意点。無ければ「なし」
3. handover には手順2の3項目以外を書かない。その他の情報は spec に反映する。
4. handover ファイルと spec ファイルの絶対パスを取得する。
5. ユーザーへの出力は、次の2つの code block だけにする。見出し、説明、前置き、後書き、補足を出力しない。`<handover-file-path>` と `<spec-path>` はプレースホルダーのまま残さず、手順4で取得した実際の絶対パスに置換する。

```
Read <handover-file-path> and the spec at <spec-path>. List ALL remaining TODOs in order, then show an ASCII diagram of the TO-BE end state after all TODOs are done. Then stop and wait — I want to discuss before you start.
```

```
Read <handover-file-path> and the spec at <spec-path>. Execute ALL remaining TODOs in order, starting from #1. No questions, no-human-loop. Verify each with real E2E evidence, update the spec TODO table + TaskList as you go, commit+push each meaningful edit. Finish everything.
```
