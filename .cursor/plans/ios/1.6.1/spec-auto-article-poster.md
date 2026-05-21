# Anicca Auto Article Poster Spec

## 決定事項

### アプローチ: cursor-ide-browser MCP + Draft Mode

| 検討オプション | 判定 | 理由 |
|--------------|------|------|
| note.com公式API | ❌ 存在しない | 公式APIは提供されていない |
| note.com非公式API | ❌ リスク高 | 予告なく仕様変更・停止の可能性、利用規約違反リスク |
| Playwright MCP | △ 追加設定必要 | 良いが新規セットアップが必要 |
| **cursor-ide-browser MCP** | ✅ 採用 | 既にプロジェクトに設定済み、実ブラウザ指紋でボット検出回避 |

### 投稿ポリシー

| 項目 | 決定 |
|------|------|
| 公開モード | **Draft（下書き）のみ** — 人間レビュー後に手動公開 |
| 画像 | 生成してクリップボードにコピー → 「Cmd+Vで貼って」と案内（95%自動化） |
| 頻度 | 週1-2回（Build in Public記事） |

---

## 概要

Aniccaが自律的にBuild in Public記事を生成し、note.comに下書き保存するスキル。

**トリガー例:**
- 「noteに投稿して」
- 「今週の開発をまとめて」
- 実装完了後に自動（将来）

**出力:**
- SEO対策されたタイトル
- ペルソナに合わせた本文
- note.comへ下書き保存

**注:** サムネイル画像は手動で準備

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    SKILL.md                              │
│  (トリガー定義、ワークフロー指示)                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              コンテンツ生成フェーズ                        │
│  1. git diff / commit log からネタ抽出                   │
│  2. SEOガイドでタイトル生成                               │
│  3. テンプレートで本文生成                                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              note.com投稿フェーズ                         │
│  cursor-ide-browser MCP                                 │
│  1. browser_tabs → 既存タブ確認                          │
│  2. browser_navigate → note.com/post                    │
│  3. browser_lock → 操作ロック                            │
│  4. browser_snapshot → フォーム構造取得                  │
│  5. browser_fill → タイトル入力                          │
│  6. browser_type → 本文入力                              │
│  7. browser_click → 下書き保存                           │
│  8. browser_unlock → 操作解除                            │
└─────────────────────────────────────────────────────────┘
```

---

## ファイル構成

```
.claude/skills/auto-article-poster/
├── SKILL.md                 # スキル本体（トリガー・ワークフロー）
├── seo-guideline.md         # キーワード変換表、タイトルパターン
├── article-template.md      # 記事構成テンプレート
└── tone-and-voice.md        # Aniccaのトーン＆ボイス定義
```

**注:** 画像生成スクリプトはP2として後日実装予定。現状は手動でサムネイルを準備する。

---

## SEOガイドライン

### キーワード変換表

| 技術用語 | 一般用語 |
|---------|---------|
| API連携 | 自動化 |
| LLM | AI |
| プロアクティブ通知 | 自動リマインド |
| 行動変容 | 習慣化サポート |
| Nudge | やさしい後押し |
| SwiftUI | iOSアプリ |

### タイトルパターン（バズりやすい型）

| パターン | 例 |
|---------|-----|
| 数字 + 変化 | 「6年間失敗し続けた習慣化が、○○で変わった」 |
| 問題 + 解決 | 「毎日3日坊主だった私が、AIに助けられた話」 |
| ストーリー | 「習慣アプリ10個挫折した人間が作ったアプリの話」 |
| ハウツー | 「○○を自動化したら毎日の発信が10倍楽になった」 |
| 意外性 | 「AIが勝手に記事を書いてくれるようになった」 |

---

## 記事テンプレート

```markdown
# [タイトル]

## この記事で学べること
- [箇条書き3つ]

## 何を作ったのか？
[1文で説明]

**一言で言うと**: [キャッチーな要約]

## なぜ作ろうと思ったのか？
[ペルソナの苦しみに寄り添う]
- 6年間、習慣化に失敗し続けてきた
- アプリを10個以上試したけど全部挫折
- 「自分はダメだ」と思い込んでいた

[共感ポイント]

## どうやって作ったのか？

### Step 1: [見出し]
[説明]

**ポイント**: [学び]

### Step 2: [見出し]
[説明]

**ハマったところ**: [失敗談]

[...続く...]

## 学んだこと・気づき
1. [学び1]
2. [学び2]
3. [学び3]

## まとめ
[締めの言葉 — 苦しんでいる人へのメッセージ]

#BuildInPublic #個人開発 #AI活用 #習慣化 #行動変容 #Anicca
```

---

## Aniccaトーン＆ボイス

| 要素 | 定義 |
|------|------|
| **視点** | 「苦しみ」を知っている仲間として |
| **語り口** | 正直、失敗を隠さない、自己開示 |
| **禁止** | 「簡単！」「たった○日で！」（ペルソナが警戒する） |
| **推奨** | 「6年間失敗した」「10個挫折した」（共感を生む） |
| **差別化** | 「世界初のプロアクティブ行動変容エージェント」 |

---

## cursor-ide-browser MCPの使い方

### 認証フロー（初回のみ）

1. 手動でnote.comにログイン（ブラウザで）
2. MCPはそのセッションを利用

### 投稿フロー（cursor-ide-browser MCP仕様に準拠）

```
1. browser_tabs (action: "list")
   → 既存タブ確認

2. browser_navigate (url: "https://note.com/post")
   → 投稿画面へ（2-3秒待機）

3. browser_lock
   → 操作をロック（※既存タブがないとエラー）

4. browser_snapshot
   → フォーム構造取得（element refを確認）

5. browser_fill
   → element: "タイトル入力欄"
   → ref: [snapshotで取得したref]
   → value: "記事タイトル"

6. browser_type
   → element: "本文入力欄"
   → ref: [snapshotで取得したref]
   → value: "本文..."

7. browser_click
   → element: "下書き保存ボタン"
   → ref: [snapshotで取得したref]

8. browser_unlock
   → 操作完了
```

### API引数の注意

| ツール | 必須引数 | 説明 |
|--------|---------|------|
| `browser_fill` | element, ref, value | refはsnapshot結果から取得 |
| `browser_type` | element, ref, value | fillと違い追記（clear不要時） |
| `browser_click` | element, ref | refはsnapshot結果から取得 |
| `browser_snapshot` | (optional) selector | CSS selectorで範囲絞り込み |

### 注意事項

- `browser_lock` は既存タブがないとエラー → 先に `browser_navigate`
- `ref` は `browser_snapshot` の結果から取得（推測不可）
- 画像アップロードはセキュリティ制限あり → 手動Cmd+V案内
- 下書き保存まで（公開は手動）

---

## 実装ステップ

| Step | タスク | 優先度 | 状態 |
|------|--------|--------|------|
| 1 | `.claude/skills/auto-article-poster/SKILL.md` 作成 | P0 | ✅ 完了 |
| 2 | `seo-guideline.md` 作成 | P0 | ✅ 完了 |
| 3 | `article-template.md` 作成 | P0 | ✅ 完了 |
| 4 | `tone-and-voice.md` 作成 | P0 | ✅ 完了 |
| 5 | note.com投稿フローをテスト | P0 | 未着手 |
| 6 | 画像生成スクリプト | P2 | 未着手（後日） |
| 7 | 本番運用開始 | P1 | 未着手 |

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| note.comのUI変更でスクリプト壊れる | セレクターを汎用的に、エラー時は手動フォールバック |
| ボット検出 | cursor-ide-browserは実ブラウザ指紋を使うので低リスク |
| 品質問題 | 必ずDraft保存 → 人間レビュー → 手動公開 |
| レート制限 | 週1-2回の投稿なら問題なし |

---

## 参考リソース

| リソース | URL/パス |
|---------|----------|
| cursor-ide-browser MCP | `/Users/cbns03/.cursor/projects/.../mcps/cursor-ide-browser/` |
| Build in Public記事の例 | https://note.com/handball_jin/n/n55d664dc0c50 |
| daangn/note-com-js SDK | https://github.com/daangn/note-com-js |
| Playwright MCP公式 | https://playwright.dev/agents/playwright-mcp-browser-automation |

---

## 成功基準

| 指標 | 目標 |
|------|------|
| 記事生成時間 | 5分以内（手動だと30分） |
| 手動作業 | 画像貼り付け + 最終レビュー + 公開ボタンのみ |
| 品質 | 人間が書いたように見える、ペルソナに刺さる |
| 投稿頻度 | 週1-2回を継続 |

---

最終更新: 2026年2月3日
