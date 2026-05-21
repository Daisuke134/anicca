# validate.sh — 100% Approval Factory Gate Spec

**Date:** 2026-03-02
**Goal:** CC が passes:true にしても、外部検証が FAIL なら ralph.sh が false に戻す。100% approval rate factory。

---

## 調査結果: Quality Gate の本当のベストプラクティス

### 1. ralph.sh の仕組み（ソース確認済み）

**ソース:** https://raw.githubusercontent.com/snarktank/ralph/main/ralph.sh + CLAUDE.md

ralph の quality gate は**CC 自身が自分で passes:true にする**仕組み。ralph.sh 側には**検証ロジックが一切ない**。CC が:
1. prd.json で passes:false を見つける
2. 実装する
3. 「quality checks (typecheck, lint, test)」を自分で実行する
4. 自分で passes:true にする

**問題:** CC が嘘をつける。checks をスキップしても passes:true にできる。今回サブスクの件でまさにそれが起きた。

### 2. SonarQube の Quality Gate（CI/CD のベストプラクティス）

**ソース:** https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates
核心の引用: 「A quality gate is a set of conditions that must be met before code can proceed to the next stage」

**ソース:** crediblesoft.com
核心の引用: 「mandatory evaluations a piece of code must pass before progressing to the next stage. Think of them as gatekeepers ensuring that quality standards are upheld without human intervention.」

**仕組み:** SonarQube は**外部プロセスが exit code で判定**する。CI パイプライン（Jenkins/GitHub Actions）が SonarQube の結果を見て、FAIL なら次のステージに進めない。**コードを書いた人が自分で「OK」と言うのではない。**

### 3. fastlane precheck + deliver（iOS の業界標準）

**ソース:** https://docs.fastlane.tools/actions/precheck/
核心の引用: 「fastlane will review your app for the most common causes of rejection」

**ソース:** https://docs.fastlane.tools/actions/deliver/
核心の引用: 「Automatically uses precheck to ensure your app has the highest chances of passing app review the first time」

**仕組み:** fastlane deliver は **submit の前に自動で precheck を実行**する。precheck が FAIL → deliver が止まる → submit されない。**これがビルトインのゲート。**

### 4. Greenlight（RevylAI）

**ソース:** https://github.com/RevylAI/greenlight
核心の引用: 「Keep looping until the output shows GREENLIT status (zero CRITICAL findings).」

**インストール済み:** /opt/homebrew/bin/greenlight
**スキル:** /Users/anicca/anicca-project/.claude/skills/greenlight/SKILL.md

---

## 答え: CI/CD パイプラインに入れるべきか？

**Yes。ただし従来の CI/CD（GitHub Actions等）ではなく、ralph.sh 自体をパイプラインにする。**

理由: 僕たちのシステムでは ralph.sh がパイプラインの役割。CC は worker（実行者）。

**問題の本質:** 今は CC が自分で passes:true にしてる = **worker が自分で QA してる**。これは SonarQube のアンチパターン。

**ベストプラクティス:**
- worker（CC）が実装する
- **別のプロセスが検証する**（SonarQube パターン）
- 検証が通らないと次に進めない

**答えは1つ:** ralph.sh に **validate.sh を追加**する。CC が iteration を終えた後、ralph.sh が validate.sh を実行して、exit code 0 でないと passes:true を認めない。

---

## なぜ CI/CD（GitHub Actions等）じゃなくて validate.sh なのか

1. **僕たちのパイプラインは ralph.sh。** GitHub Actions は git push → test → deploy の流れ。僕たちは ralph.sh → CC → validate.sh → 次の US の流れ。パイプラインの「ランナー」が GitHub ではなく ralph.sh。
2. **ローカル実行。** Mac Mini で動いてる。GitHub Actions に ASC 認証情報や Xcode を入れるのは複雑でコストがかかる。
3. **SonarQube のパターンと同じ。** SonarQube も CI のステップとして validate を挟む。ralph.sh の中に validate.sh を挟むのは同じ構造。
4. **fastlane deliver の設計と同じ。** deliver は submit の前に precheck を自動実行する。validate.sh は submit の前に checklist を自動実行する。

---

## 具体的な設計

### validate.sh（新規作成）

ralph.sh が毎 iteration の後に自動実行するスクリプト。CC は触れない。

Gate 1: greenlight preflight → CRITICAL=0 確認
Gate 2: asc subscriptions list → MISSING_METADATA がないか確認 + prices count > 0
Gate 3: screenshots/framed/ に >= 3 枚の PNG 確認
Gate 4: asc builds list → processingState=VALID 確認
Gate 5: submission-checklist.md の全項目を asc CLI で確認

全部 PASS → exit 0 → ralph.sh が次の iteration に進める
1つでも FAIL → exit 1 → ralph.sh が prd.json の passes:true を取り消す

### ralph.sh の変更

CC の iteration 後に validate.sh を呼ぶ:
- validate.sh が exit 0 → そのまま
- validate.sh が exit 1 → 最後に passes:true にされた US を false に戻す + Slack 通知

### CLAUDE.md.template の変更

US-005 にサブスク完全設定の項目を追加:
- サブスクリプション全ロケール表示名設定（asc-subscription-localization）
- サブスクリプション価格設定（asc-ppp-pricing）
- サブスクリプション配信可否: availableInNewTerritories=true
- サブスクリプショングループのローカライゼーション設定
- Quality Gate: state ≠ MISSING_METADATA + prices > 0

US-008 にサブスク Review スクショを追加:
- Paywall画面のスクショを撮影
- asc subscriptions review-screenshots create

---

## フェーズ構成（変更なし）

US のフェーズ数は変えない。validate.sh が全 US のゲートになる。

| Phase | CC がやること | validate.sh が確認すること |
|-------|-------------|-------------------------|
| US-001 | トレンドリサーチ | （基本チェックのみ） |
| US-002 | プロダクト計画 | （基本チェックのみ） |
| US-003 | 市場調査 | （基本チェックのみ） |
| US-004 | スペック生成 | （基本チェックのみ） |
| US-005 | ASC + サブスク完全セットアップ | subscriptions state ≠ MISSING_METADATA, prices > 0 |
| US-006 | iOS 実装 | BUILD SUCCEEDED, greenlight CRITICAL=0 |
| US-007 | テスト | テスト全 PASS |
| US-008 | スクショ+メタデータ+ビルド | framed screenshots >= 3, metadata complete, sub review screenshots |
| US-009 | 提出 | submission-checklist.md 全 PASS, greenlight GREENLIT |

**キモ: CC が passes:true にしても、validate.sh が FAIL なら ralph.sh が false に戻す。CC は validate を通過するまで同じ US をやり直し続ける。**

---

## 使うスキル（全部インストール済み）

| スキル | パス | どの US |
|--------|------|--------|
| greenlight | .claude/skills/greenlight/SKILL.md | validate.sh Gate 1 |
| asc-submission-health | .claude/skills/asc-submission-health/SKILL.md | validate.sh Gate 5 |
| asc-subscription-localization | .claude/skills/asc-subscription-localization/SKILL.md | US-005 |
| asc-ppp-pricing | .claude/skills/asc-ppp-pricing/SKILL.md | US-005 |
| asc-shots-pipeline | .claude/skills/asc-shots-pipeline/SKILL.md | US-008 |
| screenshot-planner | .claude/skills/screenshot-planner/SKILL.md | US-008 |

**submission-checklist.md**: .claude/skills/mobileapp-builder/references/submission-checklist.md — validate.sh Gate 5

---

## 修正すべきファイル

1. **validate.sh（新規）** — .claude/skills/mobileapp-builder/validate.sh.template として作成。ralph.sh がアプリディレクトリにコピーして自動実行。
2. **ralph.sh** — iteration 後に validate.sh を呼ぶコードを追加
3. **CLAUDE.md.template** — US-005 にサブスク完全設定 + Quality Gate 追加
4. **CLAUDE.md.template** — US-008 にサブスク Review スクショ追加
5. **SKILL.md** — validate.sh の存在と役割を Rule に追加

---

## 実装順序

1. validate.sh テンプレートを .claude/skills/mobileapp-builder/validate.sh.template に作成
2. ralph.sh に validate.sh 呼び出しを追加
3. CLAUDE.md.template の US-005, US-008 を更新
4. 現在の Micro Mood アプリで E2E テスト
