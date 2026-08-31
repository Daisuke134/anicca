# execution-notes — Phase L 最大応募マシン (Lancers / Mercor / CrowdWorks)

> 旧 sprint-4 (2026-07) の notes は `docs/archive/execution-notes-sprint-4-2026-07.md` へ退避済み。

Goal 受領 2026-08-31。Phase C（Eliza 基盤 C01–C09）は完了済み。

## 名指しされた破損3 lane — 全て一次証拠で診断済み・2つは修復済み

| lane | 診断（一次証拠） | 現状 |
|---|---|---|
| `lancers-revenue-storefront` | 第1原因=`[Errno 28] No space left on device` が全書き込みで反復。ディスク回収後も exit 1 が残り、stdout の `{"error":"account_unavailable","logged_in":false}` から**セッション失効**が第2原因と判明 | **修復済み・exit 0** |
| `job-search-mercor` | `EarningsReadbackError: provider must be mercor`。実ファイル `earnings-readback.json` が `status:"blocked"` / `page_url:".../explore"`(≠/earnings) / `provider` キー欠落。`mercor_earnings_capture.py:40-41` が blocked 形を書き `:122-123` で**無条件 return 0**、`run-mercor.sh` の CAPTURE_RC 判定を通過して sync が crash する**契約不一致** | 診断済み・未修正（Dais 指示で Lancers 優先） |
| `hf-gig-storefront-direct` | 調査時点で `state = running`。exit 1 は release pin 切れ由来 | **修復済み（`lm-loop apply`）** |

## Lancers 条件別 判定

| 条件 | 判定 | 証拠 |
|---|---|---|
| (1) 認証 + read-only 二回同値 | **PASS** | 20秒間隔の2回が SHA256 `485cc032…` で完全一致。`logged_in:True` `source_complete:True` boards=2 unread=1 proposals=38 selecting=15。provider effect 0 |
| (2) profile 完成 | **FAIL** | 公式画面で完成度 **50%**。未完了=写真/ビジネス経験/本人確認/機密保持確認/電話確認。実績0件・評価0件。基本単価は空だったので設定し `10000` を読み返し確認済み |
| (3) 最大応募 | **BLOCKED** | 応募0件。判断モデルは動作を実証（案件5594217→submit_required/48万円/35日/提案文生成）したが、Codex が9/6まで利用上限。routing 変更は spec 制約とピン留めテストに抵触するため Dais の判断待ち |

## 公式応募履歴の読み返し（条件(3)の証拠、2026-08-31）

`https://www.lancers.jp/mypage/proposals/limit:100/sort:Proposal.id/direction:DESC`
（ページ表題「提案した仕事一覧」）を実ブラウザで読み、**公式 proposal ID を38件取得**。
最大 `5593844` / 最小 `5518137`。

- ★ `work_sync` が返す `proposal_pipeline.current_count: 38` と**公式38件が完全一致** ★
  → loop の集計は捏造しておらず、公式と突合できる
- ローカル claim 台帳 `application.json` は fingerprints 195 / pending 0
- 直近 pass が `duplicate_project` とした `5594055` は**公式履歴に存在しない**
  → claim は「応募した」ではなく「判断済み（応募 or 見送り）」を意味するため、
    195 − 38 = 157 は見送り済みと解釈できる。**欠陥と断定できる証拠は無い**
  → ただし claim が応募と見送りを区別しないため、状況が変わった案件が二度と再評価されない。
    再評価の要否は `ELZ-L10B`（最大応募）で扱う

**このセッションの実測内訳**: 確認13件 → 新規応募0件 / 見送り13件（全件が判断済み）。
重複応募0を replay で確認。

## 応募判断経路の修復（5段階、すべて一次証拠）

1. **存在しないパス** — `application_loop.py`/`work_sync.py` が `skills/agent-runner/agent_runner.py` を参照。git 履歴ゼロ＝最初から不在。release にも無い。実体は `runtime/agent-runner/`（1858行）。2ファイル2行修正。テスト 9 failed/42 passed で変更前後同一
2. **Codex 枯渇** — `attempt-01/02.stdout.log` に `You've hit your usage limit … try again at Sep 6th, 2026`。応募 task class だけ codex→codex しかフォールバックが無く全滅。同ファイル内に codex→claude の実例が2つある
3. **フェンス未除去** — `extract_claude_payload` がエンベロープのみ剥がし、中身の ```json フェンスを残すため呼出側の `json.loads` が失敗。既存 `OPENCLAW_JSON_FENCE` を再利用して除去。**`planner_runner_failed` → `ok:true`**。ガードテスト 18 passed

## 決めたこと
- routing 変更は**押し通さない**。spec に「model provider と routing は現行から変更しない」と明記、かつピン留めテスト2本が守っている。一度加えた claude フォールバックは撤回し全緑に復帰させた。A（Codex課金）か B（フォールバック許可＋テスト/spec更新）かは Dais の判断
- site 固有 selector/regex を production code に焼かない（`session_recovery.py` は破棄）
- profile は本名でなくペルソナで運用（正本 `skills/gig-work/profile/PROFILE-ASSETS.md`）

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

### 本番 fleet 停止と復旧 2026-08-31
- `~/Library/LaunchAgents/ai.anicca.*.plist` 182本中 132本が、削除済み release を
  ProgramArguments に固定していた（今夜のディスク回収で release が消え、plist が未更新）
- Coconala/gig の7レーン全部が該当し、唯一の収益源が停止していた
- `lancers-revenue-telegram-report` の exit 78 EX_CONFIG も同一原因
- ★`lm-loop doctor` は ok:true を返す。registry しか見ず installed plist の program 実在を
  検査しないため、この故障クラスを検知できない。doctor 側の欠陥（未修正、要 atom 化）★
- `bin/lm-loop apply` で復旧。DEAD 132→67、alive 34→99。
  money-critical（gig 7本 + Lancers 5本 + job-search-mercor）は全て ALIVE
- 残 67 は marketing/fundraiser/taskmarket 等の二次系（未対応）
- 再実行後: hf-gig-apply-direct running、telegram-report は 78→exit 1、
  hf-gig-paid-direct exit 1（いずれも原因未特定）

### Lancers セッション復旧 2026-08-31
- `/mypage` が `/user/login` へリダイレクトし `#login_form`=1 → セッション失効が lane 崩壊の真因
- lane には状態判定しかなく、自分で再確立する経路が無い（人間前提の設計上の穴、要 atom 化）
- SSOT の資格情報と `gog gmail` の通知読み取りで自動復旧。人間の操作なし
- 結果 `/mypage` で loginForm:0。`work_sync.run_tick()` が
  ok:True / logged_in:True / source_complete:True / board_count:2 / unread_count:1
- storefront と application lane が exit 1 → exit 0

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
