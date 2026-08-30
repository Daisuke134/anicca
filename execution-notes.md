# execution-notes — Phase L 最大応募マシン (Lancers / Mercor / CrowdWorks)

> 旧 sprint-4 (2026-07) の notes は `docs/archive/execution-notes-sprint-4-2026-07.md` へ退避済み。

Goal 受領 2026-08-31。Phase C（Eliza 基盤 C01–C09）は完了済み。

## 確認した証拠

### ディスク（全 lane の共通ブロッカー）— 解消
- 2026-08-30 深夜: 空き 0B、`Write`/`Bash` すら ENOSPC で不能
- 2026-08-31 現在: `df -h /System/Volumes/Data` → **18Gi free / 91%**（別 agent が回収）

### ai.anicca.lancers-revenue-storefront — 原因=ディスク、要再実測
- `launchctl print`: runs=4, last exit code=1, not running
- stderr: `[Errno 28] No space left on device: .../.cleanup-latest.json.*` が全書き込みで反復
- 併発: `storefront_offer:_AccountLockBusy`（複数回）、`storefront_offer:OSError`
- **判定: ENOSPC が主因。ディスク回復後の再実行で再判定が必要（未実施）**
- AccountLockBusy が独立の問題として残るかは未確認

### ai.anicca.job-search-mercor — 原因=契約不一致の実バグ（特定済み）
- `launchctl print`: runs=3, last exit code=1
- stderr 末尾: `job_search_loop.mercor_earnings.EarningsReadbackError: provider must be mercor`
  （`mercor_earnings.py:50`、`mercor_earnings_sync.py:23` 経由）
- 実ファイル `~/.local/state/anicca/job-search/mercor/earnings-readback.json`（600B, mode 600）:
  - `status: "blocked"`, `reason: "payment_rows_require_structured_extraction"`
  - `page_url: "https://work.mercor.com/explore"`（**/earnings ではない**）
  - `provider` キー自体が存在しない
- `mercor_earnings_capture.py:40-41` が blocked 形を書き、**:122-123 で無条件に return 0**
- `run-mercor.sh:116` の `CAPTURE_RC` 判定を通過 → `:122` の sync が blocked 形を受け取り crash
- **真因: capture は blocked を正当な終端として返せるが、sync に blocked 分岐が無い契約不一致**
- 別件（同 stderr 内）: `gog gmail thread get` が 60s timeout。独立の問題として未対応

### ai.anicca.hf-gig-storefront-direct
- `launchctl print`: **state = running**, runs=25。exit 1 は過去の記録
- 現時点で稼働中。Coconala 本体なので触らない

### CrowdWorks
- 実装 0（`find skills -iname '*crowdworks*'` → 0 件）

### ★Mercor の応募0は「バグ」ではなく正しい挙動★（2026-08-31 判明）
直近 pass `mercor-20260830-202001-90608` の `attempt-01.result.json`:
- `status: needs_human`、`inspected_listings: 10`、**`submitted: 0`**、`needs_human: 2`
- 10件の内訳:
  - 1件 = 既に応募済み（`observe_only_submitted_pending_review`）
  - 2件 = 人間による assessment 必須（Pharmacology Lab Review / Finance Interview）
  - 2件 = 中間フォーム未完（米国居住要件 / 3年以上のヘルスケア実務）
  - **5件 = `submit_visible=true` なのに `not_submitted_missing_verified_fact` で見送り**
    理由: 「5年以上の Pricing/ROI」「米国在住 Devoted Health」「5年以上の法務/コンプラ」
    「5年以上のコンプラ/規制」「5年以上のインシデント管理」
- profile SSOT `~/.config/anicca/job-search/profile.json`（mode 600）と突合:
  - `base: Tokyo, Japan` / `citizenships: [Japan]` / `foreign_work_authorizations: []`
  - `date_of_birth: 2002-01-30`（24歳）
- **結論: 米国居住要件も5年以上の専門実務も事実として満たさない。agent は嘘をつかずに正しく見送っている。**
- したがって Mercor で「最大応募」を達成するには虚偽申告が必要であり、Goal の制約
  「虚偽の経歴を profile に書かない」と直接衝突する。**Mercor は Dais の検証済み事実に対して
  構造的に不適合な provider**（米国中心・資格ゲート型）。
- **戦略上の含意: 最大応募の主戦場は Lancers と CrowdWorks（日本語・日本在住・タスク型）である。**

## 未解決項目（次にやる順）
1. Mercor: capture blocked ↔ sync 契約不一致を repo 正本で修正（release は immutable なので repo → 新 release）
2. Lancers: ディスク回復後に storefront lane を再実行し、ENOSPC 以外の失敗が残るか実測
3. Lancers: profile 整備（L03B）
4. Lancers: 最大応募（L10B）
5. Mercor: 同じ地点まで
6. CrowdWorks: L01（認証 + read-only 在庫）

## 決めたこと
- Upwork は雛形にしない（入金 0 の失敗 lane）。再利用の出所は Coconala のみ
- 稼働中の Coconala lane と hf-gig-storefront-direct は触らない
