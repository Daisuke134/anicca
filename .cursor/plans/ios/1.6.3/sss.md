  全体 TO-DO リスト

  #: T1
  タスク: reference MD を thin 化
  対象ファイル: references/us-006-implement.md
  内容: 600行 → ~50行。「tdd-feature スキルをロード」+ Factory固有の注意事項のみ残す
  ────────────────────────────────────────
  #: T2
  タスク: reference MD を thin 化
  対象ファイル: references/us-007-testing.md
  内容: 「maestro-ui-testing スキルをロード」+ Factory固有の注意事項のみ残す
  ────────────────────────────────────────
  #: T3
  タスク: reference MD を thin 化
  対象ファイル: references/us-004-specs.md
  内容: 「迷ったら prd-generator/architecture-spec も読め」を削除。1 US = 1 スキルに
  ────────────────────────────────────────
  #: T4
  タスク: US-008e を分割
  対象ファイル: references/us-008-release.md + SKILL.md テーブル
  内容: US-008e(release-review) と US-008f(validate+TF) に分割。1 US = 1 スキル
  ────────────────────────────────────────
  #: T5
  タスク: US-009 に asc-submission-health を正式ロード化
  対象ファイル: references/us-009-submit.md
  内容: 「参考のみ」→「ロード必須」に変更
  ────────────────────────────────────────
  #: T6
  タスク: implementation-spec スキルに references/ 追加
  対象ファイル: implementation-spec/
  内容: prd-generator と architecture-spec から必要部分を移植して references/ に配置
  ────────────────────────────────────────
  #: T7
  タスク: release-review に修正ループ追加
  対象ファイル: release-review/SKILL.md
  内容: レポート出力だけでなく、Critical/High → 修正 → 再レビューのループを追加
  ────────────────────────────────────────
  #: T8
  タスク: 300行超の reference に目次追加
  対象ファイル: us-008-release.md
  内容: 残る部分（Step 0-6 + 分割後の008e/008f）に目次追加
  ────────────────────────────────────────
  #: T9
  タスク: scripts/ ディレクトリ作成
  対象ファイル: mobileapp-builder/scripts/
  内容: setup-env.sh, unlock-keychain.sh, slack-report.sh, gate-check.sh
  ────────────────────────────────────────
  #: T10
  タスク: Description pushy 化
  対象ファイル: mobileapp-builder/SKILL.md frontmatter
  内容: トリガーキーワード追加
  ────────────────────────────────────────
  #: T11
  タスク: WHY なしルールに理由追記
  対象ファイル: mobileapp-builder/SKILL.md CRITICAL RULES
  内容: Rule 3,12,14,16,17,18,38 に WHY 追加
  ────────────────────────────────────────
  #: T12
  タスク: SKILL.md テーブル修正
  対象ファイル: mobileapp-builder/SKILL.md L28-49
  内容: Skills 列を正確に（「(inline)」表記を削除、正しいスキル名に）
  ────────────────────────────────────────
  #: T13
  タスク: 各ミニスキルの BP チェック
  対象ファイル: 全15スキル
  内容: 500行以下か、description pushy か、references/ 活用しているか

  優先順位

  Phase 1（構造変更 — 最重要）:
    T1 → T2 → T3 → T4 → T5 → T6

  Phase 2（スキル強化）:
    T7 → T13

  Phase 3（Polish）:
    T8 → T9 → T10 → T11 → T12
---


 ---
  更新版 TODO リスト

  #: T1
  タスク: us-001-trend.md thin 化
  詳細: 378行→~40行。レシピを idea-generator スキルに移動
  ────────────────────────────────────────
  #: T2
  タスク: us-002-planning.md thin 化
  詳細: 245行→~30行。レシピを prd-generator スキルに移動
  ────────────────────────────────────────
  #: T3
  タスク: us-003-research.md thin 化
  詳細: 291行→~30行。レシピを competitive-analysis スキルに移動
  ────────────────────────────────────────
  #: T4
  タスク: us-004-specs.md thin 化
  詳細: 570行→~60行。レシピを implementation-spec + ios-ux-design に移動。「迷ったらprd-generator」削除
  ────────────────────────────────────────
  #: T5
  タスク: us-005a-infra.md thin 化
  詳細: 171行→~40行。レシピを asc-signing-setup に移動
  ────────────────────────────────────────
  #: T6
  タスク: us-005b-monetization.md thin 化
  詳細: 402行→~40行。レシピを asc-ppp-pricing に移動
  ────────────────────────────────────────
  #: T7
  タスク: us-008-release.md 分割 + thin 化
  詳細: 715行→各~30行。008d に App Privacy 移動、008e=レビューのみ、008f=TestFlight 新設
  ────────────────────────────────────────
  #: T8
  タスク: us-009-submit.md thin 化
  詳細: 132行→~40行。asc-submission-health 正式ロード + apple-appstore-reviewer ロード
  ────────────────────────────────────────
  #: T9
  タスク: implementation-spec スキル強化
  詳細: us-004-specs.md から PRD/ARCH/IMPL/TEST/RELEASE テンプレ + Gate + Cross-Reference を移植
  ────────────────────────────────────────
  #: T10
  タスク: release-review スキル統合強化
  詳細: asc-submission-health の7項目チェックを統合 + 修正ループ追加
  ────────────────────────────────────────
  #: T11
  タスク: asc-ppp-pricing スキル強化
  詳細: us-005b のレシピ移植（IAP作成 + RC setup + uiPreviewMode）
  ────────────────────────────────────────
  #: T12
  タスク: idea-generator スキル強化
  詳細: us-001 のレシピ移植（トレンド収集 + フィルタリング）
  ────────────────────────────────────────
  #: T13
  タスク: SKILL.md テーブル更新
  詳細: US-008f 追加、Skills 列を正確に
  ────────────────────────────────────────
  #: T14
  タスク: Description pushy 化
  詳細: mobileapp-builder SKILL.md frontmatter
  ────────────────────────────────────────
  #: T15
  タスク: WHY なしルールに理由追記
  詳細: Rule 3,12,14,16,17,18,38
  ────────────────────────────────────────
  #: T16
  タスク: scripts/ ディレクトリ作成
  詳細: setup-env.sh, slack-report.sh, gate-check.sh
  ────────────────────────────────────────
  #: T17
  タスク: 各ミニスキルの BP チェック
  詳細: 500行以下、description pushy、references/ 活用