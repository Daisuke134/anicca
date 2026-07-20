---
paths: ["aniccaios/**"]
---

# ブランチ & デプロイ

main=Production（自動デプロイ）／dev=trunk（staging 自動）／release/x.x.x=App Store 提出。
フロー: dev → feature ブランチ → PR → dev → main → release。1編集 = 即 commit+push。commit/push 前に `git fetch`。branch の終着は merge か削除（`gh pr merge --merge --delete-branch`）。
iOS は Fastlane 必須（`cd aniccaios && fastlane <lane>`、xcodebuild 直接禁止）。提出前に `greenlight preflight <app_dir>` で CRITICAL=0。
iOS E2E = `mcp__maestro__*`（maestro CLI 直接は使わない）。
