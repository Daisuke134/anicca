# Disk 恒久管理 — OSS 採用決定（2026-07-11、実 gh/repo 調査）

## 根本原因（実測確定）
- `~/.openclaw/.git` = 2.0GB。**state/*.jsonl + logs/**/*.log を 207ファイル git 追跡**していた = ~2GB/日成長の正体。append-only ledger を毎 pass commit していた。
- 0GB 事故の第2因子: claudevm.bundle 6.8G（Cowork VM が再生成する既知の disk eater）が自動回収対象外だった。

## 2軸の OSS 調査結論（車輪の再発明禁止）

### AXIS 1: macOS 自動 cleanup / 低容量 watcher
- **「free < N GB で自動発火する watcher」の OSS は存在しない**（dead/toy repo のみ）→ 我々の emergency-disk-guard（毎分 launchd + 閾値）は正しい novel piece、再発明ではない
- cleanup **エンジン**は採用: **`2ykwang/mac-cleanup-go`**（434★, MIT, 2026-07-09 最活発, `--clean --dry-run` の非対話 CLI = launchd 向き, impact level safe/moderate/risky/manual で risky 既定除外・SIP 保護自動除外）→ 我々の protect list（.env/state/ledger/model-cache）と衝突しない
- 診断は **`dundee/gdu`**（5799★, `-n -t 20 -o json` で最大 reclaimable dir を機械可読出力）→ guard が「今何が食ってるか」を先に見て動く
- 参考: mac-cleanup-py(2371★, 手動のみ) / dust(11965★, 対話向き) / erdtree(stale)

### AXIS 2: git repo 肥大（~2GB/日）
- 出典 github/git-sizer README:「Avoid storing log files and database dumps in Git... regenerate or store in a package registry/fileserver」= まさに state/*.jsonl + logs のケース
- **恒久解 = 削除でなく untrack**（memory の `**/state/*.jsonl` 不可侵 = ファイルは消さない、と両立）:
  1. `.gitignore` に `logs/**/*.log` `**/state/*.jsonl` `state/**/*.jsonl`（← 旧 ignore は直下 log しか効かず subdir が漏れていた）
  2. `git rm -r --cached <207 files>` → commit（✅ 2026-07-11 実施、`b6e6b370`、ファイル残存確認済み）
  3. 履歴圧縮（既に .git に baked の 2GB）= `git filter-repo --path state --path logs --invert-paths` or bfg → **disk headroom 確保後に実施**（今 free 2GB で gc すら失敗するデッドロック）
- forward: runtime state は repo working tree の外（例 `~/.openclaw-state/`）へ、が標準の「code は git・state は外」分離。パッケージ化 OSS は無い＝ .gitignore 規律

## 実施状況（2026-07-11）
- ✅ claudevm 6.8G + whisper 削除（0→2GB）
- ✅ emergency-disk-guard（毎分 launchd、free<4GB で積極 sweep、LLM 0、lock 付き）
- ✅ ~/.openclaw の state/log を untrack（成長停止、`b6e6b370`）
- ⬜ mac-cleanup-go + gdu を brew install → guard に配線（診断=gdu、実掃除=mac-cleanup-go safe tier）
- ⬜ ~/.openclaw/.git 履歴圧縮（filter-repo、headroom 後）
