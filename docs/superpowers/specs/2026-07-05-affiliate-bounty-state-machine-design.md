# affiliate / bounty を clip-promote型の純粋状態機械へリファクタ(Task #15)

## 開発環境

| 項目 | 値 |
|---|---|
| worktree | `~/anicca/.worktrees/affiliate-bounty-statemachine/`(実装フェーズで作成) |
| ブランチ | `feature/affiliate-bounty-statemachine` |
| 対象repo | `~/anicca`(git管理、`earn/affiliate` + `earn/bounty`) |
| 状態 | spec REV1、GATE 1審査前 |

## 0. なぜこれをやるか(2026-07-05ヘルスチェックで発見した実バグ)

fresh evidence(2026-07-05):
- **affiliate**: `~/affiliate/queue/`に未投稿カルーセルが**7件**滞留(最新は07-04 17:40作成)。`~/affiliate/posted/`は**2件のみで最後は6/30**。**さらに重大な発見**: commission検知スクリプト
  (`~/.claude/skills/earn-affiliate-slideshow/scripts/amazon_report.py`)と記録スクリプト
  (`record-affiliate-earn.mjs`)は実在するが、`affiliate-cli.sh`/`run.sh`/`producer.sh`のどこからも
  **一度も呼ばれていない**(grep確認、ヒット0)。`~/.smtm/earn-loops/affiliate/earn-ledger.jsonl`も
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

## 1. 参照実装(clip-promote、fresh grep根拠)

- `~/anicca/skills/earn/clip-promote/decide.py` — `decide(state, now)`純関数。
  phase = `SELECT→JOIN→CLIP→POST→SUBMIT→MEASURE→WITHDRAW→RECORD`、終端`STALLED`。
  未知/空phaseは安全に`SELECT`へ(デッドエンド無し)。
- `~/anicca/skills/earn/clip-promote/run.sh`のcase文(fresh grep、行番号確認済み):
  `RECORD)`(51行)`SELECT)`(70行)`JOIN)`(95行)`CLIP)`(133行)`POST)`(171行)
  `SUBMIT|WITHDRAW|STALLED)`(207行、"not-yet-wired"スタブ)。
  **重要な事実**: decide.pyは`MEASURE`をphaseとして返しうるが、run.shには`MEASURE)`という
  専用caseが無い(grep確認、6個のcase labelにMEASUREは含まれない)。つまりclip-promote自体、
  「decide.pyがphaseを返す」ことと「run.shがそのphase用の実装を持つ」ことは**独立**であり、
  未実装のphaseは正直に「not-yet-wired」と応答してよい、という既存の設計判断がある
  (HONESTY原則: 見ていないUI/未実装ロジックを偽装しない)。本specでもこの原則を踏襲する。
- `~/anicca/skills/earn/clip-promote/tests/test_decide.py` — 9ケース、fixed epoch、
  境界値(47h59m/48h/100h+views>0)を明示検証。

## 2. affiliate用 decide.py 設計

### 現状(deep-researcher報告、fresh grep根拠)
- `affiliate-cli.sh:9`のSTARTUP prompt(1行の巨大文字列): selfheal-check→deck.json作成→
  `producer.sh`→`EARN_MODE=execute run.sh`→mail報告→`.affiliate-core-last-pass` touch、という
  順序を1ターンに直列化。
- `run.sh`(L11-14で定数確認): `QUEUE=~/affiliate/queue`, `POSTED=~/affiliate/posted`,
  `ACCTS=~/.cloak/affiliate-accounts.json`。L23-28で「スライド3枚以上+caption.txtがある最古の
  ディレクトリ」を選択、L31-38で「status==ready の最初のアカウント」を選択、L43-45で
  discover/execute分岐、成功したら`mv "$SET" "$POSTED"`(L89)。**run.shは1 wakeにつき
  ちょうど1つの投稿(POST)のみを行う**、producer呼び出しやselfheal判定はrun.shの外
  (affiliate-cli.shのプロンプト側)にある。
- `producer.sh` — deck.json検証(3枚以上・連番)→PIL決定的背景生成(LLM不使用)→
  `compose_slides.py`でJP文字合成→1080x1920サイズ検証→caption.txtに`#PR`強制付与。
  **完全に決定的なツール**。LLM判断が要るのはdeck.json自体の文章生成のみ。
- `amazon_report.py`(`~/.claude/skills/earn-affiliate-slideshow/scripts/`) —
  CDP経由でaffiliate.amazon.co.jpダッシュボードをスクレイプし`commission_jpy>0`を検知。
  **現状どこからも呼ばれていない(dangling)**。
- `record-affiliate-earn.mjs`(同ディレクトリ) — INV-1〜5ゲート(`source==="amazon_report"`
  必須、`amount_jpy>0`必須等)を満たさない限り何も書かない。append-onlyな
  `~/.smtm/earn-loops/affiliate/earn-ledger.jsonl`へ書く。**同じく現状どこからも呼ばれていない**。

### 新規phase設計(REQ-A1)

```
PRODUCE   コンテンツが無い/新規追加すべき  → deck.json作成+producer.sh実行(既存ロジック流用)
POST      queueに投稿可能なsetがある      → run.shの既存POSTロジック流用(1 wake 1件)
MEASURE   postedにcommission未確認の項目がある → amazon_report.py実行、commission_jpy>0なら次へ
RECORD    commission確認済み              → record-affiliate-earn.mjs実行、DONE
STALLED   MEASURE開始からDEAD_ZERO_DAYS(30日)経過してもcommission=0 → 諦めて記録なしで終了
```

`decide(state, now)`のstate schema(新規`~/.cloak/affiliate-state.json`):
```json
{"phase": "PRODUCE|POST|MEASURE|RECORD|STALLED",
 "current_set": "aff<epoch>のディレクトリ名 or null",
 "posted_at": epoch秒 or null,
 "commission_jpy": 0,
 "measured_at": epoch秒 or null}
```

決定ロジック(clip-promoteのMEASURE/DEAD_ZERO_HOURSパターンを踏襲、affiliateはコミッション
反映まで数日かかりうるためDEAD_ZERO_DAYS=30日と長めに設定 — この数値はDais確認が必要な
仮値、実際のAmazonアフィリエイト反映レイテンシの一次情報が無いため):
```python
def decide(state, now):
    phase = (state or {}).get("phase") or "idle"
    if phase in ("idle", "RECORD", "STALLED"):
        return "PRODUCE" if <queue empty判定> else "POST"
    if phase == "PRODUCE":
        return "POST"  # producer.sh実行後は常にPOSTへ(生成した/既存のqueueを問わずPOSTを試す)
    if phase == "POST":
        return "MEASURE" if state.get("posted_at") else "POST"  # 投稿成功でMEASUREへ
    if phase == "MEASURE":
        if state.get("commission_jpy", 0) > 0:
            return "RECORD"
        posted_at = state.get("posted_at", 0)
        if now - posted_at >= DEAD_ZERO_DAYS_DEFAULT * 86400:
            return "STALLED"
        return "MEASURE"
    return "PRODUCE"
```

**既存run.sh/producer.shは書き換えない**(REQ-A2): 新規`affiliate/run.sh`のcase文に
`PRODUCE)`/`MEASURE)`/`RECORD)`ケースを追加するのみ。`POST)`ケースは既存ロジックを
ほぼそのまま流用(1 wake 1件という既存の粒度は変えない)。

## 3. bounty用 decide.py 設計

### 現状(deep-researcher報告、fresh grep根拠)
- `run.sh`はEARN_MODE=discover(L17-42、`gh api search/issues`で列挙、判断なし)/
  gate(L87-152、機械的フィルタ:funder withdrawn・既存PR無し・farmリポジトリ除外・
  金額正規表現抽出)/attempt(L44-58、`gated.json`のsurvivors[0]を`attempts.jsonl`に
  `status:claim`で追記するのみ)/track(L60-81、`gh pr view`ポーリング→`MERGED`なら
  `record-earn.mjs`)の4モードを持つが、**モード間の遷移順序と「実際にPRを書く」核心部分は
  run.shの外、bounty-cli.shの自然言語プロンプトのみが握っている**。
- **重要な非対称性**(deep-researcher指摘): bountyの「issueをVSDD RED→GREENで直しPRを開く」は
  clip-promoteの全ステップ(ブラウザ操作+ポーリングのみ、決定論的)と違い**本物のコード理解・
  実装判断**を要する。run.sh自身のコメント(47行目)が「the actual fix IS real engineering
  (legitimately the brain's job)」と認めている。**decide.pyの純関数はここを代替できない** —
  「ATTEMPT phaseに入ったら対話ターンに実装を委譲し、その完了(pr番号セット)をポーリングで
  待つ」という、clip-promoteのWITHDRAW(sig有無をポーリング)と同型のパターンにせざるを
  得ない。

### 新規phase設計(REQ-B1)

```
DISCOVER   bountiesを列挙(既存run.sh discover流用、変更なし)
GATE       機械的フィルタでsurvivors選定(既存run.sh gate流用、変更なし)
ATTEMPT    survivorをwork-order化(既存run.sh attempt流用、attempts.jsonlにstatus:claim)
AWAIT_PR   ★対話ターンへの委譲ポイント★ attempts.jsonlのpr fieldがnullの間はこのまま。
           decide.pyはここでは何も強制しない(browser/code操作は含まない) — run.sh側の
           AWAIT_PR)ケースは「pr fieldが埋まっているか確認するだけ」の受動的チェック。
           実際にGitHubへコメント→fork→修正→PRオープンする行為は、bounty-cli.shの
           STARTUP prompt内で対話ターンが行う(現状のまま変更しない、REQ-B2で明記)
TRACK      pr番号がある → 既存run.sh track流用(gh pr view ポーリング)
RECORD     MERGED確認済み → record-earn.mjs実行(既存流用)、DONE
STALLED    PR rejected/close(unmerged)、またはATTEMPTから一定日数(REQ_STALE_DAYS、
           仮値14日、Dais確認要)経過してもPRが開かれない → 諦めて次のsurvivorへ
```

state schema(新規`~/anicca/skills/earn/bounty/state/decide-state.json`):
```json
{"phase": "DISCOVER|GATE|ATTEMPT|AWAIT_PR|TRACK|RECORD|STALLED",
 "current_key": "repo#issueの形式 or null",
 "claimed_at": epoch秒 or null,
 "pr": PR番号 or null}
```

**既存run.shの4モード(discover/gate/attempt/track)は書き換えない**(REQ-B2): 新規
`decide.py`はこれらモードを**呼び出す順序の決定**のみを担当し、各モードの内部実装には
一切手を入れない。「PRを実際に書く」ステップは**意図的に対話ターンの仕事のまま残す**
(clip-promoteとの類推が破綻する箇所であり、無理に自動化しない — これはYAGNI/過剰実装
回避の判断であり、バグではない)。

## 4. スコープ判断(YAGNI)

| 項目 | 今回やる/やらない | 理由 |
|---|---|---|
| affiliate: PRODUCE/POST/MEASURE/RECORD/STALLEDのdecide.py化 | ★今回実装★ | 既存のPOSTロジックはそのまま使え、MEASURE/RECORDは完全に未配線だったので新規追加 |
| bounty: DISCOVER/GATE/ATTEMPT/AWAIT_PR/TRACK/RECORD/STALLEDのdecide.py化 | ★今回実装★ | 既存の4モードはそのまま使え、状態遷移の決定だけを新規のdecide.pyに集約 |
| bountyの「PRを書く」ステップ自体の自動化 | 今回やらない | 本物のコード判断が必要、対話ターンの仕事のまま(REQ-B2で明記) |
| `<name>-cli.sh`のSTARTUP promptの大幅簡素化 | ★今回実装★ | 巨大な複数ステップ自然言語プロンプトを「decide.pyの返す1遷移を実行するだけ」の
  薄いプロンプトに置き換える(clip-promote-cli.shと同型) |
| DEAD_ZERO_DAYS(30日)/STALE_DAYS(14日)の正確な値 | 仮値のまま実装、Dais確認は別途 | 一次情報(Amazonのコミッション反映レイテンシ実測、Algora bountyの現実的な放置期間)が
  無いため推測値。動作自体は仮値のままでも正しく機能する(値の調整は後からいつでも可能) |

## 5. 検証計画(GATE 2: TDD)

| 項目 | 検証方法 |
|---|---|
| affiliate decide.pyの全phase遷移 | `tests/test_decide.py`新規作成、clip-promote版と同型(9ケース以上、fixed epoch、DEAD_ZERO_DAYS境界値) |
| bounty decide.pyの全phase遷移 | 同上、AWAIT_PR→TRACKの遷移(pr番号有無)とSTALLE_DAYSの境界値を含む |
| 既存run.shの4モード(bounty)が壊れない | 変更前後で`EARN_MODE=discover/gate/attempt/track`を個別実行、出力が変更前と一致することを確認 |
| 既存run.sh POSTロジック(affiliate)が壊れない | 変更前後でdiscoverモードの出力が一致することを確認 |
| 新規MEASURE/RECORD(affiliate)が実際に機能する | `amazon_report.py`を実行し実際のダッシュボードスクレイプが動くか確認(実アカウントログイン
  が必要、この場ではモック不可 — 実機確認は実装後に別途行う) |
| queue backlog(affiliate 7件)の解消 | 実装後、次の自然wakeでqueueが徐々に減っていくことを継続監視で確認(1 wake 1件のPOST粒度は
  変えないため、7件解消には7 wake以上かかる想定 — 急がず、正常動作の証拠として扱う) |
| bounty survivorへの初回attempt | 実装後、次の自然wakeでATTEMPT phaseに入りattempts.jsonlに実際に行が追加されることを確認 |

## 6. GATE 1(SPEC)判定について

このspecはVCSDDのBuilder(私)が書いた初稿。次のステップは`vcsdd:vcsdd-adversary`
(Sonnet)によるfresh-context spec review。PASSするまで実装に進まない。
