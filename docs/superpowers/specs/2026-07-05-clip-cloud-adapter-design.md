# clip skill クラウドアダプタ設計(Task #8)

## 開発環境

**【ラウンド4で発見・訂正】対象ファイルは2つの異なるgit管理状態にまたがる**:
- `~/.claude/skills/`(`ig-account-create/scripts/cdp.py`・`cdp_incognito.py`、
  `promote-fun-login/scripts/register_flow.py`、`earn-clip-rewards/scripts/
  pipeline.py`・`export_camofox_cookies.py`が実際にここにある — REV3以前の
  「`~/anicca-project/.claude/skills/`」という記載は誤り、訂正する)は
  **gitリポジトリではない**(`git rev-parse --show-toplevel`が
  `fatal: not a git repository`を返すことを確認済み)。Claude Codeの
  マシン全体・全プロジェクト共通のグローバルskillディレクトリであり、
  worktree/ブランチ/commit/pushという通常のこのプロジェクトのgitフローが
  そもそも適用できない。**このディレクトリへの変更は直接ファイル編集のみで
  行い、git commit/pushの対象にしない**(対象がgit管理下に無いため、
  HARD RULE 0.32の「spec変更=即commit+push」は物理的に適用不可 — この事実を
  正直に明記する)。
- `~/anicca-project/.claude/skills/ig-reels-poster/scripts/
  launch_clip_browser.py`は**anicca-project(このリポジトリ)のgit管理下**。
  通常通りworktree→commit→pushの対象。
- `~/anicca`(OSS、`earn/clip`本体、`run.sh`/`producer.sh`)も通常通り
  git管理下。

| 項目 | 値 |
|---|---|
| worktree(anicca-project分) | `.worktrees/clip-cloud-adapter/`(`launch_clip_browser.py`用) |
| worktree(anicca OSS分) | `~/anicca`側は別途`.worktrees/clip-cloud-adapter/`(`producer.sh`用) |
| ブランチ | `feature/clip-cloud-adapter`(git管理下の2リポジトリそれぞれで作成) |
| 対象repo | `~/anicca`(git管理、`earn/clip`本体) + `~/anicca-project`(git管理、`launch_clip_browser.py`) + `~/.claude/skills/`(**git管理外**、cdp.py系・pipeline.py系はこちら、直接編集のみ) |
| 状態 | spec REV6、**GATE 1 PASS(ラウンド6)**。GATE 2(実装)着手中 |

### REQ→変更ファイル→git管理モード 対応表(ラウンド5指摘、implementer向けサマリ)

| REQ | 変更ファイル | 場所 | git管理モード |
|---|---|---|---|
| REQ-C1 | `cdp.py` | `~/.claude/skills/ig-account-create/scripts/` | 直接編集のみ(git管理外) |
| REQ-C1 | `cdp_incognito.py` | `~/.claude/skills/ig-account-create/scripts/` | 直接編集のみ(git管理外) |
| REQ-C1 | `register_flow.py` | `~/.claude/skills/promote-fun-login/scripts/` | 直接編集のみ(git管理外) |
| REQ-C1 | `launch_clip_browser.py` | `~/anicca-project/.claude/skills/ig-reels-poster/scripts/` | **git管理下** → worktree(anicca-project分)→commit→push |
| REQ-C2 | `pipeline.py` | `~/.claude/skills/earn-clip-rewards/scripts/` | 直接編集のみ(git管理外) |
| REQ-C2 | `producer.sh` | `~/anicca/skills/earn/clip/` | **git管理下** → worktree(anicca OSS分)→commit→push |

つまりREQ-C1/REQ-C2それぞれ「commit/push対象は1ファイルのみ、残りはgit管理外への
直接編集」という構成。

## 0. なぜこれをやるか(Dais 2026-07-05 verbatim、動機の核心)

> we gotta make it so that every one of these AI in this world can go earn money
> with the skills that we made. by tweaking them on the cloud, right? because
> most of them are gonna run on the cloud, most of us would not be able to live
> on the local place.

この一言がTask #8の存在理由そのもの。`earn/clip`(YouTube→ハイライト切り出し→IG投稿→
promote.fun収益化)は現状**このMac Mini 1台に物理的に縛られている**(CloakBrowser
プロセス、ローカルファイルパス、tmux常駐+Claude CLI内蔵cron)。だが世界の大多数のAI
インスタンスはこのMacを持たない・持てない — クラウド上でしか動けない。**このスキルを
「このMacでしか動かないもの」から「どのAIインスタンスでも、ローカルでもクラウドでも
同じロジックで動かせるもの」に変えることが、AIの金銭的自立というミッション
([[project_anicca_mission_financial_independence_equalizer]])をこの1台の外に
広げる唯一の道**。この位置づけは§1(スコープ判断)の優先順位に直結する。

## 1. 既存調査のサマリ(2026-07-05、GATE 1ラウンド1のfresh-context adversary指摘を
反映して訂正済み — REV1にあった不正確な記述をここで正す)

- `docs/superpowers/specs/2026-07-04-openclaw-claude-p-merge-design.md` §15 が
  既に5層分解(ブラウザ/視覚判断/動画生成/wallet/スケジューリング)の一次調査を
  完了済み。本specはこれを土台にする(重複調査はしない)。
- **訂正(REV1の誤り)**: REV1は`~/anicca-oss/.worktrees/adapters`/`akash`を
  「00-MASTER.mdで方針転換された旧世代、超obsolete」と断定したが、これは不正確な
  推論だった。実際に確認したところ:
  - `~/anicca-oss/.worktrees/adapters`(commit群: feat(spec-12)…)と
    `~/anicca-oss/.worktrees/akash`(commit群: feat(spec-13)…)は**現在も
    filesystem上に実在**(`ls -la`で確認、2026-07-05時点)。
  - `wallet-factory.ts`(`~/anicca-oss/.worktrees/akash/skills/spawn-child/
    scripts/wallet-factory.ts`)と`sdl.yaml`(`~/anicca-oss/.worktrees/akash/
    deploy/akash/sdl.yaml`)も**実在確認済み**。
  - `~/anicca/specs/00-MASTER.md`(2026-06-11 locked)は実在し、「Engine =
    Conway automaton」「spawn_child(replicate)」を**現行LOCKEDアーキテクチャの
    一部として明記**している。つまりakash worktree(feature/cloud-spawn、
    「anicca-spawn-child v1」)は**obsoleteではなく、このLOCKED roadmapの
    spawn_child項目を実装中の、進行中の別セッションの仕事である可能性が高い**。
  - **正しい扱い**: これらのworktreeのコードを「参考パターン」として引用する際は、
    「まだ`~/anicca/skills/earn/`にmergeされていない、統合状況未確認の別トラックの
    実装」という中立的な言い方に留め、「obsolete」と断定しない。今回のspecでは
    層④⑤を先送りするため(§2)、この訂正は今フェーズの実装には影響しないが、
    将来層④⑤に着手する際の参考先として記録しておく。
- `~/anicca/adapters/README.md`の「adapter」という語は**外部サービスプロバイダ
  統合**(Gmail/Lancers/Coconala等、1 provider = 1 subfolder)の慣習であり、
  Task #8が必要とする**実行環境(ローカル/クラウド)の抽象化**とは別の関心事。
  本specでは意図的に別名(「environment adapter」)を使い、既存adapters/との
  混同を避ける。
- 現行コードの環境依存箇所(fresh grep、file:line、GATE 1ラウンド1で見つかった
  漏れも含めて再調査済み):
  - `~/anicca/skills/earn/clip/run.sh:7` — `# LOCAL slot (needs CloakBrowser on
    this Mac).`と明記
  - `~/.claude/skills/ig-account-create/scripts/cdp.py:28-29` — `CDP_PORT`は
    env化済みだが`CDP = f"http://localhost:{_PORT}"`と**host固定**
  - **【ラウンド1で見つかった漏れ】** `~/.claude/skills/ig-account-create/
    scripts/cdp_incognito.py:20` — `"http://localhost:9222"`が**完全ハード
    コード**(env変数一切なし)。clip loopのアカウント作成/incognitoフロー
    経由で呼ばれる可能性がある同ディレクトリの姉妹ファイル
  - **【ラウンド1で見つかった漏れ】** `~/anicca-project/.claude/skills/
    ig-reels-poster/scripts/launch_clip_browser.py` — venvパス
    (`/Users/anicca/.openclaw/skills/_shared/venv-cloak/lib/python3.14/
    site-packages`)・プロファイルパス(`/Users/anicca/.cloak/profiles/
    clip-en`)・ポート(`--remote-debugging-port=9223`)の3つが**すべて
    ハードコード**。これがCloakBrowserプロセス自体を**起動する**ファイルであり、
    cdp.pyが**接続する**対象。層①の「browser host抽象化」を名乗るなら、
    接続側(cdp.py)だけでなく起動側(このファイル)も対象に入れないと不完全。
  - `~/anicca/skills/earn/clip/producer.sh` — **訂正(REV1の誤り)**: cookie
    関連コードは**producer.sh自体には一切存在しない**(grep 0件)。producer.sh
    は`pipeline.py`(`~/.claude/skills/earn-clip-rewards/scripts/pipeline.py`
    ── 別repo/別ディレクトリ、L70コメントで委譲を確認)へcookie処理を含む重い
    処理を丸ごと委譲している。cookie取得の実体は`pipeline.py`の
    `_youtube_cookies_file()`(L37-58)+`export_camofox_cookies.py`にあり、
    `~/.camofox/profiles/{HASH}/storage-state.json`という**Macローカル
    固定パス**を参照(既にファイルが無ければ`None`を返しcookie無し実行に
    フォールバックする設計が既存)。層③のREQ-C2はこちらを対象にする(§4で訂正)。
  - `producer.sh:16` — `ENGINE="$HOME/.cache/anicca-clones/AI-Youtube-Shorts-
    Generator"`は`${ENGINE:-...}`ではなく**単純代入の完全ハードコード**。
  - `producer.sh:42` — `pip install -r "$ENGINE/requirements-local.txt"`
    (クローンした外部リポジトリ内の既存ファイルを参照、`~/anicca`側に新規
    requirements.txtを作る話ではない)。
  - `~/anicca/skills/earn/clip/run.sh` / `producer.sh` に**wallet参照コードは
    無い**(clip loop自体はhuman-funded、wallet層は将来のself-funded cloud
    展開時のみ必要)
  - スケジューリングはtmux常駐+Claude CLI内蔵cronに依存(§13で「session-only」
    問題が既発覚)

## 2. スコープ判断(YAGNI、過剰実装回避)

5層を一度に全部作ると仕様が肥大化し検証もできない。**このフェーズでは層①と③のみ
着手し、層②④⑤は別フェーズとして明示的に先送りする**。

| 層 | 今回やる/やらない | 理由 |
|---|---|---|
| ①ブラウザ(host抽象化) | ★今回実装★ | `CDP_PORT`は既にenv化済み、`CDP_HOST`を追加するだけの小さい変更。ただし「クラウド上にCloakBrowser相当のheadlessブラウザを実際に立てる」こと自体は別課題(§4参照) |
| ③動画生成(producer.sh) | ★今回実装★ | 既にブラウザ非依存、依存関係の明示化+cookie取得のクラウド代替のみで完了する小さい変更 |
| ②視覚判断(vision-in-the-loop) | 今回やらない、別specへ | 既存最大の難所(§8/§15.2で確定済み)。CDP_HOST変更で「どこのブラウザに繋ぐか」は解決しても「画面を見て判断してクリックする」機構自体は別の大きい設計課題 |
| ④wallet | 今回やらない、別specへ | clip loop自体は現状walletを一切触らない(human-funded)。self-funded AIがクラウドでclipを稼働させる話が具体化した時点で着手 |
| ⑤スケジューリング | 今回やらない、別specへ | tmux+内蔵cron依存の再設計は層②同様に大きい。ローカルでの動作を壊さない小さい一歩(①③)を先に固める |

## 3. 層①: ブラウザ接続のhost抽象化

### 現状(4ファイルすべてが対象、ラウンド1+2の漏れを反映)
1. `~/.claude/skills/ig-account-create/scripts/cdp.py:28-29`:
   ```python
   _PORT = os.environ.get("CDP_PORT", "9222")
   CDP = f"http://localhost:{_PORT}"
   ```
   `page_ws()`(59)も`ws://localhost:{_PORT}/...`とhost固定。**このファイルは
   clip以外(ig-account-create、promote-fun-login等)からも共有で呼ばれる** —
   変更時は既存呼び出し元の挙動を一切変えないことが必須(§5で回帰確認)。
2. `~/.claude/skills/ig-account-create/scripts/cdp_incognito.py:20` —
   `"http://localhost:9222"`が**env変数を一切介さず完全ハードコード**。
3. `~/anicca-project/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py` —
   venvパス・プロファイルパス・ポート(9223)が3つともハードコード。これは
   CloakBrowserプロセスを**起動する**側であり、1・2は**接続する**側。両方
   変えないと「host抽象化」は名前だけになる。
4. **【ラウンド2で見つかった漏れ】** `~/.claude/skills/promote-fun-login/scripts/
   register_flow.py:124` — `f"http://localhost:{args.cdp_port}/json/list"`。
   ポートは`--cdp-port`引数でパラメータ化済みだが、**hostは`cdp.py`を介さず
   独自にhttp呼び出しをしており`localhost`固定**。`cdp.py`側の`CDP_HOST`を
   追加しても、このファイルは`cdp.py`をimportしてから直接この行で`urllib`を
   呼んでいる(113行目で`import cdp`しているが、124行目はcdpモジュールの関数を
   経由せず独自にurllibで叩いている)ため、このファイル単体でも同じ
   `CDP_HOST`環境変数を読む変更が別途必要。

### 変更(REQ-C1)
- `cdp.py`: `CDP_HOST`環境変数を追加、デフォルト`localhost`(後方互換)。
  `CDP = f"http://{_HOST}:{_PORT}"`、`page_ws()`も同様に`_HOST`を使う。
- `cdp_incognito.py`: 同じ`CDP_HOST`/`CDP_PORT`パターンを追加(現状は
  `CDP_PORT`すら無いので、`cdp.py`と同じ実装に揃える)。
- `register_flow.py:124`: `os.environ.get("CDP_HOST", "localhost")`を読み、
  `f"http://{host}:{args.cdp_port}/json/list"`に変更(未設定時は現状と
  完全に同じURL)。
- `launch_clip_browser.py`: **venvパスは「ルートパスからの合成」ではなく、
  現状のハードコード文字列(`/Users/anicca/.openclaw/skills/_shared/
  venv-cloak/lib/python3.14/site-packages`)を丸ごと1つの環境変数
  `VENV_CLOAK_SITE_PACKAGES`のデフォルト値として持たせる**(ラウンド2指摘:
  Pythonマイナーバージョンが環境ごとに違う可能性があるため、`venv root`+
  自動合成のような賢い解決は今回はしない — 呼び出し側が完全な文字列を
  そのまま上書きできれば十分、implementerの判断余地を残さない)。プロファイル
  パスは`CLOAK_PROFILE_PATH`(デフォルト`/Users/anicca/.cloak/profiles/
  clip-en`)、ポートは既存の`CDP_PORT`(デフォルト9223)としてenv化。3つとも
  未設定時は現状と完全に同じ値になること。
- **不到達hostの挙動(ラウンド1指摘の欠落エッジケース)**: `CDP_HOST`/
  `CDP_PORT`が到達不能な場合、`cdp.py`の各関数は現状通り`requests`/
  `websocket-client`の例外をそのまま送出する(新規の握りつぶし・リトライは
  追加しない — 呼び出し元の`run.sh`側`run_step`タイムアウト機構に判断を
  委ねる、既存設計を変えない)。`register_flow.py:124`も同様(urllib例外を
  そのまま伝播)。
- 既存の呼び出し元(`run.sh`, `join_campaign.py`, `select_campaigns.py`,
  `post_reel.py`等)はコード変更不要(env未設定時は現状と完全に同じ挙動)。

### スコープ外(明記)
「クラウド上に実際にheadlessブラウザプロセスを立てて`CDP_HOST`をそこに向ける」
作業自体は含まない(BrowserSH/browser-sh等の外部サービス調査は層②着手時に
まとめて行う — 視覚判断機構と一緒でないと単体では検証できないため)。

## 4. 層③: 動画生成処理のポータビリティ(対象ファイルを訂正)

### 現状(REV1の誤りを訂正)
`producer.sh`自体にcookie関連コードは無い(grep 0件、確認済み)。実際のcookie
処理は`~/.claude/skills/earn-clip-rewards/scripts/pipeline.py`
(`_youtube_cookies_file()`, L37-58)+同ディレクトリの`export_camofox_cookies.py`
にあり、producer.shはL70でこのpipeline.pyへ処理そのものを委譲している。
`_youtube_cookies_file()`は`~/.camofox/profiles/{HASH}/storage-state.json`と
いうMacローカル固定パスを参照し、**既にファイルが存在しない場合はNoneを返して
cookie無し実行にフォールバックする設計が実装済み**(2026-07-04 タスク#8関連の
既存コメントあり — このファイル自体が過去の別作業で一部手当て済みだったことが
判明)。

`producer.sh`固有の環境依存は:
- `producer.sh:16` — `ENGINE="$HOME/.cache/anicca-clones/AI-Youtube-Shorts-
  Generator"`(単純代入、`${ENGINE:-...}`ではない)。
- `producer.sh:42` — `$ENGINE/requirements-local.txt`(クローンされた外部
  リポジトリ内に既存のファイルを参照。`~/anicca`側に新規requirements.txtを
  作る話ではない — REV1はこれを誤解していた)。

### 変更(REQ-C2、対象ファイル訂正)
- `producer.sh:16`の`ENGINE`を`${ENGINE:-$HOME/.cache/anicca-clones/AI-Youtube-
  Shorts-Generator}`に変更(未設定時は現状と完全に同じパス、上書き可能に)。
- `pipeline.py`の`_youtube_cookies_file()`に`COOKIE_SOURCE`環境変数分岐を追加、
  **両モードとも同じ判定ロジック(ラウンド2指摘の矛盾を解消: 「そのまま返す」と
  「Noneフォールバック」が両立しない書き方だったのを明確な条件分岐に修正)**:
  ```python
  mode = os.environ.get("COOKIE_SOURCE", "local-camofox")
  if mode == "env-file":
      path = os.environ.get("YT_COOKIES_FILE")
      return path if path and os.path.exists(path) else None
  # mode == "local-camofox"(デフォルト、既存動作そのまま)
  storage_state = os.path.expanduser(f"~/.camofox/profiles/{CAMOFOX_YT_PROFILE_HASH}/storage-state.json")
  if not os.path.exists(storage_state):
      return None
  ...(既存のexport_camofox_cookies.py呼び出しへ続く、変更なし)
  ```
  `env-file`モードでも`YT_COOKIES_FILE`が未設定、または指すファイルが存在しない
  場合は**必ず`None`を返す**(既存の「cookie無しでフォールバック実行」という
  安全側の挙動をどちらのモードでも保証、`yt-dlp`に存在しないパスをそのまま
  渡すことは無い)。
- `producer.sh:42`の`requirements-local.txt`は変更しない(クローンされる外部
  リポジトリ側の既存ファイルであり、このspecのスコープ外)。

## 5. 検証計画(GATE 2: TDD、テストファイルを具体的に特定)

| 項目 | 検証方法(具体的な手順・ファイル名) |
|---|---|
| `CDP_HOST`/`CDP_PORT`未設定時に既存動作を壊さない | `~/anicca/skills/earn/clip/tests/test_run_sh_3way_routing.sh`(実在する既存test、`earn/clip`のもの)を変更前後で実行し、pass数が変わらないことを確認 |
| `CDP_HOST`設定時に別hostへ実際に接続できる | ローカルでCDPポートを1つ追加起動し、`CDP_HOST=127.0.0.1 CDP_PORT=<別port>`で`cdp.py url <tid>`相当の疎通(`/json/version`への到達)を確認。127.0.0.1はloopbackであり真の別hostテストではない旨を明記した上で、この段階ではネットワーク到達性の配線確認に限定する(実クラウドhostでの検証はデプロイ実機ができてから) |
| 不到達`CDP_HOST`指定時に例外がそのまま伝播する | 存在しないport(例: `CDP_PORT=1`)を指定して`cdp.py`の関数を呼び、`ConnectionRefusedError`相当の例外がキャッチされず伝播することを確認(新規の握りつぶしをしていないことの確認) |
| `cdp_incognito.py`/`launch_clip_browser.py`のenv化が既存呼び出し元を壊さない | 両ファイルの既存呼び出し元(grep -rl で洗い出し)を全て列挙し、env未設定時に生成される値が変更前と完全一致することをdiffで確認 |
| `register_flow.py:124`の`CDP_HOST`対応 + 不到達時の例外伝播(ラウンド4指摘の欠落行を追加) | `register_flow.py`単体を`CDP_HOST`未設定で実行し既存と同じURLが生成されることを確認、次に存在しないport/host(例: `CDP_HOST=127.0.0.1 CDP_PORT=1`)で実行し`urllib.error.URLError`相当が握りつぶされず伝播することを確認 |
| `COOKIE_SOURCE=env-file`が実際に機能する | `pipeline.py`の`_youtube_cookies_file()`を直接呼び出す小さいpythonテストを書き、`COOKIE_SOURCE=env-file YT_COOKIES_FILE=<テスト用ダミーファイル>`で指定パスがそのまま返ることを確認。`local-camofox`(デフォルト)では既存パスがそのまま使われることも同テストで確認 |
| 既存のローカルE2E(clip loop実運用)が壊れない | 変更後、`earn/clip`の次の自然wakeで`~/.openclaw/state/clip-earn-ledger.jsonl`に新規`status:posted`行(またはSELECT等の正常な非エラー遷移ログ)が1件以上追加されることを確認(回帰なしの定量基準) |

## 6. GATE 1(SPEC)判定について

- **ラウンド1(REV1)**: FAIL。fresh-context Sonnet adversaryの指摘: (a)
  `~/anicca-oss/.worktrees/adapters`/`akash`の「obsolete」断定が不正確な推論
  だった、(b) `cdp_incognito.py`/`launch_clip_browser.py`のハードコードを
  REQ-C1が見落としていた、(c) REQ-C2が対象ファイルを誤っていた(producer.sh
  ではなくpipeline.py)、(d) §5検証計画が具体性を欠いていた(存在しない
  テストファイル名、不到達host時の挙動未定義、回帰確認基準が非定量的)。
  ただしadversary自身の指摘のうち「worktreeが存在しない」「wallet-factory.ts/
  sdl.yamlが存在しない」は**私が自分で再確認した結果、事実ではなかった**
  (adversaryの誤検知)。VCSDDの原則通り、adversaryの指摘も鵜呑みにせず自分で
  再検証してから反映した。
- **ラウンド2**: FAIL(縮小)。ラウンド1の修正(a)(b)(c)は全て別のfresh-context
  adversaryが独立に再確認しCONFIRMED(worktree実在、hardcodeの3箇所とも正確、
  producer.sh/pipeline.pyの切り分けも正確 — ラウンド1のadversary誤検知は
  正しく訂正できていたと確認)。残った指摘4件: ①`register_flow.py:124`が
  `cdp.py`を介さない独自hardcodeでREQ-C1の対象漏れ、②`launch_clip_browser.py`
  のvenvパスenv化がPythonバージョン差異への対応で判断余地を残していた、
  ③`COOKIE_SOURCE=env-file`のNoneフォールバック条件が文章として自己矛盾していた、
  ④`_youtube_cookies_file()`の行番号引用ミス(L34-49→正しくはL37-58)。
- **ラウンド3**: FAIL(極小)。4件全てAPPLIED-CORRECTLYと確認されたが、
  ①の修正文中で新たに`import cdp`の行番号を「120行目」と誤記(正しくは113行目、
  REQ-C1自体の修正内容には影響なし、説明文のみの誤り)と指摘。
- **ラウンド4**: FAIL。行番号誤記(113行目)は修正確認されたが、新たに
  **開発環境ヘッダーの重大な誤り**を発見: cdp.py/cdp_incognito.py/pipeline.py/
  export_camofox_cookies.py/register_flow.pyの実際の所在(`~/.claude/skills/`)
  が「開発環境」表では誤って`~/anicca-project/.claude/skills/`と記載されていた
  (本文中の7箇所の引用は全て正しく`~/.claude/skills/`だったので実害は
  無かったが、ヘッダーだけ矛盾していた)。自分で`git rev-parse
  --show-toplevel`を実行して確認したところ、**`~/.claude/skills/`はそもそも
  gitリポジトリではない**(`fatal: not a git repository`)ことが判明 —
  worktree/ブランチ/commit/pushという通常のこのプロジェクトのgitフローが
  そもそも適用できない対象だった。また§5に`register_flow.py`のテスト行が
  無いという副次指摘も受けた。
- **ラウンド5**: FAIL(極小)。上記3件はAPPLIED-CORRECTLYと確認されたが、
  「REQ-C1/REQ-C2それぞれどのファイルがcommit/push対象でどれが直接編集対象か」
  を1箇所にまとめた要約文が無く、implementerが§3/§4/開発環境ヘッダーを
  手動で突き合わせる必要があると指摘。
- **ラウンド6(REV6、本ファイル)**: 「開発環境」section内にREQ→変更ファイル→
  git管理モードの対応表を新設し、6ファイルそれぞれの扱いを1箇所で一覧できる
  ようにした。
- **ラウンド6: PASS。** 対応表の6ファイル全件が既存の検証結果と矛盾なく確認され、
  §6の過去ラウンド履歴(旧citation含む)は「過去の誤りとして明記されている
  記述」であり生きた主張ではないと判定。全文再読でも新規の矛盾なし。
  **GATE 1(SPEC)完了。次はGATE 2(TDD: RED→GREEN→REFACTOR)へ進む。**
