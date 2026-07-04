# affiliate / bounty を clip-promote型の純粋状態機械へリファクタ(Task #15)

## 開発環境

| 項目 | 値 |
|---|---|
| worktree | `~/anicca/.worktrees/affiliate-bounty-statemachine/`(実装フェーズで作成) |
| ブランチ | `feature/affiliate-bounty-statemachine` |
| 対象repo | `~/anicca`(git管理、`earn/affiliate` + `earn/bounty`) |
| 状態 | spec REV6(GATE 1ラウンド1-5 FAIL、measure_commission.pyのクロスリポジトリ配線を具体化) |

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

`~/anicca/skills/earn/clip/run.sh:111-126`(REQ-008、fresh grep根拠。GATE 1ラウンド2で
「全文引用」という表現が不正確と指摘され訂正 — 実際は116行目コメント・117-119行目の
コメントブロックを含む全16行、以下が正確な全文):
```bash
# REQ-008: self-heal runs ONCE per wake, BEFORE new-content posting, using the SAME resolved
# HANDLE/TID this wake already confirmed logged-in. Runs regardless of whether a new clip is
# queued (independent of the QUEUE-empty check below) but never blocks the posting pipeline
# below regardless of its own outcome (best-effort; failure here must not prevent a new post).
SELF_HEAL="${CLIP_SELF_HEAL_OVERRIDE:-$(dirname "${BASH_SOURCE[0]}")/self_heal.py}"  # test hook (PROP-009), unset in production
if [ -f "$SELF_HEAL" ]; then
  # FIXED after Phase 3 FIND-103: pass the paths run.sh ALREADY resolved via _instance_paths.sh
  # above, instead of self_heal.py re-deriving ANICCA_INSTANCE suffixing independently in Python
  # (a duplicate/drifting-logic risk with zero enforcement mechanism to keep the two in sync).
  CDP_PORT="$PORT" "$PY" "$SELF_HEAL" --handle "$HANDLE" --tid "$TID" --wake "$WAKE" \
    --pending-verify "$PENDING_VERIFY" --posted "$POSTED" --ledger "$LEDGER" 2>/dev/null || true
fi

if [ -z "${CLIP}" ]; then
  emit "nothing new to post (queue empty; self-heal already ran this wake)"; exit 0
fi
```
挙動確認: `self_heal.py`の終了コードは`|| true`(121行目)で握りつぶされ、124行目の
`if [ -z "${CLIP}" ]`チェックはself_healの結果に一切依存しない。self-healがPOSTを
ブロックしないという主張は正しいと確認済み。`CLIP_SELF_HEAL_OVERRIDE`という
テストフック(115行目コメント)も存在する — bounty用の`gh`モック機構(§3.3)で
同じ命名パターンを踏襲する。
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

### ★GATE 1ラウンド2で発見した致命的な事実誤認(REV3で訂正)★

REV2の`measure_one.py`設計は「投稿済みアイテム1件ごとにcommissionを個別確認する」
という前提だったが、これは**実装不可能な前提だった**。実際に`amazon_report.py`
(21-42行)を読むと:
- **引数を一切取らない**(`main()`はitem/URLを一切受け取らない)。
- affiliate.amazon.co.jpの「**今月のレポート**」カードから`紹介料合計`
  (=**アカウント全体・当月累計**のコミッション)をスクレイプするだけ。
- **どの投稿がどのクリック/購入を生んだかを一切区別できない**(per-post
  attributionの仕組みがAmazon Associatesのこのダッシュボード上に存在しない)。

つまり「アイテムXのcommissionを確認する」という操作自体が、このツールでは
そもそも不可能。REV2の`measure_one(item)`という関数シグネチャは実装できない
(adversary finding #2は完全に正しく、致命的)。

**さらに追加で発見した不整合**: `record-affiliate-earn.mjs`のINV-4は
`report_export_id`(非空文字列)を必須とするが、`amazon_report.py`は
そのようなIDを一切生成しない(ダッシュボードのライブスクレイプであり、
Amazonの「レポートをエクスポート」機能を使っていないため)。この2つの
スクリプトは**過去の別々の設計意図で書かれ、一度も実際に繋げて動かされて
いない**(だからこそdanglingのまま放置されていた、と推測できる)。

### 修正した設計: アイテム単位ではなく「アカウント全体の当月累計」を追跡する(REQ-A2)

per-post attributionを諦め、「アカウント全体で今月コミッションが**増えたか**」
だけを検知する、より単純で実装可能な設計に変更する。これは「どの投稿が稼いだか」
は分からないが、「アフィリエイトで実際にお金が発生したかどうか」というHARD RULE
0.24(no-fake-earn)の核心要件は満たす。

新規state(`~/anicca/skills/earn/affiliate/state/commission-watermark.json`):
```json
{"month": "2026-07", "last_commission_jpy": 0, "last_checked_at": epoch秒 or null}
```

新規`~/anicca/skills/earn/affiliate/measure_commission.py`(引数なし、
`amazon_report.py`をそのまま呼ぶラッパー):
```python
def measure_commission(watermark_path, ledger_record_fn, now, amazon_report_fn):
    """アカウント全体の当月コミッションの増分だけを検知。個別投稿とは紐付けない。
    呼び出し元(run.sh)が毎wake無条件に呼ぶ。POSTを一切ブロックしない(self_heal.py型)。"""
    report = amazon_report_fn()  # amazon_report.pyの実際の出力: {commission_jpy, asof, store_id, ...}
    if report.get("error"):
        return {"status": "error", "detail": report["error"]}  # ログイン切れ等、正直に報告して終了
    wm = _load(watermark_path) or {"month": None, "last_commission_jpy": 0, "last_checked_at": None}
    this_month = report["asof"][:7]  # "2026-07-05 ..." → "2026-07"
    if wm["month"] != this_month:
        # 月が変わった: Amazon側のカードも新しい月のカウントにリセットされている。
        # ★GATE 1ラウンド3で発見(finding F2)★: 単に新basisとして黙って採用するだけだと、
        # 月初めて確認した時点で既にAmazon側が示している金額(=今月分の実コミッション)を
        # 一度も記録せずに失っていた(baseline化=無記録、が毎月確実に起きるバグだった)。
        # 正しい扱い: 新月の初回確認時点の値自体を「0からの増分」として記録してから、
        # それをbaselineにする(前月からの繰越ではなく、新月の実績として正しく計上)。
        if report["commission_jpy"] > 0:
            export_id = f"live-scrape-{report['asof'].replace(' ', 'T').replace(':', '')}"
            ledger_record_fn({
                "source": "amazon_report", "amount_jpy": report["commission_jpy"],
                "report_date": report["asof"][:10], "report_export_id": export_id,
                "order_items": report.get("ordered_items"),
            })
        wm = {"month": this_month, "last_commission_jpy": report["commission_jpy"], "last_checked_at": now}
        _save(watermark_path, wm)
        return {"status": "new-month-baseline-recorded" if report["commission_jpy"] > 0 else "new-month-baseline",
                "commission_jpy": report["commission_jpy"]}
    delta = report["commission_jpy"] - wm["last_commission_jpy"]
    wm["last_checked_at"] = now
    if delta > 0:
        # report_export_id: amazon_report.pyはAmazonの正式なレポートexport機能を使っていない
        # (ライブダッシュボードのスクレイプ)。record-affiliate-earn.mjsのINV-4は非空文字列
        # であれば足りるため、"live-scrape-<asof>"という決定論的な代替IDで満たす(捏造ではなく、
        # 「いつ観測した実データか」を指す実在のタイムスタンプ由来)。
        export_id = f"live-scrape-{report['asof'].replace(' ', 'T').replace(':', '')}"
        ledger_record_fn({
            "source": "amazon_report", "amount_jpy": delta,
            "report_date": report["asof"][:10], "report_export_id": export_id,
            "order_items": report.get("ordered_items"),
        })
        wm["last_commission_jpy"] = report["commission_jpy"]
        _save(watermark_path, wm)
        return {"status": "recorded", "delta_jpy": delta}
    _save(watermark_path, wm)
    return {"status": "no-change"}
```

**posted/ディレクトリの意味は変更しない**(REQ-A2の訂正に伴いREQ-A1は撤回):
投稿済みアイテムは引き続き`~/affiliate/posted/`に置かれたままでよい(個別
commission追跡をしないので「計測待ち」という状態遷移が不要になった)。
将来的にディスク容量が気になれば別途アーカイブ処理を検討するが、**今回の
スコープには含めない**(YAGN、7件程度のPNG+txtはディスク上無視できる量)。

### クロスリポジトリ配線(REQ-A3、GATE 1ラウンド5指摘で追加 — 実体は別ディレクトリ)

★GATE 1ラウンド5で発見★: `measure_commission(watermark_path, ledger_record_fn, now,
amazon_report_fn)`は純関数として定義したが、実際に呼び出す`amazon_report.py`と
`record-affiliate-earn.mjs`は`~/anicca/skills/earn/affiliate/`ではなく
**`~/.claude/skills/earn-affiliate-slideshow/scripts/`という別ディレクトリツリー**
に実在する(§0/§2で既出の事実)。この2つを実際にどう橋渡しするかが未記載だった
(REQ-B1の1点目がラウンド3で疑似コード無しを指摘されたのと同種の欠落)。

`measure_commission.py`の`__main__`ブロック(新規、`~/anicca/skills/earn/affiliate/
measure_commission.py`の末尾に追加):
```python
AFFILIATE_SLIDESHOW_SCRIPTS = os.path.expanduser("~/.claude/skills/earn-affiliate-slideshow/scripts")

def _amazon_report_fn():
    """amazon_report.pyをsubprocessで呼び、そのJSON標準出力をパースする。
    引数なし(スクリプト自体が引数を取らない、§2で確認済み)。CDP_PORTはenv経由で
    daily-driver(9222、affiliateアカウントがログインしているポート)を使う既存の
    デフォルトのまま、明示的な上書きはしない。"""
    p = os.path.join(AFFILIATE_SLIDESHOW_SCRIPTS, "amazon_report.py")
    out = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": f"amazon_report.py did not return valid JSON: {out.stdout[:200]!r} {out.stderr[:200]!r}"}

def _ledger_record_fn(row):
    """record-affiliate-earn.mjsをsubprocessで呼ぶ。INV-1〜5はmjs側が検証するので
    ここでは二重チェックしない(失敗したら例外をそのまま伝播、握りつぶさない)。"""
    p = os.path.join(AFFILIATE_SLIDESHOW_SCRIPTS, "record-affiliate-earn.mjs")
    subprocess.run(["node", p, "--row", json.dumps(row)], check=True, timeout=15)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--watermark", required=True)
    ap.add_argument("--wake", required=True)
    a = ap.parse_args()
    result = measure_commission(a.watermark, _ledger_record_fn, time.time(), _amazon_report_fn)
    print(json.dumps(result, ensure_ascii=False))
```

### `run.sh`への配線(REQ-A3、clip run.shのREQ-008と同じ位置関係)

```bash
# MEASURE: 毎wake無条件に1回、アカウント全体のコミッション増分だけ確認。
# POSTを一切ブロックしない(REQ-008と同型)。
"$PY" "$HOME/anicca/skills/earn/affiliate/measure_commission.py" \
  --watermark "$STATE/commission-watermark.json" --wake "$WAKE" 2>/dev/null || true

# 以降、既存のPOSTロジック(SET選択→アカウント選択→投稿)は完全に無変更で継続
```
(GATE 2のテストでは`_amazon_report_fn`/`_ledger_record_fn`を直接呼ばず、
`measure_commission()`本体にダミー関数を注入する既存の単体テスト方針
(§5)を使う — この`__main__`ブロック+2つのsubprocessヘルパーは実配線確認
(§5「measure_commission.pyの実配線確認」の行)でのみ実行し、モックしない)。
**既存のPOST用ロジック(queue選択・アカウント選択・投稿実行部分)は一切書き換えない**
(REQ-A4)。追加するのは「measure_commission.py呼び出し1行」のみ。

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
   という粒度は変えない、選び方だけを直す)。GATE 1ラウンド3指摘(finding F5)で
   具体化、現行L51-56相当を以下に置き換える:
   ```bash
   attempt(){
     local gj="$STATE/gated.json" af="$STATE/attempts.jsonl"
     [ -f "$gj" ] || gate >/dev/null 2>&1
     # 修正: survivors[0]固定ではなく、attempts.jsonlに未登録の最初の1件を選ぶ
     local pick; pick=$("$PY" -c "
import json,os
survivors=json.load(open('$gj')).get('survivors',[])
claimed=set()
if os.path.exists('$af'):
    for line in open('$af'):
        line=line.strip()
        if not line: continue
        try: d=json.loads(line)
        except Exception: continue
        if d.get('key'): claimed.add(d['key'])
for s in survivors:
    k=s['repo']+'#'+str(s['issue'])
    if k not in claimed:
        print(json.dumps(s)); break
" 2>/dev/null)
     [ -n "$pick" ] || { emit "attempt: no unclaimed gated survivor to claim (all already attempted or real-USD inventory empty)"; return; }
     # 以降(work-order書き込み)は既存ロジックのまま変更なし
     local key; key=$("$PY" -c "import json,sys;d=json.loads(sys.argv[1]);print(d['repo']+'#'+str(d['issue']))" "$pick" 2>/dev/null)
     "$PY" -c "import json,sys;d=json.loads(sys.argv[1]);print(json.dumps({'key':d['repo']+'#'+str(d['issue']),'repo':d['repo'],'issue':d['issue'],'bounty_usd':d.get('bounty_usd',0),'pr':None,'status':'claim','wake':sys.argv[2]}))" "$pick" "$WAKE" >> "$af"
     emit "attempt: WORK-ORDER written for $key"
   }
   ```
   (既存の重複チェック`grep -qF`は、上記のPython側`claimed`集合構築に統合済みのため
   削除 — 同じ役割を1箇所で担う、二重実装を避ける)。
2. **`track()`にSTALLED検知を追加**: 現状`MERGED*`のみ判定(L73)、`CLOSED`
   (mergeされずclose)を無視している。

### ★GATE 1ラウンド2で発見した2つの不正確な記述(REV3で訂正)★

1. **「jsonlの最新行が正、という既存パターン」は存在しない**(adversary finding #3)。
   `track()`(L64-74)は`while IFS= read -r line; do ... done < "$af"`で**全行を
   単純に走査するのみ**、「同じkeyの複数行のうち最新を正とする」重複解決ロジックは
   どこにも実装されていない。この主張は撤回する。
2. **while-readループの実行中に同じファイル(`$af`)へ追記するのは未定義動作リスク**
   (adversary finding #3)。bashの`while read < file`は開いたファイルディスクリプタを
   順に読むが、同じシェルプロセスが同時にそのファイルへ`>>`で書き込むと、読み取り位置と
   書き込み位置の整合性はPOSIX的に保証されない。

**修正した実装方針(GATE 1ラウンド3のfinding F3を反映、idempotency追加)**:
`track()`のループ内では**メモリ上のリスト**に「stalledと判定されたkey」を溜める
だけにし、`done < "$af"`でループが完全に終了した**後**に、まとめて`$af`へ追記する
(1回のみのファイルI/O、ループとの競合を避ける)。**さらに、既に`status:"stalled"`の
行が存在するkeyは、ループに入る前の時点で除外し、`gh pr view`を二度と呼ばない**
(ラウンド3指摘: この除外が無いと毎wake重複した`stalled`行が無限に追記され続ける
バグになる)。「最新行が正」ではなく「一度でもstalled行が出たら以後そのkeyは完全に
スキップする」という単純な集合演算にする(append-onlyのまま、in-place編集なし):
```bash
track(){
  local af="$STATE/attempts.jsonl" merged=0 tracked=0
  [ -f "$af" ] || { emit "track: no attempts yet (state/attempts.jsonl empty)"; return; }
  # 事前に「既にstalled行が1回でも出たkey」の集合を作り、以後の処理から完全除外する
  # (これが無いとgh呼び出し+stalled追記が毎wake重複し無限増殖する — ラウンド3 finding F3)
  local resolved; resolved=$("$PY" -c "
import json
resolved=set()
for line in open('$af'):
    line=line.strip()
    if not line: continue
    try: d=json.loads(line)
    except Exception: continue
    if d.get('status')=='stalled' and d.get('key'):
        resolved.add(d['key'])
print(' '.join(sorted(resolved)))
" 2>/dev/null)
  local stalled_keys=""   # ループ中はここに溜めるだけ、$afへは書かない
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    local repo pr key; repo=$("$PY" -c "...")
    key=$("$PY" -c "import json,sys;print(json.loads(sys.argv[1]).get('key',''))" "$line" 2>/dev/null)
    pr=$("$PY" -c "...")
    [ -n "$repo" ] || continue
    case " $resolved " in *" $key "*) continue;; esac   # 既にstalled確定済みならgh呼び出しごと丸ごとスキップ
    tracked=$((tracked+1))
    [ -n "$pr" ] || { echo "[bounty] track $repo (no PR yet — awaiting brain)"; continue; }
    # BOUNTY_GH_OVERRIDE: テストフック、clip run.shのCLIP_SELF_HEAL_OVERRIDEと同じ命名慣習
    local gh_bin="${BOUNTY_GH_OVERRIDE:-gh}"
    local st; st=$("$gh_bin" pr view "$pr" -R "$repo" --json state,reviewDecision 2>/dev/null | "$PY" -c "...")
    case "$st" in
      MERGED*) merged=$((merged+1));;
      CLOSED*) stalled_keys="$stalled_keys $key";;   # ループ内では溜めるだけ
    esac
  done < "$af"
  # ループ終了後にまとめて追記(ファイルI/Oの競合を避ける)。resolvedに既に無いkeyのみ
  # (同一wake内で複数回stalled判定されても1行だけ、$stalled_keysが重複を含む可能性は
  # 無い — 1 attemptにつきループは1回しか通らないため)
  for k in $stalled_keys; do
    "$PY" -c "import json;print(json.dumps({'key':'$k','status':'stalled'}))" >> "$af"
  done
  ...(既存のsettle処理は変更なし)
}
```
**この修正はREQ-B1のスコープを1点だけ広げる**: `gh`呼び出しに`BOUNTY_GH_OVERRIDE`
というテストフック変数を追加する(GATE 2のtrack()テストで`gh`をモックするために
必須、既存のattempt()/discover()/gate()には手を入れない)。

### 「PRを書く」ステップは自動化しない、しかし優先順位を変える(REQ-B2)

deep-researcher指摘通り、PRの中身を書く行為は本物のエンジニアリング判断であり
decide.py的な純関数には代替できない。**ここはREV1の判断を維持する**。

ただし今回のヘルスチェックで見つかった実際のバグ(attempts.jsonlが一度も作られて
いない=discover/gate止まりでattemptにすら到達しない)の真因は、bounty-cli.shの
STARTUP promptが「discover→gate→attempt→(PRを書く)→track→report」という順序を
**全て1ターンに詰め込んでいる**ため、と診断済み(§22.2)。この対策として:

- **STARTUP promptの構造を変える**(REQ-B3、GATE 1ラウンド2指摘で具体化):
  現行`bounty-cli.sh:17`のSTARTUP文字列は「selfheal-check→(1)DISCOVER→(2)GATE→
  (3)ATTEMPT+PR作成→(4)TRACK→report→touch」という順。この`(1)DISCOVER`の**直前**に
  新規ステップ`(0)`を挿入する。挿入する正確な文言(既存文言との接続点を明記):

  現行(挿入箇所直前、`bounty-cli.sh:17`より抜粋):
  `"...then rm the file anyway. THEN (1) DISCOVER: EARN_MODE=discover bash ..."`

  変更後(★GATE 1ラウンド3のfinding F4を反映、タイムアウト/断念パスを追加★。
  さらに★ラウンド4のfinding FIND-1を反映★ — ラウンド3の断念パス自体が
  「既にstalled行が存在するかを一度も確認せず`GIVE UP`のたびに新規追記する」
  という、`track()`側でF3として直したのと**全く同じ重複追記バグを、LLMが
  読む自然言語プロンプト側の別経路で再導入していた**。この経路は`track()`の
  bash実装がカバーする範囲の外(agentが直接attempts.jsonlを読み書きする)
  なので、track()のresolved集合ロジックとは独立に、ここでも同じ「既にstalled
  済みならスキップ」チェックを明記する必要がある):
  `"...then rm the file anyway. THEN (0) CHECK FOR UNFINISHED WORK FIRST: read `
  `~/anicca/skills/earn/bounty/state/attempts.jsonl; for each key, if it ALREADY `
  `has a status:stalled line anywhere in the file, treat that key as fully resolved `
  `-- do NOT re-evaluate it, do NOT append another stalled line for it, skip it `
  `entirely. Among keys with NO stalled line yet, if ANY has status:claim AND pr is `
  `null, that is unfinished work from a previous pass. Check that line's wake field `
  `(epoch seconds at claim time; if wake is missing or not a plain number, treat `
  `this claim as fresh/not-stale rather than erroring). If now - wake >= 7 days `
  `(BOUNTY_STALE_DAYS), GIVE UP on it -- append {"key":<same key>,"status":"stalled"} `
  `to attempts.jsonl ONCE (you already confirmed above no stalled line exists yet for `
  `this key, so this single append is safe and will never repeat for this key on `
  `future passes), then proceed to (1) DISCOVER below as normal. Otherwise (claim is `
  `fresh, under 7 days old), do NOT run discover/gate this pass, instead ACTUALLY `
  `FINISH that bounty right now (comment /attempt #N on that GitHub issue as `
  `Daisuke134, fork the repo, fix the issue via VSDD RED->GREEN, open a PR referencing `
  `the issue, then update that attempts.jsonl line setting pr to the PR number), THEN `
  `skip to step (4) TRACK below. Only if NO unfinished (non-stalled, pr-null) claim `
  `exists at all, proceed to (1) DISCOVER: EARN_MODE=discover bash ..."`

  これにより「前回のwakeでATTEMPTまで到達したが力尽きた」場合、次のwakeは
  discover/gateへ進む前に必ずこの未完了work-orderを検知し、そこで足止めされる
  (新しいbountyを探しに行けない)構造になる — clip-promoteのWITHDRAW待ちパターン
  (completeするまで同じ対象に固執する)と同じ効果を、自然言語プロンプトの
  順序変更のみで実現する。ただし`BOUNTY_STALE_DAYS`(仮値7日、一次情報無いため
  推測値)を超えたら自分でstalledとして諦め、次のbountyへ進めるようにする —
  無限ブロックを防ぐ。**「既にstalled済みのkeyは二度と評価しない」という
  チェックを最初に置くことで、この断念パス自体が無限に重複追記するバグを
  防ぐ**(`track()`のresolved集合と同じ考え方を、agentが直接読み書きする
  この経路にも独立に適用)。

## 4. スコープ判断(YAGNI、REV2で訂正)

| 項目 | 今回やる/やらない | 理由 |
|---|---|---|
| affiliate: `measure_commission.py`新規実装(account-level delta) + run.shへの1行配線 | ★今回実装★ | MEASURE/RECORDが完全に未配線だった実バグを、POSTをブロックしない形+実装可能な形で直す |
| affiliate: 既存POSTロジック(queue選択・アカウント選択・投稿) | 変更しない | 既に正しく動いている(6/30の2件は実際に投稿できた実績あり) |
| affiliate: per-post commission attribution | 今回やらない(実装不可能と判明) | `amazon_report.py`はアカウント全体・当月累計しか取得できず、個別投稿への帰属は
  Amazon Associatesダッシュボード自体に存在しない機能。account-level delta方式で代替 |
| bounty: `attempt()`のsurvivor選択ロジック修正 | ★今回実装★(小さい修正) | 既にclaimedなsurvivorに永久に足止めされるバグを直す |
| bounty: `track()`へのSTALLED検知追加(ループ外での追記+`BOUNTY_GH_OVERRIDE`追加) | ★今回実装★(小さい修正) | CLOSED(unmerged)を無視し続けるバグを直す、while-read中の追記競合も回避 |
| bounty: discover/gate/attempt/trackの内部ロジック(判定条件そのもの) | 変更しない | 既に正しく機能している(gate()のフィルタ条件等) |
| bounty: 「PRを書く」ステップの自動化 | 今回やらない | 本物のコード判断が必要、対話ターンの仕事のまま |
| bounty-cli.sh: STARTUP promptの順序変更(未完了work-order優先、REQ-B3に具体的文言記載) | ★今回実装★ | 「詰まる」実バグの直接対策 |
| affiliate/bounty双方のcli.sh STARTUP大幅簡素化(decide.py型への全面書き換え) | 今回はやらない、範囲を絞る | bountyは既に4モードの設計自体は健全(§3で確認)、affiliateもPOSTロジックは健全 —
  壊れていない部分まで書き換えるのは過剰実装。実際に壊れている箇所だけをピンポイントで直す |
| DEAD_ZERO_DAYS等の仮値 | account-level delta方式には不要になったため撤回 | §2の設計変更によりdead-zero判定自体が不要(投稿と計測を紐付けないため) |

## 5. 検証計画(GATE 2: TDD)

| 項目 | 検証方法 |
|---|---|
| `measure_commission.py`の全分岐(error/new-month-baseline/recorded/no-change) | `tests/test_measure_commission.py`新規作成、ダミーの`amazon_report_fn`/`ledger_record_fn`を注入(実ブラウザ不要、`amazon_report.py`のCDP呼び出し部分はテスト対象外) |
| `measure_commission.py`がPOSTをブロックしない | run.sh変更後、`~/affiliate/queue`に複数アイテムがある状態で1 wake実行し、`measure_commission.py`の結果に関わらずPOSTが実行されることを確認(結合テスト) |
| 既存POSTロジックが壊れない | 変更前後で`EARN_MODE=discover`の出力が一致することを確認 |
| `record-affiliate-earn.mjs`のINV-1〜5を満たすrowが生成される | `measure_commission.py`が構築する`--row`のJSONが実際にvalidateRow()を通過することを単体テストで確認(`report_export_id`の代替IDフォーマットも含む) |
| `attempt()`のsurvivor選択修正 | survivors 2件・1件目が既にattempts.jsonlにある状態を作る新規テストフィクスチャを用意し、2件目が選ばれることを確認 |
| `track()`のSTALLED検知(ループ外追記) | `BOUNTY_GH_OVERRIDE`でダミーの`gh`相当スクリプト(CLOSED、reviewDecision非MERGEDを返す)を注入し、`status:stalled`行がループ終了後に追記されることを確認 |
| bounty-cli.sh STARTUP順序変更 | プロンプト文字列内で「(0) CHECK FOR UNFINISHED WORK FIRST」が「(1) DISCOVER」より前に出現することを文字列比較で確認 |
| STARTUP文言(0)の断念ロジック自体の正しさ(GATE 1ラウンド4指摘、FIND-2対応) | プロンプト文言はLLM解釈でありコードとして直接実行はできないため、**同じ判定基準をPythonで決定論的に再実装したリファレンス実装**(`tests/test_unfinished_work_logic.py`、新規)を書き、3つのfixture(①stale claim・stalled行なし→GIVE UP相当の判定になる ②stale claim・既にstalled行あり→スキップ判定になる ③fresh claim・7日未満→PR続行判定になる)全てで意図した分岐になることを確認する。これはLLMが実際にこの通り解釈する保証にはならない(NLプロンプトの原理的限界、正直に明記する)が、判定基準そのものに論理的欠陥が無いことは決定論的に検証できる |
| queue backlog(affiliate 7件)の解消 | 実装後、次の自然wakeでqueueが減っていくことを継続監視で確認(POSTがMEASUREにブロックされなくなったため、1 wake 1件のペースで着実に減るはず) |
| bounty survivorへの初回attempt | 実装後、次の自然wakeでattempts.jsonlに実際に行が追加されることを確認 |
| `measure_commission.py`の実配線確認 | 実装後、実アカウントログイン環境で最低1回`amazon_report.py`呼び出し自体が成功することを確認(モック不可、実装後に別途実施) |

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
- **ラウンド2(REV2)**: FAIL。fresh-context Sonnet adversaryの指摘:
  (a)★致命的★ `measure_one.py`の設計が前提としていた「投稿アイテム単位のcommission
  確認」が実装不可能と判明 — `amazon_report.py`は引数を取らずアカウント全体・
  当月累計しか返さない、per-post attributionの手段がAmazon Associatesダッシュボード
  自体に存在しない (b) `track()`の「jsonlの最新行が正、という既存パターン」という
  主張が事実誤認(そのようなロジックは存在しない)、かつwhile-readループ中に同じ
  ファイルへ追記するのは未定義動作リスク (c) §5の「既存のテスト用フィクスチャ」が
  実在しない(`tests/`ディレクトリ自体が無い)、`gh`呼び出しにモック用のテストフックが
  無くGATE 2で指定した検証方法が実行不可能 (d) REQ-B3(STARTUP prompt順序変更)が
  抽象的な意図表明のみで具体的な文言が無い (e) §1.2の引用が「全文引用」と主張しつつ
  実際は数行省略していた。
  検証の結果、全て正当な指摘と確認。特に(a)は§2の設計全体を作り直す必要がある
  致命的な欠陥だった。
- **ラウンド3**: FAIL。fresh-context Sonnet adversaryの指摘:
  (a)★致命的★ 新month-baseline処理が、月初めて確認した時点で既にAmazon側が示す
  金額を一度も記録せず握りつぶす構造的バグ(HARD RULE 0.24 no-fake-earnの逆:
  no-fake-lossというべき欠落)、これが毎月確実に発生する (b) track()のstalled
  追記にidempotencyが無く、同じkeyに対して毎wake重複したstalled行を無限に
  追記し続ける新バグを作っていた(ラウンド2で直した競合を、別の形の未解決バグに
  すり替えただけだった) (c) REQ-B3の「未完了work-order優先」に断念パス
  (timeout)が無く、PRを開けない難しいbountyに永久ブロックされうる — このspec
  自体が解決しようとしている「詰まる」失敗モードを別の形で再生産する (d)
  REQ-B1の1点目(attempt()のsurvivor選択修正)が2点目と違い疑似コード無しで
  実装可能性を欠く。
  検証の結果、全て正当な指摘と確認。
- **ラウンド4**: FAIL。fresh-context Sonnet adversaryの指摘: (a)新月baseline処理
  ・track()のresolved集合・attempt()のsurvivor選択修正は全て正しく実装可能と
  確認(Q1/Q2/Q4 PASS)。(b)★ラウンド3で直したはずのF3(重複追記)と全く同じ
  バグが、REQ-B3の断念パス(agentが直接attempts.jsonlに書き込む経路)で
  再導入されていた — 「既にstalled行が存在するか」を確認せず`GIVE UP`のたびに
  新規追記する設計だったため、7日超過後は毎wake重複してstalled行が増え続ける
  (FIND-1、critical)。(c)この断念ロジック自体を検証する手段が§5に無かった
  (FIND-2)。(d)`wake`フィールドが数値である前提が未検証・未文書化だった
  (FIND-3、non-blocking)。
  検証の結果、(b)(c)は正当かつblocking、(d)も反映すべきと判断。
- **ラウンド5**: FAIL(局所)。FIND-1/2/3は全てAPPLIED-CORRECTLYと確認され、
  ラウンド1〜4で指摘された全項目・スポットチェックした既存引用も矛盾なし。
  新規発見: `measure_commission.py`(純関数は定義済み)が実際に呼ぶ
  `amazon_report.py`/`record-affiliate-earn.mjs`は別ディレクトリツリー
  (`~/.claude/skills/earn-affiliate-slideshow/scripts/`)にあり、この2つへの
  具体的な橋渡し(subprocess呼び出し等)が一度も書かれていなかった
  (REQ-B1の1点目がラウンド3で指摘されたのと同種の「疑似コード無し」欠落)。
- **ラウンド6(REV6、本ファイル)**: `measure_commission.py`の`__main__`ブロック+
  `_amazon_report_fn`/`_ledger_record_fn`という2つのsubprocessヘルパーを追加、
  クロスリポジトリ配線を具体化(REQ-A3)。次はこのREV6を再度fresh-context
  adversaryにかけ、PASSするまで実装に進まない。
