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
| 3 | `.git` の gc (4リポジトリ) | 425 MB | **done** (§5.3) |
| 4 | `~/anicca-monk-factory/renders` — 動画の中間生成物 | **9.0 GB** | **done** 11.36GB → 2.36GB (§5.4) |
| 5 | `~/.cloak/state-backups` — 世代を残して剪定 (**profiles には触らない**) | 2.4 GB | **done** 7世代 → 3世代 (§5.5) |
| 6 | colima — 稼働ワークロードの確認 | 0 | **done — 消さない判断** (§5.6) |
| 7 | `~/Documents/Codex` の重複 clone | **6.3 GB** | **done** 6.44GB → 63MB (§5.7) |
| 8 | `~/clips` の投稿済み/却下分 | 3.5 GB | **done** 6.20GB → 2.73GB (§5.8) |
| 9 | `~/Projects` の worktree と動画出力 | 2.4 GB | **done** (§5.8) |
| 10 | `~/.openclaw/workspace/runs` の古い run | 1.1 GB | **done** 106件削除 (§5.8) |
| 11 | orca の Codex セッション履歴 (14日超) | 0.3 GB | **done** (§5.8) |
| 12 | 再発防止: 無制限に太るログ/キャッシュに上限を入れる | — | pending |
| 13 | 保留中の worktree 12件 (3.97GB) — WIP を commit してから削除 | 3.97 GB | pending |

### 現在地

```
空き容量:  7.1 GB (セッション開始時)  →  22.2 GB   (+15.1 GB)
```

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

### 5.3 `git gc` 4リポジトリ — 425 MB

| repo | before | after |
|---|---|---|
| `~/anicca-project` | 2481MB | 2451MB |
| `~/.openclaw` | 3368MB | 2994MB |
| `~/Projects/life-manager-main` | 1537MB | 1520MB |
| `~/anicca` | 1328MB | 1324MB |

回収は小さい。**これらの `.git` が大きいのはゴミではなく本物の履歴**だという結論。`--aggressive` は時間対効果が悪いので回していない。

### 5.4 `anicca-monk-factory/renders` 11.36GB → 2.36GB

`~/anicca-monk-factory` 自体は不可侵ストアだが、`renders/` の中身は1本ごとの**中間生成物** (`clip_01..13.mp4` + `concat.mp4`)。最終成果物は配信済みで、古いディレクトリは既に空だった。`ffmpeg`/render プロセスが動いていないことを確認してから、**7日より古い170件を削除**。

### 5.5 `~/.cloak/state-backups` 7世代 → 3世代

`claude-projects` と `creds` の日次バックアップが7世代 (各 536〜801MB)。**`~/.cloak/profiles` (Dais がログイン済みの forever ブラウザ) には一切触っていない。** 直近3世代 (07-30/07-31/08-01) を残して古い4世代を剪定。

### 5.6 colima — 消さない判断

`docker ps` で中身を確認したところ、**life-manager のローカル本番スタックが25時間 healthy で稼働中**:

```
life-manager-local-api-1        Up 25 hours (healthy)
life-manager-local-scheduler-1  Up 25 hours (healthy)
life-manager-local-worker-1     Up About an hour (healthy)
life-manager-local-postgres-1   Up 25 hours (healthy)
life-manager-local-object-store-1  Up 25 hours (healthy)  (minio)
```

→ **停止・削除しない。** `docker system df` は 1.983GB を reclaimable と表示するが、その実体は `openclaw-sandbox:bookworm-slim` と `debian:bookworm-slim` — オンデマンドで必要になるタグ付きイメージなので残す。dangling は0で、prune の回収は 28.67kB だった。

なお **VM 内で消してもホスト側のスパースディスクは自動では縮まない**ので、ここは元々ホスト空き容量に効きにくい。

### 5.7 `~/Documents/Codex` 6.44GB → 63MB — 今日の出血源

今日 (08-01) だけで 6.32GB。中身は Codex セッションのワークスペース `let-s-download-a-folder-depositories/repositories/` で、**4つの repo を clone したもの**:

| repo | サイズ | 状態 |
|---|---|---|
| `Daisuke134/life-manager` | 2655MB | clean。**`~/anicca` と `~/Projects/life-manager-main` に続く3個目の重複コピー** |
| `langchain-ai/openwiki` | 476MB | clean |
| `StarTrail-org/PixelRAG` | 67MB | clean |
| `humanlayer/advanced-context-engineering-for-coding-agents` | 36MB | clean |

全て dirty=0 かつ remote 付き = **ローカル作業ゼロ、いつでも再取得可能**。HARD RULE #-1.5 (「download = clone ではなく README を読んでセットアップ」) が禁じている行動の産物そのもの。削除。

### 5.8 その他

| 対象 | 判断根拠 | 回収 |
|---|---|---|
| `~/clips/posted` `~/clips/flagged` | 投稿済み / 却下済み。`queue` (86件・未投稿) と `queue-franklin` `queue-clawrouter` は**残す** | 3.47 GB |
| `~/Projects/anicha-video/out` `out_v3` | 動画のレンダリング出力。再生成可能 | 2.22 GB |
| `~/Projects/.worktrees/life-manager/` 2件 | dirty=0 + ref 生存。**`taskmarket-work-loop` は LaunchAgent から参照されている稼働ディレクトリなので残した** | 0.21 GB |
| `~/.openclaw/workspace/runs` 106件 | 名前に日付を持つ run 成果物。7日より前を削除 (`mtime` は全件が新しく出るため**ディレクトリ名の日付で判定**) | 1.07 GB |
| orca の Codex セッション履歴 | `sessions/2026/{03,04,05,06}` と `07/01..17` を削除。直近14日は残す | 0.32 GB |

**触らなかったもの (理由つき)**:

| 対象 | サイズ | 理由 |
|---|---|---|
| `~/.cloak/profiles` | 7.67 GB | HARD RULE 0.39 — Dais がログイン済みの forever ブラウザ |
| `~/anicca-rtdash` | 7.87 GB | 不可侵ストア |
| `~/profitable-claude/skills/bounty-hunter/state` | 1.21 GB | `**/state/` は不可侵。gig loop は稼働中 |
| `~/gig/projects` | 2.60 GB | LaunchAgent から参照あり |
| `~/Projects/.worktrees/life-manager/taskmarket-work-loop` | 1.07 GB | LaunchAgent から参照あり |
| colima の VM ディスク | 4.5 GB | life-manager 本番スタックが稼働中 |
