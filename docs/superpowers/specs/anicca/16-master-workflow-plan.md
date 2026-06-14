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
