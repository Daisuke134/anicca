# factory-restructure — フォルダ分離 + 2層構造統一 + リネーム

**Date**: 2026-03-01
**Status**: ⬜ 未実行

---

## 0. As-Is → To-Be

### As-Is

```
daily-apps/                          ← iOS と Web が混在
├── 20260301-webapp/                 ← Web
├── breath-calm/                     ← iOS
├── calmcortisol/                    ← iOS
├── ...

~/.openclaw/skills/
├── webapp-factory-orchestrator/     ← 1層構造（管理+ビルド混在）
├── mobileapp-factory/               ← 管理のみ（正しい）

~/.claude/skills/
├── mobileapp-builder/               ← 古い版（daily-apps 参照11箇所）

.claude/skills/
├── mobileapp-builder/               ← 新しい版（daily-apps 参照なし）
```

### To-Be

```
web-apps/                            ← Web アプリ専用
├── .env                             ← 共通キー（VERCEL_TOKEN等）
├── 20260301-deepwork/
│   └── .env.local                   ← アプリ固有（STRIPE_PRICE_ID等）
├── 20260302-focustimer/
└── ...

mobile-apps/                         ← iOS アプリ専用
├── breath-calm/
├── calmcortisol/
└── ...

~/.openclaw/skills/
├── web-app-factory-manager/         ← Anicca: cron→管理→監視
├── mobileapp-factory/               ← Anicca: cron→管理→監視（パス修正のみ）

.claude/skills/
├── web-app-factory/                 ← CC: Web アプリビルド指示
│   ├── SKILL.md                     ← 今の prompt.md を移動
│   ├── CLAUDE.md.template
│   ├── prd.json.template
│   └── ralph.sh
├── mobileapp-builder/               ← CC: iOS アプリビルド指示（変更なし）
```

ソース: [Turborepo](https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository) / 引用: 「Split packages into apps/ for applications and services and packages/ for everything else」
ソース: [12-Factor App](https://12factor.net/config) / 引用: 「env vars are granular controls, each fully orthogonal to other env vars... independently managed for each deploy」

---

## 1. 命名規則

| レイヤー | Mobile | Web | 役割 |
|---------|--------|-----|------|
| **Anicca スキル（管理）** | mobileapp-factory | web-app-factory-manager | cron → フォルダ作成 → テンプレコピー → ralph.sh 起動 → 監視 |
| **CC スキル（ビルド）** | mobileapp-builder | web-app-factory | CC への全ビルド指示。ralph.sh がこれを読む |
| **OSS 名** | mobile-app-factory | web-app-factory | skill.sh / ClawHub で公開する名前 |

---

## 2. web-app-factory（CC スキル）の中身

| ファイル | 内容 | 元ファイル |
|---------|------|-----------|
| `SKILL.md` | CC への全ビルド指示（US-001〜007） | `~/.openclaw/skills/webapp-factory-orchestrator/prompt.md` を移動 |
| `CLAUDE.md.template` | `Read .claude/skills/web-app-factory/SKILL.md and follow it exactly.` | 新規作成 |
| `prd.json.template` | タスクテンプレート（US-001〜007 の雛形） | 新規作成 |
| `ralph.sh` | ループスクリプト。`web-apps/.env` を source。`--mcp-config` 付き | 移動 + 修正 |

---

## 3. web-app-factory-manager（Anicca スキル）の中身

Mobile の mobileapp-factory と同じ構造:

```
STEP 1: web-apps/YYYYMMDD-HHMMSS-app/ を作成
STEP 2: テンプレートをコピー
  cp .claude/skills/web-app-factory/prd.json.template → prd.json
  cp .claude/skills/web-app-factory/CLAUDE.md.template → CLAUDE.md
  cp .claude/skills/web-app-factory/ralph.sh → ralph.sh
  touch progress.txt
STEP 3: Slack #metrics に起動報告
STEP 4: ralph.sh を起動（tmux or exec background）
STEP 5: 監視（system event → Slack 転送）
STEP 6: 完了後 → Slack 報告 + Webhook 登録依頼
```

---

## 4. ralph.sh の --mcp-config 修正

**`claude --print` でも `--mcp-config` で MCP サーバーを使える。**

```
claude --help より:
  --mcp-config <configs...>  Load MCP servers from JSON files or strings
```

| 変更対象 | 変更内容 |
|---------|---------|
| web-app-factory の ralph.sh | `claude --dangerously-skip-permissions --print --mcp-config ~/.claude/mcp.json < CLAUDE.md` |
| mobileapp-builder の ralph.sh | 同上（Pencil MCP が使えるようになる） |

---

## 5. .env 配置

### 共通キー: `web-apps/.env`

```bash
VERCEL_TOKEN=（ダイスが作成済み — web-apps/.env に設定する）
STRIPE_SECRET_KEY=（~/.openclaw/.env から移動）
POSTIZ_API_KEY=（~/.openclaw/.env から移動）
POSTIZ_X_INTEGRATION_ID=（~/.openclaw/.env から移動）
```

### アプリ固有キー: `web-apps/YYYYMMDD-xxx/.env.local`（CC が自動生成）

```bash
STRIPE_PRICE_ID=price_xxx        # CC が US-002 で生成
NEXT_PUBLIC_URL=https://xxx      # CC が US-006 で生成
STRIPE_WEBHOOK_SECRET=whsec_xxx  # ダイスがデプロイ後に追加
```

ソース: [12-Factor App](https://12factor.net/config) / 引用: 「The twelve-factor app stores config in environment variables」

---

## 6. ゴミ削除

| # | ファイル | 内容 | アクション |
|---|---------|------|-----------|
| 1 | `~/.openclaw/.env` L226 | `# VERCEL_TOKEN=  # TODO:...` | 行削除 |
| 2 | `~/.config/mobileapp-builder/.env` | `# VERCEL_TOKEN=  # TODO:...` | 行削除 |
| 3 | `~/.openclaw/skills/webapp-factory-orchestrator/` | 旧スキル全体 | ディレクトリ削除 |
| 4 | `~/.claude/skills/mobileapp-builder/` | 古い版（daily-apps 参照11箇所） | ディレクトリ削除（プロジェクト内の新版が正） |

---

## 7. mobileapp-factory パス修正

| ファイル | 箇所 | 変更 |
|---------|------|------|
| `~/.openclaw/skills/mobileapp-factory/SKILL.md` L17 | `daily-apps/<name>/` | `mobile-apps/<name>/` |
| `~/.openclaw/skills/mobileapp-factory/SKILL.md` L20 | `daily-apps/$(date)` | `mobile-apps/$(date)` |
| `~/.openclaw/skills/mobileapp-factory/SKILL.md` L90 | `daily-apps/<date>-app` | `mobile-apps/<date>-app` |

---

## 8. cron 設定

| cron | スケジュール | スキル | 状態 |
|------|-------------|--------|------|
| mobileapp-factory-morning | 毎日 07:00 JST | mobileapp-factory | ✅ 既存 |
| **web-app-factory-daily** | **毎日 15:00 JST** | **web-app-factory-manager** | ⬜ 新規作成 |

---

## 9. TODO（実行順序）

| # | タスク | 依存 |
|---|--------|------|
| 1 | `web-apps/` `mobile-apps/` フォルダ作成 + 既存アプリ移動 | なし |
| 2 | `web-apps/.env` 作成（VERCEL_TOKEN + 共通キー） | 1 |
| 3 | CC スキル `.claude/skills/web-app-factory/` 作成（SKILL.md, CLAUDE.md.template, prd.json.template, ralph.sh） | 1 |
| 4 | Anicca スキル `~/.openclaw/skills/web-app-factory-manager/` 作成（SKILL.md） | 3 |
| 5 | 旧 `~/.openclaw/skills/webapp-factory-orchestrator/` 削除 | 4 |
| 6 | `~/.openclaw/skills/mobileapp-factory/SKILL.md` パス修正（3箇所） | 1 |
| 7 | `~/.claude/skills/mobileapp-builder/` 削除（古い版） | なし |
| 8 | `~/.openclaw/.env` VERCEL_TOKEN コメント行削除 | なし |
| 9 | `~/.config/mobileapp-builder/.env` VERCEL_TOKEN コメント行削除 | なし |
| 10 | ralph.sh に `--mcp-config ~/.claude/mcp.json` 追加（web + mobile 両方） | 3 |
| 11 | git push | 1-10 |
| 12 | web-app-factory-daily cron 作成（毎日 15:00 JST） | 4 |
| 13 | テスト cron で E2E 確認（後でタイミング決定） | 12 |
| 14 | デプロイ後 STRIPE_WEBHOOK_SECRET 登録 | 13 |

---

## 10. 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC1 | `web-apps/` フォルダが存在し Web アプリが入っている | `ls web-apps/` |
| AC2 | `mobile-apps/` フォルダが存在し iOS アプリが入っている | `ls mobile-apps/` |
| AC3 | `daily-apps/` が空 or 削除済み | `ls daily-apps/` |
| AC4 | `web-apps/.env` に VERCEL_TOKEN がある | `grep VERCEL_TOKEN web-apps/.env` |
| AC5 | `.claude/skills/web-app-factory/SKILL.md` が存在 | `ls .claude/skills/web-app-factory/` |
| AC6 | `~/.openclaw/skills/web-app-factory-manager/SKILL.md` が存在 | `ls` |
| AC7 | 旧 `webapp-factory-orchestrator/` が削除済み | `ls` で存在しない |
| AC8 | mobileapp-factory SKILL.md に `daily-apps` 参照がない | `grep daily-apps` |
| AC9 | ralph.sh に `--mcp-config` がある | `grep mcp-config ralph.sh` |
| AC10 | cron `web-app-factory-daily` が 15:00 JST で設定済み | cron jobs 確認 |

---

## 11. 境界（やらないこと）

| やらないこと | 理由 |
|------------|------|
| スキルのリネーム（mobileapp-factory → mobile-app-factory-manager 等） | Web 側を先に動かす。Mobile のリネームは別タスク |
| OSS 切り出し | E2E テスト完了後 |
| Turborepo / Nx 導入 | 今は不要。フォルダ分離だけで十分 |





  完全な調査結果

  Cookie分析（実証済み）

  ┌────────────────┬───────────────────────────┬──────────────────────┬────────────────────────────────────────────────────┐
  │     Cookie     │         ドメイン          │         寿命         │                      保存場所                      │
  ├────────────────┼───────────────────────────┼──────────────────────┼────────────────────────────────────────────────────┤
  │ DES (trust     │ idmsa.apple.com           │ 30日 (2592000秒)     │ ~/.fastlane/spaceship/keiodaisuke@gmail.com/cookie │
  │ token)         │                           │                      │                                                    │
  ├────────────────┼───────────────────────────┼──────────────────────┼────────────────────────────────────────────────────┤
  │ myacinfo       │ apple.com                 │ セッション（数時間） │ 同上                                               │
  │ (セッション)   │                           │                      │                                                    │
  ├────────────────┼───────────────────────────┼──────────────────────┼────────────────────────────────────────────────────┤
  │ dqsid (ASC)    │ appstoreconnect.apple.com │ 30分 (1800秒)        │ 同上                                               │
  └────────────────┴───────────────────────────┴──────────────────────┴────────────────────────────────────────────────────┘

  DES cookie作成日: 2026-03-08 17:39 → 有効期限: 2026-04-07

  ツール比較（全て実証済み）

  ┌────────────────┬──────────────────────────────────────────┬─────────────────────────────────┐
  │                │                 fastlane                 │             asc web             │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ アプリ作成     │ ✅ produce（2FA不要）                    │ ✅ apps create（2FA必要）       │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ App Privacy    │ ✅ upload_app_privacy_details（2FA不要） │ ✅ web privacy apply（2FA必要） │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ セッション寿命 │ 30日（DES cookie）                       │ 20分以下                        │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ 2FA頻度        │ 月1回（spaceauth実行時のみ）             │ 毎回                            │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ パスワード     │ env varで自動                            │ env varで自動                   │
  ├────────────────┼──────────────────────────────────────────┼─────────────────────────────────┤
  │ Cookie保存     │ ~/.fastlane/spaceship/                   │ ~/.asc/iris/（壊れてる）        │
  └────────────────┴──────────────────────────────────────────┴─────────────────────────────────┘

  結論: fastlane一択。asc webはセッションが20分で切れるからゴミ。

  FrostBit App Privacy — 完了済み

  fastlane upload_app_privacy_details_to_app_store
  → Login successful（2FA不要）
  → Setting DATA_NOT_COLLECTED
  → App data usage is already published
  → Result: true

  3つの手動ステップの最終結論

  ┌─────┬─────────────────┬─────────────────────────────────────┬──────────┬───────────────────────────────────────┐
  │  #  │      操作       │               ツール                │ 2FA頻度  │               自動化度                │
  ├─────┼─────────────────┼─────────────────────────────────────┼──────────┼───────────────────────────────────────┤
  │ 1   │ アプリ作成      │ fastlane produce                    │ 月1回    │ パスワードのみで完全自動（DES有効時） │
  ├─────┼─────────────────┼─────────────────────────────────────┼──────────┼───────────────────────────────────────┤
  │ 2   │ App Privacy     │ fastlane upload_app_privacy_details │ 月1回    │ パスワードのみで完全自動（DES有効時） │
  ├─────┼─────────────────┼─────────────────────────────────────┼──────────┼───────────────────────────────────────┤
  │ 3   │ RevenueCat SK鍵 │ 手動                                │ 毎アプリ │ 自動化不可（Web UIのみ）              │
  └─────┴─────────────────┴─────────────────────────────────────┴──────────┴───────────────────────────────────────┘

  ダイスの手動作業スケジュールSo which means that if we just follow this for the fast lane, we can actually create a new app. And we actually can create a new app privacy too. 

  ┌──────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │   頻度   │                                             やること                                             │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 月1回    │ Mac Miniで FASTLANE_PASSWORD=... fastlane spaceauth → 2FAコード入力 → DES cookie更新（30日有効） │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 毎アプリ │ RC DashboardからSK鍵をコピー → Slackでralph.shに渡す                                             │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ それ以外 │ 何もしなくていい                                                                                 │
  └──────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘

  WAITING_FOR_HUMAN のトークン浪費修正

  今のフローの問題: CC内でSK鍵が必要 → CC終了 → 新CC起動（1M+ tokens消費） → SK鍵読む

  修正: ralph.shのPREFLIGHTで全ての人間入力を事前収集:

  ralph.sh PREFLIGHT:
    [1] fastlane auth check → DES有効？ → Yes → OK / No → spaceauth実行
    [2] RC SK鍵 → .envに既にある？ → Yes → OK / No → Slack通知 → 待機
    [3] 全入力揃った → CC iteration開始

  CCは人間に何も聞かない。全てralph.shが事前に準備する。

  ---
  レシピ（Spec）に書き出すか？パッチ対象は:

  ┌─────────────────────────┬─────────────────────────────────────────────────────────────────┐
  │        ファイル         │                              変更                               │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ ralph.sh (テンプレート) │ PREFLIGHT: fastlane auth + RC SK鍵チェック追加                  │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ us-005a (テンプレート)  │ asc apps create → fastlane produce + upload_app_privacy_details │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ us-005b (テンプレート)  │ RC SK鍵をPREFLIGHTから受け取るフロー                            │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ us-009 (テンプレート)   │ App Privacy削除（US-005aに移動済み）                            │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ .env (テンプレート)     │ FASTLANE_PASSWORD 追加                                          │
  └─────────────────────────┴─────────────────────────────────────────────────────────────────┘

⏺ Ran 1 stop hook (ctrl+o to expand)
  ⎿  Stop hook error: Failed with non-blocking status code: /bin/sh: .claude/hooks/scripts/stop-continue.sh: No such
  file or directory

✻ Churned for 3m 50s

⏺ Background command "Find DES cookie storage location" completed (exit code 0)
  ⎿  UserPromptSubmit hook error

⏺ バックグラウンドタスク完了。既にcookie分析は終わってるので追加情報なし。

  ダイスの返答待ち — Spec書き出すか？


3. 全ログ深掘り — 問題と改善チェックリスト

  3.1 トークン浪費の根本原因テーブル

  #: W1
  問題: スクショ3回やり直し
  発生場所: US-008a (iter 18-21)
  トークン浪費: ~25M余分
  根本原因: 1回目: スクショセットに既存画像残存。2回目: asc screenshots uploadがToo many screenshotsエラー。3回目: REST
    APIで既存削除→再アップ
  改善策: 初回に既存スクショをREST APIで全削除してから始めるパターンをCLAUDE.mdに追加
  ────────────────────────────────────────
  #: W2
  問題: トレンドリサーチが重すぎ
  発生場所: US-001 (iter 1)
  トークン浪費: 29.4M
  根本原因: 25+アイデア生成、各アイデアに対してiTunes検索+Web検索。Firecrawl CAPTCHA → DuckDuckGo fallback
  改善策: アイデアを10個に制限。トップ3だけ深掘り。他はスコアのみ
  ────────────────────────────────────────
  #: W3
  問題: 市場調査が重すぎ
  発生場所: US-003 (iter 3)
  トークン浪費: 11.2M
  根本原因: 8競合全てをプロファイル。TAM/SAM/SOMの3層分析
  改善策: 競合は上位5社のみ。TAMは1手法（bottom-up）のみ
  ────────────────────────────────────────
  #: W4
  問題: Spec 7ドキュメント生成
  発生場所: US-004a+b (iter 4-5)
  トークン浪費: 13M
  根本原因: 2,756行のSpec。過剰品質
  改善策: テンプレートSpecを用意。各アプリ固有部分だけ埋める
  ────────────────────────────────────────
  #: W5
  問題: validate.shによるpasses リセット
  発生場所: US-008e (retests)
  トークン浪費: ~5M余分
  根本原因: Gate 2がfalse positive(1320x2868)。passes:trueをfalseにリセット→再検証ループ
  改善策: Gate 2のfalse positiveフィルターは修正済み。validate.shのfalse positive検知を事前テスト
  ────────────────────────────────────────
  #: W6
  問題: 2FA待ちでのiteration浪費
  発生場所: US-005a, US-009
  トークン浪費: ~3M
  根本原因: セッション切れ→WAITING_FOR_HUMAN→新iteration起動→コード期限切れ→また待ち
  改善策: 上記セクション2の対策A+B
  ────────────────────────────────────────
  #: W7
  問題: CC起動時のコンテキスト読み込み
  発生場所: 全iteration
  トークン浪費: 各iter ~1M
  根本原因: 毎回CLAUDE.md(11KB) + prd.json(18KB) + progress.txt(49KB) を全部読む
  改善策: progress.txtの肥大化を防ぐ。完了したUSの詳細はアーカイブに移動

  3.2 アーキテクチャ改善チェックリスト

  ┌─────┬────────────────────────┬───────────────────────────────┬──────────────────────────────┬──────────────────┬──────┐
  │  #  │          改善          │             現状              │          あるべき姿          │       効果       │ 優先 │
  │     │                        │                               │                              │                  │  度  │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │     │                        │                               │ Codebase Patterns(上位)のみ  │ 毎iterationで-40 │      │
  │ F1  │ progress.txt肥大化防止 │ 49KB（557行）を毎iteration全  │ 保持。完了USの詳細は         │ KB入力 = -10M    │ 🔴   │
  │     │                        │ 読み                          │ logs/us-xxx-summary.md       │ tokens/build     │ HIGH │
  │     │                        │                               │ に分離                       │                  │      │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F2  │ Specテンプレート化     │ 7ドキュメント×300行を毎回ゼロ │ テンプレートのブランクを埋め │ -10M             │ 🔴   │
  │     │                        │ から生成                      │ るだけ                       │ tokens/build     │ HIGH │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F3  │ スクショ前に既存データ │ 既存スクショが残っていてエラ  │ iter開始時にREST             │ -25M             │ 🔴   │
  │     │ クリーン               │ ー→やり直し                   │ APIで既存スクショ全削除      │ tokens/build     │ HIGH │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F4  │ ASC                    │ セッション切れで2FA必要→itera │ PREFLIGHTで asc web login    │ 2FA問題解消      │ 🔴   │
  │     │ webセッション事前warm  │ tion浪費                      │ 実行                         │                  │ HIGH │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F5  │ REST APIでApp Privacy  │ asc web (web                  │ /v1/appPrivacyDeclarations   │ 2FA完全不要      │ 🟡   │
  │     │                        │ scraping、2FA必要)            │ REST API (JWT、2FA不要)      │                  │ MED  │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F6  │ トレンドリサーチ効率化 │ 25+アイデア全部深掘り         │ 10アイデア生成→トップ3だけ深 │ -15M             │ 🟡   │
  │     │                        │                               │ 掘り                         │ tokens/build     │ MED  │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F7  │ 1-iteration上限トーク  │ 制限なし（iter-1は29.4M使用） │ 15M/iteration上限。超えたらH │ 暴走防止         │ 🟡   │
  │     │ ン数                   │                               │ ARD STOP                     │                  │ MED  │
  ├─────┼────────────────────────┼───────────────────────────────┼──────────────────────────────┼──────────────────┼──────┤
  │ F8  │ validate.sh事前テスト  │ 本番でfalse                   │ 新Gate追加時にdry-runテスト  │ リセットループ防 │ 🟢   │
  │     │                        │ positive→リセットループ       │ 必須                         │ 止               │ LOW  │
  └─────┴────────────────────────┴───────────────────────────────┴──────────────────────────────┴──────────────────┴──────┘
