# 26 — gig ループ AS-IS / TO-BE / 実行計画（compact-proof 正本・忘れ厳禁）

**これは gig ループを「自己検証・自己修復・自己改善する best-practice browser-use loop」に直すための唯一の durable 計画**。会話は compact で揮発する→ここに全部焼く。SSOT(00) の L1 はここを指す。検証BPの詳細は [25-browser-use-verify-selfimprove-bp.md](25-browser-use-verify-selfimprove-bp.md)。

Dais 確定方針(2026-07-11):
- **先に B0/B1/B2 の capability を loop に持たせる**（今は「やれと指示すらされていない」＝当然やらない。特に **B0 出品は harness に存在しない**）→ その上に検証/自己修復を載せる。
- 移動/改名しない・その場で直す。一つずつ・各段階で私(claude-p)が **結果画面を browser で読んで**確認してから次へ。

---

## §1 AS-IS（実DOM確定・2026-07-11 :9222 で実観測。★私の初期ファイル推論「出品ゼロ」は誤りだった、browserが真実★）

アカウント: coconala、Google OAuth ログイン済（cookie `_coconala_session` ~2028、`CakeCookie[login_history]=Google`）。表示名 **「Kosuke AIエンジニア」**（= mtdc はハンドル/ID。Dais 確認済で正当）。KYC 済(Dais 確認)。

| 項目 | 実測 |
|---|---|
| loop 稼働 | ✅ ALIVE・今日も pass 完走。返信/応募/学習は活発（applied.jsonl 275行、lessons 100+pass） |
| **出品(サービス)** | **5件存在**: 公開中3=「業務自動化スクリプト Python/Node.js」¥10,000 /「SNSをAIで自動化しますます OSS自律AI」¥10,000 /「AI×AniccaがTikTok縦動画作りますます」¥3,000、**下書き放置2件(タイトル未設定)**。★ typo「しますます/作りますます」・下書き塩漬け・最適化ゼロ ★ |
| **取引中の注文** | **1件**: 買い手 jibieaian「IFU Double Face｜クラファン認知拡大 SNS運用代行」**¥40,000**・納品予定 2026/08/14・状態「取引中」（応募経由。**本物の金が1本動いている、未検収=未入金**） |
| earnings.jsonl | 空 = 確定入金 ¥0（¥40kは納品→検収待ち） |
| **harness の欠落** | ❌ **B0 出品ステップが STARTUP に無い**（cdp_shuppin.py も無い）＝loop は出品を作りっぱなしで**管理・改善・拡張していない**。応募(2%床)にだけ労力を注ぐ |
| **検証(auditor.sh)** | ❌ **report-skeptical でない** — core が自分で書いた applied/earnings.jsonl を信じるだけ。実の 出品管理/取引管理/売上 画面を読まない＝嘘・空回りを見抜けない |

**一言**: 「店を3つ開けたのに放置し、割の悪い出稼ぎ(応募)に通い続ける。出稼ぎ先で¥40kを1本掴んで今納品中。成果は自己採点。」

### 発見した正しい mypage URL（hard-won・実装で使う。ヘッダは `provider-header` の入れ子 shadow-DOM で querySelector 不可、再帰 shadowRoot 探索が必要）
- 出品サービス管理: `coconala.com/mypage/services_lists`（title「出品サービス管理」）
- 出品する: `coconala.com/services/add`
- 取引中(出品側): `coconala.com/mypage/received_orders/open`（title「取引中｜取引管理(出品)」）
- 売上/取引通知: `/mypage/activities/transaction`、`/mypage/dashboard_provider`
- 応募管理: `/mypage/job_matching/applied/offers`（単発/継続/スカウトのタブ）
- ※ `/mypage/services` `/mypage/identifications` `/mypage/received_orders` 等は 404。上記が正。

---

## §2 TO-BE（あるべき自走ループ）
```
        ┌──────────────── gig core (毎 pass) ─────────────────┐
[B0 出品] 自分の店を常時 手入れ・拡張: 下書き2件を完成公開/typo修正/
          公開3件を最適化(タイトル・説明・価格・画像)/AIが勝てるcat追加。
          → 受動 inbound 受注（100人と競合しない・応募2%床を回避）＝金脈
[B1 返信] 全トークルーム返信・仮払い来たら納品・検収→評価（現状維持=十分）
[B2 応募] 応募を継続、量↑・範囲↑(category直URL+keyword)・質↑（改善が主眼）
[納品]    成果物作成→納品→検収→高評価→リピート
   各ステップ後 → cdp_snapshot.py で screenshot+action を trajectory に記録
        └──────────────────────────────────────────────────────┘
                              │
     ┌──────────── verifier (report-skeptical, 別context) ──────────┐
     │ ①core報告に依存しない ②結果画面を自分で読む＝ground-truth:      │
     │   出品管理=公開中か / 取引管理=納品済か / 売上=¥立ったか(決め手) │
     │ ③trajectory+screenshot と突合→ 二値 PASS/FAIL + failure_reason  │
     └──────────────────────────────────────────────────────────────┘
                              │ FAIL / ¥0 継続
     ┌──────────── self-heal ────────────┐
     │ 失敗→Reflexion で教訓化→次passに注入 / 成功→AWM で再利用skill化   │
     │ 根が harness/コード → self-fix.sh が Opus で自分で修正→再検証     │
     └──────────────────────────────────────────────────────────────┘
```

---

## §3 B0/B1/B2/納品 の capability 定義（= STARTUP prompt に「何をせよ」を明記する中身。今 B0 は存在しない）
- **B0 出品(SHUPPIN・新規追加)**: 毎pass、`/mypage/services_lists` を読む→(a)下書き2件を完成させ公開 (b)typo・弱いタイトル/説明/価格/カバー画像を改善 (c)公開数が目標(例5-7)未満なら AIが勝てるcat(AI活用支援/資料作成PPT/SNS運用/記事/翻訳/文字起こし/LP/自動化)で `/services/add` から新規出品。成果物サンプルは公式 `pptx`/portfolio skill で作る。
- **B1 返信/納品(現状維持)**: 全トークルーム sweep→返信・仮払い契約は成果物作成して納品・検収済は評価依頼。¥40k jibieaian を確実に 2026/08/14 まで納品完了させる。
- **B2 応募(改善)**: `max_apply_per_pass` を上げ(5→10〜15)、scan を category直URL+keyword に拡張、AI禁止/実績必須/物理必須を除外、掲載直後(応募一桁)を優先。**質と量の両方を上げる**。
- 各ステップで **cdp_snapshot.py `<pass_id> <seq> <label>`** を呼び trajectory を残す。

---

## §4 検証設計（BP=25準拠。★決め手は screenshot でなく結果画面の実データ読返し★）
3層: ①trajectory(action ログ=弱) ②screenshot(中) ③**ground-truth 読返し(強・事実)**=出品管理/取引管理/売上 の実DOMを別途読む。
- 実装: `browser-use/benchmark/judge.py`(実fetch済198L) を copy+tweak した **gig_judge**。`JudgementResult{reasoning, verdict:bool, failure_reason, impossible_task, reached_captcha}`。
- report-**skeptical**: core の summary は渡すが「実際に起きたか screenshot/結果画面で二重確認せよ」と明示（judge.py L148/L143/L101）。ground_truth 不一致なら verdict 必ず false(L76)。二値判定(rubric中間スコア禁止)。
- 金(¥)は **実 売上/検収 画面 or 入金でのみ PASS**（jsonl の自己申告では PASS しない）。
- 別 context の fresh spawn で報告非依存を担保（= auditor が reality-verifier を起動）。

---

## §5 自己修復設計（BP=25準拠）
- verdict=false / ¥0 が N日継続 → **Reflexion**: 「何が違ったか」をテキスト教訓化し次pass prompt / strategy memory に注入。
- 成功 trajectory → **AWM**: 再利用可能 workflow/skill として memory 化（evaluator が correct と認めた物のみ）。
- 根が harness/コード → **self-fix.sh** が Opus で該当スクリプト/STARTUP を修正 → 同じ judge 基準で再検証（fix→verify 反復、上限5=VCSDD既定）。
- 連携ファイル: `~/.openclaw/state/.gig-core-selfheal-request.json`（STARTUP が pass 冒頭で読む既存フック）、`~/anicca/skills/self/self-fix.sh`。

---

## §6 実行順序と done 条件（★Dais順: capability を先に、検証/自己修復を後に★）

| # | 段 | やること | done（私が browser 実読で確認） |
|---|---|---|---|
| **1** | **B0 capability 追加** | STARTUP に B0 出品ステップ明記 + `cdp_shuppin.py`(出品作成/編集/公開) + 下書き2件完成・typo修正 | `/mypage/services_lists` に **公開中の出品が増え/整い**、下書き0、typo無し（実DOM） |
| **2** | **B2 改善** | max_apply↑・scan拡張・質向上を STARTUP に反映 | 1pass で応募数が実際に増え、AI禁止/物理案件を除外している（trajectory+実応募履歴） |
| **3** | **B1 確実化** | ¥40k jibieaian の納品を完遂させる導線を明記 | 取引管理で jibieaian が「納品済→検収」へ進む（実DOM） |
| **4** | **検証土台** | `gig_judge`(judge.py copy) + auditor を report-skeptical 化(結果画面読返し) | verifier が出品公開数/納品/売上を独立に読み二値判定を audit.jsonl に出す |
| **5** | **自己修復** | verdict=false/¥0継続 → Reflexion+self-fix.sh 配線 | 壊れた時 次passで自分で直り再検証が回る |
| **6** | **入金** | 出品 inbound か jibieaian 検収で初の実¥ | **売上画面 or 入金 tx を私が実読**で ¥>0 確認（自己申告不可） |

**done 全体**: 出品が手入れされ inbound を受け、応募も増え、納品が完遂し、verifier が結果画面で真偽を出し、失敗が自己修復し、**実¥が結果画面で確認できた**とき。それまで「完了」と言わない。

---

## §6.5 gig 稼ぎ戦略 spec(2026-07-08) 完全実装チェックリスト（★Dais 原案・全部やる・忘れ厳禁★）
正本 spec = `docs/superpowers/specs/2026-07-08-gig-feasibility-volume-listing-design.md`。★spec の scope は `~/profitable-claude/...` を指すが **live loop は `~/anicca/skills/earn/gig/`**。end-state は profitable-claude(G-PRODUCTIZE)だが当面 anicca live に実装する★。現実装率(2026-07-11 監査):

| spec MUST | 現% | 実装する内容 |
|---|---|---|
| §2 出品(listing)を本命チャネルに | ~20% | 今日 薄B0追加済。下記 playbook で格上げ |
| §50 出品で売れる型 | ~0% | タイトル=結果ベネフィット(検索語前半・50字)/サムネ文字入れ「修正無制限/即日/商用OK」/説明1000字「対象→内容→納品物→流れ→料金→注意」/松竹梅3プラン+有料オプション/実績ゼロは相場60-80%・モニター価格で星5最優先/カテゴリは成果物ベースで競合回避/毎日ログイン+週1更新 |
| §63 応募速度最重要 | ~30% | 新着(sort=new)優先・掲載直後30分以内・数日経過案件は無駄打ち回避を prompt rule 化 |
| §6/§7 50/50 自己改善(status quo + **BP web検索毎pass更新**) | ~0% | B4 に「agent-reach/firecrawl で gig BP を検索し出品/提案の型を更新」を追加。固定せず loop 自身が更新 |
| §6 funnel metrics(カテゴリ別 listings_live/proposals/replies/orders/paid_jpy) | ~30% | gig-funnel.jsonl 拡張・auditor 集計 |
| §3 viable 全件応募・飽和(応募30+)自動skip | ~50% | max_apply 12(済)+ 飽和 skip rule 明記 |
| §4 占い再分類(skip→listing 1カテゴリ) | 0% | strategy.json skip から「霊感/占い」除去→listing 対象へ |
| §5 never-refuse 明記 | ~30% | 「合法・実行可能な依頼は絶対断らない、断るのは feasibility不可 or 違法/scam のみ」を prompt に |
| §1 feasibility gate(可=browser完結/不可=電話SMS実地資格録音物理) | ~60% | 可/不可の明示定義を prompt に(skip列挙だけでなく) |
| §67 DM 30分返信 nurture | ~80% | 現状維持(唯一効いてる) |
| §73 個別作文(テンプレ一斉禁止) | ~70% | 依頼固有の一文必須を強化 |
| §69 最初の1件hack | ~10% | ニッチ絞る/競合上位10分析/プロフィール100%/本人確認/出品直後の露出ブースト期に即応募+通知者に即DM |

**全体 ~30-40% → 目標 100%。** 各項目 done = 私が結果画面 or loop出力で実装を実確認。

## §7 既に作った物 / 状態
- ✅ `~/anicca/skills/earn/gig/scripts/cdp_snapshot.py` — trajectory capture。**実 :9222 で screenshot 実撮影・成功確認済**（1920×854 PNG + trajectory.jsonl 生成、URL/title 記録）。
- ✅ `docs/loop-engineering/25-...bp.md` — 検証+自己改善BP（judge.py 実物裏取り）。
- ✅ 段#1 B0 capability: STARTUP に B0 SHUPPIN + trajectory + cron idempotent + max_apply 5→12 追加、commit+push、restart 活性化。
- ✅ **B0 実発火(2026-07-11 23:57)**: loop 自己申告で 下書き2件公開(業務AI活用診断¥8000/id4302213・SEO診断¥10000/id4244912) + 新規1件(見やすいパワポ¥8000/id4308502)。★未検証(reports lie)★ + typo「作りますます」残 + trajectory PNG 0枚(cdp_snapshot 未呼出=配線未効)。
- 🔄 **増分1(出品playbook格上げ) = VCSDD 実装済・審査中**: worktree `feature/gig-strategy-prompt-upgrade`(commit 935d3647)、verify 11/11 PASS(RED 7/11 非空確認)。fresh adversary(Sonnet) 実行中。
- ⬜ **RESUME 手順(compact後ここから)**:
  1. adversary PASS(blocking 0)確認 → `cd ~/anicca && git merge feature/gig-strategy-prompt-upgrade`（live working tree へ反映）
  2. ★live `~/gig/strategy.json`(v38) の skip_categories から「霊感/スピリチュアル/占い」を削除★（builder既知課題・default だけでは propagate しない・passprep は live 優先）
  3. `bash ~/anicca/skills/earn/gig/gig-cli.sh --restart` で playbook 活性化
  4. **私が browser :9222 で own-eyes 確認**: /mypage/services_lists で 3サービス公開中 + typo「作りますます」が直った + 松竹梅/モニター価格反映 / trajectory PNG が今度は出るか
  5. 次増分: funnel metrics(コード) → 50/50 BP web検索自己改善 → verifier土台(gig_judge) → self-heal配線
- copy元 judge.py: scratchpad/judge_bu.py（raw main 198L, VERIFIED）。worktree cleanup: merge後 `git worktree remove .worktrees/gig-strategy-prompt-upgrade`。
