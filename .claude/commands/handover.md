---
description: セッション引き継ぎノートを生成し、/goal プロンプト付きで Dais のメールへ自動送信する（区切り/終了時）。.claude/handovers/YYYY-MM-DD_HHmm.md に保存。
---

# セッション引き継ぎノート生成 + メール送信（人手ゼロで完結）

セッション終了時や作業の区切りで、引き継ぎノートを生成し、**Dais が何もしなくても済むように** `/goal` プロンプト込みでメール送信までやる。

## 手順（この順に必ず全部やる）

1. 今回のセッションで行ったことを振り返る。
2. `.claude/handovers/` が無ければ作成。
3. `date +%Y-%m-%d_%H%M` で時刻取得 → `YYYY-MM-DD_HHmm.md` で保存（同名なら `_2` 連番）。
4. 下記構成でノートを書く。
5. `git add + commit + push`。
6. **★メール送信（必須・下記の正確なコマンドを使う。gog の設定を探し回らない）★**
7. 送信の message_id を最終報告に載せる（送った証拠）。

## 引き継ぎノートの構成

必ず以下を含める。該当なしは「なし」と記載。

### 今回やったこと / 決定事項 / 捨てた選択肢と理由 / ハマりどころ / 学び / 次にやること / 関連ファイル
- 事実ベース・箇条書き中心。推測や曖昧表現を避ける。
- 「捨てた選択肢と理由」は特に重要（同じ議論を繰り返さない為）。

### ★次セッションの /goal コマンド（必須・これが本体）★
Dais がそのまま貼れば **human-in-the-loop 無しで残作業を E2E 完遂**できる `/goal` を1つ生成して載せる。
- `goal-setter:goal-setter` skill の流儀（`~/.claude/skills/goal-prompt-builder/` の golden template）で書く。
- **5節をこの順で**: `Objective` / `Scope` / `Constraints` / `Done when` / `Stop if`。
- `Done when` は **machine-checkable な検証コマンド + evidence 条件**で書く（自己申告 done 禁止・実 side-effect / 実ブラウザ / on-chain / message_id で照合）。
- `Constraints` に必ず: VCSDD token 上限厳守 / 実装は Sonnet subagent / spec を実装側で曲げない / spawn 前後に TaskList→TaskCreate→TaskStop / 実測せず断定しない / 編集毎 commit+push / ¥0 は ¥0 と報告。
- `Stop if` に必ず: 同一フェーズ3回 FAIL で止めて handover / 破壊的・不可逆操作 / 週次token残 10%未満。

### 新セッション開始プロンプト
- 次の agent がそのまま貼って開始できる正確なプロンプトを1つ。冒頭で「まず `/context` を測れ」を入れる。

## ★メール送信（正確なコマンド。毎回これをそのまま使う）★

gog の keyring password と account は **`~/.zshenv` に恒久設定済み**（`GOG_KEYRING_PASSWORD` / `GOG_ACCOUNT=keiodaisuke@gmail.com`）。
だから **探し回らない**。以下1コマンドで送る（ノート全文を本文にする）:

```bash
HN=.claude/handovers/<生成したファイル名>.md
zsh -c "source ~/.zshenv; gog gmail send \
  --account keiodaisuke@gmail.com \
  --to keiodaisuke@gmail.com \
  --subject '[Anicca handover] $(date +%Y-%m-%d_%H%M) — <一行サマリ>' \
  --body-file '$HN'"
```

- `zsh -c "source ~/.zshenv; ..."` にするのは `GOG_KEYRING_PASSWORD` を確実に読ませる為（`-ic` は daytona 補完で `compdef` ノイズが出るので使わない）。
- 万一 `no TTY`/`missing --account`/`keyring` エラーが出たら **フォールバック**（探し回らず即これ）:
  ```bash
  export GOG_KEYRING_PASSWORD=$(grep '^GOG_KEYRING_PASSWORD=' ~/.openclaw/.env | head -1 | cut -d= -f2-)
  gog gmail send --account keiodaisuke@gmail.com --to keiodaisuke@gmail.com \
    --subject '[Anicca handover] ...' --body-file "$HN"
  ```
- `--body-file` に**ノート全文**を渡す（`/goal` プロンプトが本文に含まれる＝Dais はメールからコピペするだけ）。

## ルール
- 簡潔・事実ベース。
- **メールを送るまでが /handover**（ノート生成だけで終わらせない）。送った message_id を報告する。
- Telegram も併用してよい（`openclaw message send --channel telegram --target 8547730585`）が、**メールは必須**。
