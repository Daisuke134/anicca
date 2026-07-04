# affiliate / bounty を clip-promote型の純粋状態機械へリファクタ(Task #15)

## 開発環境

| 項目 | 値 |
|---|---|
| worktree | `~/anicca/.worktrees/affiliate-bounty-statemachine/`(実装フェーズで作成) |
| ブランチ | `feature/affiliate-bounty-statemachine` |
| 対象repo | `~/anicca`(git管理、`earn/affiliate` + `earn/bounty`) |
| 状態 | spec REV2(GATE 1ラウンド1 FAIL、根本的な設計ミスを修正) |

## 0. なぜこれをやるか(2026-07-05ヘルスチェックで発見した実バグ)

fresh evidence(2026-07-05):
- **affiliate**: `~/affiliate/queue/`に未投稿カルーセルが**7件**滞留(最新は07-04 17:40作成)。`~/affiliate/posted/`は**2件のみで最後は6/30**。**さらに重大な発見**: commission検知スクリプト
  (`~/.claude/skills/earn-affiliate-slideshow/scripts/amazon_report.py`)と記録スクリプト
  (`record-affiliate-earn.mjs`)は実在するが、**一度も実行呼び出しされていない**
  (`affiliate/run.sh:5,90`に`record-affiliate-earn`という**文字列の言及**はコメントとして
  存在するが、実際に`node .../record-affiliate-earn.mjs`を呼ぶコードはどこにも無い —
  GATE 1ラウンド1のadversaryが指摘した通り「grep hit 0」ではなく「コメント言及のみで
  実行呼び出しは0件」が正確な表現)。`~/.smtm/earn-loops/affiliate/earn-ledger.jsonl`も
  **存在しない**。つまりこのloopには最初からMEASURE/RECORDフェーズの配線が無く、6/30に投稿した
  2件についても一度もコミッションを確認していない。
- **bounty**: `state/gated.json`にsurvivor 1件($10 bounty、qwer80371832/loadertest#3)を発見済みだが
  `state/attempts.jsonl`が**一度も作られていない**(=一度もPRを試みたことがない)。

### 根本原因(§22.2、既存specとの整合)

`docs/superpowers/specs/2026-07-04-openclaw-claude-p-merge-design.md` §22.2で診断済み:
clip-promoteは`decide.py`という純粋状態機械が「1 wakeにつき1つの境界の明確な遷移」を返し、
run.shがそれを実行する設計。self-healは状態ファイル駆動で**毎wake確実に前進する**。

affiliate/bountyは対照的に、`<name>-cli.sh`のSTARTUP promptが「①cron自己修復→②コンテンツ
作成→③producer→④投稿→⑤mail報告」という複数ステップを**1つの巨大な自然言語プロンプトに
詰め込み、1ターンでLLMに全部やらせる**設計。実際に観測した通り、①に時間を使うと②③④に
到達せずターンが終わる — これが「詰まる」原因であり、しかも「クラッシュ検知」ベースの
自己修復機構(`.{name}-core-selfheal-request.json`)では検知できない(tmuxは生きているため)。

## 1. 参照モデルの選び直し(GATE 1ラウンド1 FAILを受けた根本的な訂正)

### 1.1 何を間違えたか

REV1は「clip-promote」を参照実装として選んだ。しかしadversaryの指摘(finding #2:
MEASUREがPOSTを構造的にブロックする)を受けて検証した結果、これは**間違った参照実装
だった**と判明した。理由:

clip-promoteは「**1度に1つのcampaignにしか関与できない**」という現実(1 campaignに
JOINしたら、そのcampaignのライフサイクルが終わるまで別campaignには進めない)を
モデル化しているため、「1 wake = 1つのグローバルphase」という設計が正しい。

しかしaffiliateは**その前提が成り立たない**: 投稿済みだが未計測のアイテムが複数
同時に存在してよく(実際6/30に2件postedのまま放置されている)、かつqueueには
常に新しいアイテムが積み上がる。「今アイテムAをMEASURE中だから、アイテムB(queueの
先頭)をPOSTできない」という制約は**存在しない現実の制約をでっち上げている**
だけであり、まさにこの制約のせいで現在の7件滞留と同じ問題を新しい形で再生産する
ところだった(adversary finding #2は正しい)。

### 1.2 正しい参照実装は`earn/clip`(clip-promoteではない)

`~/anicca/skills/earn/clip/run.sh:111-125`(REQ-008、fresh grep根拠、全文引用):
```bash
# REQ-008: self-heal runs ONCE per wake, BEFORE new-content posting, using the SAME resolved
# HANDLE/TID this wake already confirmed logged-in. Runs regardless of whether a new clip is
# queued (independent of the QUEUE-empty check below) but never blocks the posting pipeline
# below regardless of its own outcome (best-effort; failure here must not prevent a new post).
SELF_HEAL="${CLIP_SELF_HEAL_OVERRIDE:-$(dirname "${BASH_SOURCE[0]}")/self_heal.py}"
if [ -f "$SELF_HEAL" ]; then
  CDP_PORT="$PORT" "$PY" "$SELF_HEAL" --handle "$HANDLE" --tid "$TID" --wake "$WAKE" \
    --pending-verify "$PENDING_VERIFY" --posted "$POSTED" --ledger "$LEDGER" 2>/dev/null || true
fi
if [ -z "${CLIP}" ]; then
  emit "nothing new to post (queue empty; self-heal already ran this wake)"; exit 0
fi
```
これがaffiliateの実際の形に合う唯一の既存パターン: **「未解決アイテムの回収
(self-heal相当)」と「新規投稿」は独立した2つのステップとして毎wake両方試み、
片方の結果がもう片方をブロックしない**。

## 2. affiliate用の設計(REV2、self_heal.py型に訂正)

### 現状(deep-researcher報告+fresh grep、確定事実)
- `affiliate-cli.sh:9`のSTARTUP prompt(1行の巨大文字列): selfheal-check→deck.json作成→
  `producer.sh`→`EARN_MODE=execute run.sh`→mail報告→`.affiliate-core-last-pass` touch、という
  順序を1ターンに直列化。
- `run.sh`(L11-14で定数確認): `QUEUE=~/affiliate/queue`, `POSTED=~/affiliate/posted`,
  `ACCTS=~/.cloak/affiliate-accounts.json`。L23-28で「スライド3枚以上+caption.txtがある最古の
  ディレクトリ」を選択、L31-38で「status==ready の最初のアカウント」を選択、L43-45で
  discover/execute分岐、成功したら`mv "$SET" "$POSTED"`(L89)。**現状のrun.shには
  case文自体が無く**、if/elseの単線フローで「1 wakeにつきちょうど1つの投稿」のみを行う。
- `producer.sh` — deck.json検証(3枚以上・連番)→PIL決定的背景生成(LLM不使用)→
  `compose_slides.py`でJP文字合成→1080x1920サイズ検証→caption.txtに`#PR`強制付与。
  **完全に決定的なツール**。LLM判断が要るのはdeck.json自体の文章生成のみ。
- `amazon_report.py` / `record-affiliate-earn.mjs` — §0で訂正した通り、コメント言及のみで
  実行呼び出しは0件(dangling)。

### 新規ディレクトリ構造(REQ-A1、clipのqueue/posted/pending-verifyパターンを模す)

```
~/affiliate/queue/           既存のまま(producer.shが書く、未投稿)
~/affiliate/posted/          意味変更: 「投稿済み・commission計測待ち」に変更
~/affiliate/measured/        新規: 計測完了(RECORDまたはSTALLED、どちらも移動先は同じ)
```

### 新規: `measure_one.py`(REQ-A2、`self_heal.py`と同型のパターン)

`~/anicca/skills/earn/affiliate/measure_one.py`を新規作成。責務は1つだけ:
`~/affiliate/posted/`から**最古のmtimeのディレクトリ1件**を選び(clipの
`_pick_oldest_clip`と同じround-robin方式)、`amazon_report.py`を実行して
そのアイテムのcommissionを確認する。

```python
def measure_one(posted_dir, measured_dir, ledger, amazon_report_fn, now,
                 dead_zero_days=DEAD_ZERO_DAYS_DEFAULT):
    """1件だけ処理。呼び出し元(run.sh)が毎wake無条件に呼ぶ。POSTブロックしない。"""
    item = _pick_oldest(posted_dir)  # 該当なければNone
    if item is None:
        return {"status": "empty"}
    commission = amazon_report_fn(item)  # CDP経由、実アカウントログイン必須
    if commission and commission > 0:
        _append_ledger(ledger, item, commission)   # record-affiliate-earn.mjs相当のゲート
        _move(item, measured_dir)
        return {"status": "recorded", "item": item, "commission_jpy": commission}
    posted_at = _mtime(item)
    if now - posted_at >= dead_zero_days * 86400:
        _move(item, measured_dir)  # 記録なしで移動、諦める(STALLED相当)
        return {"status": "stalled", "item": item}
    _touch(item)  # 未確定のまま、次回また試す(round-robinで別アイテムに順番が回る)
    return {"status": "still-pending", "item": item}
```

`DEAD_ZERO_DAYS_DEFAULT = 30`(仮値、Amazonのコミッション反映レイテンシの一次情報が
無いため。動作原理は仮値のままでも正しく機能する — 値調整は後からいつでも可能)。

### `run.sh`への配線(REQ-A3、clip run.shのREQ-008と同じ位置関係)

```bash
# MEASURE: 毎wake無条件に1件だけ試みる。POSTをブロックしない(REQ-008と同型)。
"$PY" "$SK/measure_one.py" --posted "$POSTED" --measured "$MEASURED" \
  --ledger "$LEDGER" --wake "$WAKE" 2>/dev/null || true

# 以降、既存のPOSTロジック(SET選択→アカウント選択→投稿)は完全に無変更で継続
```
**既存のPOST用ロジック(queue選択・アカウント選択・投稿実行部分)は一切書き換えない**
(REQ-A4)。追加するのは「measure_one.py呼び出し1行」と「POSTED先の意味変更
(posted→measured移動はmeasure_one.pyが担当)」のみ。

## 3. bounty用の設計(REV2、既存4モードの性質を再確認して最小修正に訂正)

### 現状の再確認(run.sh全文読了、156行、確定事実)

`attempt()`(L48-58)は既に**重複クレーム防止**を持つ: `attempts.jsonl`に同じ`key`が
既にあれば`emit "already claimed"`で何もしない(L55)。`track()`(L60-81)は
**既にattempts.jsonlの全行を毎回走査する**(単一currentアイテムという制約は
そもそも無い)。**REV1の「single current_key」state設計はbountyの実態に合っておらず、
adversary finding #4は正しい** — 訂正する。

### 実際に必要な修正は2箇所だけ(REQ-B1)

1. **`attempt()`のsurvivor選択を修正**: 現状`pick = survivors[0]`固定(L51)のため、
   survivors[0]が既にattempts.jsonlにある場合、"already claimed"と言うだけで
   survivors[1]以降を試さない。→ **survivorsを先頭から走査し、attempts.jsonlに
   キーが無い最初の1件を選ぶ**よう修正(既存の「1 wakeにつき1件だけ新規claim」
   という粒度は変えない、選び方だけを直す)。
2. **`track()`にSTALLED検知を追加**: 現状`MERGED*`のみ判定(L73)、`CLOSED`
   (mergeされずclose)を無視している。→ `CLOSED`かつ`reviewDecision`が
   `MERGED`でない場合、そのattemptを`stalled`として記録(append-onlyの原則を
   保つため、同じkeyで`status:"stalled"`の新規行を追記する — jsonlの「最新行が
   正」という既存パターンに倣う、in-place編集はしない)。

### 「PRを書く」ステップは自動化しない、しかし優先順位を変える(REQ-B2)

deep-researcher指摘通り、PRの中身を書く行為は本物のエンジニアリング判断であり
decide.py的な純関数には代替できない。**ここはREV1の判断を維持する**。

ただし今回のヘルスチェックで見つかった実際のバグ(attempts.jsonlが一度も作られて
いない=discover/gate止まりでattemptにすら到達しない)の真因は、bounty-cli.shの
STARTUP promptが「discover→gate→attempt→(PRを書く)→track→report」という順序を
**全て1ターンに詰め込んでいる**ため、と診断済み(§22.2)。この対策として:

- **STARTUP promptの構造を変える**(REQ-B3): 「未完了のwork-order(attempts.jsonlに
  `status:claim`かつ`pr:null`の行)があるかどうかのチェックを、discover/gateより
  **前**に置く。もし未完了work-orderがあれば、新しいbountyを探しに行く前に
  **まずそれを終わらせる**(PRを開くところまで)ことを最優先タスクとして明示する。
  これにより、前回のwakeでATTEMPTまで到達したが力尽きた場合でも、次のwakeは
  真っ先にその続きをやる構造になる(clip-promoteのWITHDRAW待ちパターンと同じ
  「完了するまで同じ対象に固執する」動きを、自然言語プロンプトの順序で再現する)。

## 4. スコープ判断(YAGNI、REV2で訂正)

| 項目 | 今回やる/やらない | 理由 |
|---|---|---|
| affiliate: `measure_one.py`新規実装 + run.shへの1行配線 | ★今回実装★ | MEASURE/RECORDが完全に未配線だった実バグを、POSTをブロックしない形で直す |
| affiliate: 既存POSTロジック(queue選択・アカウント選択・投稿) | 変更しない | 既に正しく動いている(6/30の2件は実際に投稿できた実績あり) |
| bounty: `attempt()`のsurvivor選択ロジック修正 | ★今回実装★(小さい修正) | 既にclaimedなsurvivorに永久に足止めされるバグを直す |
| bounty: `track()`へのSTALLED検知追加 | ★今回実装★(小さい修正) | CLOSED(unmerged)を無視し続けるバグを直す |
| bounty: discover/gate/attempt/trackの内部ロジック(判定条件そのもの) | 変更しない | 既に正しく機能している(gate()のフィルタ条件等) |
| bounty: 「PRを書く」ステップの自動化 | 今回やらない | 本物のコード判断が必要、対話ターンの仕事のまま |
| bounty-cli.sh: STARTUP promptの順序変更(未完了work-order優先) | ★今回実装★ | 「詰まる」実バグの直接対策 |
| affiliate/bounty双方のcli.sh STARTUP大幅簡素化(decide.py型への全面書き換え) | 今回はやらない、範囲を絞る | REV1は「clip-promote型の全面リファクタ」を狙ったが、bountyは既に4モードの
  設計自体は健全(§3で確認)、affiliateもPOSTロジックは健全 — 壊れていない部分まで
  書き換えるのは過剰実装。実際に壊れている箇所(MEASURE未配線、survivor選択、
  STALLED検知、優先順位)だけをピンポイントで直す |
| DEAD_ZERO_DAYS(30日)の正確な値 | 仮値のまま実装、Dais確認は別途 | 一次情報が無いため推測値、動作原理は仮値のままでも正しく機能する |

## 5. 検証計画(GATE 2: TDD)

| 項目 | 検証方法 |
|---|---|
| `measure_one.py`の全分岐(empty/recorded/stalled/still-pending) | `tests/test_measure_one.py`新規作成、clipの`self_heal.py`のテストパターンに倣う(ダミーの`amazon_report_fn`を注入、実ブラウザ不要) |
| `measure_one.py`がPOSTをブロックしない | run.sh変更後、`~/affiliate/queue`に複数アイテムがある状態で1 wake実行し、`measure_one.py`の結果に関わらずPOSTが実行されることを確認(結合テスト) |
| 既存POSTロジックが壊れない | 変更前後で`EARN_MODE=discover`の出力が一致することを確認 |
| `attempt()`のsurvivor選択修正 | survivors 2件・1件目が既にattempts.jsonlにある状態を作り、2件目が選ばれることを確認(既存のgated.json/attempts.jsonlのテスト用フィクスチャで再現) |
| `track()`のSTALLED検知 | `gh pr view`のモック出力(CLOSED、reviewDecision非MERGED)を注入し、`status:stalled`行が追記されることを確認 |
| bounty-cli.sh STARTUP順序変更 | プロンプト文字列内で「未完了work-orderチェック」が「discover」より前に出現することを確認(文字列比較で十分、実行はcronの自然発火まで待つ) |
| queue backlog(affiliate 7件)の解消 | 実装後、次の自然wakeでqueueが減っていくことを継続監視で確認(POSTがMEASUREにブロックされなくなったため、1 wake 1件のペースで着実に減るはず) |
| bounty survivorへの初回attempt | 実装後、次の自然wakeでattempts.jsonlに実際に行が追加されることを確認 |
| record-affiliate-earn.mjs / amazon_report.pyの実配線確認 | `measure_one.py`から実際に呼ばれ、実アカウントログイン環境で最低1回動作確認(モック不可、実装後に別途実施) |

## 6. GATE 1(SPEC)判定について

- **ラウンド1(REV1)**: FAIL。fresh-context Sonnet adversaryの指摘: (a) affiliateの
  decide.py設計がMEASURE中はPOSTを返せない構造になっており、7件の滞留解消という
  spec自身の目的(§0/§5)と矛盾する重大な設計欠陥(critical) (b) decide.pyの
  purity境界が未定義(queue-empty判定を誰がstateに書き込むか不明) (c) 既存
  `affiliate/run.sh`にはcase文自体が存在せず、PRODUCE/MEASURE/RECORDケース追加が
  具体性を欠く (d) bountyの「single current_key」state設計が、既に多重
  attempt対応済みの`attempts.jsonl`/`track()`の実態と矛盾 (e) STALLED時に
  「次のsurvivorへ」がREQ-B2(既存4モード無変更)と矛盾し実装不能 (f)
  `record-affiliate-earn`の「grep hit 0」という表現が不正確(コメント言及は
  実際にはある、実行呼び出しが0件、が正確)。
  検証の結果、(a)(b)(c)(d)(e)(f)は全て正当な指摘と確認。特に(a)は根本的で、
  参照実装の選定自体(clip-promote)が間違っていたと判明 — 正しい参照実装は
  `earn/clip`のself_heal.pyパターン(§1.2)。
- **ラウンド2(REV2、本ファイル)**: 参照実装をclip-promoteからclip(self_heal.py型)へ
  変更し、affiliateはMEASURE/POSTを独立させた設計に全面訂正(§2)。bountyは
  「single current_key」の状態機械を撤回し、既存4モードの中の2箇所の小さいバグ修正
  (survivor選択・STALLED検知)+ STARTUP prompt優先順位変更、という最小スコープに
  訂正(§3)。次はこのREV2を再度fresh-context adversaryにかけ、PASSするまで実装に
  進まない。
