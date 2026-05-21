# mobileapp-builder v2 — 改善 Spec（SDD方式）

**作成日:** 2026-02-24
**ステータス:** レビュー待ち
**スコープ:** GitHub `Daisuke134/mobileapp-builder` を OSS として誰でも使えるレベルに引き上げる

---

## 概要（What & Why）

### What

`npx skills add Daisuke134/mobileapp-builder -g -y` でインストールし、「アプリ作って」と言うだけで、
**トレンドリサーチ → SDD Spec → 実装 → TestFlight → App Store 提出**を全自動化するスキル。

エンドユーザーはコードも Xcode も ASC も知らなくてよい。
スキルが全ての重労働をやる。人間は **3回だけ承認** すれば App Store に並ぶ。

### Why

ソース: [Anthropic - Multi-agent best practices](https://www.anthropic.com/engineering/claude-code-best-practices)
引用: 「Autonomous agents work best when humans approve high-stakes decisions rather than every step」

iOSアプリを App Store に出せない最大の理由:
1. Xcode / ASC / RevenueCat の設定が複雑すぎる
2. リジェクト理由が分からない（PrivacyInfo、IAP、App Privacy 等）
3. スクリーンショット・メタデータのローカライズが面倒

このスキルはこれを全部やる。

---

## 受け入れ条件

| # | 条件 | 確認方法 |
|---|------|---------|
| AC1 | `npx skills add Daisuke134/mobileapp-builder -g -y` 1コマンドでインストール完了 | `npx skills list` に表示される |
| AC2 | SETUP.md の手順で prerequisites を自動チェック・案内 | `scripts/check-prerequisites.sh` |
| AC3 | STOP 1: spec.md を表示し、ユーザー承認待ちで停止する | Slack 承認または「OK」待機 |
| AC4 | STOP 2: TestFlight にプッシュ後、テスター招待してユーザー通知・停止する | Slack メッセージ + 待機 |
| AC5 | STOP 3: App Privacy 手動設定案内後、「完了」でそのまま submit する | ASC Web 手順案内 |
| AC6 | PHASE 8 STOP GATE: IAP が READY_TO_SUBMIT でなければ次に進まない | `asc validate subscriptions` |
| AC7 | 提出後 `asc review submissions-list` で state=WAITING_FOR_REVIEW | CLI |
| AC8 | Greenlight CRITICAL=0 確認 (PHASE 11) | `greenlight preflight <app_dir>` |

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **リポジトリ** | `github.com/Daisuke134/mobileapp-builder` |
| **ブランチ** | `main` |
| **作業状態** | Spec レビュー待ち（実装未着手） |

---

## As-Is / To-Be

### As-Is（現状の問題）

| 問題 | 影響 |
|------|------|
| 3つの STOP GATE が SKILL.md に埋もれている | ユーザーが「どこで止まるか」分からない |
| Prerequisites に install コマンドがない | 「asc コマンドが見つからない」で詰まる |
| サブスキルのインストール手順がない | `x-research` 等が入っていない状態で実行される |
| Pencil MCP・Maestro MCP の設定手順がない | PHASE 9 でブロックされる |
| `npx skills add` でインストールしても動かない | SETUP.md がない |
| README が開発者向けで、初心者向けでない | ターゲットユーザー（コードを知らない人）が使えない |

### To-Be（変更後）

| 変更箇所 | 内容 |
|---------|------|
| **新規: `SETUP.md`** | Prerequisites + install コマンド全記載。スキル最初に読む |
| **新規: `scripts/check-prerequisites.sh`** | 必要ツールの存在確認スクリプト。不足ツールを案内 |
| **SKILL.md 改修: STOP GATE 3箇所を明示** | STOP 1 / STOP 2 / STOP 3 を太字・フレームで目立たせる |
| **SKILL.md 改修: description 更新** | 3-stop UX を description に明記 |
| **README 改修: Prerequisites セクション** | 初心者が1から使えるセットアップ手順 |
| **SKILL.md 改修: サブスキル install コマンド** | PHASE 0 の冒頭に各スキル install 確認を追加 |

---

## STOP GATE 詳細設計（3箇所）

### STOP 1: Spec 承認（PHASE 0.5 完了後）

ユーザーへのメッセージ（テンプレート）:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 1 — Spec 承認
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

トレンドリサーチが完了しました。以下のアプリを作ります:

  アプリ名: {app_name}
  コンセプト: {concept}
  月額: ${price_monthly_usd} / 年額: ${price_annual_usd}
  ターゲット: {target_users}

Spec 全文: {spec_path}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
「OK」で実装開始 / 「変更: {内容}」で修正
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

実装: `slack-approval` スキル を読んで requestApproval() を実行
承認 → PHASE 1 へ / 拒否 or 変更指示 → PHASE 0.5 に戻る

### STOP 2: TestFlight 承認（PHASE 10 完了後）

ユーザーへのメッセージ（テンプレート）:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 2 — TestFlight テスト
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ビルドを TestFlight に配信しました。

  ビルド: {version} (#{build_number})
  テスターグループ: {group_name}
  招待済みメールアドレス: {tester_email}

TestFlight アプリでインストールして動作確認してください。

確認項目:
  □ アプリが起動する
  □ オンボーディングが最後まで進める
  □ Paywall が表示される
  □ 通知許可が出る
  □ 設定画面のリンクが開く

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
「OK」で App Store 提出へ / 「修正: {内容}」でコード修正
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

実装: `slack-approval` スキル を読んで requestApproval() を実行
承認 → PHASE 11 へ / 修正指示 → PHASE 3 に戻る（ralph-autonomous-dev で修正 → PHASE 10 再実行）

### STOP 3: App Privacy + 最終提出（PHASE 11.5 完了後）

ユーザーへのメッセージ（テンプレート）:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 3 — App Privacy 設定（手動 — 2分）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

App Privacy は ASC API で設定できません（404 が返ります）。
以下の手順で2分で完了します:

1. https://appstoreconnect.apple.com → My Apps → {app_name}
2. 左メニュー「App Privacy」→「データの使用方法を編集」
3. 収集するデータを選択:
   □ {data_category_1}（{purpose}）
   □ {data_category_2}（{purpose}）
   ※ ユーザーとデバイスへのリンク → 「いいえ」
4. 「完了」→「保存」

完了したら「完了」と送信してください。
エージェントが即座に App Store 提出します。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

実装: 「完了」受信 → PHASE 12 (`asc submit create --confirm`) 即実行
PHASE 12 完了後 → 「App Store に提出しました。審査中です。」と報告

---

## Prerequisites 定義（SETUP.md に記載する内容）

### ユーザーが持っていれば OK なもの（スキルが確認・案内する）

| # | 必須 | 確認方法 | 案内 |
|---|------|---------|------|
| 1 | Apple Developer アカウント（有料） | `asc apps list` が動くか | https://developer.apple.com/enroll/ |
| 2 | ASC API Key（p8ファイル + Key ID + Issuer ID） | `~/.asc/private_keys/AuthKey_*.p8` の存在 | ASC → Users and Access → Keys |
| 3 | RevenueCat アカウント | `REVENUECAT_API_KEY` 環境変数 | https://app.revenuecat.com/ |
| 4 | OpenAI API Key（アイコン生成用） | `npx snapai config --show` | https://platform.openai.com/api-keys |
| 5 | Mixpanel プロジェクト | `MIXPANEL_TOKEN` 環境変数 | https://mixpanel.com/register |

### スキルが自動インストール・確認するツール

| # | ツール | インストールコマンド | 確認コマンド |
|---|--------|-------------------|------------|
| 1 | `asc` CLI | `brew install nickvdyck/tap/asc` | `asc --version` |
| 2 | `fastlane` | `brew install fastlane` | `fastlane --version` |
| 3 | `greenlight` | `cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build && sudo cp build/greenlight /usr/local/bin/` | `greenlight --version` |
| 4 | `npx snapai` | `npm install -g snapai` | `npx snapai --version` |
| 5 | `imagemagick` | `brew install imagemagick` | `convert --version` |
| 6 | `ios-deploy` | `brew install ios-deploy` | `ios-deploy --version` |
| 7 | Python `PIL` | `pip3 install Pillow requests PyJWT` | `python3 -c "import PIL"` |

### スキルが確認する Claude Code MCP（自動インストール不可 — 手順案内）

| # | MCP | 設定手順 |
|---|-----|---------|
| 1 | **Pencil MCP** | [pencil.com/mcp](https://pencil.com/mcp) のインストール手順に従う |
| 2 | **Maestro MCP** | `npx @maestro-org/mcp-server@latest` を MCP settings に追加 |

### スキルが自動インストールする Claude Code サブスキル

| # | スキル | インストールコマンド |
|---|--------|-------------------|
| 1 | `x-research` | `npx skills add Daisuke134/anicca-products@x-research -g -y` |
| 2 | `tiktok-research` | `npx skills add Daisuke134/anicca-products@tiktok-research -g -y` |
| 3 | `apify-trend-analysis` | `npx skills add Daisuke134/anicca-products@apify-trend-analysis -g -y` |
| 4 | `ralph-autonomous-dev` | `npx skills add Daisuke134/anicca-products@ralph-autonomous-dev -g -y` |
| 5 | `screenshot-creator` | `npx skills add Daisuke134/anicca-products@screenshot-creator -g -y` |
| 6 | `slack-approval` | `npx skills add Daisuke134/anicca-products@slack-approval -g -y` |
| 7 | `app-icon` | `npx skills add code-with-beto/skills@app-icon -g -y` |

---

## テストマトリックス

| # | テスト対象 | テスト名 | カバー |
|---|-----------|---------|--------|
| 1 | check-prerequisites.sh: 全ツール存在時 | `test_all_prerequisites_pass` | AC2 |
| 2 | check-prerequisites.sh: asc未インストール時 | `test_missing_asc_shows_install_command` | AC2 |
| 3 | check-prerequisites.sh: p8ファイル未存在時 | `test_missing_p8_shows_setup_guide` | AC2 |
| 4 | STOP 1: spec.md 生成後に停止する | `test_stop1_waits_for_approval` | AC3 |
| 5 | STOP 2: TestFlight プッシュ後に停止する | `test_stop2_waits_for_approval` | AC4 |
| 6 | STOP 3: App Privacy 案内後に停止する | `test_stop3_shows_instructions` | AC5 |

---

## 境界（Boundaries）

### 変更するファイル（mobileapp-builder リポジトリ内）

| ファイル | 変更内容 |
|---------|---------|
| `SKILL.md` | description 更新、STOP 1/2/3 明示、サブスキル install 確認追加 |
| `README.md` | Prerequisites セクション全面改訂 |
| `SETUP.md`（新規） | 初心者向け完全セットアップガイド |
| `scripts/check-prerequisites.sh`（新規） | 必要ツール自動確認スクリプト |

### 変更しないファイル

| ファイル | 理由 |
|---------|------|
| `references/iap-bible.md` | 現状のまま動作中 |
| `references/spec-template.md` | 現状のまま動作中 |
| `references/submission-checklist.md` | 現状のまま動作中 |
| `scripts/add_prices.py` | 現状のまま動作中 |
| 14 PHASE の中身 | 実証済み・変更禁止。STOP 追加のみ |

### やらないこと

| 禁止 | 理由 |
|------|------|
| 14 PHASE のロジックを書き直す | 実証済みロジック。触れたら壊れる |
| 新しい PHASE を追加する | スコープ外 |
| App Privacy を自動化する | ASC API が 404 を返す（確認済み） |
| Android / Expo / RN 対応 | スコープ外（Swift/SwiftUI のみ） |
| Superwall 追加 | RevenueCat のみポリシー |

---

## 実行手順（実装後の確認コマンド）

```bash
# 1. スキルインストール確認
npx skills add Daisuke134/mobileapp-builder -g -y
npx skills list | grep mobileapp-builder

# 2. Prerequisites チェック
bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh

# 3. テスト実行（STOP GATE の動作確認）
# → Claude Code で「mobileapp-builderでアプリを作って」と言って STOP 1 が出るか確認
```

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（Claude Code スキル。UI は Claude の出力のみ） |
| 新画面 | なし |
| 結論 | Maestro E2E 不要（スキルはメッセージ出力のみ。実機テストは STOP 2 でユーザーが行う） |

---

## ソース（全判断の引用元）

| 判断 | ソース | 引用 |
|------|--------|------|
| 3-stop UX | [Anthropic - Multi-agent best practices](https://www.anthropic.com/engineering/claude-code-best-practices) | 「Humans approve high-stakes decisions rather than every step」 |
| Skills の description 形式 | [Anthropic - Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | 「The description is critical for skill selection」 |
| SKILL.md <500行制約 | [Anthropic - Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | 「Body content: your implementation instructions (<500 lines)」 |
| Prerequisites in SKILL.md | [Anthropic - Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | 「Start by reading the contents of bundled files... paying attention to dependencies」 |
| App Privacy は API 不可 | 実機検証 2026-02-24 | `/v1/apps/{id}/appDataUsages` は 404 を返す（実証済み） |
| `asc submit create --confirm` | 実機検証 2026-02-24 | PATCH reviewSubmissions.state は 409 を返す（実証済み） |
| IAP screenshot はネイティブ解像度 | 実機検証 2026-02-24 | リサイズは Apple「寸法が正しくありません」で拒否（実証済み） |
| `npx skills add` の書式 | [Vercel - Skills Tool](https://github.com/vercel-labs/skills) | 「GitHub shorthand: owner/repo」 |
