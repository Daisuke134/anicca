# ディスク回収 (228GB のうち 198GB 使用、空き 5〜7GB)

作成: 2026-08-01 / branch: `fix/cleanup-control-runtime-restore`
発端: [[2026-08-01-remote-control-robustness-design.md]] §4.8 — Remote Control を直す作業中に、空きが10分で 9.6GB → 5.4GB へ落ちるのを観測した。

---

## 1. Goal (done 条件)

```
done = 以下がすべて真
  A. 空き容量が 40GB 以上
  B. 消したものが「なぜ安全か」を各件について自分で確認した記録が残っている
  C. 稼働中のもの (colima のワークロード / daily-driver ブラウザ / launchd ループ) を壊していない
  D. 再発防止: 無制限に太るログ/キャッシュに上限が入っている
```

---

## 2. 計測の落とし穴 (先に潰した)

| 罠 | 実際 |
|---|---|
| `du -x` を使う | ★使うな★ `/Users/anicca` は `/System/Volumes/Data` に firmlink されているため、`-x` が境界と誤認して**大半のサブツリーを黙って飛ばす**。`anicca-project` が 21.87GB なのに内訳合計が 4GB にしかならず気付いた |
| `du` をパイプで直接読む | 出力が途中で切られる。**必ずファイルに落としてから読む** |
| `du` の数字 = 実容量と思う | APFS のクローン/スパースは共有ブロック。Chromium `code_sign_clone` は `du` 4.5G だったが削除しても空きは **6GB → 6GB で不変**。colima の `disk`/`datadisk` も見かけ 120G / 実 8.75G |
| APFS ローカルスナップショット | `tmutil listlocalsnapshots /` → **0件**。今回は無関係 |

---

## 3. 実測インベントリ (2026-08-01 18時台)

`du -d2 /Users/anicca` をファイルに落として取得 (1635行)。**`/Users/anicca` 単独で 221.72 GB** = ディスクの中身は実質すべてホーム。

| 場所 | サイズ | 性質 / 一次判断 |
|---|---|---|
| `~/.openclaw` | **27.81 GB** | LIVE runtime。うち `.git` 6.58 / `workspace` 5.94 / `skills` 4.40 / `agents` 3.98 |
| `~/anicca-project` | **21.87 GB** | うち `.worktrees` 12.28 / `.git` 4.85 |
| `~/.cloak` | **17.37 GB** | うち `state-backups` **9.08** / `profiles` 7.67。プロファイルは不可侵、**backups は剪定対象** |
| `~/Library` | 15.35 GB | うち `Application Support` 8.76 |
| `~/Projects` | 15.10 GB | うち `life-manager-main` 5.77 |
| `~/anicca-monk-factory` | 12.84 GB | うち `renders` **11.36** = 動画の出力物、再生成可能 |
| `~/.colima` | 8.75 GB | VM ディスク。稼働中 |
| `~/anicca-rtdash` | 7.87 GB | 不可侵ストア |
| `~/anicca` | 6.50 GB | 母艦 (life-manager) |
| `~/Documents/Codex` | 6.44 GB | |
| `~/clips` | 6.20 GB | 動画クリップ |
| `~/gig` | 4.94 GB | |
| `~/.claude` | 4.43 GB | |
| `~/profitable-claude` | 3.94 GB | |
| `~/.local` | 3.84 GB | |

`.git` の合計だけで **11.4 GB** (`~/.openclaw` 6.58 + `~/anicca-project` 4.85)。

---

## 4. TODO (順序が正本。番号順に着手、飛ばさない)

| # | タスク | 想定回収 | 状態 |
|---|---|---|---|
| 1 | 全体インベントリ | — | **done** (§3) |
| 2 | `.worktrees` — 1件ずつ「merge 済 / 未push commit 無し / 未使用」を確認して削除 | 12.28 GB | **done** — 12.28GB → 3.97GB (§5.2) |
| 3 | `.git` の gc (`~/anicca-project` + `~/.openclaw`) | 11.4 GB のうち一部 | pending |
| 4 | `~/anicca-monk-factory/renders` — 動画出力物、再生成可能 | 11.36 GB | pending |
| 5 | `~/.cloak/state-backups` — 世代を残して剪定 (**profiles には触らない**) | 9.08 GB | pending |
| 6 | colima — 稼働ワークロードを確認 → 不要なら停止・削除 | 8.75 GB | pending |
| 7 | `~/Library/Application Support` の内訳と回収 | 8.76 GB | pending |
| 8 | `~/Documents/Codex` と `~/clips` の精査 | 12.64 GB | pending |
| 9 | `~/.openclaw` の workspace / skills / agents 精査 (**memory と state/*.jsonl は不可侵**) | 14 GB のうち一部 | pending |
| 10 | 再発防止: 無制限に太るログ/キャッシュに上限を入れる | — | pending |

---

## 5. 作業ログ

### 5.2 `.worktrees` 12.28GB → 3.97GB (2026-08-01)

**判定基準を途中で組み直した。** 最初は「未push commit の数」で見ようとしたが、これは誤り:

> **worktree のディレクトリを消しても、branch も commit も親リポジトリの `.git` に残る。**
> 失われるのは **未コミットの変更だけ**。

なので判定軸は「dirty か否か」と「branch ref がその**親リポジトリ**に生きているか」の2つ。

もう1つ罠があった。`.worktrees/` 配下41ディレクトリのうち、`git worktree list`(anicca-project) に出るのは10件だけ。残りは **`~/Projects/life-manager-main` や `~/.cache/codex-repos/life-manager.git` の worktree** が anicca-project の下に置かれていたもの。各ディレクトリの `.git` ファイルの `gitdir:` を読んで**本当の親リポジトリを解決してから** ref の生存を確認する必要があった。

| 段階 | 対象 | 判断根拠 | 回収 |
|---|---|---|---|
| 第1波 | 26件 | dirty=0 かつ branch ref が親リポジトリに存在 | **920 MB** |
| 第2波 | `panel-8d2-zero-temporary-link` / `core-8f-context-onboarding-discovery` / `lm-call-fix` | dirty がそれぞれ**ちょうど1件**で、中身は `?? .codegraph/`(生成インデックス) と `?? .vcsdd/index.json`(VCSDD は HARD RULE 0.37 で永久禁止) のみ。いずれも `origin/dev` に merge 済 | **1,476 MB** |

削除後は各親リポジトリで `git worktree prune` を実行して管理エントリも掃除した。

**保留した12件 (3.97GB)** — 本物の未コミット作業があるため消さない:

| worktree | サイズ | 保留理由 |
|---|---|---|
| `cloud-agent-todo-01` | 799MB | spec 変更 + 未追跡の調査成果物 (inventory/manifest) |
| `anicca-gig-ifu-v4-run41` | 639MB | `shuppin.jsonl` 変更 + `evidence/gig-79670-B2/` |
| `shelter-nosana-independence` | 457MB | nosana bridge の実装/テストに変更 |
| `sol-panel-8h-ux-privacy` | 454MB | panel-api 実装/テストに変更 |
| `lm-p0-order8d` | 453MB | daily-preflight 実装に変更 |
| `perxona-life-manager` | 452MB | life-call の実装追加 |
| `release-1.9.5` | 451MB | **memory `feedback_worktrees_release195_agent_economy_are_active` により現役** |
| `steel-browser-ephemeral` | 207MB | worktree ではなく独立 clone。別途判定が要る |
| 他4件 | 小 | 未コミットあり / 壊れた worktree |

→ これらは「WIP を branch に commit してから消す」のが正しい手だが、**他エージェントの作業を勝手に commit するのは避ける**。別タスクとして残す。
