/goal Life Manager cloud（anicca-products apps/life-call、Railway 本番）の P0/P1 全14タスクを実装〜本番デプロイ〜no-mock E2E まで完遂し、証拠付きで DONE 報告する。正本 spec = docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md（§10 決定・§10c patch・§12 E2E シナリオ・rotation runbook）。TaskList LM-* を進捗の正とし、状態変化ごとに更新。P2/P3（connector/health/mind/policy 等）は本 goal の後続。

Done（全 pass で完了。証拠 = 実 tool 出力/実着信/実TG/実gcal/DB row。mock/dry/self-report 禁止）:
1. 実イベントで T-10/T-5 が着信し AI が日本語で発話するのを Dais が確認（LM-24 target_legs fix + LM-2 claim解放 merge、lm_wake_log 実 row）
2. TG inline ボタン往復が本番で動く（LM-23）
3. 場所曖昧イベントが Gmail/web 検索で解決 or closed 質問1発のみ、lm_ask_log.resolved_from 記録（LM-3、open question 禁止）
4. 13 secret 全 rotate（runbook 準拠、TG webhook 手動再登録・Netlify 側同時更新含む）→ /health 200 + TG echo + dial preflight ok（LM-21）
5. staging に life-call 配線（staging 専用 secret、本番使い回し禁止）+ smoke script exit 0。以後 prod merge は staging green 後のみ（LM-18）
6. 「出た？」→「まだ」→ 遅刻連絡メール実送信の実往復（LM-5 v1、GPS なし設計）
7. onboarding: blocking 質問 ≤1 + Gmail(Unipile) stage skippable + context graph ≥5 fields が DB に載る（LM-6）
8. calendar transport を Unipile 化 + event cache（LM-25）で Composio polling 依存を排除、実 gcal で list/create/patch 動作。travel ratio が台帳+週次 TG に出る（LM-4）
9. api-cost/outcome ledger 実 row（LM-7）+ 実請求ベース margin 表を spec 追記（LM-19）
10. repo 収斂: life-manager repo から Railway deploy、移行後 /health 200 + 実 call 1 本（LM-20）
11. TikTok bio link 設定（screenshot 証拠）+ caption CTA（LM-22）
12. dev loop D0: launchd 無人 1 pass が実 PR + TG 報告を生む。merge はしない（LM-1）

実行方式: コード実装 = /flowb（worktree .worktrees/lm-p0 の PLAN.md → codex exec Sol 自走、agmsg 相談線、stdin は < /dev/null）。ops/browser/E2E/merge = メインセッション自身。vcsdd/adversary subagent は使わない。検証は必ず自分の実測で行い、codex の自己申告は実ファイル+自分のテスト再実行で裏取る。
境界（must）: Stripe webhook/課金経路を壊さない。破壊的 migration 禁止（ADD COLUMN IF NOT EXISTS のみ）。prod への merge は staging smoke green 後のみ。テストを弱めて green にしない。PII を public issue に書かない。rotate は runbook の HIGH-CAUTION 4 点（Netlify 共有・setWebhook 手動・LM_UID_SECRET 403 リスク・Stripe endpoint 別 secret）を先に潰す。
Block: 同一 fail が3 手法で再現 / creds・承認が必要で代替なし / schema・課金・prod を許可なく越える判断が必要 → 停止して最小の次アクションと再開コマンドを残す。進捗は execution-notes.md に維持し、各証拠パス後に更新。unblocked の必須証拠が残る限り「next steps だけ書いて停止」しない。最終報告は成果→証拠→残課題の順、日本語、見ていない読者向け。
