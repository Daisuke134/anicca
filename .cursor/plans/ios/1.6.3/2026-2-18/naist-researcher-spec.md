# 仕様書：naist-researcher v1.0
# 学振DC1研究計画書 自動生成スキル

最終更新: 2026-02-21
ステータス: Confirmed（調査完了・実装待ち）

---

## 開発環境

| 項目 | 値 |
|------|-----|
| リポジトリ | `github.com/Daisuke134/naist-researcher`（✅ 作成済み） |
| ブランチ | `main` |
| Mac Mini | `ssh anicca@100.99.82.95` |
| スキル配置先（Mac Mini） | `/home/anicca/skills/naist-researcher/` |
| スキル配置先（ローカル） | `~/.claude/skills/naist-researcher/` |
| K-Dense writer | `~/.claude/skills/claude-scientific-writer/`（セットアップ必要） |
| 作業ディレクトリ | `/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/2026-2-18/` |

---

## 概要（What & Why）

| 項目 | 内容 |
|------|------|
| 名前 | `naist-researcher` |
| 一言説明 | 研究テーマを入力するだけで、学振DC1研究計画書の初稿をRalphループで自動生成するスキル |
| なぜ必要か | 研究計画書の初稿作成に平均2〜3週間かかる。文献調査・採択例参照・査読シミュレーションを全部AIが並列で実行することで30分に短縮する |
| 対象ユーザー | 田中研 / ComBeNSラボメンバー（学部生・修士・博士） |
| 動作環境A | Claude Code / Cursor（ローカル実行） |
| 動作環境B | Slack × OpenClaw（Mac Mini、インストール不要） |
| v1スコープ | 学振DC1研究計画書の日本語初稿生成のみ |

---

## 使用する既存ライブラリ（オリジナルはゼロ）

| ライブラリ | 役割 | 入手先 | 確認状況 |
|-----------|------|--------|---------|
| `K-Dense-AI/claude-scientific-writer` | 文献検索・論文執筆・引用管理・図生成・査読シミュレーション | `github.com/K-Dense-AI/claude-scientific-writer` | ✅ クローン済み・動作確認済み |
| `parallel-web` スキル（K-Dense内） | 全Webサーチ・URL抽出・深掘りリサーチ | `skills/parallel-web/scripts/parallel_web.py` | ✅ K-Dense内に存在確認 |
| `research-lookup` スキル（K-Dense内） | 学術論文検索（Perplexity Sonar Pro経由） | `python research_lookup.py` | ✅ K-Dense内に存在確認 |
| `research-grants` スキル（K-Dense内） | グラントプロポーザル生成ワークフロー（JSPS向けカスタマイズ） | `skills/research-grants/SKILL.md` | ✅ K-Dense内に存在確認 |
| `peer-review` スキル（K-Dense内） | 採択例との比較・査読スコア算出・改善フィードバック | `skills/peer-review/` | ✅ K-Dense内に存在確認 |
| `scientific-schematics` スキル（K-Dense内） | 研究フロー概念図の自動生成 | `python scripts/generate_schematic.py` | ✅ K-Dense内に存在確認 |
| `ralph-autonomous-dev`（既存スキル） | スコア閾値まで自動反復するループ制御 | `.claude/skills/ralph-autonomous-dev/SKILL.md`（既存） | ✅ 既存 |

---

## 必須APIキー（3つ全て必要）

| APIキー | 用途 | 取得先 |
|--------|------|-------|
| `ANTHROPIC_API_KEY` | Claude API（必須） | console.anthropic.com |
| `OPENROUTER_API_KEY` | Perplexity Sonar Pro Search（research_lookup.py経由） | openrouter.ai |
| `PARALLEL_API_KEY` | parallel_web.py 全Webサーチ | parallel.ai または K-Dense README参照 |

---

## K-Dense scientific-writer 正しいインストール方法

```bash
# ❌ 間違い（Claude Code マーケットプレイスに存在しない）
/plugin install claude-scientific-writer

# ✅ 正解: git clone（無料）
git clone https://github.com/K-Dense-AI/claude-scientific-writer ~/.claude/skills/claude-scientific-writer

# または pip install（有料パッケージ版）
pip install scientific-writer

# APIキー設定（~/.env または ~/.zshrc に追加）
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."
export PARALLEL_API_KEY="..."
```

---

## パイプライン全体フロー

```
ユーザー入力（Slack or Cursor）
「研究テーマ・ラボ・締切」を送る
        ↓
Phase 1: 文献調査（K-Dense tools使用）
  1-1: research_lookup.py でテーマ関連論文20本取得
       → sources/papers_YYYYMMDD_research.md に保存
  1-2: parallel_web.py search で先行研究・競合手法調査
       → sources/search_YYYYMMDD_background.md に保存
  1-3: parallel_web.py research --processor pro-fast で深掘り
       → sources/research_YYYYMMDD_gaps.md に保存
  1-4: 先行研究のギャップ（Gap Analysis）を特定
        ↓
Phase 2: 初稿生成（research-grants スキル、JSPS DC1版）
  - 学振DC1フォーマット（5,000〜8,000字）
  - 採択例2本の構造に従う（社会的背景→目的→新規性→方法→期待成果）
  - writing_outputs/<timestamp>_dc1_draft/ に保存
  - scientific-schematics で概念図1枚生成
       → python scripts/generate_schematic.py "研究フロー図" -o figures/research_flow.png
        ↓
Phase 3: peer-review スキルでEval
  - 採択例2本と比較してスコア算出（0〜100）
  - フィードバック（弱点リスト）を生成
        ↓
スコア < 85？
  YES → fix_plan.md に弱点を書く → Phase 2に戻る（Ralphループ）
  NO  → RALPH_STATUS: EXIT_SIGNAL: true
        ↓
Slack #auto-research-xxx に結果を配信
  - 完成ファイル（GitHub）のURL
  - スコア推移（ラウンド別）
  - 強み・改善点サマリ
```

---

## K-Dense コマンド早引き（実際のコマンド）

| タスク | コマンド |
|-------|---------|
| 学術論文検索 | `python research_lookup.py "topic keywords" -o sources/papers_YYYYMMDD_topic.md` |
| Webサーチ | `python scripts/parallel_web.py search "query" -o sources/search_YYYYMMDD_topic.md` |
| URL取得 | `python scripts/parallel_web.py extract "url" --objective "focus" -o sources/extract_YYYYMMDD_source.md` |
| 深掘りリサーチ | `python scripts/parallel_web.py research "query" --processor pro-fast -o sources/research_YYYYMMDD_topic.md` |
| 概念図生成 | `python scripts/generate_schematic.py "diagram description" -o figures/output.png` |

**重要**: 全サーチ結果は必ず `sources/` に保存する（`-o` フラグ必須）。

---

## Ralph ループ詳細

| 項目 | 値 |
|------|-----|
| 終了条件 | peer-review スコア ≥ 85/100 |
| 最大反復回数 | 5回（Circuit Breaker） |
| Circuit Breaker発動条件 | 同一エラー3回連続 or 5回反復で閾値未達 |
| Circuit Breaker時の動作 | Slack に「改善が止まりました。手動確認が必要です」を送信して停止 |
| 状態管理ファイル | `.ralph/fix_plan.md`（チェックボックス形式） |
| 進捗記録 | `.ralph/progress.txt`（各ラウンドのスコア推移） |

### fix_plan.md フォーマット

```markdown
# 研究計画書 改善タスク

## 現在のスコア: XX/100（目標: 85/100）

## Round N の弱点（peer-reviewフィードバック）
- [ ] 社会的背景が薄い → 罹患者数・社会コストを追加
- [ ] 先行研究との差分が不明確 → ギャップを1段落で明示
- [ ] 図の説明が不足 → キャプション追加

## 完了済み
- [x] Round 1: 研究目的の曖昧さを解消
- [x] Round 2: 新規性セクション強化
```

---

## 採択例の学習データ

| # | ソース | 分野 | 取得方法 | 保存先 |
|---|--------|------|---------|--------|
| 1 | 吉田 DC1 2011年（東大、面接免除採択） | 工学（てんかん×迷走神経刺激×機械学習） | Firecrawlスクレイプ済み | `data/jsps-examples/yoshida-dc1-2011.md` |
| 2 | 谷隅 DC1 2019年（同志社大） | 神経科学（ラット逆転学習×OFC-VS回路） | Firecrawlスクレイプ済み | `data/jsps-examples/tanisumi-dc1-2019.md` |

### 採択例から確認した実際の構造パターン

| 評価項目 | 配点 | 採択例の共通パターン（実データから確認） |
|---------|------|--------------------------------------|
| 社会的背景（冒頭） | 20点 | 「国内○万人罹患」など数値で開始。社会コストを明示。吉田例：「てんかんは100人に1人が罹患、国内100万人」 |
| ファネル構造 | 15点 | 社会課題→技術課題→本研究の貢献という段階的絞り込み |
| 新規性の明確さ | 20点 | 「〇〇は解明されていない」→「本研究では〜で解明する」の2段構造 |
| 研究方法の具体性 | 20点 | 年度別スケジュール・評価指標・使用装置が明記。谷隅例：OFC-VS回路の具体的な解剖学的記述あり |
| 図・概念図 | 10点 | 研究の全体像を示す図が1枚以上。吉田例：概念図あり |
| 期待成果・社会貢献 | 15点 | 研究完了後の波及効果が具体的（臨床応用、次の研究フェーズ等） |
| **合計** | **100点** | **85点以上 = 採択レベルと判定** |

---

## ファイル構成（リポジトリ）

```
naist-researcher/
├── SKILL.md                        ← Claude Code / Cursor が読むスキル定義（MUST）
├── CLAUDE.md                       ← プロジェクトルール（MUST）
├── README.md                       ← インストール手順・使い方（MUST）
├── .ralph/
│   ├── PROMPT.md                   ← Ralphが読む目標定義
│   └── fix_plan.md                 ← 反復タスクチェックリスト（自動更新）
├── data/
│   └── jsps-examples/
│       ├── yoshida-dc1-2011.md     ← 採択例1（Firecrawlでスクレイプ済み）
│       └── tanisumi-dc1-2019.md    ← 採択例2（Firecrawlでスクレイプ済み）
├── prompts/
│   ├── generate.md                 ← Phase 2: 初稿生成プロンプト（学振DC1特化）
│   ├── review.md                   ← Phase 3: peer-reviewプロンプト（JSPS評価基準）
│   └── slack-notify.md             ← 完成時Slack通知プロンプト
├── templates/
│   └── jsps-dc1-template.md        ← 学振DC1フォーマットテンプレート
└── writing_outputs/                ← K-Dense準拠: 生成物はここに蓄積
    └── <timestamp>_<theme>/
        ├── progress.md
        ├── sources/                ← 全サーチ結果（research_lookup.py, parallel_web.py出力）
        ├── drafts/                 ← v1_draft.md, v2_draft.md, ...
        ├── figures/                ← 概念図
        └── final/                  ← 最終稿
```

---

## SKILL.md の定義（Claude Code / Cursor 用）

```yaml
---
name: naist-researcher
version: 1.0.0
description: >
  学振DC1研究計画書を自動生成するスキル。研究テーマを入力するだけで、
  K-Dense scientific-writerを使った文献調査→初稿生成→peer-reviewループ→Slack配信まで全自動で実行する。
  Use when: 「学振を書きたい」「研究計画書を作りたい」「DC1の申請書」
  「終わるまでやれ」と言われた場合はRalphループを起動する。
keywords: [学振, DC1, DC2, 研究計画書, JSPS, grant, proposal, research]
auto_activate: true
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob]
---
```

---

## README.md の内容（配布用）

### セットアップ（初回のみ、5分）

```bash
# Step 1: naist-researcherをインストール
git clone https://https://github.com/Daisuke134/naist-researcher ~/.claude/skills/naist-researcher

# Step 2: K-Dense scientific-writerをインストール（依存）
git clone https://github.com/K-Dense-AI/claude-scientific-writer ~/.claude/skills/claude-scientific-writer

# Step 3: Python依存をインストール
pip install -r ~/.claude/skills/claude-scientific-writer/requirements.txt

# Step 4: APIキーを設定（~/.zshrc または ~/.env に追加）
export ANTHROPIC_API_KEY="sk-ant-..."     # 必須
export OPENROUTER_API_KEY="sk-or-..."     # Perplexity論文検索に必要
export PARALLEL_API_KEY="..."             # Webサーチに必要
```

### 使い方

#### Mode A: Cursor / Claude Code

```
1. Cursor または Claude Code を開く
2. 以下をコピペして送る：

「学振DC1の研究計画書を書きたい。
 テーマ：[ここに研究テーマを書く]
 ラボ：田中研 / ComBeNS
 締切：[月]末
 終わるまでやれ。」

3. 30分待つ。以上。
```

#### Mode B: Slack（インストール不要）

```
1. Slackで #auto-research-自分の名前 チャンネルを作る
   （例: #auto-research-narita）

2. 以下をコピペしてAniccaに送る：

「学振DC1の研究計画書を書きたい。
 テーマ：[ここに研究テーマを書く]
 ラボ：田中研 / ComBeNS
 締切：[月]末」

3. 30分待つ。以上。
```

---

## 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| 1 | research_lookup.py が動作し論文リストが返る | `python research_lookup.py "test" -o test.md` が成功する |
| 2 | parallel_web.py が動作しWebサーチ結果が返る | `python scripts/parallel_web.py search "test" -o test.md` が成功する |
| 3 | 研究テーマ入力後30分以内に初稿が生成される | 実際に実行してタイム計測 |
| 4 | 生成物が学振DC1フォーマット（5,000〜8,000字）に準拠している | 字数カウント + テンプレート差分チェック |
| 5 | peer-reviewスコアが算出される（0〜100点） | スコア数値が出力されることを確認 |
| 6 | スコア85未満の場合はRalphループが継続する | fix_plan.md のチェックボックス更新を確認 |
| 7 | スコア85以上でEXIT_SIGNALが出力される | `RALPH_STATUS: EXIT_SIGNAL: true` の出力を確認 |
| 8 | 完成時にSlackの #auto-research-xxx に通知が届く | 実際にSlackで受信確認 |
| 9 | 生成物に概念図が1枚以上含まれる | writing_outputs/figures/ に画像ファイルが存在することを確認 |
| 10 | Circuit Breakerが5回で発動し、Slackに報告される | 意図的に低スコア状態を維持して確認 |
| 11 | 採択例2本がdata/jsps-examples/に存在する | ファイル存在確認 |
| 12 | 全サーチ結果がsources/に保存される | sources/フォルダに各フェーズのファイルが存在することを確認 |

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|---------|--------|
| 1 | research_lookup.py でテーマ論文20本取得 | `test_research_lookup_returns_papers` | ✅ |
| 2 | parallel_web.py でWebサーチ実行 | `test_parallel_web_search_executes` | ✅ |
| 3 | 研究テーマ入力→初稿生成 | `test_generate_proposal_from_topic` | ✅ |
| 4 | peer-reviewスコア計算（0〜100） | `test_peer_review_scoring` | ✅ |
| 5 | スコア<85でRalphループ継続 | `test_ralph_loop_continues_below_threshold` | ✅ |
| 6 | スコア≥85でEXIT_SIGNAL出力 | `test_exit_signal_above_threshold` | ✅ |
| 7 | 5回上限でCircuit Breaker発動 | `test_circuit_breaker_max_iterations` | ✅ |
| 8 | Circuit Breaker時にSlack通知 | `test_circuit_breaker_slack_notification` | ✅ |
| 9 | 完成時にSlack配信 | `test_slack_delivery_on_completion` | ✅ |
| 10 | 採択例データの読み込み | `test_load_jsps_examples` | ✅ |
| 11 | 学振DC1フォーマット準拠チェック | `test_dc1_format_compliance` | ✅ |
| 12 | sources/フォルダに全サーチ結果が保存される | `test_sources_folder_populated` | ✅ |

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| Slack配信 | あり |
| 新規ユーザーフロー | あり（インストール→初回実行） |
| 結論 | Maestro不要。Slack受信確認 + 実際の初稿生成を手動E2Eとする |

---

## 境界（v1でやらないこと）

| 対象 | 理由 |
|------|------|
| 学振DC2・科研費・AMED等 | v1スコープ外 |
| 実験コード自動生成 | AI-Scientistスコープ、別スキル |
| フル論文執筆（Introduction〜Conclusion） | v2で対応 |
| 英語論文 | v1は日本語学振DC1のみ |
| 他ラボへの横展開 | v1はComBeNS専用。v2でオープン化 |
| 自動提出（JSPS e-Rad） | 人間が必ず最終確認してから提出する |
| LaTeX形式出力 | v1はMarkdown。v2でLaTeX対応 |

---

## Slack アナウンス文言（金曜日配布用）

```
【🎓 研究計画書、AIに書かせてみませんか？】

田中研 × ComBeNSラボ向けに
「学振DC1研究計画書 自動生成スキル」を作りました。

やることは1つだけ。
研究テーマをAniccaに送るだけ。

─────────────────────────
👇 こんな感じで送ってください

「学振DC1を書きたい。
 テーマ：EEGとMLを使った睡眠障害の早期検出。
 締切：5月末。」

→ 30分後に初稿が届きます。
─────────────────────────

裏でやってること：
① 関連論文20本以上を自動取得（Perplexity Sonar Pro）
② 採択例2本を参照してDC1フォーマットで初稿生成
③ 採択例と自動比較（0〜100点でスコア化）
④ 85点以上になるまで自動改善（最大5回）
⑤ Slackに完成版を配信

【使い方 2種類】

▶ Slack版（インストール不要・今すぐ使える）
　Slack で #auto-research-自分の名前 チャンネルを作る
　→ Anicca に話しかけるだけ

▶ Cursor / Claude Code版（自分のPCで動かす）
　README通りに5分でセットアップ：
　https://github.com/Daisuke134/naist-researcher

質問は @ダイス まで
```

---

## X（Twitter）アナウンス文言

```
NAISTの研究室で「学振DC1自動生成スキル」を作った。

研究テーマを送るだけで：
→ 論文調査（20本以上、Perplexity Sonar Pro）
→ DC1初稿生成（採択例フォーマット準拠）
→ 採択例と自動比較・スコア化
→ 85点超えるまで自動改善（最大5回）
→ Slackに届く

使ったもの（全部OSSのBestPractice）:
・K-Dense scientific-writer（8900 stars）
・Ralph autonomous loop（既存スキル）
・OpenClaw（Slack連携）

オリジナルはゼロ。全部繋いだだけ。

OSS: https://github.com/Daisuke134/naist-researcher
```

---

## 実装手順（この順番通りに実行する）

| # | 手順 | 担当 | コマンド/操作 | 完了条件 |
|---|------|------|-------------|---------|
| 1 | 採択例1をファイルに保存 | Claude | `firecrawl scrape URL > data/jsps-examples/yoshida-dc1-2011.md` | ファイルが存在する |
| 2 | 採択例2をファイルに保存 | Claude | `firecrawl scrape URL > data/jsps-examples/tanisumi-dc1-2019.md` | ファイルが存在する |
| 3 | GitHubリポジトリ作成 | Claude | `gh repo create cbns-naist/naist-researcher --public` | リポジトリが存在する |
| 4 | SKILL.md 作成 | Claude | 本仕様書の定義通りに書く | SKILL.md が存在する |
| 5 | CLAUDE.md 作成 | Claude | K-Dense CLAUDE.mdをベースにJSPS向けに調整 | CLAUDE.md が存在する |
| 6 | templates/jsps-dc1-template.md 作成 | Claude | 学振DC1の公式フォーマットに基づいて作成 | template が存在する |
| 7 | prompts/generate.md 作成 | Claude | 学振DC1特化の初稿生成プロンプトを書く | generate.md が存在する |
| 8 | prompts/review.md 作成 | Claude | JSPS評価基準に基づくpeer-reviewプロンプトを書く | review.md が存在する |
| 9 | .ralph/PROMPT.md 作成 | Claude | Ralphゴール定義を書く（スコア85以上が目標） | PROMPT.md が存在する |
| 10 | README.md 作成 | Claude | 本仕様書のREADMEセクションをコピー | README.md が存在する |
| 11 | K-Dense APIキーを確認 | ダイス | OPENROUTER_API_KEY、PARALLEL_API_KEY が手元にあるか確認 | キーが手元にある |
| 12 | ローカルでデモ実行 | ダイス | Claude Code で「学振DC1を書きたい。テーマ：XXX。終わるまでやれ。」 | 初稿が生成される |
| 13 | peer-reviewスコアが出ることを確認 | ダイス | 出力を確認 | 0〜100点のスコアが表示される |
| 14 | Mac Miniにデプロイ | Claude | `scp -r naist-researcher/ anicca@100.99.82.95:/home/anicca/skills/` | Mac Mini上にファイルが存在する |
| 15 | OpenClaw にスキル登録 | Claude | `ssh anicca@100.99.82.95 "openclaw skills install /home/anicca/skills/naist-researcher"` | openclaw skills list に表示される |
| 16 | Slack #auto-research-test でデモ実行 | ダイス+Claude | Slackで送信 | 30分以内に初稿が届く |
| 17 | ラボメンバーにSlackアナウンス | ダイス | 上記アナウンス文言をコピペ | 送信完了 |

---

## コスト管理

| 項目 | 上限 | 根拠 |
|------|------|------|
| 1回の計画書生成あたりのAPIコスト | $2.00 | YCハッカソン実績（6リポジトリ=$297）の1/50相当 |
| Ralphループ最大回数 | 5回 | Circuit Breaker設定 |
| 1日あたりの実行上限 | 10回 | OpenClaw Cap Gate設定 |

---

最終更新: 2026-02-21
ステータス: 実装手順 #1〜#10 完了。GitHub: https://github.com/Daisuke134/naist-researcher
次のアクション: 手順 #11（APIキー確認）→ #12（ローカルデモ実行）
ブロッカー: ダイスが OPENROUTER_API_KEY・PARALLEL_API_KEY を持っているか確認が必要（手順#11）
