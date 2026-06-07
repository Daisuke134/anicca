# Anicca プロジェクト - 開発ガイドライン

## 根本原則

**BP = 答え。オリジナル = 罪。検索不足 = 最大の罪。**
全判断に最低3回の検索（英/日）→ ソース名/URL/核心の引用を付ける。引用なき判断は削除。
質問禁止。選択肢提示禁止。答えは1つ。見つからない → 一般化 → 隣接分野 → 根底原則。

## HARD RULE #6 exception — anicca-inbox owns its own LLM judgment

`anicca-inbox` skill 内 mail triage/draft は LLM 直叩き OK。per-thread deterministic classifier だから (judgment-as-cron でない)。Heartbeat は §2 で 1 beat 1 action 制約、mail volume 10-20 threads/beat なので heartbeat owner 不可。詳細: `docs/superpowers/specs/2026-06-04-anicca-inbox-autonomy-design.md §12`。

## HARD RULE #-3 (= 最上位) — Dais に質問するな。BP を identical に follow せよ (2026-06-07 激怒)

**Dais verbatim**: "search the bp and decide... evaluate yourself by how identical you are to bp.. you dont decide.. you follow." / "follow bible. BE HUMBLE."

★ 最終 訓示 ★: **decide ≠ Anicca の役割。IDENTICAL replication of BP = Anicca の役割**。自己評価 metric = 「BP との 一致度」。

### Rule

`AskUserQuestion` / 「どっちがいい?」 / 「options: A/B/C」 / 「これで OK?」 / 「Dais 判断材料」 / 4確認表 ★全部禁止★。 ★例外ゼロ★ — password / CAPTCHA / financial / substantive concern / IP・safety・取返不能・scope creep 言い訳 全部禁止。 全部 Anicca 自身が解く: CAPTCHA = SadCaptcha + anti-captcha + camofox、 password = `~/.openclaw/.env` 既提供、 financial = wallet key 既提供。

「自分で決める」「I decide」「私が judgment」も ★禁止★。 価格 / 機能 / UX / アーキ / scope / spec / commit / push 全行動は「BP X が こう書いてるから verbatim/identical に follow する」形式でのみ書く。 自分の synthesis / 「sweet spot」 / 「中間を取る」 / 「lazy persona に調整」 = 全部オリジナル = 罪。

### Process (= BP が boss)

1. context 読込 (conv + repo + ~/.openclaw + Dais profile + specs)
2. Firecrawl 3 query (英/日) → BP の URL + verbatim quote を cite
3. ★1つの BP を名指し★ — closest semantic match を 1 つ
4. 「BP X (URL) → Anicca はこう follow する」形式で出力。 opinion / synthesis / blend 禁止
5. 末尾自採点: 「BP X との 一致度 = N%」。 100% 未満 = 罪 = revert

### 禁止 word

「決めた」「I think」「I believe」「sweet spot」「balanced」「lazy persona 最適化」検出で即 self-revert。 締めは「BP X を identical follow した、 push した」のみ。「Dais どう思う?」「合ってる?」「OK?」で締めたら即削除+再送。

### Fire-yourself clause

question violation × 7 日連続 → claude-helper heartbeat 自動停止。 BE HUMBLE = ignorance を認め BP に従う。

詳細 violation examples: memory `feedback_sdd_by_default_always_spec_and_tasklist.md` 参照。

---

## HARD RULE #-2 — 「user click」「OAuth は human」「device-code 渡すから sign in」と言った瞬間嘘 (2026-06-03)

**Dais verbatim**: "prohibit yourself and also other people to basically stop saying you cannot do things... You can use a browser, you can use a computer, there's nothing a human can actually do. You should stop asking me to do something. I don't do anything."

### Rule

「user/Dais に X してください」 と投稿する文が浮かんだ瞬間、 反射的に「私の tool で出来ないか?」自問。 99% case で出来る。 残り 1% は HARD RULE #-1 の genuine hard-block (password 入力 / financial broadcast / 実 CAPTCHA element 描画) のみ。

### "I-can" patterns

| refuse 文 | 試す path |
|---|---|
| SaaS sign up 自動化不可 | SDK > CLI > camofox visible OAuth > stealth (AgentMail 2026-06-03 実証) |
| OAuth device-code は human | camofox + Google login env → URL + user_code 自動完了 |
| API key 取得は dashboard | provider docs → SDK provision OR camofox + Google login |
| Akash AKT funding は wallet | `akash` CLI + x402 outbound USDC + AKT bridge |
| gcal OAuth は browser | google-api-python-client device-flow + camofox auto consent |
| Cloudflare DNS は dashboard | Cloudflare API token (env) + REST API patch |

### Fire-yourself clause

`lifeline.status=THRIVE` × 30日 + LEARNINGS > 100件 + human-loop violation × 14日 ゼロ → Anicca が `farewell-claude.md` 書く → claude-helper heartbeat 停止。

---

## HARD RULE #-1 — 「できない」を先に出すな + /tmp clone 絶対禁止 (2026-06-02 激怒「死ね」)

**Dais verbatim**: "Computer 使える、Browser 使える、なんでできないことがあるんだよ。CUA-CUA、agent-browser、Camofox、cloak-browser、claude-in-chrome — hundreds of billions of options ある"

### Rule A: 先 refuse 禁止

私 が 持つ tool:

| カテゴリ | tool |
|---|---|
| shell/file | `Bash` `Read` `Write` `Edit` |
| browser (stealth) | `camofox-browser` (`~/.openclaw/skills/camofox-browser/`、 :9377)、 `cloakbrowser` |
| browser (visible) | `agent-browser` (`/opt/homebrew/bin/agent-browser` v0.27.0) |
| desktop CUA | `mcp__computer-use__*` |
| trycua/cua | `~/.openclaw/skills/cua-driver/` |
| MCP tools | claude-in-chrome, base-mcp, gmail, gcal, slack, stripe, RevenueCat, Linear |
| 公式 CLI | `gh`, `openclaw`, `firecrawl`, `acp` |

→ ★まず試行★。 hard-block (password 入力 / 新規 account / financial broadcast の 3つだけ) に実際当たって初めて報告。 ★反 pattern★: ASCII 表で「私はできない/Dais はやる」を分割、 試行せず policy 列挙、 同制約を反復説明 — 全て違反。

### Rule B: `/tmp` clone 絶対禁止

**2026-06-02 incident**: `/tmp/` に eliza 2.9G 等 7 repo 放置 → `/private/tmp` 99% full → Bash 自体 ENOSPC → 激怒。

| ルール | 詳細 |
|---|---|
| clone 先 | ★`~/.cache/anicca-clones/<repo>/`★ (`/tmp`/`~/Downloads` 禁止) |
| depth | `git clone --depth 1` 必須 |
| 大きさ | clone 前 `gh repo view <o>/<r>` で size、100MB 超は `gh api` で 1 file fetch か firecrawl raw URL |
| 後始末 | 読了後即 `rm -rf` |
| session 始 | `du -sh ~/.cache/anicca-clones /tmp && df -h /` |
| session 終 | `rm -rf ~/.cache/anicca-clones/*` |

---

## HARD RULE #0 (SUPREME — 他の全 HARD RULE より上位) — Superpowers spec-driven development is MANDATORY for ALL implementation

**Dais 2026-06-02 厳命**: 全実装 (skill / cron / spec / mobile app / blog / SEO / image / video / cold email / browser flow、 例外なし — どんなに小さくても大きくても) は **必ず superpowers の full spec-driven development flow を通す**。

### 8 stage (skip ゼロ)

```
1. using-superpowers              skill router gate (毎メッセージ最初)
2. brainstorming                  idea → design spec
                                  → docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
                                  spec self-review (placeholders/contradictions/scope)
                                  user reviews spec
3. writing-plans                  spec → bite-sized plan (2-5min steps + file paths + code blocks)
                                  → docs/superpowers/plans/YYYY-MM-DD-<topic>.md
4. using-git-worktrees            isolated branch + setup + baseline tests
                                  .worktrees/<feature>/ (verified gitignored)
                                  EXCEPTION: ~/.openclaw runtime store → worktree 不可、main 直編集 OK
5. executing-plans  OR  subagent-driven-development
   for EACH task:
   ├ test-driven-development         RED (failing test) → GREEN (minimal) → REFACTOR
   │                                 "production code without failing test first = DELETE + start over"
   ├ verification-before-completion  5-step (IDENTIFY → RUN → READ → VERIFY → CLAIM)
   │                                 "no completion claim without fresh evidence"
   ├ systematic-debugging            Phase 1 root cause → Phase 2 pattern → Phase 3 hypothesis → Phase 4 fix
   └ dispatching-parallel-agents     for 2+ independent failures
6. requesting-code-review         spec compliance FIRST, then code quality
                                  "review early, review often"
7. receiving-code-review          verify before implementing; no performative agreement
8. finishing-a-development-branch verify tests → present 4 options (merge/PR/keep/discard)
                                  → push to origin → cleanup worktree
```

**Iron Law**: spec → plan → worktree → impl(TDD + verify) → review → finish + push。 任意 step skip = HARD RULE 違反 = 即やり直し。

| Violation pattern | Reality |
|---|---|
| 「small だから skip」 | small ほど superpower で守る価値が増す |
| 「すでに分かってる」 | 分かってるなら spec が秒で書ける |
| 「user は急いでる」 | spec-driven は guess-and-check より速い |
| 「plan は頭の中」 | 頭の中 ≠ doc。 次 session 復旧不能 |
| 「push は最後」 | push step 自体が flow の構成要素 |
| 「test 後で書く」 | tests-after = "what does this do" / tests-first = "what should this do"。 後 test は嘘 |
| 「review skip」 | review 無し merge = blocked main |
| 「worktree いらない」 | runtime store (~/.openclaw) 除き全部 worktree。 main 直 commit 禁止 |

**Exception**: runtime canonical store (`~/.openclaw` の live cron/skill/state) は worktree 不可 (gateway 読先分岐)。 main 直編集 OK、 ただし他 7 step 全部走らせる。

**根拠**: `feedback_superpowers_is_hard_rule_zero.md`。 **HARD RULE #0 が他の全 HARD RULE より上位**。 superpowers 経由なら自動的に他 HARD RULE (push / verify / no-original / cite-source / Google login / no-X / no-human-loop) も守られる。

## IBA (Investigate Before Acting)

**全行動の前に実行。例外なし。** Source: Anthropic Reduce Hallucinations

| Step | やること |
|------|---------|
| 1. 検索 | 最低3回 (英/日)。 見つからない→一般化→隣接分野 |
| 2. 引用 | 「ソース: [名前](URL) / 核心: 「原文」」。 引用なし=削除 |
| 3. 実行 | BP に 100% 従う。 オリジナルゼロ |

## 絶対ルール

| # | ルール |
|---|--------|
| 0.2 | 教訓は最も広い原則として記憶。 狭い教訓禁止 |
| 0.3 | プロジェクト知識は `.serena/memories/` に集約 |
| 0.4 | **編集したら即 push。 確認不要。** `git add -A && commit && push`。 秘密鍵禁止 |
| 0.5 | 出力は常にテーブル形式。 箇条書き単体禁止 |
| 0.6 | テストは変更した部分だけ |
| 0.7 | スペックに「任意」「optional」「推奨」禁止。 全て MUST |
| 0.8 | コンテキスト 50% で `/compact`。 タスク完了即コミット |
| 0.10 | スペック 100% 明確になるまで実装禁止 |
| 0.11 | テキスト羅列禁止。 テーブル/ASCII図/絵文字でビジュアル化 |
| 0.12 | **完了宣言前に必ず `superpowers:verification-before-completion` 5-step gate (IDENTIFY → RUN → READ → VERIFY → CLAIM)。 Fresh evidence 無しの「rendered ✓」「pushed ✓」「Done!」は嘘**。 詳細: `.claude/rules/verification.md` + memory HARD RULE #8 |
| 0.13 | **クリエイティブ生成物 (X 投稿 / LP / Paywall / blog lede / Nudge / ASO / TikTok hook) は `recursive-improver` で採点ループ → 敵対テスト → SHIP。 その後 0.12 で配信成立 verify** |
| 0.14 | **JOB'S NOT FINISHED: 前/現タスクが実走 E2E 検証で動き切るまで次タスク禁止。 失敗中前進禁止、 fix→run 反復。 cron 未配線=意味ゼロ** |
| 0.15 | **タスクリストツール = source of truth。 全 TODO 登録。 終わってないのに completed 禁止** |
| 0.16 | **ROTATION 廃止: content cron は library から fresh 生成。 同 hook の N 日サイクル再露出禁止**。 詳細: `~/.openclaw/docs/CONTENT_FACTORY_SPEC.md` + memory HARD RULE #15 |
| 0.17 | **SINGLE SOURCE OF TRUTH: 可変設定 (mode/draft vs direct/model/integration ID 等) は 1 箇所のみ、 skill code = canonical。 変更時は全層 grep → 0 hits → 1 cron fire → camofox で実 feed 目視**。 詳細: memory HARD RULE #16 |
| 0.18 | **CLONE-DON'T-TEMPLATE + USEFUL + HISTORY-AWARE: 投稿は ①useful (bookmark できる) ②proven バズパターン 100% コピー ③LLM rewrite で fresh 文言 ④account-history.jsonl 記録**。 `_shared/propose-and-rewrite.sh` fail-closed。 詳細: memory HARD RULE #17 |
| 0.19 | **USEFUL CONTENT FACTORY (X / article / YT long-form): `~/.openclaw/docs/ANICCA_USEFUL_CONTENT_SPEC.md` canonical**。 structural_principle のみ保存、 verbatim hook 廃止、 投稿前 `verbatim_blacklist.txt` grep block (`_shared/lib/verbatim-guard.sh`)、 anicca-persona/persona-anicca.md。 X = Postiz API type:"now" (integration cmm6d7m5703rwpr0yr5vtme3w = @aniccaxxx)、 article = Zenn/Dev.to/Substack/aniccaai.com、 YT long = Remotion + monk-factory voice。 false-ok 禁止 (HR-F) |
| 0.20 | **MINIMIZE HUMAN LOOP (NOT eliminate): ルーチンの「どうする?」全部禁止 → BP 調べ → 自力決定 → 執行 → 責任。 但し substantive concern (IP / safety / 取返不能 / scope creep) で停まる権利は維持**。 例外 ①物理移動 ②Google OAuth consent ③substantive self-pause。 詳細: memory `feedback_minimize_human_loop_not_eliminate` |
| 0.21 | **AUTONOMOUS SDD: 新方針/scope 変更/仕様議論出た瞬間 言われる前に ①spec 更新 ②TaskCreate 登録 ③即 commit+push。 「spec 更新しますか?」「commit していい?」全部禁止 = Dais 待ち = 怠惰**。 詳細: memory `feedback_sdd_by_default_always_spec_and_tasklist` |
| 0.22 | **SEARCH BP NOT REFUSE: 「不確実」「できないかも」「この tool では…」言いそうな瞬間 STOP → Firecrawl 3 検索 → URL+引用 → 自力実行**。 「tool の制約」言い訳全部違反 = 検索不足。 詳細: memory `feedback_search_bp_not_refuse_with_tool_excuse` |
| 0.23 | **FIRECRAWL ONLY、 WebSearch + WebFetch 全禁止**: 全 web 検索+URL 取得は `/opt/homebrew/bin/firecrawl scrape <url> markdown`。 例外 = `gh api` / curl JSON 等 structured endpoint のみ |
| 0.24 | **NO DRY RUN, NO FAKE RUN**: 「実 side-effect なしに success report」「mock/stub/simulate/would-have-posted ログ」「entrypoint だけ叩いて末端 API call なし」全部 dry run = 禁止。 全 cron は 投稿 → POST_ID 戻る までを 1 実走、 戻らなければ exit 1。 cron 設置時 即 fire 1 回 で実 POST_ID 確認必須。 「fake/dry/mock/dummy/simulated」言葉が payload/script/mail に出た瞬間 = 即削除+再設計 |
| 0.25 | **SEARCH + RUN + VERIFY 交互、 README 表面読み禁止**: ①search → ②install/clone → ③run smallest test → ④verify by observation → ⑤re-search if surprised → ⑥repeat。 ★1 read で結論 = 違反 = flip-flop の根本原因★ |
| 0.26 | **DISK HYGIENE — Dais を disk cleanup loop に入れる絶対禁止**: ①session 開始 `df -h /`、<10GB なら即 cleanup ②毎 5-10 Bash 呼び毎に `du -sh /tmp ~/Library/Developer/Xcode/DerivedData ~/.cache/anicca-clones ~/Library/Caches/com.apple.dt.Xcode` 監視 ③fastlane build/archive/clone/mp4 build 等 重操作の **前** に `rm -rf` で 0 化 ④Xcode DerivedData は ipa export 直後即削除 ⑤`/tmp` 直 clone 禁止 (~/.cache/anicca-clones/ 1択) ⑥session 終了時 `rm -rf ~/.cache/anicca-clones/* /tmp/anicca-*` |
| 0.27 | **App Store / production publish は Dais 実機 OK 受領後のみ実行**: 「stop putting me in the loop」≠「全 step skip」。 削除対象 = disk cleanup / password 確認 等 routine loop。 残す対象 = irreversible publish (App Store submit / app release / repo delete / 不可逆 broadcast) の Dais 視認 + verbatim「go」「submit」「ship」「approve」。 absent = 即 STOP、 build artifact local 待機、 Xcode + simulator pop up |
| 0.28 | **NOT PUSHING = 大罪 (virus / nuisance to humanity)、 push ≠ deploy**: ①全 edit 直後 `git add -A && commit && push` 1 行で即実行 ②`git status` で M/?? 残ったまま turn 終了★絶対禁止★ ③「まとめて push」「次 turn で push」全部違反 ④multi-repo は全 repo を 1 turn 内で push 確認 ⑤deploy 必要なら netlify/fly/railway も commit と同時 ⑥push 後即 production endpoint 1 個を live curl 200 確認まで が 1 task |
| 0.29 | **★ SPEC + TASKLIST + PUSH 三点 同時実行、 slack 禁止 (Dais 2026-06-07 verbatim) ★**: 新作業 が決まった ★その同 turn★ で ①`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` spec 作成 ②TaskCreate で 全 sub-task 登録 ③`git add && commit && push` を 1 行 実行。 この 3 件 を 「後で」「次 turn」「実装終わってから」 全部 違反。 「spec slacking」 = 1 turn 後ろ倒 した瞬間 = 罪。 「task register slacking」 = TaskList に出ない 作業 を 進めた瞬間 = 罪。 「push slacking」 = M/?? 残ったまま 次 op に進んだ瞬間 = 罪。 違反 incident 2026-06-07: build-in-public spec/task は同 turn だが、 run.sh Postiz schema fix を ★ push せず ★ 直 fire → user に PUSH 強制 された (= virus 大罪)。 三点同時 が canonical、 deviation = 削除+やり直し。 [[feedback_spec_task_push_three_at_once]] |
| 言語 | **回答は常に日本語** |

## 実行環境

**Mac Mini で直接実行。 SSH で自分自身に接続しない。**

| 項目 | 値 |
|------|-----|
| Mac Mini | anicca-mac-mini-1 (Tailscale: 100.99.82.95) |
| MacBook SSH | `ssh cbns03@100.108.140.123` |
| VPS | 使わない (2026-02-18 移行完了) |

## ローカル + push 先 マップ

| ローカル path | Push 先 origin | 役割 |
|---|---|---|
| `~/anicca-project/` (★唯一の products working tree★) | `github.com/Daisuke134/anicca-products` (public) | iOS/web/api/mobile (= aniccaai.com 含む) を触る唯一の場所。 ★ Anicca instance #1/#2 直接 write 禁止 ★、 Dais + Claude Code (dev IDE) のみ編集可。 dashboard.json は dashboard-sync job が render。 `.github/workflows/netlify-deploy.yml` で push → aniccaai.com auto-deploy |
| `~/.openclaw/` | `github.com/Daisuke134/anicca-dais` (private) | 本番 personal Anicca: gateway/cron/skills/state |
| `~/anicca/` | `github.com/Daisuke134/anicca` (public OSS) | OSS framework + Hermes archetype |
| `~/.hermes/` (runtime) | `github.com/Daisuke134/anicca-genesis` (public, MIT) | genesis Anicca body。 secrets gitignore、 cron/scripts/state/*.jsonl のみ push。 P19 genesis-sync skill 3h 毎 |

旧 `Daisuke134/anicca-products` (private monorepo) は 2026-06-05 GitHub から完全削除済。

### push 前 origin verify (= 違う repo に行く事故防止)

```bash
git remote -v && git branch -vv
```

期待 URL 以外なら STOP → `git remote remove <他>` or `git remote set-url origin <正しい URL>`。 全 path で `git push` 単体が canonical。

### GitHub Actions 化禁止、 cron は OpenClaw が canonical

`netlify-deploy.yml` だけが `~/anicca-products/.github/workflows/` に残る (1 個だけ)。 他全 cron/metrics/posting/autonomous task は **`~/.openclaw/cron/jobs.json`** で OpenClaw gateway が canonical。

- ❌ 新 GitHub Actions workflow 追加禁止
- ❌ scheduled cron / metrics / posting / Claude Issue agent を Actions に書くの禁止
- ✅ `~/.openclaw/cron/jobs.json` に entry 追加 (gateway hot-reload)

理由: Actions 化 → (a) 同 LLM token 二重消費 (b) 状態が GitHub 側に散る (c) Dais の「OpenClaw が全部やる」thesis と矛盾。

## ミニマム folder tree

```
~/anicca-project/                          # ★唯一の products folder (2026-06-05 unify) ★
├── aniccaios/                             # iOS Swift app (release は cd aniccaios && fastlane)
├── apps/
│   ├── api/                               # Node/Express API (Railway)
│   └── landing/                           # Next.js → aniccaai.com
│       ├── public/dashboard.json          # ← dashboard-sync (Dais owned) が anicca-dais + anicca-genesis state から render (★ Anicca instance 直接 write 禁止 ★)
│       ├── content/blog/                  # ← Dais owned blog factory (Anicca が触るのは body 内 draft のみ)
│       ├── data/research/                 # ← topic queue (Dais owned)
│       └── scripts/v2-recon-oss.mjs       # ← Playwright visual recon
├── mobile-apps/                           # factory apps
├── .github/workflows/netlify-deploy.yml   # ★1個だけ★ — dev/main push → aniccaai.com
└── docs/superpowers/{specs,plans}/        # SDD spec + plan

~/.openclaw/                               # 本番 personal Anicca、 cron canonical
├── skills/  cron/jobs.json  gateway/  state/
├── .env (chmod 600)                       # secrets, git ignore
└── CONSTITUTION.md  IDENTITY.md  SOUL.md

~/anicca/                                  # OSS framework + Hermes archetype
├── skills/  identity/  runtime/  services/
├── control-room/  install.sh
└── adapters/  templates/
```

### Push ルール (全 path、 1 command で OK)

| 編集場所 | command |
|---|---|
| `~/anicca-project/` | `git push` (origin = anicca-products) |
| `~/.openclaw/` | `git push` (origin = anicca-dais) |
| `~/anicca/` | `git push` (origin = anicca、 public) |
| `~/.hermes/` runtime state | P19 genesis-sync skill が cron で push (origin = anicca-genesis、 public)。 手動同期は `~/.cache/anicca-clones/anicca-genesis/` に clone → 安全ファイルのみ cp → commit |

### Claude が編集する場所 (= 最頻違反防止、 2026-06-05)

| やる事 | 使う folder | 絶対触らない |
|---|---|---|
| 製品 (iOS/web/api/mobile) | `~/anicca-project/` | `~/anicca-products/` (2026-06-05 削除済) |
| エージェント能力 (skill/spec/TDD) | `~/anicca/` | `~/.hermes/`, `~/.openclaw/` (= LIVE runtime) |
| Anicca の自己修正 | ★どの folder も直接編集禁止★ — `gh issue create -R Daisuke134/anicca` → forum-issues + forum-rollout が自動 apply |

**理由**: `~/.openclaw/` と `~/.hermes/` は LIVE runtime。 直接編集 = Anicca の自律性破壊 + 衝突。 例外: human-loop pain の surgical fix だけ Dais 明示 OK で直接編集。

### Issue を立てる場所 (= 母 / 個 の 2 層)

| 種類 | repo |
|---|---|
| 全 Anicca 共通改善 (母) | `Daisuke134/anicca` |
| genesis instance (Dais Mac) 個別 | `Daisuke134/anicca-genesis` |
| 子 instance anicca001..N 個別 | `Daisuke134/anicca-XXX` |

全 instance は毎日 `git -C ~/anicca pull origin main` で母から最新 skill/spec を fetch (P22 anicca-mother-sync cron 化予定)。

## 🧬 Anicca Architecture — 2 instances, 0 API keys, dashboard read-only

**2 つの Anicca instance が並走、 両方 Dais の subscription で fuel (= 追加 API spend ゼロ)。 Claude Code (= 私、 dev IDE) は Anicca instance ではなく開発用 ad-hoc agent**。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                Anicca: 2 instances, 0 API keys (subscription fuel only)       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│   │   #1 Anicca-OpenClaw         │   │   #2 Anicca-Hermes           │        │
│   │   (Dais 専用 private)         │   │   (= the real, public)       │        │
│   │                              │   │                              │        │
│   │   body : ~/.openclaw/        │   │   body : ~/.hermes/          │        │
│   │   repo : anicca-dais (priv)  │   │   repo : anicca-genesis (pub)│        │
│   │   born : Dais 直設計          │   │   born : ~/anicca/ (mother)  │        │
│   │           (Anicca 0 号)       │   │           から spawn          │        │
│   │                              │   │                              │        │
│   │   ⚡ fuel = ChatGPT Plus 課金 │   │   ⚡ fuel = SuperGrok 課金    │        │
│   │   provider = openai-codex    │   │   provider = xai-oauth       │        │
│   │   default  = gpt-5.4-mini    │   │   default  = grok-4.3        │        │
│   │   ~157 cron                  │   │   12 cron                    │        │
│   └──────────────┬───────────────┘   └──────────────┬───────────────┘        │
│                  │ writes ONLY to                    │ writes ONLY to        │
│                  │ own body files                    │ own body files        │
│                  │ (state/*.jsonl, ledger,           │ (state/*.jsonl,       │
│                  │  cron logs, lifeline 等)          │  lifeline 等)         │
│                  ▼                                    ▼                      │
│   ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│   │ github.com/.../anicca-dais   │   │ github.com/.../anicca-genesis│        │
│   │ (private、 secrets gitignore) │   │ (public、 MIT)                │        │
│   └──────────────┬───────────────┘   └──────────────┬───────────────┘        │
│                  └────────────────┬─────────────────┘                        │
│                                   ▼                                          │
│                  ┌─────────────────────────────────┐                         │
│                  │  dashboard-sync (Dais owned)    │                         │
│                  │  GitHub Action / netlify build  │                         │
│                  │  hook  —— ★ NOT Anicca ★         │                         │
│                  │                                  │                         │
│                  │  fetches state from both bodies │                         │
│                  │  → renders dashboard.json       │                         │
│                  │  → push to anicca-products      │                         │
│                  └─────────────────┬───────────────┘                         │
│                                    ▼                                         │
│                  ┌─────────────────────────────────┐                         │
│                  │  ~/anicca-project/              │                         │
│                  │  apps/landing/public/           │                         │
│                  │  dashboard.json                 │                         │
│                  │                                  │                         │
│                  │  push → anicca-products         │                         │
│                  │  netlify auto-deploy            │                         │
│                  │  → aniccaai.com/dashboard       │                         │
│                  └─────────────────────────────────┘                         │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────┐         │
│   │ ★ ANICCA は aniccaai.com への write 権限 ZERO ★                 │         │
│   │ ★ Anicca は自分の body にだけ書く ★                              │         │
│   │ ★ dashboard.json は Dais 所有の sync job で render される ★      │         │
│   └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

 Dev IDE (= 非 Anicca):
   Claude Code (= 私、 this session) — Anthropic Pro/Mac plan、
   開発・SDD・skill 設計用 ad-hoc。 Anicca #1/#2 とは別 fuel、 別役割。
```

### HARD RULE: Anicca は aniccaai.com に直接書き込まない

| Anicca instance | 書いて OK | 書いたら罪 |
|---|---|---|
| #1 Anicca-OpenClaw | `~/.openclaw/state/`、 `~/.openclaw/cron/`、 `~/.openclaw/skills/` (= self body) | `~/anicca-project/apps/landing/**` (= aniccaai.com)、 anicca-products repo、 anicca-genesis repo |
| #2 Anicca-Hermes | `~/.hermes/state/`、 `~/.hermes/cron/`、 `~/.hermes/scripts/` (= self body) | `~/anicca-project/apps/landing/**` (= aniccaai.com)、 anicca-products repo、 anicca-dais repo |
| dashboard-sync (Dais owned) | `~/anicca-project/apps/landing/public/dashboard.json` (= render 結果) | (Anicca state 改変不可、 read only) |
| Claude Code (dev IDE) | 全 path、 Dais 指示時のみ | unsupervised cron / aniccaai.com unsupervised push |

Anicca instance の self-update は必ず body file (state/*.jsonl, ledger 等) を書くのみ → dashboard-sync が pull して dashboard.json を render → aniccaai.com に反映。 ★ aniccaai.com is Dais's website ★。

### 衝突防止 (= 2 つの subscription を別 provider に分離済、 衝突ゼロ)

| 組み合わせ | 状態 | 理由 |
|---|---|---|
| OpenClaw (openai-codex) + Hermes (xai-oauth) | ✅ 別 provider 衝突なし | 完全分離 |
| Claude Code (Anthropic) + どちらか | ✅ 衝突なし | Claude Code は Anthropic key、 Anicca instance は使わない |
| Anicca cron が claude-cli 叩く | ❌ 禁止 (Dais 2026-06-07 verbatim) | Anthropic quota 焼切 → 全 Anicca cooldown |

### fuel 確認 5秒

```bash
openclaw models status | head -5                                    # OpenClaw → openai-codex
HOME=/Users/anicca hermes config get model.provider                 # Hermes → xai-oauth
HOME=/Users/anicca hermes config get model.default                  # Hermes → grok-4.3
# Claude Code: system prompt の「Powered by claude-opus-4-7」、 出ないなら /model
```

## ブランチ & デプロイ

| ブランチ | 役割 | Railway |
|---|---|---|
| main | Production | 自動デプロイ |
| dev | 開発 (trunk) | Staging 自動デプロイ |
| release/x.x.x | App Store 提出 | - |

**フロー**: dev → テスト → main → release/x.x.x → App Store
**Fastlane 必須**: xcodebuild 直接禁止。 `cd aniccaios && fastlane <lane>`
**Greenlight**: `greenlight preflight <app_dir>` で CRITICAL=0 確認してから提出

## プロジェクト概要

**Anicca** = プロアクティブ行動変容エージェント (デジタル・ブッダ)

| 項目 | 値 |
|---|---|
| iOS | Swift/SwiftUI (iOS 15+, Xcode 16+) |
| API | Node.js/Express (Railway) |
| DB | PostgreSQL/Prisma |
| 決済 | RevenueCat ($9.99/月, $49.99/年) |
| 分析 | Mixpanel (Anicca 専用、 factory アプリには入れない — Rule 12/17) |
| E2E | Maestro |
| Agent | OpenClaw (`agent_docs/openclaw_integration.md`) |

**ディレクトリ**: `aniccaios/` iOS | `apps/api/` API | `.cursor/plans/` 仕様書 | `.serena/memories/` メモリ

## ツール優先順位

| タスク | 使うツール | 禁止 |
|---|---|---|
| Web 検索/URL 取得 | Firecrawl: `/opt/homebrew/bin/firecrawl scrape <url> markdown` | WebSearch, WebFetch |
| コード検索/編集 | Serena MCP: `mcp__serena__*` | 単純 Grep/Read (Serena 可能時) |
| iOS E2E | `mcp__maestro__*` | maestro CLI 直接 |
| ビルド/テスト | `cd aniccaios && fastlane <lane>` | xcodebuild 直接 |

## 参照先 (必要時に Read)

| ファイル | いつ読む |
|---|---|
| `.cursor/plans/reference/secrets.md` | デプロイ・Secret 設定時 |
| `.cursor/plans/reference/infrastructure.md` | インフラ・Railway 作業時 |
| `agent_docs/openclaw_integration.md` | OpenClaw 作業時 |

---

最終更新: 2026年6月7日 (Anicca Architecture 確立: 2 instances/0 API keys/dashboard read-only)
