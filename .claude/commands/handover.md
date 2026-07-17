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
Dais がそのまま貼れば **human-in-the-loop 無しで次の最優先を E2E 完遂**できる `/goal` を生成して載せる。
- **★`/goal` は必ず1つだけ★**（goal-setter の掟 = "one durable objective"）。複数 goal を1回に渡すと executor が散って**どれも完遂できない**。残作業が複数ドメインにまたがっても、**最優先の1ドメインだけ** `/goal` にする。他は下の「次にやること」表に置く（表は goal ではなく次セッションが順に拾う索引。落ちない）。
- 最優先の選び方: 「今これが終われば一番前に進む」1つ。迷ったら Dais に「次の1 goal はどれか」だけ聞く。
- `goal-setter:goal-setter` skill の流儀（`~/.claude/skills/goal-prompt-builder/` の golden template）で書く。
- **5節をこの順で**: `Objective` / `Scope` / `Constraints` / `Done when` / `Stop if`。
- `Done when` は **machine-checkable な検証コマンド + evidence 条件**で書く（自己申告 done 禁止・実 side-effect / 実ブラウザ / on-chain / message_id で照合）。
- `Stop if` に必ず: 同一フェーズ3回 FAIL で止めて handover / 破壊的・不可逆操作 / 週次token残 10%未満。

#### `Constraints` に必ず入れる（全タスク共通・省略禁止）
```
- 開発方式 = GLVS（Goal → Loop → Verify → State）。会話でなく file に進捗を書く
- 実装は Sonnet subagent / spec を実装側で曲げない / VCSDD token 上限厳守
- spawn 前後に TaskList → TaskCreate → TaskStop
- 実測せず断定しない（既定の姿勢 = 「私は間違っている」。断定前に外部検索 + 実測）
- 車輪の再発明禁止（作る前に web+gh で既存実装を探して copy+tweak）
- 編集ごとに commit+push（確認を求めない）
- ¥0 は ¥0 と報告する。盛らない
```

#### ★コードを1行でも触る残作業がある場合、`Constraints` に VCSDD を明記する（省略禁止）★
残作業が実装・修正・リファクタ・設定変更のいずれかを含むなら、次のブロックを**そのまま**入れる。
（ドキュメント/記事のみの残作業なら、このブロックは不要 — 代わりに「該当なし（doc のみ）」と1行書く）
```
- ★実装は VCSDD の実コマンドを phase 順に呼ぶ。SPEC 本文への手書き追記は進捗ではない★
    /vcsdd:vcsdd-init → vcsdd-spec → vcsdd-spec-review → /vcsdd:vcsdd-tdd(RED)
    → vcsdd-impl(GREEN) → vcsdd-adversary → vcsdd-harden → vcsdd-converge
  `.vcsdd/features/<name>/state.json` の phase が進んでいないものは「やった」と言わない
- 規模に応じ mode: lean / strict を選んでよいが、★フェーズ自体は飛ばさない★
- adversary は毎 iteration fresh spawn（model: sonnet 明示）。blocking 1件でも次フェーズ禁止
- 最後に reality-verifier が実ブラウザ / on-chain / 実コマンド出力で source of truth を確認するまで完了と言わない
- worktree-per-task（`git worktree add .worktrees/<task> -b feature/<task>`）
```

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
