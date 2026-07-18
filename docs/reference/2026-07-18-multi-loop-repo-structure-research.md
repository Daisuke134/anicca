# 複数自律 agent loop を 1 OSS repo でホストするフォルダ構成 best practice

調査日: 2026-07-18 / 対象 repo: `~/profitable-claude`（human-funded Claude-P loops）
結論の要旨: **新しい構成を発明しない。`profitable-claude` が既に体現している「skills/<name>/ 自己完結 dir + 1 本の loop 台帳 JSON + deny-by-default gitignore + install-relative launchd」を勝者パターンとして丸ごと踏襲し、実測で見つかった 2 つの不整合（launchd の置き場、state の置き場）を「1 規約に統一」して塞ぐ。** 発明ではなく、既存実例（Anthropic 公式 + OpenClaw + 自 repo）から共通パターンを copy する。

---

## TL;DR — 推奨構成 tree

```
profitable-claude/
├── README.md                    # 導線 + loop 台帳の人間可読ミラー（表）
├── CLAUDE.md                    # repo 固有ルールのみ（参照1行主義）
├── install.sh                   # install-relative に launchd を生成/bootstrap（path hardcode 禁止）
├── .env.example                 # 全 loop が読む env の唯一のカタログ（実値は commit しない）
├── .gitignore                   # deny-by-default（`*` + `!` allowlist）
├── config/
│   └── loop-registry.json       # ★唯一の loop 台帳（SSOT）: 名前/skill_dir/status/cadence/evidence_path/健康確認
├── bin/                         # 全 loop 横断のオーケストレータ（loop 自身のロジックは入れない）
│   ├── start-all.sh             #   registry を読んで live loop を起動
│   ├── status.sh                #   registry を読んで各 loop の健康を集計
│   └── ceo-run.sh               #   横断の予算/評価パス（= orchestrator 専用 loop）
├── launchd/                     # ★横断オーケストレータの plist だけ（ceo-runner 等）
│   ├── ai.anicca.ceo-runner.plist
│   └── ai.anicca.ceo-weekly-eval.plist
├── skills/
│   ├── README.md                # skills カタログ（索引）
│   ├── <loop-name>/             # ★1 loop = 1 自己完結 dir（copy/削除で 1 loop 丸ごと着脱）
│   │   ├── SKILL.md             #   何をする loop か（Anthropic skill 仕様準拠）
│   │   ├── <name>-cli.sh        #   起動/再起動エントリ（start-all がこの名前を叩く）
│   │   ├── <name>-healthcheck.sh#   健康確認（registry の健康確認コマンド欄が指す）
│   │   ├── run.sh               #   1 pass の本体（loop がやる、orchestrator はやらない）
│   │   ├── launchd/             #   ★この loop の plist はここ（core-healthcheck / auditor）
│   │   ├── scripts/             #   補助スクリプト
│   │   ├── __tests__/           #   この loop の negative test
│   │   ├── references/          #   RUNBOOK / strategy.default.json 等
│   │   └── state/               #   実行時 state（gitignore 対象、path だけ registry が契約）
│   └── ...
├── ledgers/                     # 横断 CEO 台帳（jsonl、gitignore 対象、path だけ tracked）
├── lib/                         # 共有 python/bash（registry enforce, budget 等）
├── tests/                       # 横断テスト（run-all.sh）
└── docs/                        # spec / STATUS（会話は揮発、file は不揮発）
```

**契約は 3 本の柱で担保する:**
1. `config/loop-registry.json` = 全 loop の SSOT 台帳（下記 §推奨の根拠 参照）。
2. `skills/<name>/` = 自己完結。plist も state も test もその dir に同居。`bin/`・`launchd/` 直下は横断 orchestrator だけ。
3. state/秘密は **repo に path 契約だけ書き、実データは gitignore で締め出す**（deny-by-default allowlist）。

---

## 実例ごとの観察（引用付き）

### 実例1: Anthropic 公式 `anthropics/skills`（skill 自己完結 + マニフェスト台帳）

- **各 skill は完全自己完結 dir**。`skills/algorithmic-art/` の中身は `SKILL.md` + `templates/` + `LICENSE.txt` だけで、外部 dir に依存しない（実測: `gh api repos/anthropics/skills/git/trees/main?recursive=1`、17 skills 全て `skills/<name>/SKILL.md` 形）。
- **マニフェスト = 1 本の JSON がコンポーネントを path で列挙する**。`.claude-plugin/marketplace.json` が各 skill を `"./skills/xlsx"` のように列挙。
  > 引用（anthropics/skills, `.claude-plugin/marketplace.json`, github.com/anthropics/skills）: `"plugins":[{"name":"document-skills",...,"skills":["./skills/xlsx","./skills/docx","./skills/pptx","./skills/pdf"]}]`
  → 核心: **「repo 直下に置いた 1 本のマニフェストが、path でコンポーネントを列挙する」** のが Anthropic 公式の台帳方式。`loop-registry.json` はこの loop 版。
- 他に `template/SKILL.md`（新規 skill の雛形）と `spec/agent-skills-spec.md`（仕様）を repo 直下に持つ = **「1 コンポーネントの作り方」を repo 自身が抱える**。

### 実例2: `openclaw/openclaw`（383k★、常駐 agent runtime monorepo）

- **top-level を「役割」で切る**（実測: `gh api repos/openclaw/openclaw/git/trees/HEAD`）:
  `skills/` `config/` `deploy/` `scripts/` `packages/` `src/` `docs/` `test/` `.agents/` + repo 直下に `.env.example` `taxonomy.yaml`。
- **skill は `skills/<name>/{SKILL.md, references/}` で自己完結**（実測: `skills/1password/` = `SKILL.md` + `references/`）。anthropics/skills と同一形。
- **repo 直下に台帳 YAML を 1 本持つ**。`taxonomy.yaml` が全サブシステムを id で列挙し成熟度をスコアする。
  > 引用（openclaw/openclaw, `taxonomy.yaml`, github.com/openclaw/openclaw）: `version: 1 / title: Maturity scorecard / summary: Draft maturity scorecard model for OpenClaw subsystems, features, apps, and platforms.` + `categoryIds:` に `agent-runtime-and-provider-execution.model-and-runtime-selection` 等を列挙。
  → 核心: **「多数のコンポーネントを抱える repo は、直下に 1 本の台帳（列挙 + 状態）を置く」**。loop-registry.json と同じ思想。
- `.env.example` を直下に持ち実 secret は追わない（deny 系 gitignore）。

### 実例3: `VoltAgent/awesome-openclaw-skills`（51k★、skills カタログ repo）

- **索引をカテゴリ別 md ファイルで持つ**（実測: `categories/ai-and-llms.md` `browser-and-automation.md` `calendar-and-scheduling.md` … 20+ ファイル）。
  → 核心: **多数コンポーネントの「導線」は、README 1 枚に詰め込まず category 別 index に分割**してよい。loop 数が README の 1 表を超えたらこの手を採る。

### 実例4（ローカル・本命）: `~/profitable-claude`（human-funded loops の現状）

- **loop は `skills/<name>/` に自己完結**。`skills/connector/` は `connector-cli.sh` `connector-healthcheck.sh` `state/` `.vcsdd/` `evidence/` + 多数の py を 1 dir に同居（実測: `find skills/connector`）。gig skill（`~/anicca/skills/earn/gig`）も同型で `run.sh` `*-cli.sh` `*-healthcheck.sh` `monitor.sh` `launchd/` `scripts/` `__tests__/` `strategy.default.json` `GIG_PASS_RUNBOOK.md` を 1 dir に持つ。
- **loop 台帳 = `config/loop-registry.json` が既に SSOT**。各 loop の `skill_dir` / `status`(live/external/stub) / `cadence_contract` / `evidence_path` / `ledger_paths` / `base_hour/minute` を 1 本に集約（実測: 12 loops 登録）。
  > 引用（profitable-claude, `config/loop-registry.json`, ローカル repo）: `"gig":{"skill_dir":"skills/gig-work","status":"live","cadence_contract":"one hourly pass nurtures/applies/lists on Coconala","evidence_path":"~/gig/gig-funnel.jsonl","ledger_paths":["~/gig/earnings.jsonl"],"base_interval_seconds":3600}`
  → **健康確認・起動・状態集計が全てこの 1 本を読む**（`bin/start-all.sh` は registry の `status==live` だけ起動し、無ければ hardcode に degrade)。
- **orchestrator は registry を読むだけ、loop 自身のロジックを持たない**（実測: `bin/start-all.sh` は registry を parse して `$skill_dir/$loop-cli.sh` を叩くだけ）。= memory の「loop がやる、orchestrator は skill 化だけ」に一致。
- **deny-by-default gitignore + allowlist**（実測: `.gitignore`）。
  > 引用（profitable-claude, `.gitignore`, ローカル repo）: `* / !.gitignore / !skills/ / !skills/** / … / state/ / .env.*`（`*` で全除外 → `!` で tracked dir を復活 → その後 `state/` `.env.*` `*.log` を再除外）。
  → **新規ファイルが誤って commit されない。state と secret は物理的に repo から締め出す。**
- **install はパス相対**（実測: `install.sh`）。
  > 引用（profitable-claude, `install.sh`, ローカル repo）: `REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # Never assume ~/profitable-claude -- an OSS installer can clone this anywhere.` かつ `--dry-run` を全副作用が通る `act()` で担保。
- `ledgers/.gitignore` = `* / !.gitignore`（横断 CEO 台帳の jsonl は dir だけ tracked、中身は追わない）。

**実測で見つかった 2 つの不整合（＝統一すべき点）:**
1. **launchd の置き場が二重**。README は per-skill（`skills/bounty/launchd/ai.anicca.bounty-core-healthcheck.plist`）を install 手順に書くのに、repo 直下 `launchd/` にも connector/explorer/life-manager の core-healthcheck plist が居る。→ **per-skill を正とし、直下 launchd/ は横断 orchestrator(ceo) 専用に限定**する（下記根拠）。
2. **state の置き場が三種混在**。`skills/<name>/state/`（connector 等）/ `~/gig`（gig, repo 外）/ `~/.cloak`（affiliate, repo 外）。→ **既定は `skills/<name>/state/`（gitignore 済み）に統一**、repo 外は「他 instance / 別 identity と共有する時だけ」の例外にし、いずれも `evidence_path` で registry に path 契約を書く。

---

## 推奨の根拠（なぜこの形か、3 点）

1. **1 loop = 1 自己完結 dir → 着脱が copy/rm だけで済む。** Anthropic 公式・OpenClaw・自 repo の 3 者が独立に同じ形（`<name>/{SKILL.md,…}`）に収束している（§実例1,2,4）。plist・state・test を同 dir に同居させると、loop の追加＝ 1 dir 追加 + registry 1 エントリ、削除＝ 1 dir 削除 + 1 エントリ削除で完結し、横断 dir を触らない。これが「混ぜない」を物理的に保証する。

2. **台帳は repo 直下に JSON/YAML を 1 本。** Anthropic の `marketplace.json`、OpenClaw の `taxonomy.yaml`、自 repo の `loop-registry.json` が全て「直下 1 本のマニフェストが path でコンポーネントを列挙する」形（§実例1,2,4）。起動(`start-all`)・状態(`status`)・健康確認・予算が全部この 1 本を読むので、**「登録していない loop は存在しない」**（= global CLAUDE.md の TaskList 原則）が構造で担保される。台帳を人が読む用にミラーした表を README に置く（自 repo は既にこの表がある）。

3. **state/secret は path 契約だけ repo に、実データは gitignore で締め出す。** deny-by-default（`*` + `!allowlist` + 末尾で `state/`/`.env.*` 再除外）は、公開 repo に「新規ファイルが `git add -A` で巻き込まれ secret が漏れる」穴を構造で塞ぐ（§実例4 引用）。実データの物理位置（`skills/<name>/state/` か `~/gig` か）は自由でよく、**registry の `evidence_path`/`ledger_paths` が唯一の path 契約**になる。install は必ず install-relative（clone 先を hardcode しない）。

---

## profitable-claude への適用案（差分だけ、丸ごと作り直さない）

現状で 90% 出来ている。以下を「1 規約に統一」する差分のみ:

| # | 現状 | 変更 | 根拠 |
|---|---|---|---|
| 1 | launchd が top-level と per-skill に二重 | **loop の plist は全て `skills/<name>/launchd/` に集約**。top-level `launchd/` は ceo-runner / ceo-weekly-eval（横断 orchestrator）だけ残す。connector/explorer/life-manager の core-healthcheck plist を各 skill dir へ移動 | §実例1,2 の自己完結原則 + memory「MOVE 前に skill+cron を grep」 |
| 2 | state が 3 箇所混在 | **既定 = `skills/<name>/state/`（gitignore 済）**。repo 外(`~/gig` 等)は「別 identity/instance 共有」時だけの明示例外。どちらも registry `evidence_path` に path を書く（実データは追わない） | §根拠3 |
| 3 | README の loop 表が唯一の導線 | loop 数が増えたら **`skills/README.md` を category 別索引に分割**（VoltAgent 方式）。当面は README 1 表で可 | §実例3 |
| 4 | install.sh は 5 job だけ wired | 新 loop 追加時、install.sh に同じ per-skill パターンで 1 section 追加（既にコメントでそう設計済み）。**launchd 生成は必ず REPO_ROOT 相対** | §実例4 引用 |
| 5 | loop 追加の手順が暗黙 | `template/`（Anthropic 方式）に相当する **loop 雛形 dir を 1 個** 置き、「新 loop = template を copy → registry に 1 エントリ追記 → install.sh に 1 section」を README に明記 | §実例1 template/ |

**移動を実行する際の不変条件（memory 準拠）:** plist を移す前に `grep -rl <plist名>` で README/install.sh/registry の参照を全て洗い、参照を同 turn で書き換える。`launchctl bootout` → path 変更 → `launchctl bootstrap` で再登録し、`launchctl list | grep ai.anicca` で実測してから完了と呼ぶ（自作 status script は自己申告なので launchctl まで降りる）。

---

## 引用一覧

1. anthropics/skills — `.claude-plugin/marketplace.json`（skills を path 列挙するマニフェスト）: github.com/anthropics/skills
2. anthropics/skills — `skills/<name>/{SKILL.md, templates/, LICENSE.txt}` 自己完結 + `template/SKILL.md` + `spec/agent-skills-spec.md`: github.com/anthropics/skills
3. openclaw/openclaw（383k★）— top-level `skills/ config/ deploy/ scripts/ packages/ docs/` + 直下 `taxonomy.yaml`(Maturity scorecard 台帳) + `.env.example`; skill は `skills/1password/{SKILL.md,references/}`: github.com/openclaw/openclaw
4. VoltAgent/awesome-openclaw-skills（51k★）— `categories/*.md` によるカテゴリ別索引: github.com/VoltAgent/awesome-openclaw-skills
5. profitable-claude（ローカル）— `config/loop-registry.json`(SSOT 台帳) / deny-by-default `.gitignore` / install-relative `install.sh` / `bin/start-all.sh`(registry を読むだけの orchestrator): `~/profitable-claude`
6. gig skill（ローカル）— 1 skill 自己完結: `run.sh *-cli.sh *-healthcheck.sh monitor.sh launchd/ scripts/ __tests__/ strategy.default.json RUNBOOK.md`: `~/anicca/skills/earn/gig`
