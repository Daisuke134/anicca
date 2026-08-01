---
name: anicca-booking
description: 廃止済みの旧イベント申込入口。実行せず、Connector の正式 runtime へ移行する。
metadata:
  type: retired-booking-agent
---

# anicca-booking（廃止済み）

この旧スキルは実行しない。旧 cron、旧ブラウザ申込、検索サイトの巡回処理は廃止した。

正式な実装と要件は次を正本とする。

- `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- `apps/life-manager/lib/connector-events-pack.js`
- `apps/life-manager/lib/outbound-event-job.js`

イベント申込は現在、認証済み Luma セッション、Google Calendar の空き枠、受付証跡、Telegram 通知を一つの Connector runtime で扱う。connpass は公式 API キー発行後の個人・非商用・読み取り専用候補探索に限り、サイトへの自動アクセスや自動参加申込には使用しない。

`scripts/run.sh` は外部アクセス前に終了コード 78 で停止する。
