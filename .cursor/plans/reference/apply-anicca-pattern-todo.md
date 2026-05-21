# Anicca への「トレードボット型」適用 TODO（VPS 現状ベース）

**作成日:** 2026-02-12  
**前提:** VPS 実機確認済み（gateway active, gpt-5.3-codex, 19 cron, 10 skills in config, skills/ + workspace/skills/ 実在）

---

## 謝罪

定義や runbook を書くことに寄せて、「毎日・毎回それを実行する仕組み」を TODO に明示しなかった。  
置いておくだけでは動かない。スキルを cron で叩くか、クローン（実行のまとまり）で回すか、のどちらかで「実行」を用意する必要がある。その前提を TODO に落とし込まずに済ませた不備を認め、謝罪する。

---

## VPS 確認結果（2026-02-12 時点）

| 項目 | 値 |
|------|-----|
| Gateway | active (running), 約 2h50m uptime |
| Primary model | openai-codex/gpt-5.3-codex |
| Workspace | /home/anicca/.openclaw/workspace |
| Cron ジョブ数 | 19（ops-heartbeat, mission-worker, trend-hunter, suffering-detector, x/tiktok poster, app-nudge-sender, moltbook-*, roundtable-*, 等） |
| managed スキル（skills/） | moltbook, slack-mention-handler, suffering-detector, app-nudge-sender, ops-heartbeat, roundtable-*, mission-worker, trend-hunter, x-poster, tiktok-poster, moltbook-monitor, moltbook-poster, 他 |
| workspace スキル | content-research-writer, daily-metrics-reporter, gitclaw |
| openclaw.json skills.entries | 10 件 |
| memory/ | 存在 |
| anicca.ai リポ | workspace 内に存在 |

---

## 適用 TODO（「実行」前提：スキル＋cron または経路で毎日/毎回回す）

| # | パターン | やること（実行まで含む） | 状態 | 備考 |
|---|----------|--------------------------|------|------|
| 1 | 役割を一言で固定 | 一行役割を SSOT（identity または agent プロンプト）に書き、VPS の agent 設定がそれを参照していることを確認する。未参照なら設定を足し、gateway 再起動。cron で動く既存スキルはその agent で動いているので「毎回その役割で動く」。 | 未 | 定義だけでなく「その設定で cron が回っている」まで確認する。 |
| 2 | スキル＝足の棚卸し | openclaw.json の skills.entries と skills/・workspace/skills/ を照合し、有効・無効・未登録を一覧化する。entries を実態に合わせて更新し、VPS で gateway 再起動。1 回の作業で「どのスキルが cron で叩かれるか」を確定させる。 | 未 | 棚卸しの結果を openclaw.json に反映しないと実行に効かない。 |
| 3 | 参照していい情報源を明文化 | 参照情報源リスト（suffering-detector 結果、nudge フィードバック、roundtable memory、moltbook-monitor、daily-metrics、Mixpanel 等）を agent が読む 1 箇所（SKILL.md または agent プロンプト）に書く。既存の suffering-detector / mission-worker 等はその agent で cron 実行されているので、書けば「毎回その情報源を参照してよい」と効く。 | 未 | 書いただけでは効かない。その 1 箇所を cron で動くスキルが参照する形にする。 |
| 4 | 記録＋外向き通知を 1 本化 | **「今日の学び」を出力するスキルを 1 本作り、cron で日次 1 回実行する。** 出力先は Slack / 監査ログ / ファイル＋gitclaw commit のいずれか 1 つに決める。daily-metrics-reporter 拡張でも新規スキルでもよい。cron を jobs.json に追加し、VPS に反映。 | 未 | スキル＋cron がないと毎日出ない。 |
| 5 | 失敗→学習のループ | Nudge 無視・低評価・解約などの事後データがバックエンドから学習ジョブ（roundtable / memory / initiative）に渡る**経路**を 1 本用意する。既存の learning-jobs（memory/initiative/cleanup/autonomy-check）の cron がそのデータを読むようにする。未なら API 呼び出し or イベントを 1 本追加し、cron がそれを叩く形にする。 | 未 | 経路が動いていないと「失敗→学習」は回らない。 |
| 6 | 人間の介入境界 | runbook（openclaw-anicca または AGENT-RUNBOOK）に「Anicca は自動で回す。人間が入るのは次のときだけ」を書く。例: crisis（#agents）、ops アラート、Slack での明示的 @Anicca、Control UI での手動操作。実行は「人間が runbook を見て判断する」なので、書いて運用で従う。 | 未 | 毎日自動実行するものではない。定義でよい。 |
| 7 | 初勝利を 1 つ定義して計測 | 初勝利を 1 つ定義する（例: suffering-detector → app-nudge 送信 → 24h 内にユーザー ack が 1 件）。**その定義をチェックするスキルを 1 本作り、cron で日次 1 回実行する。** 結果を Slack / 監査ログ / Mixpanel のいずれか 1 箇所に出す。jobs.json に追加し、VPS に反映。 | 未 | スキル＋cron がないと毎日計測されない。 |

---

## 進め方の注意

- 4・5・7 は「スキル（または経路）＋cron」で実際に動かすまでやる。定義だけにしない。
- 1・2・3 は設定・ドキュメントの更新だが、「その設定で既存 cron が回っている」ことを確認する。
- 6 は runbook に書いて運用で従う。
- 完了したら状態を「済」にし、証跡（どのスキルを追加したか、cron の jobId、どのファイルを変えたか）を一行メモする。
