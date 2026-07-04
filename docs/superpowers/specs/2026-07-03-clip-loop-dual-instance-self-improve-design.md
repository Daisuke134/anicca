# Clip-Rewards: Dual-Instance (claude-p + ClawRouter) + Self-Improvement Loop — Design

**Date**: 2026-07-03 · **Branch**: `feature/clip-rewards` · **Owner**: 私 (myclaude, human-funded)
**Inspiration**: やまもとりゅうじ氏の記事(Claude=切り抜きページのオペレーター論、2026-07-03 Dais共有)
**Prior state**: `2026-06-28-clip-rewards-state.md` (D-01〜D-59、5日前から更新停止 = 実質stall)

## 0. 記事から抽出した設計原則(北極星)

1. **再生数のために作るな。再生数の"先にある出口"のために作れ。** → 出口(payout先)が確定しないユニットは着手しない。
2. **Claude=オペレーター、ツールではない。** 1本ずつの手動切り抜きではなく、「発信者選定→出口選定→生成→投稿→採点→改善」を1つの自然文指示で回し続ける系にする。
3. **判断はモデルに委ねる、regexハードコードしない。** どの瞬間を切るか(ジャンル別の型)、どの発信者/出口を選ぶかは、SKILL.mdの自然言語指示 + 実データで判断させる。
4. **週次の採点ループが無いと「ただのギャンブル」。** 掴みの型・発信者・プラットフォーム・再生数・視聴維持・保存・コメント・クリックを記録し、勝ちパターンに寄せる。
5. **初日から詰め込まない。** 新規アカウントは段階的投稿(記事: week2は1日2-3本)。

## 1. 現状の根本問題(2026-07-03 調査で確認、要再修正)

- `producer.sh` が `~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv` 消失で5日間 fail-closed。`~/clips/queue/` が空。
- claude-p (tmux `anicca-clip-core`, Dais の Claude subscription) だけが動いており、ClawRouter (自己資金、`~/anicca/runtime/loop/brain.mjs`) は clip-earn に一切関与していない。
- 出口(promote.fun state machine)はコード完成・テストGREENだが、自走させる Sutando loop harness が未着工 = 休眠。
- 週次採点ループが存在しない。

## 2. To-Be アーキテクチャ

### 2.1 インスタンス分離(絶対に混ぜない)

| | claude-p インスタンス | ClawRouter インスタンス(新規) |
|---|---|---|
| 実行基盤 | tmux + `claude --dangerously-skip-permissions` (Dais subscription) | genesis `~/anicca` loop 経由、ClawRouter (:8402) 課金 |
| wallet | `~/.cloak/myclaude-solana.json` (既存、xxKC33TY...) | 新規keypair(このユニット専用、myclauseと非重複) |
| clip accounts | `~/.cloak/clip-accounts.json` (既存、@aiclipsvault等) | 新規ファイル、別ハンドル群、既存accountと重複禁止 |
| ledger | `~/.openclaw/state/clip-earn-ledger.jsonl` (既存) | 別ファイル(instance別に分離、dashboard集計時にmerge) |
| 判断層(モデル) | Claude Sonnet | ClawRouterがルーティングするモデル(現行 `auto` 方針) |
| 決定論コード(producer/run.sh/poster.sh) | **共通**、`ANICCA_INSTANCE` env で wallet/account-list/ledger pathを切替 | 同上 |

理由: 1 wallet を複数callerが共有すると出金が食い合う(既存メモリ実例)。判断ロジック(SKILL.md自然言語)は共有できるが、実行基盤(wallet/account/ledger)は完全分離必須。

### 2.2 self-improvement loop(記事の週3パターンを実装)

```
毎投稿 → ledgerに記録: {creator, hook_type, platform, views, retention, saves, comments, clicks_to_exit}
週次 wake →
  1. ledgerを集計、hook_type × platform でパフォーマンス比較
  2. 勝ちパターン(views/saves上位)を SELECT の優先順位に反映
  3. 負けパターン(記事: 「教育系が死んでるなら未練を捨てて、やめる」)を自動デプライオリタイズ
  4. producer/run.shが5日以上fail-closedし続けている等の異常は self/issue-dev 経由で自動issue化
```

### 2.2.5 producer.sh 自己修復(2026-07-04 追加、タスク#9)

★ 実インシデント: `~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv` はディスク掃除で
定期的に消える(このセッション中だけで2回発生)。従来は「人間/devセッションが気づいて手で
再構築」していた = HARD RULE #-2「人間をloopに入れるな」違反。★

**根本原因(2026-07-04 実機調査で確定)**: `~/scripts/disk-cleaner.sh`(launchd
`com.anicca.disk-cleaner`、1時間毎)の `sweep "$HOME/.cache/anicca-clones" 0` が
`anicca-clones` 配下の **mtime 24h超の全ファイル/ディレクトリを無差別削除**する
(`find ... -mtime +0` は age=0でも「24時間以上前に変更」を意味する)。`.venv/bin/python`
等の拡張子なしバイナリは `is_protected()` の保護パターン(拡張子/パス名ベース)に
一致しないため毎回消える。実測: 2026-07-04 04:11-04:21 の cleaner 実行ログで
`freed +-10GB` = このタイミングで engine ディレクトリ(clone+venv、数GB)が丸ごと
削除されたことと符合。producer.sh 側の自己修復だけでは「直っても1時間以内にまた
消される」いたちごっこになるため、**二重修正**とする:

1. **disk-cleaner.sh 側(根本原因の是正)**: `is_protected()` に
   `*/anicca-clones/*/.venv/*` を追加し、`sweep anicca-clones` の対象から
   永続 venv を除外する。one-off clone (venv を持たない読み取り専用clone) は
   従来通り即時掃除対象のまま。
2. **producer.sh 側(防御的自己修復、Task #9 本題)**: 起動時に venv 欠落を検知したら、
   自分でリポジトリの再clone (`--depth 1`) + venv再構築 + pip installを行い、
   そのまま処理を継続する。①が将来別の原因で破られても、②が単独で無人回復する。

日次cron(`ai.anicca.clip-producer`、AM3:17)が完全に無人で回復する。人間/dev/私が
二度と気づいて直す必要が無くなる。

**実機検証(2026-07-04、完了)**:
1. `timeout` 無しで producer.sh を実行 → 実際に `engine venv missing` で即exitすることを
   再現確認(fabricationでなく実ログ)。
2. disk-cleaner.sh に `*/.cache/anicca-clones/*/.venv/*` 保護パターン追加(v7→v8)。
3. producer.sh に self_heal_engine() 実装 → venv欠落状態から実行 → 実際に
   `git clone --depth 1` + `python3 -m venv` + `pip install -r requirements-local.txt` を
   自力実行し `"self-heal OK — engine venv rebuilt, continuing"` → pipeline.py起動まで
   自動遷移することを実機確認(PID 22537、/tmp/producer-selfheal-*.log)。
4. **追加で発見した根本バグ**: pipeline.py が長尺ソース(今回2時間38分=9518s)を
   丸ごとDL+丸ごとfaster-whisper文字起こししており、self-healしても現実的な時間内に
   完走しない設計だった(旧cronログの3連続失敗もこれが真因の可能性)。
   `~/.claude/skills/earn-clip-rewards/scripts/pipeline.py` に `get_duration()` +
   `--download-sections` slicing(SLICE_SECONDS=360、動画中間360秒のみDL)を追加、
   daily.sh の既存パターンを踏襲。
5. **E2E実機再検証(修正後、fresh evidence)**: producer.sh を再実行 → sliced download
   (`*4579-4939`)→ whisper → highlight pick → 9:16 crop → caption burn → verify_clip
   gate 通過 → `~/clips/queue/6xlmaorRY0w_EN.mp4` 生成、全工程 約4分で完走(旧: 10分
   timeoutでも終わらず)。生成物を独立に ffprobe 確認: 202×360(9:16比率)、
   60.0s、video+audioストリーム両方存在(silent NGでない)、MD5
   `9f23f8090d9dfca0ef1657b20a94beb6`。verify_clip.sh gate は producer.sh 内で
   実際に通過(fail-closeなら"not queued"emitでqueueに残らない設計、今回は
   queueに実在=通過の証拠)。

**Task #9 完了条件(4点とも満たした)**: ① self-heal実装 ② disk-cleaner根本原因是正
③ 実機でvenv欠落→自己修復→処理継続を確認 ④ 実際にqueueへ検証済みclipが生成される
ところまでE2E確認。日次cron(AM3:17)は次回から無人で完走する見込み。

**★ 追補(2026-07-04、Dais指摘「クリーナーが複数あると危険」で発覚した続報)★**:
disk-cleaner.shの`.venv`保護追加だけでは不十分だった。実際には**独立した3つの
クリーナー**が同じ`~/.cache/anicca-clones`を別ロジックで掃除しており、うち2つが
未修正のまま稼働し続けていた:

| # | 実体 | 頻度 | anicca-clones挙動(修正前) |
|---|---|---|---|
| ① | launchd `com.anicca.disk-cleaner` → `~/scripts/disk-cleaner.sh` | 1時間毎 | mtime24h超を無差別削除(最初にvenv保護追加済み) |
| ② | launchd `ai.anicca.disk-janitor` → `~/.openclaw/skills/anicca-disk-janitor/run.sh` | **5分毎** | mtime24h超を無差別削除、venv保護なし |
| ③ | OpenClaw cron `anicca-disk-hourly`(LLM経由) → `~/.openclaw/skills/disk-janitor/run.sh` | **10分毎** | `rm -rf anicca-clones/*` **年齢条件なし・毎回無条件** |

③は特に致命的で、self-healでvenvを再構築しても最大10分で無条件削除される設計
だった。Dais指摘「クリーナーが複数あると複雑でバグの温床になる、1つでいいのでは」
を受け、**3つを1つに統合**:

1. `~/scripts/disk-cleaner.sh` を v9 として全機能統合(①のlaunchd実績を正としてベース化、②③のユニーク機能=codex-runtimes/openai-curated掃除、sao-content-factory/tiktok-marketing/honne-ai掃除、sessions.json rotate等を統合)、`clean_anicca_clones()`共通関数で`.venv`保護を一本化
2. launchd頻度を300秒(5分毎)に統一、`StartInterval`を`PlistBuddy`で書換+`launchctl unload/load`で反映
3. ②`ai.anicca.disk-janitor.plist` → unload + `.disabled-2026-07-04`にリネーム(復元可能)
4. ③OpenClaw cron `anicca-disk-hourly`(ID `79b05373-4edf-4a2e-a0b2-06681d37efd0`) → `~/.openclaw/cron/jobs.json`で`enabled:false`に変更

**実機検証で2つの追加バグを発見・修正**:
- 統合直後の初回実装は`find "$HOME" -type d -name "$name" ...`を11パターン分
  ループ、$HOME全体をI/O律速でフルスキャンし**5分超**かかることが判明(`sample`で
  プロセスが`read`でI/O待ち、状態`UN`と確認)。300秒間隔のlaunchdで前回インスタンス
  が終わる前に次が起動し、手動実行も重なって**最大9プロセス同時稼働**という
  实機事故を確認。
- 対策① find対象を1回の`-o -name`combined queryに統合(11回→1回)
- 対策② find対象を`$HOME`全体でなく既知プロジェクトルート(`anicca-project`,
  `anicca`, `.openclaw`, `.hermes`, `Downloads`)に限定
- 対策③ `mkdir`によるatomic lock(macOSに`flock`が無い為)を追加、前回インスタンス
  が`kill -0`で生存確認できれば新規実行はサイレントskip

**最終実機検証(2026-07-04、fresh evidence)**: 単独実行で`EXIT:0 ELAPSED:12s`、
ログに`v9 done`正常記録、`.venv`生存確認。同時に2プロセス起動しても両方
正常完了(ロックがinstance跨ぎの多重起動を防ぐ設計、高速化で重複自体がほぼ
起こらなくなった)。launchd `com.anicca.disk-cleaner`のみ稼働、他2つは無効化済み。

### 2.3 出口(payout)の優先順位

記事原則1「出口のために作れ」に従い、着手順は **出口の確度が高い順**:
1. promote.fun (`~/anicca/skills/earn/clip-promote/`) — コード完成済、Sutando harness作るだけで動く。最短。
2. ClipAffiliates — wallet bind API発見済だがcampaign枯渇中(D-22)、定期リトライのみ。
3. Whop — GraphQL cookie-replay実証済だがjoin mutationがiframeにブロックされ未解決。
4. Vyro — CPM$3(最良)だが未着手、要調査。

## 3. VCSDD実装順序(タスク化、この直後にTaskCreate)

1. producer.sh 復旧(venv再構築 or 依存を軽量化、disk-cleanup耐性を持たせる)
2. `ANICCA_INSTANCE` env切替をproducer/run.sh/poster.shに追加(claude-p既存動作を壊さない後方互換で)
3. ClawRouterインスタンス用の新規wallet+account群+ledger初期化 + genesis loopから呼べるエントリポイント
4. 週次self-improvementループ(集計スクリプト + SELECTへのフィードバック)
5. self/issue-dev への stall検知配線(queue空N日 → 自動issue)
6. promote.fun Sutando loop harness (`clip-promote-cli.sh` + healthcheck + launchd) — 出口を1つ確定させる本命

各項目は vcsdd-init → spec → red → green → adversary → E2E(実際にIG/YT投稿URL確認)で進める。

## 4. 2026-07-04 実機監査で発見した追加課題(Dais「クリーナーが危険」指摘への調査から派生)

Dais から disk-cleaner の安全性 + claude-p/ClawRouter の実稼働状況を問われ、実機ログ・実プロセスを
監査した結果、当初のタスク#9スコープを超える複数の実問題を発見した。

1. **disk cleaner 3重問題**(解決済み): `com.anicca.disk-cleaner`(1h毎)/`ai.anicca.disk-janitor`
   (5分毎)/OpenClaw cron `anicca-disk-hourly`(10分毎、LLM経由)の3つが独立に`anicca-clones`を
   別ロジックで掃除しており、うち`anicca-disk-hourly`は年齢条件すら無く毎回無条件`rm -rf`。
   1つ(`~/scripts/disk-cleaner.sh` v9、5分毎)に統合、他2つは無効化(disabled、復元可能)。
   統合直後に$HOME全体11回findループがI/O律速で5分超かかり最大9プロセス重複起動する事故を
   実機確認→find統合+スコープ限定(既知プロジェクトルートのみ)+mkdir atomicロックで解決。
   実機12秒完走・venv保護を確認。

2. **tmuxソケット消失→4loop重複起動**(解決済み): clip/affiliate/video/bounty の4つのclaude-p
   loop全てで`/tmp/anicca-*-tmux.sock`が消失、5分毎healthcheckが「死んでいる」と誤判定して
   新規セッションを重複起動(元のtmuxサーバー自体は生存していた為、新旧セット計8プロセスが
   並行稼働、Load Avg 8.99まで悪化)。孤立した古いプロセスをkillして解消。ソケット消失自体の
   根本原因は未特定(Task登録、disk-cleanerのsweepはtype f/dのみでsocket非対象と確認済み)。

3. **ClawRouter用producer.sh実行経路が存在しない**(発覚、対応中): ClawRouterのledger実機調査
   (`~/.anicca/state/ledger.jsonl`)で、`earn/clip`スロットは自律的に75回選択されているが全て
   `"queued_clip=none"`で空振りと判明。原因: 日次producer cron(`ai.anicca.clip-producer`、
   AM3:17)にANICCA_INSTANCE環境変数が無く claude-p専用。ClawRouter用に
   `ai.anicca.clip-producer-clawrouter.plist`(AM3:47、ANICCA_INSTANCE=clawrouter)を新規作成・
   ロード済み。instance分離導入(本spec §2.1)以前は実際にClawRouterがclaude-p専用アカウント
   `@aiclipsvault`へ誤投稿していた形跡もledgerに残っている(分離配線後は解消を確認)。
   ClawRouter専用IGアカウントがまだ無い為(REQ-102未達成)、E2E生成確認はTask #6で継続中。

4. **pipeline.py: get_duration()のcookie無し呼び出しバグ**(修正済み): sliced-download判定用の
   `get_duration()`が`--cookies-from-browser`無しでyt-dlpを呼んでおり、YouTube bot検出
   ("Sign in to confirm you're not a bot")で失敗→durationがNone→sliceされずフル長(2h38m)を
   ダウンロードしてしまう実機事象を確認。`yt_dlp()`と同じcookie引数を追加して修正。

5. **CloakBrowser cookie復号失敗**(原因確定、対応方針決定): 上記4の修正後もyt-dlpの
   `--cookies-from-browser chromium:~/.cloak/profiles/clip-en`が
   `"Extracted 0 cookies from chromium (12 could not be decrypted)"`で実質機能せず。

   **調査(2026-07-04)**: `security find-generic-password -s "Chromium Safe Storage"`が
   `"could not be found in the keychain"`で失敗。`security list-keychains`を実行すると
   `/Library/Keychains/System.keychain`のみが返り、**`login.keychain-db`がsearch listに
   含まれていない**ことが根本原因(このマシンの無人/ヘッドレス運用セッションが正規のGUI
   ログインセッションのsecurity contextを持っていない)。`security unlock-keychain`や
   `security list-keychains -s`で修正を試みたが、Bashツール経由の各コマンド呼び出しが
   別プロセス(別security session)扱いになる為、設定が永続化されず失敗。

   **yt-dlp公式ソース(`yt_dlp/cookies.py`)を直接確認**: `MacChromeCookieDecryptor`は
   `_get_mac_keyring_password()`(`security find-generic-password`呼び出し)経由のみで、
   Linux版にある`peanuts`固定キーのフォールバック(`--password-store=basic`時に使われる)は
   **macOS向けには実装されていない**。つまりyt-dlp自体の使い方を変えても、Chromiumベースの
   ブラウザ(CloakBrowser含む)である限りmacOS Keychainは回避不能と判明。一方
   `_extract_firefox_cookies()`は`cookies.sqlite`を暗号化なしで直接読むのみで、
   OS keychainに一切依存しない。

   ★ Dais 判断(2026-07-04)★: CloakBrowser daily-driver優先の既定方針
   (`feedback_use_cloakbrowser_daily_driver_not_camofox`)は維持しつつ、今回は
   「ブラウザ選択」ではなく「cookie暗号化方式がOS依存で、Chromiumである限り原理的に
   回避不能」という技術的制約が理由の例外として、**camofox(Firefox)を新規プロファイルで
   採用してよい**との明示許可を得た。「何が起きたか・なぜ移行したか」を必ず記録すること、
   というDais指示によりこの節を記録。CloakBrowser(Chromium)側の運用は変更せず、YouTube
   cookie取得専用にcamofoxプロファイルを1つ追加する(既存プロファイルの置き換えではない)。

   **実装(完了)**: camofox(:9377、userId=anicca/sessionKey=clip-yt)でYouTubeにアクセスし
   既存Googleログインを確認(92件のYouTube/Google cookie、平文JSON `storage-state.json`に
   保存済み、profile hash `45136ac6a5321e8fcfc75c3b306c5714`)。
   `~/.claude/skills/earn-clip-rewards/scripts/export_camofox_cookies.py`を新規実装し
   storage-state.json→Netscape cookies.txtへ変換。`pipeline.py`の`get_duration()`/
   `yt_dlp()`を`--cookies-from-browser chromium:...`から`--cookies <camofox export>`に
   切替。追加発見: yt-dlpの新JSチャレンジ解決システム(EJS)が`--remote-components
   ejs:github`無しだと解決スクリプトDLをスキップし、n-challenge解決失敗→全フォーマット
   ゼロになる不具合も併せて修正。

   **実機E2E検証(2026-07-04、fresh evidence)**: producer.sh実行 → cookie付きbot検出突破
   確認(`--list-formats`で360p実フォーマット取得、以前は`sb0-3`storyboardのみ) →
   sliced download(9146s→360s)→ whisper → crop → caption → verify_clip gate通過 →
   `~/clips/queue/`へ実clip生成。さらに claude-p 自身(anicca-clip-core tmux、毎時cron)
   も同修正の恩恵を受け、手動介入なしに別動画(`Xs94KBeIiAo`)を自律生成・queueへ格納
   したことを確認(lifetime posts 4→11に増加)。Task #8完了。

6. **Task #7(tmuxソケット消失→重複起動)の再発と根本対策(完了)**: §4.2で応急処置(kill)
   のみだった問題が、その後12時間で**3回再発**(04:55/10:51/15:46/17:01の4世代が同時に
   積み重なり、clip/affiliate/video/bounty各loopで最大8プロセス、計32プロセス並行稼働を
   実機確認)。gigのみ既存のbackoff機構(`gig-healthcheck.sh`)により暴走せず0プロセス
   (健全)だった対比が根本対策の方向性を示した。

   **対策**: gigの実証済みパターン(pkill by process name + 60分5回backoff)を
   clip/affiliate/video/bountyの4つの`*-healthcheck.sh`全てに移植(v2)。ソケットが
   消失していても`pkill -f "claude --name <session>"`でプロセス名ベースに確実にkillして
   から再起動するため、「ソケット切断=別プロセスと誤認して重複起動」が構造的に起きなく
   なる。ソケット消失自体の根本原因(disk-cleanerのsweepはtype f/d限定でsocket非対象と
   確認済み、それ以外の原因は依然未特定)は残るが、重複が積み重なる実害は解消。

   実装: `~/anicca/skills/earn/{clip,affiliate,video,bounty}/*-healthcheck.sh`をv2に
   書換、commit+push済み。修正反映前に発生していた重複(4世代×4loop)は手動で整理済み、
   全loop 1プロセスずつの状態に復帰したことを確認。

タスク化(#6〜#8、TaskList参照): #6 ClawRouter producer経路E2E確認、#7 tmuxソケット消失原因
+healthcheck重複防止、#8 cookie復号失敗の根本解決(camofox Firefox cookie方式へ切替、実装中)。
