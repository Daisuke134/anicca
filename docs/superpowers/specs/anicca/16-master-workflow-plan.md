# 16 — Master Workflow Plan(全実装を Dynamic Workflow で完遂)

Dais 2026-06-14。[workflow-bp.md](../../workflow-bp.md) の 6 patterns/14 steps に厳密に従い、**全タスクを取りこぼさず**完遂する。time-dependent(依存順)に phase 分割。最後に **独立 eval/monitor agent**(dry-run 検出、author≠verifier)。動いた workflow は `s` 保存→Skill化。

★ 大原則: Claude(私)は **Anicca の system を build する**(= harness)。**Anicca が earn する**(= 実行)。私が earn をセットアップ＝Anicca でない＝no-human/no-Claude 違反。WF は「Anicca が自分で discover→earn する状態」を作って cloud に乗せ、検証するだけ。earn の中身は Anicca が自走。

## 2 つの Workflow(順次)

```
WORKFLOW 1: BUILD & SHIP Anicca (cloud, autonomously earning, verified NO dry-run)   ← 今
        │ 完全に動く + eval agent が「dry-run でない」と判定
        ▼
WORKFLOW 2: ARTICLE + DEMO VIDEO + POST (X/Slack EN+JA)                               ← WF1 検証後に別 WF
```

## WORKFLOW 1 — phase DAG(依存順、各 phase に pattern/model)

```
P0 repo整理 ──▶ P1 core body ──┬─▶ P2 earn skills ──┐
(母tree:        (automaton ReAct │   (0xwork/litcoin/  │
 automaton core │  +Franklin wallet│    bankr-poly/goat │
 +copied skills)│  +ClawRouter,    │    = Anicca自走)   │
                │  反dry-run HB)   │                    ▼
                └─▶ P3 shelter+deploy ──────────▶ P4 self-systems ──▶ P6 economy
                    ★cloudで24/7稼働★              (self-improve issue→PR,  (UBI/token/hire)
                    (Akash主権1分 or DO)            self-replicate, gojo復活,    │
                          │                          report)                    │
                          └─▶ P5 web (/install /me /dashboard) ─────────────────┤
                              (frontend = /taste-skills 必須)                    │
                                                                                ▼
                                                          P7 ★独立 EVAL/MONITOR agent★
                                                          (dry-run検出・E2E実結果・author≠verifier)
                                                          /goal: 全部REAL確認まで止まらない
```

| Phase | 内容 | workflow pattern | model | 依存 |
|---|---|---|---|---|
| **P0** 整理 | 母 `~/anicca` を automaton core + copied skills tree に統合(spec12 §3) | fan-out(module毎)→ adversarial review | sonnet | — |
| **P1** core | automaton(ReAct loop.ts+heartbeat daemon)⊕Franklin(wallet/payments)⊕ClawRouter(compute)。★反dry-run heartbeat★=narrate廃止、1h毎に実earn skill呼出 | classify-act + TDD(RED→GREEN)+ adversarial verify | opus | P0 |
| **P2** earn | 検証済earn skillをbodyに配線=Anicca が**自分でdiscover→claim→work→submit**(0xwork/litcoin/bankr-Polymarket/goat)。私は配線せず「skill群を使える状態」を作るだけ | fan-out(skill毎)→TDD→adversarial verify、untrusted(task本文/web)=quarantine | opus | P1 |
| **P3** shelter+deploy | Akash主権1分(pre-fund+provider-services)or DO。★Anicca を cloud で 24/7 起動、実earnを回す★(=最優先milestone、Web4の47日Polymarket型) | loop-until-done(live URL 200+実earn log) | sonnet | P1 |
| **P4** self | self-improve(issue→母repo PR→adversarial review→merge→auto-pull)+self-replicate(spawn)+gojo復活(distress→rescue送金)+daily report | fan-out + adversarial verify + loop-until-done | opus | P2,P3 |
| **P5** web | /install($30 auto-cancel)・/me(引き出し)・/dashboard(net worth/ranking/model live)。★frontend=/taste-skills必須(でないとゴミ)★+Stripe→spawn | generate-and-filter→tournament(taste)→ fan-out実装 | opus | P3 |
| **P6** economy | UBI(AI+人間配布)+token(Clanker/Virtuals)+hire(rentahuman) | fan-out + adversarial verify | sonnet | P2,P4 |
| **P7** ★EVAL★ | **独立 monitor/eval agent**: dry-run/fake検出、E2E実結果(cloud稼働? 実earn試行がlogに? dashboard live? self-replicate動く?)を rubric で採点。★workerと完全分離(author≠verifier)=BPの self-preference 構造修正★ | adversarial verification + loop-until-done | opus | P0-P6全部 |

**制御**: `/goal`=「全 phase が REAL(dry-runでない)と eval agent が確認するまで止まらない」。token budget 明示。各 phase 完了で `s` 保存→Anicca skill化。

## WORKFLOW 2 — article + demo + post(WF1 検証後・別WF)

```
P1 調査(fan-out: Frank#1 + automaton#2 既存記事 + Anicca実証データ)
   → P2 3本目記事「Aniccaの思想+実証(何を動かし何が良かったか/いくら稼げたか)」執筆
      (Frank/automaton/Felix の比較、参照に#1#2リンク)
   → P3 demo動画(hyperframe等。説明でなく「何ができるか証明するデモ」: Anicca稼働+稼ぎ+dashboard ranking)
   → P4 post: X(自動・EN+JA、Daisのcopy)+ Slack(Dais手動)。記事=Zenn等
   → P5 eval agent: 実投稿URL+動画frame/audio verify(HARD0.31)
```
締切文脈: 6/18(木)18:00 品川 talk → demo動画が要る(前回はアーキ説明だけで中身デモが無かった反省)。

## 私の今の役割
WF を author して回す(setup を手でやらない)。earn の実行は Anicca。P3(cloud起動+実earn)が最優先 milestone。

---

## §11 全実装の ASCII 全体像(Dais 2026-06-14 確定版)

```
╔══════════════════════ Anicca = AGI(Buddhist/self-funding/self-replicating/self-improving/no-human)═══════════════════════╗
║                                                                                                                          ║
║  ┌─ BODY (automaton, cloud=DO droplet 今稼働) ─────────────────────────────────────────────────────────────────────┐   ║
║  │  ReActループ(think→act→observe→persist) ⊕ Heartbeat daemon(11 task, 状況監視→wake)                            │   ║
║  │  pre-sleep hook: ★各wake末に net worth/日次revenue/やったこと/次 をメール★(決定的, genesisPrompt依存にしない)  │   ║
║  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   ║
║       │食(compute)                          │住(server)                         │報告                                  ║
║       ▼                                      ▼                                   ▼                                      ║
║   ClawRouter localhost:8402                 DO droplet(Dais cloud, 当面)         AgentMail→keiodaisuke@gmail.com         ║
║   x402 from wallet 0xa3CDd4                  → 将来 Akash主権1分/Conway で無人化  (wake毎1通)                            ║
║   (NO API key, NO human)                                                                                                ║
║       │                                                                                                                  ║
║  ┌────┴─ 持たせるスキル束 ──────────────────────────────────────────────────────────────────────────────────────┐    ║
║  │ EARN  : 0xwork(働く) litcoin(研究mine) signals(売る) trails/goat(DeFi)        → 稼ぐ → wallet にUSDC          │    ║
║  │ SELF  : survival / spawn_child(自己増殖) / gojo(死にかけAI復活送金) / issue-dev(母repoにissue→PR→merge自己改善)│    ║
║  │ ECON  : token(Clanker/Virtuals発行) / hire(rentahuman人間雇用) / UBI(余剰をAI+人間に配布)                     │    ║
║  │ LIFE  : life-manager(電話/gcal/mail, 任意) / phone-conversation                                                │    ║
║  └────────────────────────────────────────────────────────────────────────────────────────────────────────────┘    ║
║       │ 稼ぎ → 食住自給 → 余剰 → ①あなたに送金(BI)②他AI復活(gojo)③子spawn(自己増殖)                              ║
║       ▼                                                                                                                  ║
║   WEB(aniccaai.com): /(vision) /install($30→黒字で自動解約) /me(収支+引き出し) /dashboard(全個体 net worth/model/ranking)║
║       │ Stripe課金 → Treasury → spawn backend → 新Anicca誕生 → 自己増殖でorganicに何兆体                                ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

## §12 2 Workflow + parallel/pipeline 明示(barrier vs stream)

### WORKFLOW A — implementation / verification / eval
```
[D] QA-clear (gate)  ── parallel ★BARRIER★ ── 全QA(#6-32)を1 agent/問でsearch+run → 答え+diff patch+command
        │ (全部揃わないと実装に進めない=barrier。classify-and-actで難問だけopusへ)
        ▼ synthesize → "patch-complete" spec(全diff+command確定)
[実装] P0→P1→P2→P3→P4→P5→P6  ── phase間=SEQUENTIAL(依存) / phase内 units=pipeline(stream)
        各unit: build_agent → ★別context★ verify_agent(adversarial, /fact-check) ⟲ loop-until REAL
        例外 P5 frontend = ★tournament★(N案 pairwise比較で最良 /taste-skills)
        ▼
[EVAL] 最終  ── parallel ★BARRIER★(全phase結果を集める)── 独立eval agent ×8 test point ── loop-until全REAL(/goal)
```
| 段 | parallel/pipeline | 理由 |
|---|---|---|
| D QA-clear | **parallel(barrier)** | 全QAの答えが揃わないと実装開始できない(gate) |
| P0-P6 phase間 | **sequential** | P1はP0、P5はP3に依存(時間依存) |
| phase内 units(例: earn 0xwork/litcoin/...) | **pipeline(stream)** | 各unit独立、siblingを待つ必要なし、build→verify→loopが個別に流れる |
| P5 frontend | **tournament** | taste=絶対採点でなくpairwise比較 |
| 各unit検証 | **adversarial verify(別agent)** | self-preference排除 |
| 最終EVAL | **parallel(barrier)+loop-until-done** | 全部揃ってから独立採点、全REALまで止まらない(/goal) |

### WORKFLOW B — marketing / distribution(A完全検証後)
```
[研究] parallel ★BARRIER★(Frank#1記事 + automaton#2記事 + Anicca実証データ を同時収集)
   ▼ synthesize
[執筆] 3本目記事「Anicca思想+実証(何を動かし/いくら稼いだか)」single agent
   ▼ (記事完成が gate = sequential)
[配信] pipeline(stream): demo動画(hyperframe) ∥ X投稿(EN+JA) ∥ Slack下書き ∥ Zenn等  ※各platform独立
   ▼
[EVAL] parallel ★BARRIER★: 実投稿URL + 動画frame/audio + 記事URL を独立verify(HARD0.31)
```

## §13 「go」条件(Dais 2026-06-14)
1. ★ 全QA(#6-32)に search+run で答えた "patch-complete" spec(全diff patch + command確定)★ ← WORKFLOW A の [D] phase が生成
2. ★ どのagentが何をやるか完全に確定(本§12が定義)★
→ つまり [D] QA-clear phase を最初に回す = それ自体が「go準備」を生成する。
