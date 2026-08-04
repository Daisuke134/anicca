# Fleet と Remote 安定化（2026-08-04）

**この1本を読めば次のセッションが続きから入れる。** 進捗をチャットに置かないための SSOT。
gig work 本体の残 TODO は `~/profitable-claude/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md` §6 が正本 → 本ファイルはそこへ入る**前**に閉じる整備タスクだけを持つ。

## 1. Goal（done 条件）

1. 全ループが燃料切れで静かに死なない — 枯渇が起きたら Telegram に届く。
2. フリートの生死が1画面で分かる — 171本のうち何が生きて何が死体か。
3. 電話 ↔ Mac が切れても作業が消えない — 進捗がファイルに残り、次セッションが拾える。

---

## 2. 2026-08-04 に実測した事実（推測と分けて記録）

### 2.1 codex 燃料の単一障害点

| 実測 | 値 |
|---|---|
| `~/.codex/auth.json` が向いていたアカウント | `daisukenarita53@gmail.com` (pro)。**8/9 04:31 まで枠切れ** |
| エラー原文 | `You've hit your usage limit. ... try again at Aug 9th, 2026 4:31 AM.` |
| 影響範囲 | codex 依存の launchd ジョブ **15本** + `hf-gig-pass` |
| gig の症状 | `agent-PAID_WORK` が8パス連続失敗。attempt-1 codex = `transient_quota`、attempt-2 claude-direct sonnet = `validation_or_task_failure`（散文を返し `no JSON object in provider result`）。1回あたり $0.59 を消費して成果ゼロ |
| 検知できなかった理由 | `launchctl list` は緑。稼働層だけ見ていると燃料層の死が見えない |

**配線の実体**: `skills/agent-runner/agent_runner.py:294-330` が `CODEX_HOME=~/.local/state/anicca/codex-runner` を立て、その中の `auth.json` を `auth_file`（既定 `~/.codex/auth.json`）への symlink として**強制**する（不一致なら `codex automation auth target mismatch` で即死）。→ `~/.codex/auth.json` の中身を差し替えるだけで全ループに反映される。

### 2.2 修正（実施済み）

```
~/.codex/auth.json                          = keiodaisuke@gmail.com (pro)  ← 全ループの燃料
~/.codex-acct2/auth.json                    = daisukenarita53@gmail.com    ← デスク作業
~/.local/state/anicca/codex-desk-53/auth.json = 53 の複製（復旧用）
~/.codex/auth.json.bak-53-20260804-202834   = 差し替え前のバックアップ
```

検証: 本番 `CODEX_HOME` で `codex exec` が `RUNNER_PATH_OK` を返す。差し替え後初回の gig-pass（`gig-pass-1785843056-60192`）で **PAID_WORK attempt-1 = codex, rc=0, error_class=None, schema_valid=True**。8パス連続失敗が止まった。

**config.json は1バイトも変えていない**（候補順は codex 先頭のまま）。Dais の裁定: フォールバックは Claude のままでよい。2アカウント自動フェイルオーバーは**不採用**。

### 2.3 フリートの実態

```
anicca の launchd ジョブ = 171本
  最終ログ更新  24h内 67 / 7日内 58 / 30日内 28 / 30日超 11 / ログなし 7
  exit ≠ 0     27本
```

5分毎に失敗し続けているもの: `life-manager-payout` / `life-manager-financial-report` / `life-manager-x402-ledger` / `life-manager-ugig-invoice-observer`（いずれも exit=1、7/30〜8/1 から）。
30日超停止: `capafy-loop-daily`(7/12) / `hf-reddit-loop-daily`(7/15) / `life-manager-daily`(7/12, exit=1) / `slack-bridge`(6/24, exit=78) ほか。

**これらは 8/2 の枠切れとは無関係。それ以前から死んでいる。**

### 2.4 監視は鳴っていた。届いていなかった

`gig-auditor` が毎時こう出していた:

```json
{"verdict": "STALE (no pass in 1489min ...)", "heartbeat_age_min": 1489,
 "actions_delta_since_last_audit": 0, "progressing": false, "jpy_earned": 120900.0}
```

出力先が誰も見ない `.log` ファイル。**アラートが無いのではなく、届かない。**

### 2.5 Remote Control（電話 ↔ Mac）

先行調査が既にある → `docs/superpowers/specs/2026-08-01-remote-control-robustness-design.md`（8本中6本 done）。

今日の実測:

| 項目 | 値 |
|---|---|
| 401 発生回数（今日） | **0**（8/1 のサーキットブレーカが効いている） |
| サービス停止（今日） | **2回** — 17:42:10、18:36:37（`launchd: service inactive`） |
| supervise ログの終了記録 | **無し** → 正常終了経路を通らずに死んだ |
| `claude-remote-control` を kill するスクリプト | 全域検索で**ゼロ**（`remote-control-supervise.sh` と `remote-control-notify.sh` のみが参照） |
| 現在 | 18:36 から連続稼働 |

**未解決**: この2回の停止の原因。残る容疑者は ①claude 本体のクラッシュ ②外部からの `launchctl kill` / `kickstart -k` ③シグナル死。

**構造的な要点**: launchd は「プロセスが居ること」しか保証しない。ループは 1 pass = 1 プロセスで状態をファイルに書くので再起動で完全復旧するが、Remote Control はセッション状態をメモリに持つため、再起動すると走っていたターンが消える。→ **解は「もっと launchd」ではなく「進捗をファイルに置く」**（本ファイルがその第一歩）。

**未検証の最有力仮説**（8/1 spec §5 より）: 同一 Mac で複数の `claude` プロセス（remote-control 常駐 / 対話セッション / reddit-loop / gig のフォールバック = 4本）が同じ OAuth 資格情報のリフレッシュトークンを取り合っている線。gh #53635 に状況証拠。**UNVERIFIED。**

### 2.6 codex のリモート座席（両アカウント同時接続）

| 実測 | 値 |
|---|---|
| 座席の単位 | **アカウント単位**（Mac 単位ではない）。両アカウント同時接続は可能 |
| 22:25:43 の状態 | `acct1(keiodaisuke) status=connected` / `acct2(53) status=connected` — 両方 |
| 失敗していた理由 | `Error: app server is running but is not managed by codex app-server daemon` = 同じ CODEX_HOME を別の app-server が握っていた（アカウント同士の争いではない） |
| 維持機構 | `com.anicca.codex-remote-keepalive`（60秒毎、`~/.codex-remote-keepalive.sh`）。**plist は存在していたが launchctl 未ロードだった** → 20:03 でログが停止していた |
| 対処 | `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.anicca.codex-remote-keepalive.plist` → 初回実行で acct1 が `connecting` → `connected` に上昇。Dais が電話（keiodaisuke ログイン）で接続を確認済み |

### 2.7 エージェント側の規律（今日の暴走の原因）

旧 `stop-require-search.sh`（Stop hook）＋ `stop-block.sh`＋ HARD RULE 0.33 / #-3 の組み合わせで、「Dais に聞くな・止まるな」が4箇所に重複していた。結果、30分以上ツールを撃ち続けて一切報告しない挙動が生まれた。

Dais verbatim: "you were just hiding your output" / "I really don't want that you were doing this whole thing without me"。

**修正済み**:
- `~/.claude/hooks/stop-require-search.sh` 削除（settings.json の登録も）
- `~/.claude/hooks/stop-block.sh` 削除（同上）
- `~/.config/ai/core.md` の No-human-loop を **3段（聞かずに実行 / 宣言して実行 / 承認を待つ）+ 「黙るな」** に改訂 → `sync.sh` で CLAUDE.md / AGENTS.md×2 / GEMINI.md へ配布
- `anicca-project/CLAUDE.md` の HARD RULE 0.33 と #-3 を同じ3段に従属させる（commit `96011231b`）

---

## 3. Telegram メッセージ設計（Dais 合意済み）

原則: ①無音＝正常は禁止（毎日必ず1通来る。来なければ監視が死んでいる） ②緑は報告しない、変化と赤だけ ③「動いた」でなく「稼いだ」を先頭に。

| 種別 | 頻度 | 中身 |
|---|---|---|
| 日報 | 毎朝1通（必ず） | 昨日の金（gig/clip/LM 別 + 累計）→ 止まっている主要ループ → 燃料残 → 生存本数 |
| 燃料切れ | 即時 | どのアカウントがいつまで枯れたか、影響ループ一覧、いま何が起きるか、選択肢 |
| ループ死亡 | 即時 | 最後の成功時刻、エラー原文、自動対処の結果、次の wake、放置した場合の損失 |
| 効果ゼロ | 即時 | 稼働は緑・成果ゼロ。24h の起動回数と応募/返信/納品の実数、原因候補、止まっている案件 |
| 復旧 | 変化時 | 何が直ったか1行、原因1行、修正1行 |
| 週報 | 日曜 | 主要3ループ（gig / clip / life-manager）だけ。ボトルネックを名指し |

通知量の見積: 平常 1通/日、荒れても 4通/日。171本を並べない。

**検知ロジック**: ループごとに `alive_if` と `healthy_if` を**別々に**定義する。今日の障害は `alive_if` が真のまま `healthy_if` が偽だった。

```
gig-pass:      alive_if = 過去2時間に pass が1回完了
               healthy_if = 過去24時間に 応募 or 納品 ≥1
clip-loop:     alive_if = 過去25時間に投稿1件
life-manager:  alive_if = 過去25時間に exit=0
燃料:          alive_if = codex が5秒テストに応答（毎時1回、$0）
```

---

## 4. TODO（順序が正本。番号順に着手、飛ばさない）

| # | タスク | done 条件 | 状態 |
|---|---|---|---|
| A1 | `stop-block.sh` 削除 | Stop フックが cozempic と orca だけ | **done 2026-08-04** |
| A2 | 「聞くな・止まるな」を3段の行動規律へ書き換え（3箇所） | core.md + project CLAUDE.md 2箇所、sync + push 済 | **done 2026-08-04**（`96011231b`） |
| E1 | `codex-remote-keepalive` を launchctl へロード | 両アカウント `connected` | **done 2026-08-04 22:25** |
| E2 | 電話から接続を確認 | Dais が keiodaisuke で Mac を確認 | **done 2026-08-04** |
| D1 | codex アカウント配置を memory に永続化 | `reference_codex_account_split_loops_vs_desk` | **done 2026-08-04** |
| D2 | 「1リソース1オーナー」を memory に | `feedback_one_resource_one_owner` | **done 2026-08-04** |
| A5 | 進捗をファイルへ（本ファイル） | 次セッションが本ファイル1本で続行できる | **done 2026-08-04** |
| B2 | 日報1通を Telegram へ（毎朝必ず） | 実送信され messageId が返る。無音＝異常と判定できる | pending |
| B3 | 燃料アラート（codex/claude の枠切れ即通知） | 枯渇を作って1通届くことを実測 | pending |
| B1 | `fleet status` を1本書く | 171本の生死・exit・最終活動が1画面 | pending |
| B4 | 効果ゼロ検知（稼働緑・成果ゼロ） | `alive_if` 真 かつ `healthy_if` 偽 で1通届く | pending |
| A3 | remote-control の停止理由をログに残す | シグナルトラップ追加。次の停止で犯人が記録される | pending |
| A4 | claude 資格情報の共有を調査 | 同時稼働 claude プロセス数 × 401 発生時刻を突合し §2.5 の仮説を白黒つける | pending |
| E3 | 座席競合を構造的に防ぐ | デスクトップアプリと CLI daemon が同じ CODEX_HOME を握らない | pending |
| C1 | exit≠0 の27本を1本ずつ決着 | 特に5分毎失敗の4本（life-manager 系）。直すか止めるか | pending |
| C2 | 30日超停止の11本を削除 | 嘘の緑が消える | pending |
| C3 | 生きている67本を `loops.toml` に登録 | owner / done条件 / alive_if / healthy_if を持つ正本ができる | pending |
| D3 | 後片付け | `~/.local/state/anicca/codex-login-kk` 削除、`/tmp/kk-login-*.py` `/tmp/gig-kick-watch.*` 削除、ブラウザリース解放確認 | pending |

**gig work 本体に入る最低ライン**: A1 / A2 / D1 / D2 / B2 / B3 が閉じていること。残りは並行で回せる。

---

## 5. 既知の落とし穴

| 症状 | 対処 |
|---|---|
| `anicca-products` で `git push`（refspec なし）が "Everything up-to-date" と出るのに ahead のまま | `git push origin <branch>` と明示する。lefthook 絡み。2026-08-04 実測 |
| `browser-guard.sh acquire` した shell が終了すると lease が stale で残る | `pid` の生死を確認してから `release`。acquire と実作業は同一コマンドで行う |
| `~/.claude/CLAUDE.md` を直接編集しても sync.sh に上書きされる | 正本は `~/.config/ai/core.md`。編集後 `~/.config/ai/sync.sh` を回す |
| PreToolUse hook が `9222` / `connect_over_cdp` を含むコマンドを deny する | `browser-guard.sh` を同じコマンド内に含める（サンクション経路） |

## 6. 関連ファイル

| path | 役割 |
|---|---|
| `~/profitable-claude/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md` | gig 本体の残 TODO 正本（§6） |
| `~/profitable-claude/docs/loop-engineering/27-fleet-architecture-spec.md` | フリート横断アーキテクチャ。§5 に新ループ12項目契約 |
| `docs/superpowers/specs/2026-08-01-remote-control-robustness-design.md` | Remote Control 堅牢化の先行調査 |
| `~/profitable-claude/skills/agent-runner/agent_runner.py` | codex/claude の候補選択と CODEX_HOME/auth の配線 |
| `~/.codex-remote-keepalive.sh` | 両アカウントの remote daemon 維持（60秒毎） |
| memory `reference_codex_account_split_loops_vs_desk` | アカウント配置 |
| memory `feedback_one_resource_one_owner` | 資源の所有者ルール |
