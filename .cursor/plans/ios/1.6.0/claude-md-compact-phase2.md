# CLAUDE.md コンパクト化 Phase 2 — 情報復元 + ベストプラクティス追加

## 概要（What & Why）

Phase 1で CLAUDE.md を 1,976行 → 268行 にコンパクト化した。
しかし2つの問題が残っている:

1. **情報欠落**: 旧CLAUDE.mdから削除されたまま、どこにも移動されていない情報がある
2. **dev差分未反映**: dev ブランチに Phase 1 後に追加された内容（リリース自動化手順等）が未反映
3. **新規ベストプラクティス**: リサーチで判明した並列サブエージェント最適値 + CLAUDE.md肥大化防止メタルールが未記載
4. **Maestro E2E漏れ問題**: エージェントがSpecにMaestro E2Eテストを含めない構造的問題

---

## 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| 1 | 旧CLAUDE.mdの全40セクションが「CLAUDE.md / rules / reference」のどこかに100%存在 | セクション照合 |
| 2 | CLAUDE.md が 300行以下を維持 | `wc -l` |
| 3 | devブランチの新コミット内容が反映されている | diff確認 |
| 4 | 新エージェントがこのルールセットだけで旧エージェントと同等の判断ができる | レビュー |
| 5 | Maestro E2Eがspecとdev-workflowで強制される仕組みがある | ファイル確認 |

---

## As-Is / To-Be（全7タスク）

### タスク1: リリース管理Q&A復元 → `git-workflow.md` に追記

**As-Is:** Q1-Q5, Q8-Q10 が完全に消失。Q6はdev-workflow.md、Q7はgit-workflow.mdに移動済み。

**To-Be:** `git-workflow.md` に `## リリース管理 Q&A` セクションを追加。

**追記内容:**

```markdown
## リリース管理 Q&A

| Q | 質問 | 回答 |
|---|------|------|
| Q1 | devで直接作業？feature ブランチ作る？ | 原則ワークツリー。ドキュメント変更のみdev直接可（worktree.md参照） |
| Q2 | いつブランチを作る？ | dev→mainマージ後。mainからrelease/x.x.xを切ってApp Store提出 |
| Q3 | mainはいつ更新？ | App Store提出の前。Backend先にProdデプロイ |
| Q4 | レビュー中に次バージョン開発OK？ | Yes。devで開発続行 |
| Q5 | 古いコードはいつ消す？ | 2-3バージョン後 or 1-2ヶ月後。95%移行で削除可 |
| Q8 | 同時に複数バージョンをレビューに出す？ | No。1つずつ |
| Q9 | 複数エージェントで同時開発？ | Git Worktrees（worktree.md参照） |
| Q10 | エージェントが勝手にマージ？ | 絶対禁止。チェックリスト提示→ユーザーOK待ち |
```

**注意:** Q1の回答をworktree.mdの矛盾解消ルールと整合させる。

---

### タスク2: ペルソナ詳細版 → `rules/persona.md` 新規作成

**As-Is:** CLAUDE.mdにコンパクト版（10行テーブル）のみ。詳細版（基本属性、コアペインの深掘り、具体的状況、失敗リスト、心理特徴）が消失。

**To-Be:** `.claude/rules/persona.md` を新規作成。以下を含む:

```markdown
# Anicca ターゲットペルソナ（詳細版）

## 基本属性

| 項目 | 定義 |
|------|------|
| 年齢 | 25〜35歳 |
| 性別 | 男女問わず（動画データでは女性が反応多め） |
| 地域 | 日本 / 英語圏 |
| ライフステージ | 社会人、一人暮らしまたはパートナーあり |

## コア・ペイン

> 「6〜7年間、主体性の欠如と自己嫌悪のループから抜け出せていない」

6-7年前から同じ問題 → 習慣アプリ10個以上試した → 全部3日坊主 → 「自分はダメ」 → 諦め → でも変わりたい

## 具体的な状況

| 状況 | 内面の声 | 期間 |
|------|---------|------|
| 夜更かしでスマホを見続ける | 「また3時だ…やめなきゃ…」 | 6-7年 |
| 朝起きられずスヌーズ10回 | 「また遅刻する…自分最悪」 | 6-7年 |
| 習慣アプリをインストール | 「今度こそ！」→3日後削除 | 10回以上 |
| 自分との約束を破る | 「どうせまた無理」 | 何百回も |

## 過去に試したもの（全部3日〜1週間で挫折）

Habitica、Streaks、Habitify等の習慣トラッカー / 瞑想アプリ（Calm、Headspace）/ ポモドーロタイマー / 早起きチャレンジ / 日記アプリ / 筋トレアプリ

## 心理的特徴

| 特徴 | 詳細 |
|------|------|
| **自己信頼ゼロ** | 「自分との約束は守れない」が前提 |
| **諦めモード** | 変わろうとすること自体が怖い |
| **隠れた渇望** | 本当は変わりたい。でも言えない |
| **他者依存傾向** | 自分では無理だから誰かに引っ張ってほしい |

## コンテンツ・UI判断基準

| 判断 | 基準 |
|------|------|
| 刺さるHook | 「6年間、何も変われなかった」「習慣アプリ10個全部挫折」 |
| 避けるHook | 「簡単に習慣化！」「たった○日で！」（信じない、警戒する） |
| UI設計 | 挫折を前提に、責めない、小さすぎるステップ |
```

**CLAUDE.mdのペルソナセクション更新:** `persona.md` への参照リンクを追加。

---

### タスク3: リリース自動化手順 → `deployment.md` に追記

**As-Is:** devブランチに `0d2cae00` で追加されたリリース自動化手順（エージェント向け完全手順、エラーリカバリ、ロールバック）がワークツリーに未反映。

**To-Be:** `deployment.md` に `## 4. リリース手順（完全自動化）` セクションを追加。

**追記内容:** devの `0d2cae00` コミットから以下を抽出:
- エージェント向けリリース手順（bash全ステップ）
- リリースエラー時のリカバリテーブル
- ロールバック手順

**追加で反映（`0c0efd76` の修正）:**
- `git-workflow.md` の GHA Debug で `--ref main` → `--ref dev` に修正
- `infrastructure.md` の GHA Debug でも `--ref main` → `--ref dev` に修正（BLOCKING #2対応）

**`tool-usage.md` Lane テーブルに追記（BLOCKING #1対応）:**
- `set_version` レーンを追加: `| set_version | バージョン番号一括更新 | fastlane set_version version:X.Y.Z |`

**注意:** Serena MCPテーブルの削除は今回スコープ外（境界ルール「復元・追加のみ」遵守）。別タスクで対応。

---

### タスク4: サブエージェント並列ルール → `skill-subagent-usage.md` に追記

**As-Is:** 並列実行の記載はあるが、具体的な推奨数値・バッチ制限・閾値がない。

**To-Be:** `skill-subagent-usage.md` の `### 並列リサーチパターン` セクションの後に追記。

**追記内容:**

```markdown
### 並列実行の最適値（Anthropic公式 + コミュニティBP）

| ルール | 値 | 根拠 |
|--------|-----|------|
| **推奨並列数** | 3-5 agents | Anthropic Multi-Agent Research |
| **最大並列数** | 7 agents（ハードキャップ10） | Claude Code Task tool仕様 |
| **コンテキスト委任閾値** | 40-60%で積極委任 | 75%で強制compact（遅い＆割り込み） |
| **委任最小タスク** | 100行以上の出力 OR 3つ以上の独立タスク | オーバーヘッド vs 効果のバランス |

**重要な制限:** Claude は並列タスクをバッチで実行する。全タスク完了後に次のバッチを開始。
10個投げると最も遅いタスク完了まで全部待機 → 5個×2バッチの方が効率的な場合あり。

Sources:
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
```

---

### タスク5: CLAUDE.mdメンテナンスルール → `CLAUDE.md` に追記（10行）

**As-Is:** CLAUDE.mdにメタルール（何をCLAUDE.mdに書くべきか）がない。結果、エージェントがCLAUDE.mdに情報を追加し続けて肥大化した。

**To-Be:** CLAUDE.mdの「絶対ルール」セクション末尾（「コンテンツ変更ルール」の後）に追加。

**追記内容:**

```markdown
### CLAUDE.md メンテナンスルール

**CLAUDE.mdへの追記前に必ず確認:**

| 判断 | 置き場所 |
|------|---------|
| 毎セッション必要？ | CLAUDE.md（300行以下を維持） |
| 特定ドメインのルール？ | `.claude/rules/` |
| 再利用ワークフロー？ | `.claude/skills/` |
| 低頻度の参照情報？ | `.cursor/plans/reference/` |

**禁止:** 300行を超える追記。超える場合は既存の内容をrules/に移動してから追記する。
**定期見直し:** 四半期ごとにClaude自体にCLAUDE.mdの最適化を依頼する。
```

---

### タスク6: Maestro E2E強制 → `spec-writing.md` + `dev-workflow.md` に追記

**As-Is:**
- `spec-writing.md`: E2Eシナリオは「オプション（UI変更がある場合）」。エージェントが「UIなし」と判断してスキップ可能。
- `dev-workflow.md`: GATE 3にMaestro判定なし。

**問題:** エージェントは楽な方に倒す。「オプション」と書いてあればスキップする。

**To-Be:**

**spec-writing.md の変更:**
コア6セクションの後のオプションを変更:

```markdown
### オプション（該当時のみ — ただしE2E判定は必須記載）

| セクション | いつ必要か |
|-----------|-----------|
| **E2E判定（必須記載）** | **常に。** UI変更あり→シナリオ必須 / UI変更なし→「E2E不要: 理由」を明記 |
| ローカライズ | テキスト追加・変更がある場合 |
| ユーザーGUI作業 | 外部サービス連携・手動セットアップがある場合 |
| Skills / Sub-agents | 複雑なタスクで明示が必要な場合 |

**E2E判定の書き方:**
```
## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | あり / なし |
| 新画面 | あり → Maestro必須 / なし |
| 新ボタン/操作 | あり → Maestro必須 / なし |
| 結論 | Maestro E2Eシナリオ: 必要 / 不要（理由: ○○） |
```
```

**dev-workflow.md の変更:**
GATE 3に追記:

```markdown
## GATE 3 Maestro判定（BLOCKING）

| 条件 | アクション |
|------|-----------|
| SpecにE2E判定セクションがない | **BLOCKING** — Specに戻って追記 |
| E2E判定=必要なのにMaestroテストがない | **BLOCKING** — Maestroテスト作成 |
| E2E判定=不要（理由明記あり） | OK — スキップ可 |
```

---

### タスク7: CLAUDE.md参照先インデックス更新

**As-Is:** `persona.md` がインデックスに含まれていない。CLAUDE.mdメンテナンスルールの記載もない。

**To-Be:** CLAUDE.mdの参照先インデックスを更新:
- `persona.md` を rules/ テーブルに追加
- ペルソナセクションに `詳細: .claude/rules/persona.md` リンク追加

---

## テストマトリックス

| # | To-Be | 検証方法 | カバー |
|---|-------|---------|--------|
| 1 | Q1-Q5,Q8-Q10 が git-workflow.md に存在 | grep確認 | OK |
| 2 | persona.md が rules/ に存在 | ls確認 | OK |
| 3 | リリース自動化が deployment.md に存在 | grep確認 | OK |
| 4 | 並列数値（3-5推奨）が skill-subagent-usage.md に存在 | grep確認 | OK |
| 5 | メンテナンスルールが CLAUDE.md に存在 | grep確認 | OK |
| 6 | E2E判定がspec-writing.mdで必須になっている | 文言確認 | OK |
| 7 | GATE 3 Maestro判定がdev-workflow.mdに存在 | grep確認 | OK |
| 8 | CLAUDE.md が 300行以下 | wc -l | OK |
| 9 | persona.md がインデックスに含まれている | CLAUDE.md確認 | OK |
| 10 | GHA Debug の --ref dev 修正が反映 | git-workflow.md + infrastructure.md確認 | OK |
| 11 | set_version レーンが tool-usage.md に存在 | grep確認 | OK |
| 12 | Skills/Sub-agents がspec-writing.mdのオプションに存在 | grep確認 | OK |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| ルールの内容を大幅変更する | 今回は復元・追加・軽微修正のみ（`--ref dev`修正、E2Eオプション→必須化は対象） |
| testing-strategy.md の変更 | Phase 1で完了済み |
| reference/ ファイルの変更 | Phase 1で完了済み |
| CLAUDE.md全体の再構成 | Phase 1で完了済み。今回は追記のみ |

---

## 実行手順

### 実行順序（依存関係考慮）

```
タスク1: git-workflow.md にQ&A追記
タスク2: persona.md 新規作成           ← 並列可
タスク3: deployment.md にリリース手順追記 ← 並列可
タスク4: skill-subagent-usage.md に並列ルール追記 ← 並列可
    ↓（上記4つ完了後）
タスク5: CLAUDE.md にメンテナンスルール追加
タスク6: spec-writing.md + dev-workflow.md にMaestro強制追記
タスク7: CLAUDE.md 参照先インデックス更新
    ↓
検証: wc -l + grep + diff
```

**タスク1-4は並列実行可能**（異なるファイルへの書き込み）。
**タスク5-7はタスク2完了後に直列実行**（CLAUDE.mdへの書き込みが競合するため）。

---

## ファイル変更サマリ

| ファイル | 操作 | 推定追記行数 |
|---------|------|-------------|
| `.claude/rules/git-workflow.md` | 追記（Q&A + --ref dev修正） | +20行 |
| `.claude/rules/persona.md` | **新規作成** | ~50行 |
| `.claude/rules/deployment.md` | 追記（リリース手順） | +50行 |
| `.claude/rules/skill-subagent-usage.md` | 追記（並列ルール） | +20行 |
| `.claude/rules/spec-writing.md` | 修正（E2E判定必須化） | +15行 |
| `.claude/rules/dev-workflow.md` | 追記（GATE 3 Maestro判定） | +10行 |
| `CLAUDE.md` | 追記（メンテナンスルール + インデックス更新 + ペルソナリンク） | +15行 |

**CLAUDE.md最終行数見込み:** 268 + 15 = **~283行**（300行以下維持）
