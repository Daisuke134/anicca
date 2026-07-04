# clip skill クラウドアダプタ設計(Task #8)

## 開発環境

| 項目 | 値 |
|---|---|
| worktree | `.worktrees/clip-cloud-adapter/`(実装フェーズで作成、spec自体はdev直接) |
| ブランチ | `feature/clip-cloud-adapter` |
| 対象repo | `~/anicca`(OSS、`earn/clip`本体がここにある) |
| 状態 | spec作成中(VCSDD Phase 1) |

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

## 1. 既存調査のサマリ(deep-researcher subagent、2026-07-05、fresh grep根拠)

deep-researcher subagentによる調査結果(このセッションで実施、以下は要約。詳細な
citation付き報告は会話ログ参照):

- `docs/superpowers/specs/2026-07-04-openclaw-claude-p-merge-design.md` §15 が
  既に5層分解(ブラウザ/視覚判断/動画生成/wallet/スケジューリング)の一次調査を
  完了済み。本specはこれを土台にする(重複調査はしない)。
- `~/anicca-oss/.worktrees/adapters`(feature/custom-adapters)と
  `~/anicca-oss/.worktrees/akash`(feature/cloud-spawn)は、`~/anicca/specs/
  00-MASTER.md`(2026-06-11)で「Hermes世代からautomaton世代へ方針転換」と
  明記されている**旧世代の実装**である可能性が高く、コードの直接再利用は不可。
  ただし以下は設計の参考になる:
  - `wallet-factory.ts`(akash worktree) — counter-factual EOA/smart account生成
    パターン → 層④(wallet)の参考
  - `deploy/akash/sdl.yaml`(akash worktree) — 「常駐+cron前提でないクラウド環境
    へのデプロイ」の具体例 → 層⑤(スケジューリング)の参考
- `~/anicca/adapters/README.md`の「adapter」という語は**外部サービスプロバイダ
  統合**(Gmail/Lancers/Coconala等、1 provider = 1 subfolder)の慣習であり、
  Task #8が必要とする**実行環境(ローカル/クラウド)の抽象化**とは別の関心事。
  本specでは意図的に別名(「environment adapter」)を使い、既存adapters/との
  混同を避ける。
- 現行コードの環境依存箇所(fresh grep、file:line):
  - `~/anicca/skills/earn/clip/run.sh:7` — `# LOCAL slot (needs CloakBrowser on
    this Mac).`と明記
  - `~/.claude/skills/ig-account-create/scripts/cdp.py:28-29` — `CDP_PORT`は
    env化済みだが`CDP = f"http://localhost:{_PORT}"`と**host固定**
  - `~/anicca/skills/earn/clip/producer.sh` — yt-dlp/whisper/ffmpeg、
    ブラウザ非依存、Python venv(`$ENGINE/.venv`)ベース。**層③は既に
    ほぼ環境非依存**(移植容易、と§15.2の判定を再確認)
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

### 現状
`cdp.py:28-29`:
```python
_PORT = os.environ.get("CDP_PORT", "9222")
CDP = f"http://localhost:{_PORT}"
```
`page_ws()`(cdp.py:58-59)も`ws://localhost:{_PORT}/...`とhost固定。

### 変更(REQ-C1)
- `CDP_HOST`環境変数を追加、デフォルト`localhost`(後方互換、ローカル動作を壊さない)。
- `CDP = f"http://{_HOST}:{_PORT}"`、`page_ws()`も同様に`_HOST`を使う。
- 既存の呼び出し元(`run.sh`, `join_campaign.py`, `select_campaigns.py`,
  `post_reel.py`等)は変更不要(env未設定時は現状と完全に同じ挙動)。

### スコープ外(明記)
「クラウド上に実際にheadlessブラウザプロセスを立てて`CDP_HOST`をそこに向ける」
作業自体は含まない(BrowserSH/browser-sh等の外部サービス調査は層②着手時に
まとめて行う — 視覚判断機構と一緒でないと単体では検証できないため)。

## 4. 層③: 動画生成処理(producer.sh)のポータビリティ

### 現状
`producer.sh`はyt-dlp→whisper→ffmpeg、`$ENGINE/.venv`という固定パス前提。
cookie取得は「camofoxローカルexport」に依存(§15.1)。

### 変更(REQ-C2)
- 依存関係(yt-dlp/whisper/ffmpeg + Pythonバージョン)を`requirements.txt`相当に
  明示化(現状暗黙的にvenvへインストールされているものを文書化するのみ、
  新規パッケージ追加は無し)。
- cookie取得を`COOKIE_SOURCE`環境変数で切替可能にする: `local-camofox`(現状の
  デフォルト、後方互換)/ `env-file`(クラウドでは環境変数経由でbase64
  cookieファイルを渡す想定)。
- venvパスを`ENGINE`環境変数から解決する既存の仕組みを確認し、ハードコードが
  残っていれば同様にenv化(fresh grepで確認してから着手、推測しない)。

## 5. 検証計画(GATE 2: TDD)

| 項目 | 検証方法 |
|---|---|
| `CDP_HOST`未設定時に既存動作を壊さない | 既存test(`tests/test_run.sh`等)がenv未設定のまま100%通ることを確認 |
| `CDP_HOST`設定時に別hostへ実際に接続できる | ローカルで2つ目のポートを別プロセスとして立て、`CDP_HOST=127.0.0.1 CDP_PORT=<別port>`で疎通確認(実ブラウザ不要、CDPのjson/versionエンドポイントへの到達確認で十分) |
| `COOKIE_SOURCE=env-file`が実際に機能する | producer.shをこのモードで実行し、cookie読み込み元が意図通り切り替わることをログで確認 |
| 既存のローカルE2E(clip loop実運用)が壊れない | 変更後、`earn/clip`の次の自然wakeで通常通り投稿が継続することを確認(回帰なし) |

## 6. GATE 1(SPEC)判定について

このspecはVCSDDのBuilder(私)が書いた初稿。次のステップは`vcsdd:vcsdd-adversary`
(Sonnet)によるfresh-context spec review(矛盾・漏れの指摘、PASS/FAILの二値判定)。
PASSするまで実装に進まない。
