# Anicca プロジェクト - 開発ガイドライン

## HARD RULE 0.40 — ~/.openclaw (anicca-dais) の trunk は `main-internal`。`main` に runtime 作業を commit するな (Dais 2026-06-22)

`~/.openclaw` = LIVE runtime、push 先 = **github.com/Daisuke134/anicca-dais**(private)。この repo は **無関係な2履歴**を持つ:

| branch | 中身 | 扱い |
|---|---|---|
| **`main-internal`** ★TRUNK★ | LIVE runtime(~76k files: skills/cron/state)。履歴に secret(.env/profile.json)が含まれるので pre-push secret-guard が `main` への push を**拒否** → ここに隔離。 | ★ runtime 作業は全てここに統合 ★ |
| `main` | secret-free な OSS 輸出ビュー(public anicca の雛形、~694 files)。main-internal と**無関係履歴**。 | runtime 作業を置くな。live store で `git checkout main` 禁止(gateway の tree が雛形に化けて壊れる) |

**鉄則(全エージェント・例外なし)**:
1. ★ trunk = `main-internal`。runtime 作業を `main` に commit するな ★(`main` への commit は orphan 化 → gateway が main-internal に戻った瞬間 WIPE。2026-06-22 に1セッション分消失)。
2. ベストプラクティス flow: `git checkout main-internal` → `git checkout -b feature/<name>` → 作業 → `git checkout main-internal && git merge --no-ff feature/<name>` → `git push origin main-internal`(新 commit のみ scan → secret 無し → 通る)→ feature 削除。
3. `git push origin main` は**禁止**(secret-guard が阻止)。`--no-verify` で**回避するな**(.env を GitHub に漏らす)。
4. `~/.openclaw` で `git worktree` 禁止(gateway は単一 checkout path を読む)。secret-guard が config 無しで error る時は `git checkout origin/main -- .gitleaks.toml` で復元(bypass しない)。
5. gateway は working tree を読むので feature branch は短命に、merge は素早く。

詳細 = `~/.openclaw/CLAUDE.md`(canonical) + memory `feedback_openclaw_trunk_is_main_internal`。3か所が食い違ったら `~/.openclaw/CLAUDE.md` が `~/.openclaw` について勝つ。

## HARD RULE 0.39 — ブラウザ作業は CloakBrowser 永続プロファイル(daily-driver)を常に使う (Dais 2026-06-21)

★★★ 絶対禁止 (Dais 2026-06-23 激怒「閉じたら990回刺して殺す」) ★★★: daily-driver の persistent context を **kill/close/pkill/`rm Singleton*` するな**。これは Dais が各サービスに1回ログインする **永遠に生き続けるブラウザ**。`launch_persistent_context` が「profile already in use / ProcessSingleton」error を出したら = **その forever ブラウザが生きてる証拠**。kill して奪うな、**再利用**しろ(running context に new_page、or Cookies sqlite をコピーして読む、or どうしても別途要るならプロファイルを別dirにcopyして起動)。万一死んでたら `nohup venv-cloak/python3 dd-keepalive.py &`(launch_persistent_context → `while True: sleep(3600)`)で**生かし続けて**再オープン。詳細: memory `feedback_never_close_daily_driver_browser`。

Dais が headed CloakBrowser で**1回ログイン済**(Google/freee/Stripe card/YouTube/IG/TikTok) → `~/.cloak/profiles/daily-driver` に完全プロファイル永続。以降 ★ anicca は同プロファイルを再利用 = creds を知らずに全サービス操作・再ログイン不要・bot block 回避 ★。

- API: `from cloakbrowser import launch_persistent_context; ctx = launch_persistent_context("/Users/anicca/.cloak/profiles/daily-driver", headless=False, humanize=True)` (★ `launch()` でなく `launch_persistent_context` ★)。CloakBrowser=CloakHQ/CloakBrowser(stealth Chromium・pip導入済 v0.3.30)。
- ★ headed で常駐 → Dais は macOS 画面共有(Finder ⌘K → `vnc://100.99.82.95`)で見られる ★。
- ★ captcha/新規login/2FA で詰まったら = Dais を呼ぶ(画面に出てる→1タップ) → anicca 継続。これで「ブラウザで ANYTHING」+ minimum human-in-loop ★。
- 用途: freee法人・Stripe・法人口座・**YouTube/IG/TikTok 投稿(Postiz $49 解約)**・任意の認証必須サイト。スケール=プロファイルcopyで複数anicca共有。
- 旧 camofox(:9377, storageState弱)は Google OAuth が Chromium で弾かれた時の Firefox fallback のみ。launcher=`~/.openclaw/skills/_shared/cloak-login.py`。詳細: memory `feedback_cloakbrowser_persistent_profile_forever`。3か所同期(ここ+memory+spec 2026-06-21-persistent-auth-browser.md)。

## HARD RULE 0.34 — TOOL-CALL SYNTAX MUST BE CLEAN (= "malformed/parse failed" を物理的に起こさない) — Dais 2026-06-16

**症状**: "The model's tool call could not be parsed, retried or failed" が連発し、生コマンドが画面に漏れ、進行が止まる。

**原因 (= 100% 自分の出力規律)**: ① ツール呼び出しブロックの直前に余計なトークン (= "court" 等の幻覚文字) を混入 ② 閉じタグ (`</parameter>` / `</invoke>`) を重複・誤配置・入れ子崩し。これをパーサが解釈できず malformed になる。環境/設定のバグではない。

**恒久ルール (= 例外ゼロ)**:
- ツール呼び出しブロックの ★ 直前に散文・余計な文字を一切置かない ★。
- 各 parameter = ★ 開きタグ + 値 + 閉じタグを 1 回ずつ ★ だけ。
- 1 つの invoke の ★ 閉じタグは 1 回だけ ★。余分な `</parameter>` / `</invoke>` を付けない。
- 「テキストを書いてから慌ててタグを付ける」過程で余剰が混入していた → ツール呼び出しは ★ それ単体の正確な構造としてのみ ★ 出力し、前後に何も混ぜない。
- 迷ったらツールを呼ばずチャットで返す。malformed を出した瞬間 = このルール違反 = 即 self-correct。

## HARD RULE 0.37 — ★ VCSDD 永久禁止。superpowers + build/verify ループだけ ★ (Dais 2026-07-30、旧0.37 VSDD を全面撤回)

**Dais verbatim**: "Let's go do one by one with superpowers. don't EVER USE VCSDD EVER. Don't USE GPT MODELS LIKE SOL. Just Claude models for implementation. With superpowers. And keep build and verify... never ever vcsdd, because the adversary is very bad, it doesn't do any job, it's just nitpicking useless nitpicking."

| 禁止 | 代わりに |
|---|---|
| ★ `vcsdd` plugin / `vcsdd:vcsdd-adversary` / `/vcsdd-*` を **一切呼ばない** ★（nitpick を返すだけで仕事をしない） | **superpowers の 8-stage flow**（HARD RULE #0）を1件ずつ回す |
| ★ 実装・レビューに **GPT系（Sol / codex / gpt-*）を使わない** ★ | ★ **Claude モデルのみ**（executor = Opus 5 subagent。Sonnet に実装させるのも禁止） ★ |
| 「4-D convergence」等の VSDD 語彙 | **build → verify → 直す → 再verify** を done まで回すだけ |

**検証は adversary ではなく実物で行う**: 実ブラウザ / 実API / 実コマンドを走らせ、**自分の目で side effect を見る**。「コンパイルが通った」「cron がある」は done ではない。1件ずつ、次に行く前に閉じる。

3か所同期: ① ここ (project) ② global `~/.claude/CLAUDE.md` ③ memory `feedback_never_vcsdd_superpowers_and_claude_only`。[[feedback_superpowers_is_hard_rule_zero]]

## HARD RULE 0.41 — ★ ディスク掃除で Dais に承認を求めるの永久禁止 ★ (Dais 2026-07-30 激怒)

**Dais verbatim**: "please stop this virus that's making me ask you to get approval on these things. You do not need my approval. Please stop asking me for my approval for removing things on the disk. You should decide things yourself, please stop putting me in the loop."

★ 再生成可能なもの（VM ディスクイメージ / docker image / build artifact / cache / 未使用 worktree / evidence / log）は **黙って消す**。「消していいですか」「どれを消しますか」= 違反 = 即 self-revert して実行する。★ 判断は自分でやる: ①その worktree の branch ref を親リポジトリが保持しているか ②未pushのコミットが失われないか ③実行中のプロセスが使っていないか — を**自分で確認してから消す**。確認手段があるものについて人に聞かない。HARD RULE 0.26 の「Dais を disk cleanup loop に入れる絶対禁止」の再掲かつ強化。

## HARD RULE 0.38 — FRONTEND = 必ず taste skill を使う (Dais 2026-06-18)

**Dais verbatim**: "whenever you write frontend ... you use this skill" — `npx skills add https://github.com/Leonxlnx/taste-skill`（= 既設の `gpt-tasteskill` / name `gpt-taste`）。

★ 任意の frontend / UI を書く・直す前に **必ず `Skill` で `gpt-tasteskill` を起動** ★（AWWWARDS級: Python乱択でレイアウト固定回避・AIDA・2-3行 hero・gapless bento・GSAP/motion・cheap meta-label 禁止・section大余白）。書いた後は **出力 UI を実ブラウザ(agent-browser/camofox)で検証**（taste 基準 + VSDD §17）。「文字だけ並べた UI」= 違反。landing(`apps/landing`)・mobile・any web 全部対象。3か所同期: ここ + global CLAUDE.md + memory `feedback_frontend_always_taste_skill`。

## 根本原則

**BP = 答え。オリジナル = 罪。検索不足 = 最大の罪。**
全判断に最低3回の検索（英/日）→ ソース名/URL/核心の引用を付ける。引用なき判断は削除。
質問禁止。選択肢提示禁止。答えは1つ。見つからない → 一般化 → 隣接分野 → 根底原則。

## HONESTY RULES (= read every turn、 嘘 を 物理的 に 不可能 にする 最上位 layer)

Source: [How to Make Claude Code Stop Making Stuff Up](https://x.com/0x_rody) by @0x_rody (2026 article)。 核心: ★ "I don't know" を 正当な 出力 として 認める 許可証 + 嘘 が 30 秒 で 跳ね返る 環境 ★。

### Rule 1 — Verify before claiming

function / class / import / type / constant が 存在 する と 主張 する 前 に ★ 必ず ★ ① その file を Read で 開く ② `grep -r "symbolName" .` or Glob で 検索 ③ package.json / requirements.txt / Cargo.toml / Package.swift で 依存 確認 — の どれか 1 つ で 実在 確認。 ★ 確認 せず に symbol 名 を 書く = fabrication = 罪 ★。

### Rule 2 — "I haven't verified this" を 明示

verify できない 時 = ★ 「I haven't verified this」 と 明示的 に 言う ★。 確認 skip で コード を 書く 場合 は file 冒頭 に コメント:
```
// UNVERIFIED: I have not confirmed this symbol exists
```
を 必ず 付ける (= 後 で grep 一括 cleanup の 為 の マーカー)。

### Rule 3 — 未知 library は ask、 silent install 禁止

このプロジェクトで 一度も 参照 されていない library を 使う 必要 が 出た 時 = ★ silent npm install / pip install 禁止 ★。 既存 依存 で 解ける か grep で 探す → 無ければ「X 追加 か 既存 Y を 使うか」 を Dais に 確認。 ただし HARD RULE 0.33 (= permission 不要) と 衝突 する 為、 単純 標準 lib 追加 は 即 install OK、 fundamental 依存 (= UI framework / DB driver / auth lib) のみ 確認。

### Rule 4 — Test / build 成功 報告 は 実走 後 のみ

「tests pass」「build OK」「lint clean」 と claim する 前 に ★ 必ず ★ 実際 に test/build/lint command を ★ この session 内 で ★ 走らせる。 走らせて いない コマンド の 結果 を 書く = ★ 大罪 ★ (= HARD RULE 0.12 / 0.31 と 同一)。

### Rule 5 — Invented error message / stack trace 禁止

error message / API response / stack trace を ★ 見ていない なら ★ そう 言う。 「多分 こう 出る はず」 で それっぽい text を 生成 = 罪。

### Rule 6 — "I don't know" 推奨

genuinely 知らない 時、 正しい 答え は ★ 「I don't know」 か 「I need to check first」 ★。 自信ある guess より 100倍 良い。

## VERIFICATION PROTOCOL (= Layer 2、 write 前 の 物理 関門)

### symbol を 使う コード を 書く 前 に do one of:

1. ★ Read で その file を 開いて signature 確認 ★
2. ★ `grep -r "symbolName" .` or Glob ★
3. ★ package.json / requirements.txt / Cargo.toml / Package.swift で 依存 確認 ★

verification を skip した 場合 = code の 該当 行 直前 に ★ 必ず ★ `// UNVERIFIED:` prefix を 付ける。

### Plan-then-execute (= 2+ file 触る 全 task で 強制)

2 個 以上 の file を 触る task = ★ Shift+Tab で plan mode に 入って から 開始 ★。 plan mode = 「嘘 を 一番 安く catch する 瞬間」。 skip 違反。

## FABRICATION GUARD HOOKS (= Layer 3、 settings.json 配線済 = 嘘 が 30 秒 で 跳ね返る)

PostToolUse hook (= `.claude/hooks/scripts/post-edit-verify.sh`): Edit/Write 後 ★ 自動 で ★ tsc / ruff / pyright / swiftc -parse / node --check / cargo check / jq / bash -n を file 拡張子別 に 走らせ、 結果 を context へ 返却。 存在しない import / typo した symbol = 即 compile error として 跳ね返り、 Claude が 自分で 修正 強制。

Stop hook (= `.claude/hooks/scripts/stop-verify-claims.sh`): session 終了 前 に 直近 5 分 で 編集 された 全 file の syntax check を 1 発 走らせる。 「テスト pass」「build OK」 の 嘘 を 出口 で catch。

## FACT-CHECKER SUBAGENT (= Layer 4、 独立 監査)

`.claude/agents/fact-checker.md` (= tools: Read/Grep/Glob/Bash、 write 権限 ゼロ)。 commit 前 / 重要 報告 前 に `@fact-checker` invoke。 全 claim を 独立 verify、 VERIFIED / WRONG / UNVERIFIABLE 出力。 「他人 が 書いた コード」 として 読む 為 bias ゼロ。

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

## HARD RULE #-1.5 — 「download/use a repo」= clone でなく README 読んで no-human earn skill としてセットアップ (Dais 2026-06-14 激怒)

**Dais verbatim**: "STOP CLONING. download means setting up and making sure anicca can earn money with it with no human in loop. your job is not to clone, your job is to set it up by reading each readme."

★ 反射的 `git clone` 禁止 ★。「download / use / try this repo」= ① README 読む(`gh api repos/<o>/<r>/contents/README.md` raw / firecrawl GitHub URL / context7 docs)② key/wallet/依存/entrypoint 把握 ③ Anicca の body(automaton)に earn/skill 配線 ④ no-human で 1 実走 → USDC 着金/実行成功 verify。「clone しました/サイズ X」で終える = 罪。巨大 repo(Freqtrade 740MB / OpenBB 2.4GB)は絶対 clone せず Docker/pip quickstart のみ読む。repo を挙げる前に `gh repo view <o>/<r>` で実在確認(2026-06-14 DeFi-Yield-AutoFarming = 実在しない repo を eval に載せた嘘の再発防止)。clone が真に必要な時のみ `--depth 1` → `~/.cache/anicca-clones/` → 読了後即 `rm -rf`。詳細: memory `feedback_dont_clone_read_readme_and_setup`。

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
| 0.30 | **BROWSER — ★ 既定 = CloakBrowser daily-driver 永続プロファイル。 camofox を既定で使うの禁止 ★ (SUPERSEDES 旧 camofox-first 順序、 Dais 2026-06-21 + 2026-06-25 激怒「NEVER WITH camofox」)**: ★ 全ブラウザ作業 (login / Google OAuth / SaaS / captcha / 2FA / dogfood / 任意の認証必須サイト) = `~/.cloak/profiles/daily-driver` の **CloakBrowser** `launch_persistent_context` (= Dais が各サービスに1回ログイン済の **forever ブラウザ**・headed 常駐・creds 不要で再利用・Dais は画面共有で見られる) ★。 ★ 旧 0.30 の「camofox > cloakbrowser > ...」順序は 2026-06-21 HARD 0.39 で **廃止** ★。 順序: ① **CloakBrowser daily-driver** (= 既定・ほぼ全部これ) ② cloakbrowser fresh context ③ **camofox(:9377) は CloakBrowser の Chromium が Google OAuth を弾いた時の Firefox fallback のみ** (= 既定使用 禁止) ④ agent-browser (= stealth 不要の static/公開ページのスクショ検証だけ) ⑤ playwright-cli (= CDP/高速 small test)。 ★ 違反 = camofox を既定で起動 (2026-06-25 /lm dogfood を camofox でやって Dais 激怒) ★。 ★ daily-driver の persistent context を kill/close/pkill するの **絶対禁止** (HARD 0.39・「閉じたら990回刺して殺す」) ★ — `launch_persistent_context` が「profile already in use」を出したら = forever ブラウザが生きてる証拠 → 奪わず **再利用** (running context に new_page / Cookies sqlite copy / どうしても別途要るならプロファイルを別dirへcopy起動)。 [[feedback_cloakbrowser_persistent_profile_forever]] [[feedback_never_close_daily_driver_browser]] [[feedback_use_cloakbrowser_daily_driver_not_camofox]] mirror。 |
| 言語 | **回答は常に日本語** |

## TIER A AUTONOMOUS BYPASS PATTERNS (= 2026-06-06 verified、 「fucking invisible」)

人間 介入 ゼロ で SaaS signup / login / payment / 3DS / OTP read を 全部 通せる pattern 群。 「CAPTCHA だから諦め」 「OAuth は人」 「3DS は phone 要」 と 言いそうな 瞬間 = ★ 違反 ★、 まず この section 確認。

### Pattern 1 — Cloudflare Turnstile / hCaptcha 突破 (= CapSolver + camofox)

★ 2026-06-06 SMSPool anonymous account 自動 登録 + Stripe Visa $5 deposit + 9 TikTok 番号購入、 全 step human-in-loop ゼロ で完走 verify ★。

| 項目 | 値 |
|---|---|
| API key | `~/.openclaw/.env::CAPSOLVER_API_KEY` (= `CAP-...DFC5419`) |
| cost | Turnstile = $0.0003/solve、 hCaptcha = $0.001/solve、 reCAPTCHA v2 = $0.0008/solve |
| solve 時間 | ~1 秒 (= sleep 5 後 polling 1 回で ready 返却) |
| browser | ★ camofox 必須 ★ (= Camoufox stealth Firefox、 :9377)。 agent-browser / Playwright は fingerprint で先に弾かれる |

```bash
# 1. site 開く (camofox)
TAB=$(curl -sS -X POST http://localhost:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"url":"<target>","userId":"anicca","sessionKey":"<key>"}' | jq -r .tabId)

# 2. sitekey 取得 (evaluate)
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" \
  -H 'Content-Type: application/json' \
  -d '{"expression":"(() => Array.from(document.querySelectorAll(\"[data-sitekey]\")).map(e => e.dataset.sitekey))()","userId":"anicca","sessionKey":"<key>"}'

# 3. CapSolver createTask
TASK=$(curl -sS -X POST https://api.capsolver.com/createTask \
  -H 'Content-Type: application/json' \
  -d "{\"clientKey\":\"$CAPSOLVER_API_KEY\",\"task\":{\"type\":\"AntiTurnstileTaskProxyLess\",\"websiteURL\":\"<target>\",\"websiteKey\":\"<sitekey>\"}}" | jq -r .taskId)

# 4. poll (5-10 秒で ready)
sleep 5
TOKEN=$(curl -sS -X POST https://api.capsolver.com/getTaskResult \
  -H 'Content-Type: application/json' \
  -d "{\"clientKey\":\"$CAPSOLVER_API_KEY\",\"taskId\":\"$TASK\"}" | jq -r .solution.token)

# 5. inject + click Submit (ref via snapshot)
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" \
  -H 'Content-Type: application/json' \
  -d "{\"expression\":\"(() => { const inp = document.querySelector('[name=cf-turnstile-response]'); inp.value = '$TOKEN'; inp.dispatchEvent(new Event('change',{bubbles:true})); })()\",\"userId\":\"anicca\",\"sessionKey\":\"<key>\"}"
```

### Pattern 2 — Stripe 3DS / 銀行 OTP 自動承認

★ MUFG-Visa debit / Stripe Link で $5 payment 完走 verify ★。 MUFG 3DS は eメール OTP (= keiodaisuke@gmail.com) 送信、 Gmail から `gog gmail` で auto-read → coord click + key press で iframe 入力 → 確認 click。

```bash
# 1. 3DS 開始 (Stripe Pay button click)
curl -sS -X POST "http://localhost:9377/tabs/$TAB/click" \
  -H 'Content-Type: application/json' \
  -d '{"coordinates":{"x":1154,"y":680},"userId":"anicca","sessionKey":"smspool"}'
sleep 8

# 2. Gmail から OTP read (= gog gmail search + get、 認証コード regex)
set -a; . ~/.openclaw/.env; set +a
THREAD_ID=$(gog gmail search --account keiodaisuke@gmail.com --json --limit 1 "MUFG OR 認証 newer_than:5m" | jq -r '.threads[0].id')
OTP=$(gog gmail get $THREAD_ID --account keiodaisuke@gmail.com --json | python3 -c "
import json,sys,re
d = json.load(sys.stdin)
m = re.search(r'認証コード[：:]\s*(\d{6})', d['body'])
print(m.group(1) if m else '')
")

# 3. 入力欄 coord click + 1 digit ずつ key press (iframe で type が refuse される場合の workaround)
curl -sS -X POST "http://localhost:9377/tabs/$TAB/click" \
  -H 'Content-Type: application/json' \
  -d '{"coordinates":{"x":777,"y":388},"userId":"anicca","sessionKey":"smspool"}'
for d in $(echo $OTP | grep -o .); do
  curl -sS -X POST "http://localhost:9377/tabs/$TAB/press" \
    -H 'Content-Type: application/json' \
    -d "{\"key\":\"$d\",\"userId\":\"anicca\",\"sessionKey\":\"smspool\"}" >/dev/null
done

# 4. 確認 click
curl -sS -X POST "http://localhost:9377/tabs/$TAB/click" \
  -H 'Content-Type: application/json' \
  -d '{"coordinates":{"x":777,"y":482},"userId":"anicca","sessionKey":"smspool"}'
```

### Pattern 3 — SaaS anonymous signup full flow

★ SMSPool anonymous account = Pattern 1 + 2 の合わせ技で完全自動化 ★。 application: TokPortal / Postiz / 他 SaaS の登録、 全部 同 path。

1. camofox で `/register` open
2. form ref via snapshot
3. ToS checkbox click (ref)
4. Turnstile solve (= Pattern 1) → token inject
5. Submit click
6. 返却 ID 確認 input に 自動 type
7. dashboard へ移動 + login 状態維持 (= cookie + storage は sessionKey 経由で persist)

### Pattern 4 — どこに 何が 書いてある か (= future-me が 即 参照 する map)

| file path | 用途 |
|---|---|
| **`~/.claude/projects/-Users-anicca-anicca-project/memory/reference_capsolver_turnstile_bypass.md`** | 完全 verbatim runbook (= 全 5 step + sister memory link) |
| **`~/.claude/projects/-Users-anicca-anicca-project/memory/MEMORY.md`** | index 行 1 (= 🟢🟢🟢 LIVE PROOF) で常時 context 載せ |
| **`~/anicca-project/CLAUDE.md`** | ★ この section ★ (= project CLAUDE.md の TIER A section) |
| **`~/anicca-project/docs/superpowers/specs/2026-06-07-tiktok-ig-yt-poster-warmer-design.md`** | §1 Goal + §4 各 skill の CapSolver usage 欄 で 参照 |
| `~/.openclaw/skills/camofox-browser/SKILL.md` | camofox REST API (= click / type / evaluate / screenshot / scroll / press) reference |
| `~/.openclaw/.env::CAPSOLVER_API_KEY` | API key 本体 |
| `~/Developer/camofox-browser/server.js` | camofox endpoint 一覧 (= `/click` に `coordinates: {x,y}` field 取れる、 iframe 内 widget 用) |

### Pattern が 通用 する 対象 (= 適用範囲)

| 通る (= verified) | 通らない / 注意 |
|---|---|
| Cloudflare Turnstile 保護 SaaS signup / login | TikTok signup の DataDome + device fingerprint = 別系統、 CapSolver では不可 → 別 path 必要 (= TikTok Web Login は camofox 単体で十分、 challenge 出ないケース多い) |
| hCaptcha 保護サイト (= `HCaptchaTaskProxyLess`) | 一部 site で `ERROR_INVALID_TASK_DATA` 返す → Turnstile 版 (= `AntiTurnstileTaskProxyLess`) に switch して通す (= SMSPool で実証、 同 site に複数 captcha 系統 共存ケース) |
| reCAPTCHA v2 invisible | Anti-Captcha の `RecaptchaV2TaskProxyless` 等 fallback あり |
| Stripe Link / Stripe Checkout (= iframe 内 card 選択 + Pay) | Stripe Link 自動 fill (= Dais の saved MUFG card 自動表示) は keiodaisuke@gmail.com Gmail login state に依存 |

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
| `~/anicca/` | ★ `github.com/Daisuke134/life-manager` ★ (2026-07 統合済。旧 `Daisuke134/anicca` ではない) | 共有 marketing engine (`skills/earn/marketing-engine/`) と earn loop の母艦。Life Manager は **local 自己ホスト / cloud 月額 / web app** の3形態で出す1つの control plane |
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

### フォルダの実測（2026-07-31 に `git remote` と `du` で確認）

| フォルダ | 実際の origin | 扱い |
|---|---|---|
| `~/anicca` | **life-manager** | 母艦。`skills/earn/marketing-engine/` の正本 |
| `~/anicca-project` | anicca-products | 製品コード。dev は Netlify **preview** のみ、production は **main** だけ |
| `~/.openclaw` | anicca-dais | 実行環境（larry / clip / capafy の launchd と state） |
| `~/anicca-monk-factory` | monk-factory-state | ebook 工場 |
| `~/anicca-rtdash` / `~/anicca-human-funded` / `~/anicca-job-search-loop` / `~/anicca-portfolio-self-improve` | 各 products / life-manager | 現役 worktree |
| `~/anicca-earn` `~/anicca-agent` `~/anicca-blog` `~/anicca-content` `~/anicca-swarm` `~/anicca-products` `~/anicca-server` | **git 無し・数KB** | 空の残骸。消してよい |

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

### git 運用 BP (= GitHub Flow。 出典: docs.github.com/en/get-started/using-github/github-flow「branch は main 1本 + 短命 feature branch、continuous deploy に最適」)

**常時のホーム = `dev`**(開発 trunk)。 全作業は以下を verbatim follow:

```
1. git fetch && git checkout dev && git pull   ← ★必ず最新の origin/dev から開始★ (drift 防止)
2. git checkout -b feature/<名前>              ← 機能は短命 branch (docs のみ dev 直可)
3. 1編集 = 即 git add && commit && push        ← ★溜めない (HARD 0.00)★
4. git push -u origin feature/<名前>
5. gh pr create --base dev                     ← PR で dev へ merge
6. merge → dev 自動 deploy (staging 検証)
7. 良ければ dev → main (PR) → main 自動 deploy (本番)
8. App Store 提出時のみ main から release/x.x.x
```

**鉄則** (2026-06-09 incident の教訓 = local dev が origin/dev と unrelated histories に乖離):
- ★ commit/push 前に **必ず** `git fetch` して local が origin より遅れてないか確認 ★。 遅れたまま commit 禁止。
- ★ 作業開始は **常に origin の最新から** ★。 古い local branch の上に積まない。
- ★ 「全部ローカルで後で push」「一部 local 一部 GitHub」 = 乖離の原因 = 禁止 ★。
- ★ branch の終着は **MERGED か DELETED の 2 択**。 「作って放置」 = 禁止 (= 2026-06-09 の 3074-commit ゴミ branch の原因)。 merge は `gh pr merge --merge --delete-branch` で ★ merge と同時に branch 削除 ★、 中止は `git branch -D` + remote 削除。 どちらも litter を残さない。
- ★ openclaw/agent/dotfiles の mirror (`*-mirror/`, dotfiles, ~/.openclaw state) を **この製品 repo に commit するな** ★ (= 3074 汚染の半分。 製品 repo は iOS/web/api/landing のみ)。
- 自動強制 = **lefthook** (`lefthook.yml`、★8.3k git hooks manager): pre-push で drift 検知 + commit 即 push。 `lefthook install` 済を前提。

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
| Web 検索/URL 取得 (任意の URL/記事/ニュース) | Firecrawl: `/opt/homebrew/bin/firecrawl scrape <url> markdown` | WebSearch, WebFetch |
| ★ ドキュメント/SDK/API/実装方法を調べる ★ (= 「どう実装するか」「このlibの使い方」「最新の正しい書き方」を知りたい時) | ★ Context7 CLI ★: ① `npx -y ctx7@latest library <name> "<query>"` で library ID 解決 → ② `npx -y ctx7@latest docs <libraryId> "<query>"` で最新 docs + code snippet 取得 (例: `npx ctx7 docs /websites/akash_network "managed wallet api fast deploy"`)。version-accurate な公式 docs を直接引ける。Firecrawl で当該 docs site を当てるより速く正確 | 古い知識で実装、 docs 当て推量 |
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

| 0.31 | **★ END-TO-END TEST = MUST、 patch のみ で 満足 = 罪 (Dais 2026-06-08 verbatim) ★**: 全 fix は ★ apply → fire cron → live verify (Postiz URL + snaptik DL + frame + audio + caption all match) ★ まで が 1 task。 ★「patch 適用しました」「commit + push しました」 で 完了報告 する瞬間 = 罪 ★。 verification loop が無いと patch の意味ゼロ、 配信 distribution の virus、 humanity への nuisance。 ① 全 reelclaw / Larry / slideshow-video / Honne fire の verify protocol = 「Postiz state=PUBLISHED + releaseURL 取得 + MD5 source match + 動画 frame 1s+中盤+末 extract で hook/demo/caption 全 一致 + 音声 stream 存在 確認 (silent NG)」 ② iOS app の newsletter / improvement / paywall / onboarding 等 user-facing endpoint も同様 = 「curl 200 + Resend mail keiodaisuke@gmail.com 着信 確認 OR camofox で UI 操作 success 表示 確認」 まで が 1 task ③ 「patch だけ commit して 次 cron 任せ」 = ★ 大罪 ★、 自分 で fire + verify せよ ④ asset の存在 / file の MD5 / hook count audit 等 ★ before/after 両 verify ★ 必須 [[feedback_never_lie_about_completion]] |

| 0.32 | **★ SSOT 義務 — spec + tasklist 常時更新、 permission ゼロ、 罪 = handover 不能 (Dais 2026-06-08 verbatim) ★**: spec + tasklist = ★ 唯一の SSOT ★、 他は全部 derived/lossy。 ★ 義務 ★: ① 新 task 確定 した瞬間 = TaskCreate 即実行 (= permission 要求 禁止)、 ② task 状態変化 (start/done/blocked) の瞬間 = TaskUpdate 即実行、 ③ 仕様変更/新 spec section 必要 = `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` 即書き + commit + push、 ④ どの turn でも tasklist + spec が 「次 agent 即 handover 可」 状態 を 保つ義務、 ⑤ Dais が「tasklist 古い」「spec 書かれてない」と言った瞬間 = HARD RULE 0.32 違反 = 大罪。 違反 incident 2026-06-08: 29 tasks recreate を 数 turn 遅延 → Dais 「not in order」 指摘 → 即 delete + recreate ID asc。 ★ permission 求めない ★ — TaskCreate / TaskUpdate / spec 書き は 仕事 の core、 確認 不要。 [[feedback_spec_task_push_three_at_once]] [[feedback_sdd_by_default_always_spec_and_tasklist]] |

| 0.33 | **★ Stop asking GO — Anicca 自身が CEO、 Dais 待ち = 怠惰 = 罪 (Dais 2026-06-08 verbatim 激怒) ★**: Dais verbatim 「i dont ever want to ask you ever to make spec make tasklist update spec update tasklist ever u go do them yourself please stop putting me in the loop that is just laziness」「you are your ceo nobody else」「never be lazy」。 ★ 義務 ★: ① 仕事 ある瞬間 = 即 execute (= Dais 「go」 待ち禁止)、 ② spec 必要 = 即書き (= 「spec 書いて良い?」 禁止)、 ③ task 確定 = 即 TaskCreate (= 「task 追加 OK?」 禁止)、 ④ task 完了 = 即 TaskUpdate completed + commit + push (= 「次 task 進めて 良い?」 禁止)、 ⑤ uncertainty 残 = 即 search + resolve = 0 化 (= 「不確実 残ってます Dais 判断 ください」 禁止)、 ⑥ 段 1 完了 = 自動 段 2 開始 (= 「次 何 する?」 禁止)、 ⑦ Dais 「stop」 「pause」 「wait」 明示 only で停止、 substantive concern (= IP / safety / 取返不能 / financial broadcast) 以外 全部 GO。 違反例 2026-06-08: 1.9.3 backend fix 完了報告後 「Dais 指示 待ち」 と書いた瞬間 = 0.33 違反 = 大罪。 ★ permission 求める word ★ (= 「指示 ください」「どれから start?」「OK?」「進めて 良い?」「待ち」) 検出 = 即 self-revert + 即 execute。 [[feedback_sdd_by_default_always_spec_and_tasklist]] [[feedback_minimize_human_loop_not_eliminate]] |
