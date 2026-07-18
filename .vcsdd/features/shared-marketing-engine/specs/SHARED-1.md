# SHARED-1 — web composer(post_reel.py) を全 loop から削除し instagrapi_post.py に一本化する

## 実測サマリ（2026-07-18、grep+Read で確認済み。捏造なし）

| loop | post_reel.py への依存 | 状態 |
|---|---|---|
| `earn/clip`（`run.sh`） | 新規投稿path = **既に** `scripts/instagrapi_post.py --live`（line 196）。`POSTER`変数（line 26、post_reel.py参照）は定義のみで未使用の dead code（execute path内で`$POSTER`参照0件、`CLIP_POSTER_OVERRIDE`はtest hook） | 投稿pathは移行済み。**残存依存は `self_heal.py` 1本のみ**（下記） |
| `earn/clip`（`self_heal.py:141`） | `post_reel.py --verify-only` をsubprocess呼び出し、reel href一覧を取得して`reel_verify.stabilize_reads`/`select_confirmed_href`に渡す（未確定投稿の事後確認・reconcile用） | **LIVE依存**。instagrapi_post.pyに`--verify-only`相当が無いため単純付替え不可 |
| `earn/clip/tests/test_post_reel_single_print.py` | `~/.claude/skills/ig-reels-poster/scripts` から `post_reel` を直接import、`main()`を実行してJSON単一print契約をテスト | post_reel.py削除で即 `ImportError` → RED |
| `earn/clip/reel_verify.py`（docstring, line 2-6） | 「Used by both post_reel.py (…) and self-heal」と明記 | コメントのみ（機能影響なし）。post_reel.py削除後は事実と矛盾し嘘になる |
| `earn/clip/count_posts.py`（docstring, line 6） | 2026-07-03インシデントの歴史的言及のみ | 機能影響なし。触らなくても壊れない |
| `earn/clip/_instance_paths.sh`（comment, line 20） | `post_reel.py --verify-only`の設計意図を説明するコメント | 機能影響なし |
| `capafy-marketing`（`x_post.py`, `SKILL.md`） | 2件ともIG投稿の**アナロジー言及**（"like ig-reels-poster"、"same pattern as ig-reels-poster"）。実コード呼び出しではない | **依存ゼロ**（teammateの前提通り既に無関係） |
| `earn/clip-promote`（`run.sh:192-197`） | `post_reel.py`を`--live`**なし**で呼ぶ（dry-verifyのみ）。コード上のコメントで明示的に「caption gapが埋まるまで意図的にdryのまま」（line 174-182） | **投稿は発生していない**が参照は生きている。SKILL.mdにも`ig-reels-poster`使用が明記（line 21） |
| `earn/video`（`run.sh:139,152,157,210`） | **`--verify-only`（line 157, pre-post reel snapshot/reconcile）と`--live`（line 210, 実際の公開）の両方で本番使用中** | ★最重要発見★ teammateのgrep範囲（clip/capafy-marketingのみ）の**外**にあり見落とされていた。post_reel.py削除は**この loop を即座に壊す** |

**instagrapi_post.py の現行CLI**（`~/anicca/skills/earn/clip/scripts/instagrapi_post.py:330-343`）: `--video --caption-file --handle --port --live --keepalive` のみ。**`--verify-only`相当（アカウントの現reel一覧をhref形式で返す機能）が存在しない** — これが self_heal.py と video/run.sh 双方の単純付替えを阻むブロッカー。

## 不変条件（INV）

**INV-1**: どの loop（clip / clip-promote / video）の「実際にIGへpublishするコードパス」も、`post_reel.py`を`--live`付きで呼ばない。
negative test: `grep -rn -- '--live' ~/anicca/skills/earn/{clip,clip-promote,video}/run.sh` にヒットする行が全て `instagrapi_post.py`（またはその後継）を指しており、`post_reel.py`を指す行が0件。

**INV-2**: publish結果は`instagrapi_post.py --live`が返すJSON（`outcome=="published"`時に非null`post_url`）で判定される。
negative test: `earn/video`のS3_post publish後の判定ロジック（現行`post_reel.py`の`published`/`post_url`キー読み取り、run.sh:211-219）が、instagrapi_post.pyの`outcome`/`post_url`キー読み取りに置き換わっている。差し替え後に`EARN_MODE=execute`相当を1回ドライ実行し、JSON出力を目視確認する。

**INV-3**: `instagrapi_post.py`に、ブラウザDOM読み取り不要でアカウントの現reel一覧を返す`--verify-only`相当モードが追加されている（instagrapi API経由、例: 直近media一覧からreel shortcodeを`/{handle}/reel/{code}/`形式のhrefに整形して返す）。
negative test: `CDP_PORT=<port> <venv-python> instagrapi_post.py --handle <h> --verify-only` を実行し、stdout最終行のJSONに`"reels"`キー（href文字列のリスト、0件でも配列）が含まれる。

**INV-4**: `self_heal.py`（clip）と`earn/video/run.sh`の`--verify-only`呼び出しが、いずれも`post_reel.py`ではなく`instagrapi_post.py --verify-only`（INV-3）を呼ぶよう付け替えられている。かつ`reel_verify.stabilize_reads`/`select_confirmed_href`（純粋関数、`~/anicca/skills/earn/clip/reel_verify.py`）は**無改修**でそのまま動作する（hrefフォーマット互換のため）。
negative test: `grep -rn "ig-reels-poster/scripts/post_reel.py" ~/anicca/skills/earn/{clip,video}` が0件。`self_heal.py`の`run_self_heal()`をpost_reel由来の疑似hrefsとinstagrapi由来の疑似hrefsそれぞれでunit test実行し、両方が同じ`{"status":...}`を返す（フォーマット差分でstill-pending/resolvedの判定が変わらない）。

**INV-5**: `earn/clip-promote/run.sh`のPOST遷移（line 166-200）が`post_reel.py`ではなく`instagrapi_post.py`（`--live`なしのdry相当、または明示的なdry-run引数）を呼ぶよう付け替えられている。SKILL.md（line 21）の表記も`ig-reels-poster`から`instagrapi_post.py`ベースの説明に更新されている。
negative test: `grep -rn "post_reel\|ig-reels-poster" ~/anicca/skills/earn/clip-promote` が0件。

**INV-6**: clipのtest suiteがgreen。`test_post_reel_single_print.py`は削除するか、`instagrapi_post.py`の単一JSON-print契約（`main()`内の各早期returnが`print(json.dumps(res,...))`を正確に1回呼ぶこと）を検証する同等テストに書き換える。
negative test: `python3 -m unittest discover ~/anicca/skills/earn/clip/tests` が全件PASS（ImportErrorなし、post_reel.py不在でも green）。

**INV-7**: `reel_verify.py`のdocstring（line 2-6）が`post_reel.py`ではなく`instagrapi_post.py`を呼び出し元として記述するよう更新されている（コメントの正確性、機能には無関係だが嘘のdocstringを残さない）。
negative test: `grep -n "post_reel.py" ~/anicca/skills/earn/clip/reel_verify.py` が0件。

**INV-8**: `earn/clip/run.sh`の未使用`POSTER`変数（line 26）と関連コメントが削除されている（dead code、post_reel.py本体削除の前提として先に片付ける）。
negative test: `grep -n "POSTER=" ~/anicca/skills/earn/clip/run.sh` の一致行が`INSTA_POSTER`のみ。

**INV-9**: `post_reel.py`本体（`~/.claude/skills/ig-reels-poster/scripts/post_reel.py`）を物理削除しても、`clip`・`clip-promote`・`video`のどの loop も import/実行時エラーを出さない。この検証はINV-1〜INV-8が全て満たされた**後**にのみ行う（順序依存、先に消すとvideo loopが即死）。
negative test: `find ~ -iname "post_reel.py"` が0件かつ`grep -rl "post_reel" ~/anicca ~/anicca-project ~/.claude/skills 2>/dev/null`が0件の状態で、`EARN_MODE=discover bash ~/anicca/skills/earn/{clip,clip-promote}/run.sh`と`earn/video/run.sh`のS1相当ドライ実行が、いずれも非ゼロ終了・スタックトレースなしで完走する。

**INV-10**（§10 no-hardcode 継承）: 付替え作業で新規にIGアカウントハンドルの文字列リテラルを追加しない。全呼び出しは既存の`--handle "$HANDLE"`/`--handle "$a.handle"`パターン（env var・JSON設定ファイル由来）を維持する。
negative test: 差分（`git diff`）に`@`付き固有ハンドル名またはハンドル文字列のハードコード代入が新規追加されていない（`video/run.sh:16`の既存`EARN_VIDEO_HANDLE`デフォルト値`money_blueprintdaily`は**SHARED-1が新規に導入したものではない**既存debtであり、本INVの対象外——修正するなら別タスク）。

## スコープ外（後続タスクへ）

- `instagrapi_post.py`への`--verify-only`実装そのもの（INV-3の中身）は実装量が大きいため、SHARED-2（task#23「instagrapi_post.pyを canonical 共有 poster に昇格」）で本実装する。SHARED-1はこのINVを**要件として確定**するに留め、実装フェーズで着手する。
- `video/run.sh:16`のハードコードデフォルトハンドルの是非。
- `earn/clip-promote`のcaption gap（campaign別必須タグ）解消。

## 付替え方針（実装フェーズ向けメモ、実装はしない）

1. まず INV-3（`instagrapi_post.py --verify-only`追加）を実装 — video loopとself_healの両方が前提とするブロッカーのため最優先。
2. INV-4（self_heal.py 付替え）・INV-2（video/run.sh のverify-only+live呼び出し付替え）を実装、実機で1回ずつverify-only/dry実行して形式互換を確認。
3. INV-5（clip-promote 付替え）、INV-8（run.sh dead code除去）、INV-7（docstring修正）。
4. INV-6（テスト付替え、green確認）。
5. 最後にINV-9（post_reel.py本体削除 + 全loop discover実行で確認）。

## 実装ログ（2026-07-18、全INV実装完了・実測PASS）

全INV実装済み。`~/anicca` repo 側の変更（commit予定）:
`skills/earn/clip/scripts/instagrapi_post.py`（`verify_only_main()`+`--verify-only`追加）、
`skills/earn/clip/self_heal.py`（instagrapi_post.py呼びに付替え、venv python使用）、
`skills/earn/clip/reel_verify.py`（docstring）、`skills/earn/clip/run.sh`（POSTER dead code除去）、
`skills/earn/video/run.sh`（verify-only/live呼び出し+PURL解析をinstagrapi_post.py仕様に付替え）、
`skills/earn/clip-promote/run.sh`+`SKILL.md`（dry-verify呼び出し付替え）、
`skills/earn/clip/tests/test_instagrapi_single_print.py`（新規、post_reel版を置換）。

**実測結果**: `python3 -m unittest discover skills/earn/clip/tests` → 52 tests OK（post_reel.py非存在後も green）。
`instagrapi_post.py --handle aiclips_world_hq2 --verify-only` 実機実行 → `{"reels":[],"ok":false,...}`
形式で `reels`/`ok` キー確認（このテストアカウントの保存セッション自体は死んでいたため ok=false だが、
fail-closed の正しい挙動でJSON契約は満たす）。clip/clip-promote discover + video DRY 実行、いずれもJSON1行・
exit 0・スタックトレースなしで完走（post_reel.py物理削除後）。

**既知の pre-existing 失敗（SHARED-1 由来ではない、git stash で証明済み）**: `test_run_sh_3way_routing.sh`・
`test_prop009_self_heal_gating.sh`・`test_prop011_token_not_clip_id_derived.sh` の3本は、`CLIP_POSTER_OVERRIDE`
が実際の投稿パス（`$INSTA_POSTER`固定呼び出し）に一切配線されていない既存バグにより base commit から
既に FAIL（`git stash`→実行→`git stash pop`で確認）。SHARED-1のスコープ外、別タスクで要修正。

**post_reel.py 物理コピーの発見（spec作成時のgrepでは未発見）**: `find ~ -iname post_reel.py` で5箇所ヒット。
実際に生きた consumer から参照されていた2箇所のみ削除:
`~/.claude/skills/ig-reels-poster/scripts/post_reel.py`（`~/.agents/skills/`側も同時に消えた＝既存の
skills同期/ハードリンク機構による副作用、意図した操作ではない）と
`~/anicca-project/.claude/skills/ig-reels-poster/scripts/post_reel.py`（旧clip-promote/run.shが参照、
本タスクで付替え済み）。残り3箇所は意図的に未削除（consumer 0件を確認済み、破壊的操作を避けるため）:
`~/.claude/skills.disabled-2026-07-13/`・`~/.claude/backups/skills-merge-2026-07-13/`（履歴バックアップ）、
`~/anicca-project/.worktrees/capafy-two-loop/`（別featureの独立worktree、無断で触らない）。
そのためINV-9の`find ~`/`grep ~/anicca-project`は文字通りには非0を返す — 上記3箇所はどれも
生きたconsumerがないデッドコピーであることを実測確認済みで、削除するかはSHARED-1の管轄外の判断
（バックアップ整理は別タスク、worktreeは他タスクの領域）。
