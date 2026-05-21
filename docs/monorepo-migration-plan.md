# Monorepo Migration Plan

最終更新: 2025-08-29

## ゴール
- Push 先を `Daisuke134/anicca.ai` に統一し、Desktop / Web / API / LP を一つのモノレポで管理。
- デプロイは各プラットフォーム（GitHub Releases / Vercel / Railway / Netlify）を継続利用し、サブディレクトリ配備に切替。

## 現在の状態
- 作業ブランチ:
  - `chore/monorepo-migration-safe` をリモートに作成・プッシュ済み（復帰用／安全な履歴）。
- 反映内容（移動と最小設定のみ、コード変更なし／復帰用ブランチ内）:
  - Desktop → `apps/desktop/`
  - Web（旧 `anicca-web`）→ `apps/web/`
  - API（旧 `anicca-proxy-slack`）→ `apps/api/`
  - LP → `apps/landing/`
  - Docs → `docs/`
  - `.gitignore` の調整（web/api を管理対象へ）
  - `netlify.toml` の base を `apps/landing` に変更
  - Desktop リリース用 Actions の作業ディレクトリを `apps/desktop` に固定
- 秘密情報の扱い:
  - 過去ローカル作業で `apps/api/.npmrc` にトークンが混入したが、リモートには push していない。
  - 安全ブランチ（`chore/monorepo-migration-safe`）には当該ファイル・履歴を含めていない（安全）。
  - 念のため、該当トークンが有効なら無効化/ローテーションを推奨。

## 当面の運用（いったん従来どおり）
- 通常開発は `main`（または既存ブランチ）で継続。
- Vercel（Web）と Railway（API）は従来リポジトリのまま運用維持。
- モノレポ移行作業に戻りたくなったら、この計画に沿って `chore/monorepo-migration-safe` から再開。

## 再開時の流れ（推奨プロセス）
1) ブランチ準備
- `git fetch` → `git switch chore/monorepo-migration-safe`（復帰用ブランチ）
- 必要なら最新 `main` を取り込み（`git merge origin/main`）し、差分がなければそのままPRへ。

2) PR 作成（まずは検証のため beta 宛て）
- 宛先ブランチ: `beta`（Staging 確認を優先）
- 目的: サブディレクトリ配備で Web/API/LP を検証、Desktop Actions の動作確認

3) ホスティング設定を「モノレポ参照」に変更（検証フェーズ）
- Vercel（Web）
  - Repository: `Daisuke134/anicca.ai`
  - Root Directory: `apps/web`
  - Prioritize Production Builds: Enabled（本番ビルド優先）
  - Include files outside root: OFF（現状は不要）
  - Build: Framework Preset=Next.js（自動で `next build`）
- Railway（API）
  - Repository: `Daisuke134/anicca.ai`
  - Directory（Monorepo Path）: `apps/api`
  - Branch: Staging=`beta`、Production=`main`
  - Wait for CI: OFF（現状）※厳格にする場合は将来 ON に
  - Watch Paths: `apps/api/**`（不要デプロイ抑止のため推奨）
  - Builder: Nixpacks（自動）、Start: `npm start`（apps/api/railway.toml に記載あり）
- Netlify（LP）
  - BaseDir: `apps/landing`（`netlify.toml` と一致）

4) 検証チェック
- Desktop（ローカル）: `cd apps/desktop && npm ci && npm run voice:simple`
- Web（Vercel Preview）: ビルド成功と表示確認、ENV の有無
- API（Railway Staging）: 起動/ヘルスチェック/主要エンドポイント
- Desktop ↔ API 疎通: 既定URL/ENV解決のログ確認（起動時＋4時間ごとのアップデートチェックに影響ないこと）

5) 本番切替
- beta で問題なし → `main` にもマージ
- Vercel/ Railway の Production が `main` を追従して自動更新
- Desktop の GitHub Releases（Beta/Stable）は既存運用を継続（リリーストリガーはそのまま）

## フォルダ構成（完成像）
```
apps/
  desktop/           # Electron デスクトップアプリ（既存ルートを移設）
    src/
    assets/
    build/
    scripts/
    dist/            # ビルド生成物（git 無視）
    electron-builder-voice.yml
    package.json
    tsconfig.json
    tsconfig.voice.json
    vitest.config.ts
    notarize.js
  web/               # Next.js（旧 anicca-web）
    app/, components/, lib/, public/, supabase/ ...
    package.json, tsconfig.json, next.config.ts, 他
  api/               # Node/Express（旧 anicca-proxy-slack を改名）
    src/server.js, src/api/**, src/services/** ...
    package.json, tsconfig.json, railway.toml
  landing/           # Netlify 静的サイト（旧 landing/）
docs/                # 運用/配布/移行ドキュメント（AGENTS.md/CLAUDE.md 等）
.github/workflows/   # Desktop リリース（working-directory=apps/desktop）
netlify.toml         # BaseDir=apps/landing
README.md            # ルート総合入口（導線のみ、詳細は docs/）
```

## ローカル開発クイックリファレンス
- Desktop: `cd apps/desktop && npm ci && npm run voice:simple`
- Web: `cd apps/web && npm i && npm run dev`
- API: `cd apps/api && npm i && npm start`

## 今後の拡張（任意）
- ワークスペース導入（pnpm）と `packages/shared` で型/SDK 共有
- GitHub Environments（staging/production）＋ CODEOWNERS で本番承認フロー強化
- Actions の `paths:` フィルタで差分ビルド

## リスクとロールバック
- サブディレクトリ配備の誤設定によるビルド失敗
  - 対処: Vercel/Railway の参照を一時的に従来リポへ戻す
- Desktop リリースへの影響
  - 本計画は Desktop の配布運用を変更しない（working-directory のみ調整）
- 秘密情報
  - 現時点でリモートに秘密は含めていないが、過去に見えたトークンが実在/有効なら速やかに無効化/再発行

