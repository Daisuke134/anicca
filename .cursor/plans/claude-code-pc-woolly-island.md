# Claude Code セットアップ監査 — 診断レポート & 最適化プラン

**日付**: 2026-07-03 / **範囲**: ~/直下2階層 + Claude設定深掘り + runtime構造のみ / **方式**: read-only（変更ゼロ）

## Context

Claude Code 環境（PC全体のディレクトリ構造 + ~/.claude + プロジェクト設定）を監査し、コンテキスト効率・安全性・保守性を最大化する再構成プランを作る。診断で判明した核心: **①ディスク92%逼迫 ②毎セッション約70KB超の常時ロード（CLAUDE.md 肥大） ③skills 226+473の三重管理と43件の名前衝突 ④`rm -rf` グローバル許可 + deny/ask ゼロ ⑤平文シークレットが設定・メモリに散在 ⑥MCP定義が3ファイルに分散 ⑦git repo が8箇所以上に無秩序分散**。

---

## 1. 現状マップ

### 1a. PC全体（ホーム直下）

```
/Users/anicca/  ← 可視 dir 約80 + ドット dir 100超 + 散在ファイル多数
├── anicca-project/   5.8G  ★メイン開発 repo（正）
├── anicca/           975M  ★OSS framework（正）… anicca-oss は同実体への symlink
├── anicca-monk-factory/ 7.4G / anicca-rtdash/ 3.1G / anicca-human-funded/ 1.5G
├── anicca-* 系が計25個（agent/blog/content/core/earn/products/swarm/x402-deploy…）
├── .openclaw/ ★LIVE runtime（cron 221 / skills 473）… .openclaw-{backups,gog,wt} + openclawnch が併存
├── .claude/          4.2G  （projects/ 2.6G = 502セッションログ, skills/ 711M, security/ 661M）
├── .cache/           7.5G  （anicca-worktrees 691M + anicca-clones 425M 残骸）
├── .cloak/ 3.8G / .colima/ 2.0G / .codex/ 463M / .agent-browser/ 682M …
├── Desktop/          183エントリ（ファイル143）★最散乱
├── Downloads/ 36 / Documents/ 4（ほぼ空、git repo 転用）
├── Developer/  … git repo 5個 / work/ 2個 / tools/ 2個
└── 直下散在ファイル: *.mp4 31M, picks.json, cron_jobs.txt, wake_log.txt, .zshrc.bak-*…
```

- **git repo 計43箇所、置き場8系統に分散**（~直下 / .dot内 / Developer / Documents / work / tools / ネスト repo）
- **同名 repo の重複 clone**: `camofox-browser`（~/Developer と ~/work）、`video-use`（~/Developer と ~/anicca-video-lab）
- **ディスク: 228Gi 中 181Gi 使用（92%）、残 16Gi** — HARD RULE 0.26 の警戒水準（<10GB）目前
- ~/.hermes は**存在しない**（CLAUDE.md のアーキ図と乖離 — ドキュメント側が古い）

### 1b. Claude Code 設定の所在

| 層 | 場所 | 実態 |
|---|---|---|
| user CLAUDE.md | `~/.claude/CLAUDE.md` 18KB/159行 + `@RTK.md` 1KB | HARD RULE 集。VSDD全仕様転記・DISK HYGIENE手続き・FUNDER APPLY(トリガー型)混入 |
| user rules | `~/.claude/rules/` 4本 28KB | 参照ドキュメント（自動ロードなし、良好） |
| user skills | `~/.claude/skills/` **226エントリ** 711MB | 実体+symlink混在。SKILL.md 欠落10 / description 空・折返し20+ |
| user commands | `~/.claude/commands/` **12本 残存** | skills 未移行。`frontend-design` は command+skill+plugin の三重定義 |
| user agents | `~/.claude/agents/` **不在** | グローバル agent ゼロ（vcsdd 系は plugin 供給） |
| user settings | `settings.json` + `.local` + **.bak ×2** | hooks 5種（rtk wrapper / ssot-guard×2 / post-edit / Stop block）。permissions: **allow に `rm -rf:*`、deny/ask 空、`skipDangerousModePermissionPrompt: true`** |
| user MCP | **3ファイルに分散**: settings.json(2) + `~/.claude/mcp.json`(6) + レガシー `~/.claude.json`(8) | 平文キー: Google API / Slack xoxb / ElevenLabs sk_ / ASC。`store-screenshot` が `/tmp` 参照。`x-search` は memory 上「DEAD」、`computer-use` は memory 上「永久禁止」なのに残存 |
| memory | `~/.claude/projects/.../memory/` **307ファイル** | ⚠️ 銀行カード・API 認証情報の平文ファイル多数。MEMORY.md.bak ×2 残存 |
| project CLAUDE.md | `~/anicca-project/CLAUDE.md` **49KB/537行** | HARD RULE 群 + アーキ図 + 手順書が混在。global と重複記述多数 |
| project .claude | settings.json（hooks 9種 = 全スクリプト実在確認済✅）+ rules 8本 + skills **226エントリ** + agents 11（.cursor/agents へ symlink） | `model: claude-opus-4-8` を pin（/model の Fable 5 保存と衝突 → 再起動で Opus に戻る） |
| project .mcp.json | 9サーバー | serena/context7/apple-docs/maestro 等、妥当 |
| .agents/skills | **166 dir、うち75 が untracked** | `.claude/skills` symlink の実体格納庫。git status 166件汚染の主因 |
| plugins | 11有効/12installed、marketplace 8 | superpowers / vcsdd / agent-skills / token-saver 等 |
| runtime | `~/.openclaw` skills 473 / cron 221。`.claude/skills` と **43件名前衝突** | jobs.json.bak 6世代+ 堆積 |

### 1c. 毎セッションの常時ロード（コンテキスト税）

user CLAUDE.md 18K + RTK 1K + project CLAUDE.md 49K + project rules 6本 + hooks 注入（SSOT guard ×2重発火 + session architecture + git snapshot + superpowers 全文）+ **skills 一覧数百件（global と project で同一 skill が二重掲載）** ≈ 体感で **セッション開始時に数万トークン**。ここが最大の恒常コスト。

---

## 2. 問題点マトリクス（影響度 × 工数）

| # | 問題 | 影響度 | 工数 | 優先 |
|---|---|---|---|---|
| P1 | ディスク92%（残16Gi）。~/.cache 残骸1.1G、.claude/projects 2.6G、file-history 118M | ★★★ セッション停止リスク(ENOSPC前科) | 小 | **即** |
| P2 | permissions: `rm -rf:*` allow + deny/ask ゼロ + dangerous-mode prompt skip | ★★★ 誤爆で取返し不能 | 小 | **即** |
| P3 | 平文シークレット（settings/mcp.json/memory 307中の credentials 群）— これらのファイルの一部は git 管理下 repo に隣接 | ★★★ 漏洩 | 中 | **即** |
| P4 | skills 過密: 226(user)+226(project、実体は.agents 166)+473(openclaw)、43衝突、SKILL.md欠落10、description不備20+ | ★★★ 誤発火・未発火 + 毎セッションの一覧トークン税 | 中 | 高 |
| P5 | CLAUDE.md 肥大（18K+49K）+「3箇所同期」設計 = ドリフト実証済（例: 0.30「camofox 最優先」vs memory「CloakBrowser 既定・camofox 使うな」が矛盾共存 / ~/.hermes 記述 vs 実体不在） | ★★★ 毎ターン全額課金 + 指示矛盾 | 中 | 高 |
| P6 | MCP 3ファイル分散 + 死んだ/禁止サーバー残存（x-search, computer-use）+ /tmp 参照 | ★★ ツール一覧肥大・不整合 | 小 | 高 |
| P7 | git 未コミット166件（.agents/skills 75 untracked）= HARD 0.00 違反状態が恒常化 | ★★ conflict 蓄積 | 小 | 高 |
| P8 | repo 8箇所分散・重複 clone・anicca-* 25個・Desktop 183 | ★★ 認知負荷・重複作業 | 大 | 中 |
| P9 | commands/ 12本未移行 + frontend-design 三重定義 | ★ 発火の不確定性 | 小 | 中 |
| P10 | model pin 衝突（project settings=opus-4-8 vs /model=Fable5）+ agents の tools/model 未指定3件 | ★ 意図しないモデルで実行 | 小 | 中 |
| P11 | .bak 堆積（settings.json.bak×2, MEMORY.md.bak×2, jobs.json.bak 6世代, .zshrc.bak） | ★ ノイズ | 小 | 低 |
| P12 | hooks 二重発火（global ssot-guard と project session-start が同種の注入を両方実施） | ★ 起動コンテキスト増 | 小 | 低 |

---

## 3. 理想の最適構成案

### 3a. PC全体の理想ディレクトリ構成

**大原則: 稼働中の canonical 4 path（`~/anicca-project` `~/anicca` `~/.openclaw` `~/.claude`）は動かさない。** CLAUDE.md・cron 221本・`~/.claude.json` の123プロジェクト登録が絶対パスで参照しており、移動は大規模破壊になる。移動対象は「それ以外」のみ。

```
/Users/anicca/
├── anicca-project/          # 変更なし（canonical）
├── anicca/                  # 変更なし（canonical）
├── .openclaw/ .claude/ 等   # 変更なし（runtime/設定）
├── Projects/                # ★新設: 上記以外の全アクティブ repo の唯一の置き場
│   ├── (Developer/, work/, tools/, Documents/ から移設)
│   └── forks/               # 外部 clone（camofox-browser 等は1本化）
├── Archive/                 # ★新設: 非稼働 repo・完了プロジェクト
│   └── (anicca-* 25個のうち非稼働分, MoneyPrinterV2, sutando, …)
├── Desktop/                 # 目標 <10 エントリ（内容物は Archive or Projects へ）
├── Documents/ Downloads/    # repo 置き場として使わない
└── (直下散在ファイル → Archive/loose-files/ or 削除)
```

**命名規則**: repo 名は `<product>-<domain>`（現行 anicca-* 踏襲）。バックアップ dir は作らない（git history が backup）。ワークツリーは `~/.cache/anicca-worktrees/` に一本化し `anicca-wt/` は廃止。

**移動マッピング（代表）**:
| 現在地 | 行き先 | 判定基準 |
|---|---|---|
| ~/Developer/*, ~/work/*, ~/tools/*, ~/Documents/youtube-auto-agent | ~/Projects/ | 直近90日 commit あり → Projects、なし → Archive |
| camofox-browser ×2, video-use ×2 | 1本だけ Projects/forks/ に残し他は削除 | remote 同一確認後 |
| 非稼働 anicca-*（cron/CLAUDE.md から参照されないもの） | ~/Archive/ | `grep -r <dir名> ~/.openclaw/cron/jobs.json ~/.claude` で参照ゼロ確認後 |
| Desktop 183エントリ | 種別ごとに Projects / Archive / 削除 | |

### 3b. Claude Code の最適構成

**振り分け原則**: 常時必要=CLAUDE.md / 手続き=skill / 強制=hook・permissions / 隔離=subagent。

```
~/.claude/
├── CLAUDE.md            # ≤6KB 目標。残すのは「常時原則」のみ:
│                        #   META-RULE(search-first) / 0.00(push) / 0.33(no-ask) /
│                        #   0.36(no-human-loop) / 0.37は3行要約+skill参照 / 0.40同
│                        # 追い出すもの:
│                        #   VSDD全仕様転記 → vcsdd plugin doc が canonical(削除)
│                        #   0.26 DISK HYGIENE 手順 → hook 化(下記)+rules/
│                        #   0.24 / 0.27 詳細 → memory 参照1行に圧縮
│                        #   RTK.md @import → PreToolUse hook が既に強制、参照1行に
│                        # 「3箇所同期」廃止 → canonical 1箇所 + 他は [[link]] のみ
├── rules/               # 現4本は妥当。CLAUDE.md から出した手続きを追加
├── skills/              # 226 → 60前後に厳選（§4 Phase 4）
├── agents/              # ★新設: fact-checker 等プロジェクト横断のものを昇格
│                        #   （read-only tools 明記 + model: sonnet/haiku 明記）
├── commands/            # 廃止（12本を skills へ移行 or 削除）
├── settings.json        # permissions 再設計:
│                        #   allow: rm は ~/.cache/anicca-*, DerivedData 等の掃除対象パスに限定
│                        #   deny:  Read(.env*), Read(**/credentials*), Bash(git push --force:*)
│                        #   ask:   Bash(rm -rf:*)(汎用形)
│                        #   skipDangerousModePermissionPrompt → false
│                        # mcpServers → mcp.json へ一本化して削除
└── mcp.json             # MCP の唯一の置き場。x-search / computer-use / 死候補を削除、
                         #   secrets は env 参照化、store-screenshot の /tmp を恒久パスへ
```

```
~/anicca-project/
├── CLAUDE.md            # ≤15KB 目標。残す: repo 固有(push先マップ/ブランチ運用/
│                        #   ツール優先順位/実行環境/アーキ図の最新版)
│                        # 追い出す: global と重複する HARD RULE 群(参照1行に)、
│                        #   HONESTY/VERIFICATION 詳細(rules/verification.md へ)、
│                        #   TIER A / 旧アーキ記述(~/.hermes 等)は削除 or memory
├── .claude/
│   ├── settings.json    # model pin 見直し(Fable運用なら pin 削除 or fable 指定)
│   ├── rules/           # 現8本維持
│   ├── skills/          # ★project 固有のみ(asc-*/maestro/fastlane 系)。
│   │                    #   汎用 skill の symlink 重複掲載をやめ global に寄せる
│   ├── agents/          # 11本の frontmatter 補完(tools/model 未指定3件)。
│   │                    #   reviewer/auditor 系は read-only tools に制限
│   └── hooks/           # 現9種維持 + disk-guard を SessionStart に追加
│                        #   (df -h チェック → <10GB で警告注入 = 0.26 の hook 化)
└── .agents/skills/      # 実体格納庫として維持。ただし git 方針を確定:
                         #   コミットする(推奨: skill は資産) or .gitignore
```

**skills 三重管理の解消方針**: `.claude/skills`(user) = 汎用、`anicca-project/.claude/skills` = repo 固有のみ、`~/.openclaw/skills` = runtime 専用（Claude Code 側から symlink しない。既存 `mau-tiktok` symlink は例外として明示）。43件の名前衝突は「どちらが新しいか」を diff で確定し片側を削除。

**モデル運用**:
| 用途 | モデル |
|---|---|
| main での計画・設計・レビュー | Fable 5（現行） |
| SubTask 実行系（大量編集・調査） | sonnet 明示 |
| deploy-checker 等の定型チェック | haiku（既存設定どおり） |
| vcsdd-adversary | opus（plugin 既定どおり、maker≠checker のモデル分離維持） |

**コンテキスト効率**: 最大のレバーは (1) skills 一覧の削減（毎セッションの system prompt を直接縮める） (2) CLAUDE.md diet (67KB→21KB 目標) (3) /compact はコミット直後のみ（既存 0.8 どおり）。

### 3c. 日々の活用改善（反復作業の自動化先）

| 反復作業 | 移行先 |
|---|---|
| ディスク監視（0.26 の手動チェック） | SessionStart hook（df + 閾値警告） |
| 「push しろ」の徹底 | 既に lefthook + Stop hook あり → CLAUDE.md の該当長文は要約に縮小可 |
| MEMORY.md / spec の3箇所同期 | 廃止 → canonical 1箇所 + リンク |
| セッションログ肥大 | 定期 cron（openclaw 側）で `~/.claude/projects` の90日超 jsonl をアーカイブ |
| jobs.json.bak 世代管理 | git 管理（~/.openclaw は repo）に任せ .bak 生成をやめる |

---

## 4. 段階的実行プラン（承認後に着手。各 Phase 完了ごとに commit+push）

### Phase 0 — 事前保全（非破壊、~30分）
1. `~/.claude` の設定ファイル群（settings/mcp/CLAUDE.md/rules）を Archive 用に 1 tarball でバックアップ（`~/Archive/claude-config-backup-YYYYMMDD.tgz`）
2. anicca-project の untracked 166件を triage: `.agents/skills` を commit するか `.gitignore` するか確定 → 実行 → push（P7 解消）
3. 重複 clone（camofox-browser/video-use）の remote・HEAD を比較して「残す側」を記録

### Phase 1 — ディスク救急（破壊的、順序厳守、~1時間で約4-5GB回収）
実行順序: **必ず「参照確認 → 削除」の順**。
1. `~/.cache/anicca-clones/` 425M — 参照なし前提のキャッシュ → 削除
2. `~/.cache/anicca-worktrees/` 691M — `git worktree list` を各 repo で確認し、登録済 worktree は `git worktree remove`、残骸は削除
3. `~/.claude/file-history/` 118M、`paste-cache/` — 削除
4. `~/.claude/projects/` 2.6G — 90日超のセッション jsonl をアーカイブ tarball 化して外部へ or 削除（memory/ サブディレクトリは**絶対に対象外**）
5. `/tmp/anicca-*` ログ・ソケット残骸 — 削除
6. `.colima` 2.0G — Docker 利用状況を確認し、未使用なら `colima delete`（要確認事項として保留可）
7. 完了後 `df -h /` で残量20GB+ を確認

### Phase 2 — 安全性（~1時間）
1. permissions 再設計（§3b のとおり）: `rm -rf:*` allow を掃除パス限定 allow + 汎用 ask に変更、deny 追加、`skipDangerousModePermissionPrompt: false`
2. シークレット退避: mcp.json / settings.json の平文キーを env 参照（`~/.openclaw/.env` 集約）に書換え → **書換え後、露出済みキー（Google API / Slack / ElevenLabs）をローテーション**
3. memory/ の credentials 系ファイル: 中身を `~/.openclaw/.env` へ移し、memory 側は「所在ポインタのみ」に書換え
4. MCP 一本化: `~/.claude/mcp.json` に統合、settings.json の mcpServers 削除、`~/.claude.json` レガシー8件から生存確認できたものだけ移行。x-search（DEAD 実証済）/ computer-use（memory で永久禁止）を削除。store-screenshot の `/tmp` パスを恒久化

### Phase 3 — CLAUDE.md diet（~2時間）
1. global CLAUDE.md 18K→6K（§3b の残す/出すリストどおり）。出した内容は rules/ または既存 memory への参照1行に
2. project CLAUDE.md 49K→15K。global と重複する HARD RULE は削除し「global 参照」1行に。~/.hermes 等の死んだアーキ記述を現状（openclaw のみ稼働）に更新
3. 「3箇所同期」条項を「canonical 1箇所 + [[link]]」に全面改訂
4. 矛盾解消: 0.30 ブラウザ順序を memory の最新（CloakBrowser daily-driver 既定）に合わせて改訂
5. 変更ごとに commit+push、diet 後に新セッションを起動して起動コンテキストの体感差を確認

### Phase 4 — skills 大掃除（~3時間、段階可）
1. SKILL.md 欠落10件: 修復 or `_archive` へ
2. description 空/折返し20+件: 1行 description を frontmatter に補完（発火精度の直接改善）
3. クラスタ統合: hyperframes×7→1（サブコマンド化）、tiktok×4→2、X/Twitter×5→2、design 系12→3-4、spec 系7→2-3、substack×2→1、stop-slop 系3→2（EN/JP）
4. 43件の user/openclaw 名前衝突: diff で新しい側を残す
5. commands/ 12本: 使用中のものを skills 化、残りは削除。frontend-design 三重定義は plugin 版を正として他を削除
6. project `.claude/skills` から汎用 symlink を撤去（global に一本化）
7. 完了後、新セッションで skill 一覧の重複掲載が消えたことを確認

### Phase 5 — PC 構造再編（~2-3時間、破壊的移動あり）
1. `~/Projects/` `~/Archive/` を作成
2. **移動前に必ず**: 対象 dir 名で `~/.openclaw/cron/jobs.json`・`~/.claude.json`・シェル設定を grep し参照ゼロを確認。参照があるものは移動しない
3. Developer/work/tools/Documents の repo → Projects/（git status clean を確認してから mv）
4. 非稼働 anicca-* → Archive/。重複 clone の非正側を削除
5. Desktop 183 → 種別仕分け（目標 <10）。直下散在ファイル → Archive/loose-files/
6. .bak 堆積（settings.json.bak×2 / MEMORY.md.bak×2 / .zshrc.bak / jobs.json.bak 6世代）を削除

### Phase 6 — 運用定着（~1時間）
1. project settings.json の model pin を運用方針（Fable main + sonnet SubTask）に合わせ整理
2. agents 11本の frontmatter 補完（tools/model 未指定3件、reviewer 系の read-only 化）
3. disk-guard hook を SessionStart に追加（0.26 の自動化）
4. セッションログの定期アーカイブ cron を ~/.openclaw/cron に追加
5. global `~/.claude/agents/` に fact-checker を昇格（全プロジェクトで利用可に）

## 検証方法
- 各 Phase 後: `df -h /`（Phase 1）、新セッション起動して起動注入量と skill 一覧を目視（Phase 3/4）、`claude doctor` 相当の設定読込エラーゼロ確認、既存 hook（post-edit-verify 等）が発火することを 1 edit で確認
- Phase 2 後: ローテーション済みキーで各 MCP が接続できることを 1 コールずつ確認
- Phase 5 後: `~/.openclaw` の cron が翌サイクル正常発火していることをログで確認
