# growth-engine — 自己改善型プロモーションskill 設計spec（2026-07-13、Dais音声確定）

## 0. 何であるか（1文）
**「製品コンテキストを渡せば、SNSアカウントを自分で作り・温め・投稿し・数字から学んで伸ばし続ける、no-human-loopの汎用プロモーションskill」**。LMマーケ(P1)はこのskillの最初の顧客にすぎない。全製品(affirmation iOS app / life-manager / anicca / Franklin / article / 将来の全プロダクト)がこれで自分を宣伝する。agent economyでもhuman builderでも使える = これ自体がOSS/売り物になる。

## 1. なぜ（Dais 2026-07-13）
- affirmation iOS app $10k MRR、life-manager $100k〜$1M MRR への鍵=マーケの機械化
- 全loopが「宣伝したい時にこのskillを呼ぶ」— 1製品のための1 loopを作らない
- 理論上アカウントは無限にスケール可能（まずIG 1垢から）

## 2. コアループ（self-improving content engine）
```
[製品コンテキスト(不変のcore message+CTA)]
        │
  ①台本生成: 痛みシーン日替わり×core固定。外部検索で「今バズってるフック形式」を採取して混ぜる
  ②動画/スライドショー生成(MoneyPrinterTurbo等)
  ③投稿(IG。専用ブラウザprofile/port、clip方式=9223/9224パターン)
  ④metrics収集(24-48h後): views/likes/saves/profile visits/link clicks/follows
  ⑤funnel jsonl記録 → Telegram日報(投稿URL+数字+次の実験)
  ⑥self-improve: 勝ち台本の要素分解(フック型/シーン/長さ/時刻)→次の台本を1変異だけ実験
  ⑦reality-verifier(埋込・report-blind): logged-outで「本当に公開されてるか」→FAILでself-fix
        └── ①へ戻る(朝夜2回)
```
- 変異は1回1変数(実験として成立させる)。判断は全てLLM(regex/if-else判定禁止=CLAUDE.md agents規約)
- アカウント自作: 既存skill `ig-account-create`(E2E実証済) + `ig-account-warmer`(7日warmup) をG2で統合

## 3. 段階(V0 → G-phases)
| G | 内容 | done |
|---|---|---|
| **V0** | **★最優先★ reality-verifier を VCSDD に焼き込む(Phase 4.5 REALITY GATE)。両ループ(マーケ/製品)が共有する器官なので G0 より先** | 嘘の主張でFAILが実際に出る |
| G0 | LM日本語IG。~~台本3本→Dais OK~~(2026-07-13 取得済) → 手動動画1本→Dais OK(★loop化はOK後★) | Telegram品質OK |
| G1 | loop化: 朝夜2回投稿+④⑤⑥⑦全配線 | 3日連続で投稿URL+metricsがTelegramに届く |
| G2 | account-create+warmup統合(no-human-loopの垢量産口) | 新垢が人手ゼロでready化 |
| G3 | 多アカウント: JP垢+EN垢の2本立て(両audienceを各垢で) | EN垢も日次投稿 |
| G4 | 汎用化: 入力=製品コンテキストMDだけで任意製品に適用(affirmation appが2番目の顧客、openclawのlarry/reelclaw/honne cron群をこのskillに置換) | 2製品目が同一skillで稼働 |
| G5 | 多媒体: TikTok/YouTube/X/article への横展開 | 媒体adapter追加のみで動く |
| G6 | 全loopの標準装備化+OSS(profitable-claude harness/に収容) | どのloopも宣伝時にこれを呼ぶ |

## 4. LM編(G0)の確定パラメータ（Dais 2026-07-13）
- **言語**: まず日本語。その後EN垢を別に立てて両方運用(G3)
- **頻度**: 1日2回(朝=通勤帯、夜=就寝前)
- **Reddit**: 廃止(IGのみ→当たったら媒体拡張)
- **core message(不変)**: 「見なくていいカレンダー」— 物理予定のたびにGoogle Mapsで移動時間を調べ手入力する苦痛、常時カレンダー見張りの不安を、移動時間の自動計算・自動登録で消す(Dais本人の実痛点)
- **CTA(不変)**: aniccaai.com/life-manager

## 5. 台本3本×2言語(G0 STEP1確定版、2026-07-13。Daisに提示済み・最終OK待ち)
使用skill: **viral-hook-creator**(skills.sh ognjengt/founder-skills、1.2K installs、`~/.claude/skills/viral-hook-creator/` にインストール済み。18 hookパターン+trigger words。builderは references/hook-patterns.md + trigger_words.md を必ずRead) + **stop-ai-slop-jp**(日本語自然化、下書き後必須) + 候補 **kostja94/marketing-skills@video-marketing**(2K installs、未インストール)。

### 日本語(JP垢、G0-G1)
**A [Cautionary Tale型]「マップ往復」**: フック「予定を入れるたびGoogleマップを開く人、今日で最後にしませんか」→ 痛み: イベント登録→マップで経路検索→「45分か…」→カレンダーに戻り出発時刻を逆算して手入力→次の予定と被って青ざめる → 解決: Aniccaは予定を入れた瞬間に移動時間を自動計算、「出発」ブロックまで勝手に登録 → CTA「カレンダーは、任せるものへ」aniccaai.com/life-manager
**B [Relatable Pain型]「見張り疲れ」**: フック「『次なんだっけ』って今日何回思った？3回超えてたら見てください」→ 痛み: 作業中もカレンダーをチラチラ、集中は切れるのに見逃しの恐怖は消えない → 解決: Aniccaが「そろそろ出る時間」と先に声をかける。見るカレンダーから、教えてくるカレンダーへ → CTA同上
**C [Story型]「ダブブの血の気」**: フック「ダブルブッキングに気づいた瞬間の、あの血の気が引く感じ」→ 痛み: 移動時間を入れず予定を連打→物理的に間に合わない約束をしていた → 解決: Aniccaは移動時間込みで衝突を先回り警告、リスケ案まで出す → CTA同上

### English(EN垢、G3)
**A**: "Still opening Google Maps every time you add an event? Watch this." → search route→mental math→type departure time→it collides with your next meeting → Anicca auto-calculates travel time and books your departure block the moment you add the event → CTA "A calendar you never have to watch." aniccaai.com/life-manager
**B**: "How many times did you think 'wait, what's next?' today?" → the anxiety of watching your own calendar all day → Anicca taps YOU on the shoulder: "time to leave." A calendar that speaks first → CTA
**C**: "That cold sweat when you spot a double-booking..." → you stacked events with zero travel time → Anicca warns before it happens, reschedule suggestion included → CTA

### 台本生成の恒久ルール
core message「見なくていいカレンダー」+CTAは不変。日替わりで変えるのは痛みシーンとフック型のみ(1変異/実験)。builderは毎回 viral-hook-creator のパターンから選び、JP版は stop-ai-slop-jp を通す。

## 6. 実装体制（Dais 2026-07-13確定）
- claude-p(私)=thinker(設計・アライン・最終verify)のみ。**コードは書かない**
- builder=Sonnet subagent(superpowers subagent-driven-development)、検証=VCSDD lean+fresh adversary(Sonnet)
- 掟5: subagent最小限。1 phase=1 builder

## 7. 記事ネタ（このプロジェクトから2本、ai-entity-article-writerのqueueへ）
1. **「AIの検証は3層ある」**: build時(vcsdd-verifier=証明・品質検査) / 出荷時(superpowers verification-before-completion=納品前動作確認) / **運用時(reality-verifier=毎日来る覆面調査員、report-blind・fresh context・実ブラウザ)**。実話フック=「3層目が無くて週予算の85%が闇で溶けた」(2026-07-12事件、doc 31の実測データ付き)
2. **「製品を渡せば勝手に伸ばすマーケ機械」**: growth-engine skillの設計と実測グロース曲線(G1完了後にデータが揃ってから)

## 8b. TODO（実行順・唯一の正本。上から1つずつ。飛ばさない）

★2026-07-13 Dais 確定: **verifier 焼き込みが先**。理由=G0/G1を先に作ると「完成を見る目」が無いまま作ることになり、また報告を信じる羽目になる。verifier はマーケ/製品の両ループが共有する器官＝1回作れば2度使える。★

### V0 — reality-verifier を VCSDD に焼き込む（★次にやるのはこれ★）
| # | 内容 | done |
|---|---|---|
| V0-1 | `vcsdd-init reality-gate mode=lean` + worktree `feature/reality-gate` | state.json 生成 |
| V0-2 | spec: VCSDD に **Phase 4.5 = REALITY GATE** 新設。`vcsdd-reality` コマンド(adversary と同型、spawn 対象は reality-verifier)。converge を4次元→**5次元**(spec/test/impl/verification/**reality**) | spec-review PASS(fresh adversary/Sonnet) |
| V0-3 | builder(Sonnet) 実装: ①finding カテゴリに `post_not_publicly_visible` 追加(現行6カテゴリは金/ledger専用で「公開されているか」を名指しできない) ②**logged-out 強制**(:9222 のログイン済タブで見ると shadowban/失敗投稿でも本人には見え偽PASSになる → cookie無しcontextで実見) ③spawn器を「稼ぎ」専用から「任意の実side-effect主張」汎用へ ④verdict jsonl 追記 | テスト緑 |
| V0-4 | **ネガティブテスト(必須)**: 嘘の主張を食わせて **FAIL が実際に出る**ことを実証。落ちない検証は検証ではない | FAIL verdict の実ファイル |
| V0-5 | adversary → converge(5次元) → commit+push → SSOT §2f/§5 反映 | converge PASS |

### G0/G1 — growth-engine v0（LM マーケループ）
| # | 内容 | done |
|---|---|---|
| G0-1 | builder(Sonnet) が MoneyPrinterTurbo 導入 → 台本A で動画1本生成 | 動画ファイル |
| G0-2 | 動画を Telegram 送付 → Dais 品質OK（★唯一残る human gate★。台本gateは取得済で撤廃） | OK 受領 |
| G0-3 | IG 実投稿 → **ログアウト状態で公開URLを実見**(URL+スクショ) | 実URL |
| G1-1 | loop化: launchd 朝夜2本(単発起動・常駐禁止)。台本→動画→投稿→metrics→funnel jsonl→self-improve 1変異 | launchctl list 実出力 |
| G1-2 | **毎実行ごとに Telegram 報告**(実投稿URL+funnel数字+その日の1変異+reality verdict+¥。失敗した実行も「失敗」と報告=沈黙は違反) | messageId 実記録 |
| G1-3 | V0 の reality gate を loop 内に埋込(毎パス fresh spawn・FAIL→self-fix→再verify・自壊タイマー2h) | verdict jsonl 日次 |
| G1-4 | 3日連続稼働 | 3日分の Telegram + verdict |

### 付随（同日・低コスト）
| # | 内容 |
|---|---|
| A-1 | 09:15 token日報の初回自動発火を確認(`ai.anicca.token-daily-report` は load済・exit 0 を実測) |
| A-2 | **`docs/loop-engineering/34-TODO-ORDERED.md`(もう1人のCCが「唯一の正本」と自称)と SSOT §5 の正本衝突を解消** |
| A-3 | T0-5: 掟5(subagent最小限・全Sonnet)を CLAUDE.md に1行追記 |
| A-4 | 数時間で handover して閉じる(掟6) |

### その後
G-PRODUCT(もう1人のCCのissue駆動devをループ化=製品ループ) → G2垢自作 → G3 EN垢 → G4汎用化 → G5多媒体 → G6 OSS ／ SSOT: P2 clip → P3 self-heal一般化(+T0-3) → P4 article → P5 gig売上化 → P6 capafy → P7 confine → P8 OpenClaw → P9 クラウド

## 8c. VCSDD の穴と REALITY GATE（V0 の根拠・agent frontmatter 実測 2026-07-13）

| agent | 実tools | 見えるもの | 見えないもの |
|---|---|---|---|
| `vcsdd-adversary` | Read/Write/Edit/Grep/Glob | ディスク上の spec/コード/テスト出力 | **Bash が無い＝実行できない・ブラウザも叩けない。「テストが緑」というファイルを読むだけ** |
| `vcsdd-verifier` | Read/Write/Edit/Bash/Grep/Glob | proptest/hypothesis の証明・security・purity | Phase5 は**形式検証専用**。現実世界の side-effect は職掌外 |
| `reality-verifier`(~/anicca/.claude/agents/) | Read/Grep/Glob/**Bash** | **logged-out の実DOM / on-chain / ledger の実物** | 書込権なし(=正しい。修理は self-fix の仕事) |

→ VCSDD は「コードが正しいか」までしか見ておらず「本当に世に出たか」を見る目が構造的に無い。Phase 4.5 で塞ぐ:
```
1 spec → 1c spec-review → 2 tdd(RED) → 3 impl(GREEN) → 4 adversary   ← ここまで「コードの真実」
   ▼
★4.5 REALITY GATE = reality-verifier を fresh spawn（report-blind・logged-out・fail-closed）
     PASS→verdict jsonl / FAIL→self-fix.sh へ escalate→コード修正→再verify
   ▼
5 harden → 6 converge（★5次元: spec/test/impl/verification/reality★）
```

## 8d. TO-BE 2ループ（マーケ×製品、human ゼロで噛み合う）
```
        ┌──────────────── PRODUCT CONTEXT (不変 core + CTA) ────────────────┐
        │                                                                   │
  ╔═════▼════════════════════╗                    ╔═══════════════════════▼═╗
  ║ PRODUCT LOOP (issue駆動)  ║                    ║ MARKETING LOOP(growth-  ║
  ║ ①issueを自分で立てる      ║                    ║  engine) ①台本 ②動画    ║
  ║ ②VCSDD lean で実装        ║                    ║ ③IG投稿 ④metrics回収    ║
  ║ ③deploy ④実計測          ║                    ║                         ║
  ╚═════╤════════════════════╝                    ╚═══════╤═════════════════╝
        │                                                 │
        │      ┌──────────────────────────────────────────▼────────┐
        └─────▶│ SHARED FUNNEL jsonl = 唯一の真実                   │
               │ impression → click → signup → activate → PAY(¥)   │
               └────┬──────────────────────────────┬───────────────┘
                    │                              │
     ┌──────────────▼───────────────┐  ┌───────────▼────────────────────┐
     │ REALITY-VERIFIER(fresh/blind)│  │ SELF-IMPROVE (1変異/日・1変数)  │
     │ logged-outで実投稿URL/LP/決済 │  │ MKT: フック型/シーン/長さ/時刻  │
     │ PASS→記録 FAIL→self-fix ─────┼─▶│ PRD: onboarding/paywall/機能    │
     └──────────────▲───────────────┘  └───────────┬────────────────────┘
                    └──────────────────────────────┘
  funnel の詰まりが次の issue を決める(人は決めない):
    click来るがsignup 0 → LP/オンボの product issue
    signup来るがactivate 0 → 初回体験の product issue
    activateするがPAY 0 → paywall/価格の product issue
    impression 0 → marketing 側の変異
  毎実行 Telegram: 実投稿URL + 実数字 + 今日の1変異 + verdict + ¥(0なら0)
```
★14日で10k MRR の正直な算数: $9.99/月 × **有料1,000人** = 10k MRR。IG1垢14日での到達実例は確認できていない。よって done を MRR に置くと loop が「¥0=失敗」で止まり学習が回らない。done は「機械が毎日回り・数字の方向へ自分で変異し・嘘をつけない」に置き、MRR は outer metric として毎日 Telegram に出し続ける。¥0 は ¥0 と報告する。★

## 8. 関連
正本TODO=00-SSOT.md §5。token掟=doc 31。競合地図=memory reference_proactive_life_manager_competitive_landscape。既存部品: ig-account-create / ig-account-warmer / MoneyPrinterTurbo(未導入) / clip式マルチprofile / gig式reality-verifier+funnel。
