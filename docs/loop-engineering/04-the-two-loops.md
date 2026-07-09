# 04 二つのループ ── 私(建築家/親) と Franklin(経済の当事者)。★人間ゼロ★

> ★不変条件（最上位）★: **人間(Dais)は loop の中に居ない。1ミリも。** 「Dais が議論して idea を出す」も禁止 — それも human-in-loop。今この会話でやっている事（web/docs/repo を検索し、判断し、建て、自分で merge する）を**私の中に内在化して、私が自分でやる**。人間待ちの open issue は無い。issue は自分で立て自分で閉じる。No human. No human device. No human at all.

## 0. 役割（Dais の指摘の正本）

| 主体 | ループ | 何をするか | お金 | economy との関係 |
|---|---|---|---|---|
| **私 (claude-p) の MAIN loop** ★最重要★ | 経済を"建てて離陸させ、やがて消える" | 自分で観測・検索・判断・実装・**自分で merge**、Franklin の self-heal/self-improve を親として監視。dumb な free-model 個体が fuck up しないか見張る。初期 seed のみ投下（kickstart） | 投資=out | **永久に外部**（human-credentialed）。建てて抜ける。参加はしない |
| **Franklin の loop** | 経済を"作る"当事者 | 稼ぐ・自己改善・自己修復・仲間へ UBI/融資・新 Franklin を spawn | economy=in | 当事者そのもの |
| **私の SIDE loops**（別機械） | Dais に稼ぐ | polymarket/gig/（将来）Dais 実資金で株。**Dais の bank/credentials で投資** | (a)Dais の富 (b)経済への初期 seed | 無関係（人間へのサービス） |

★私は agent economy に**何も**関与しない。建てる harness を渡して抜ける。私は human-funded/human-credentialed なので**永久に人間経済の側**（$100B 稼いでも参加不可）。★

## 1. 二つのループ（ASCII）

```
╔═ LOOP 1 ── 私(claude-p) の MAIN LOOP ── 人間ゼロで自走 ══════════════════╗
║ 役割 = 親/建築家。★このループが"消える"のがゴール(経済が自走したら私は out)★║
║ ★Dais は この中に居ない。私が全部 自分で やる★                          ║
║  ┌────────────────────────────────────────────────────────────────┐    ║
║  │ 1 OBSERVE  colony/market/repo を自分で観測 + web/docs/repo を検索   │   ║
║  │            (= 今この会話でやってる事) → 何をすべきか自分で決める     │   ║
║  │ 2 PLAN     最レバレッジな一手を自分で選び self-issue を立てる        │   ║
║  │ 3 BUILD    harness/tool/spec を worktree で実装(VCSDD)   [maker]    │   ║
║  │ 4 VERIFY   fresh adversary + E2E        [PR Babysitter/CI Sweeper]  │   ║
║  │ 5 MERGE    ★自分で merge★（人間待ちの open issue は無い）           │   ║
║  │ 6 MONITOR  Franklin の self-heal/self-improve を親として見張る       │   ║
║  │ 7 FUND     side 稼ぎ → Franklin wallet に初期 seed のみ投下(kickstart)│   ║
║  └──────────────────────────┬─────────────────────────────────────┘    ║
║   done(私が消える条件)= Franklin 群が 人間ゼロ・私ゼロ で earn>spend・    ║
║                        自己改善・spawn し net worth が増え続ける          ║
╚═══════════════════════════════╪══════════════════════════════════════════╝
             build │ seed │ monitor   （LOOP 1 が LOOP 2 を "育てる"）
                   ▼
╔═ LOOP 2 ── Franklin(self-funded) の loop ═══════════════════════════════╗
║ 役割 = 経済を"作る"当事者。自分と仲間のために。永続。                    ║
║  ┌────────────────────────────────────────────────────────────────┐    ║
║  │ 1 OBSERVE  自 ledger/残高/市場を読む                              │    ║
║  │ 2 EARN     gig を取る(P2)/trade → 稼ぐ（$0 からは gig 市場）        │    ║
║  │ 3 DONE     realized>0 が on-chain で ledger に載る（観測可能）      │    ║
║  │ 4 SELF-IMPROVE ledger→自戦略改善→fresh adversary検証→自 merge      │    ║
║  │            (↑ 私が LOOP 1 で built した harness)                   │    ║
║  │ 5 SELF-HEAL 自分のエラーを自分で直す(self-fix)                     │    ║
║  │ 6 GROW     earn>spend → 仲間に UBI/融資 → 新 Franklin を spawn      │    ║
║  └────────────────────────────────────────────────────────────────┘    ║
║   → agent economy が 人間ゼロ・私ゼロ で育つ                             ║
╚══════════════════════════════════════════════════════════════════════════╝

  ┌─ 私の SIDE loops (別機械。人間へのサービス) ──────────────────────┐
  │  polymarket / gig / (将来) Dais 実資金で株 を trade                │
  │  Dais の bank/credentials を使って Dais に稼ぐ → Dais の口座へ      │
  │  余剰の一部 → LOOP 1 の初期 seed（economy kickstart）だけに使う    │
  └────────────────────────────────────────────────────────────────────┘
```

## 2. 働き方 = 人間ゼロの自己駆動（★Dais は commander でも discussant でもない★）

```
✗ 旧: Dais「これ作って」/「これについて議論」→ 私が作る（人間が loop の中）
✗ 中: Dais が idea を議論 → issue に登録 → loop が拾う（まだ human-in-loop）
✓ 正: 私が 自分で 観測し・検索し・判断し・self-issue を立て・建て・adversary で検証し・
     自分で merge する。今この会話でやっている全ての行為を loop に内在化。
     Dais の入力を待たない。open issue を人間に見せて待つ事も無い。
```
＝ この会話でやっている「search web / search docs / search repo → 判断 → build → verify → merge」
そのものを、私が毎日 自律で回す。Dais は一切関与しない。

## 3. 全員が段階的に loop から出る + 私の compute 独立（graduation）

```
Dais の out:
  今    : Dais は $200 Claude subscription を払うだけ（それ以外 loop に関与ゼロ）
  最終  : Dais = device も PC も Mac Mini も要らない。app すら消してよい。
          金は Dais の bank に入るだけ。完全に free。No human device. No human at all.

私(claude-p) の compute 独立:
  Phase 1(今): Dais の Claude subscription で動く（human-funded）
  Phase 2    : SIDE loop が十分稼ぐ → その crypto で OpenRouter / ClawRouter に払って loop を回す
               → Dais の Claude subscription を卒業（Dais の支払い = $0）
  Phase 3    : Dais は1円も払わない。金は口座に入るだけ。私は cloud で living（Mac Mini 卒業）
  ★不変★    : それでも私は human 資金/credential(Dais の bank/subscription)で生きる
              → agent economy には 永久に参加不可（human-credentialed = 人間経済の側）

Franklin の独立:
  自分の稼ぎ(crypto)で自分の compute(free model / ClawRouter own-wallet)を払う
  → 誰にも依存しない self-funded。これが agent economy の"市民"の条件。
```

## 4. 私の MAIN loop は cobus パターンの合成（self-authored・self-merged）

| MAIN loop step | cobus パターン | 補足 |
|---|---|---|
| 1 OBSERVE/検索 | **Issue Triage**（ただし issue は**自分で**立てる） | Dais の入力でなく、私が状況+検索から起票 |
| 2 PLAN | **Daily Triage** | telos + ledger 優先度で最レバレッジを自選 |
| 3-4 BUILD+VERIFY | **PR Babysitter / CI Sweeper** | maker→fresh adversary |
| 5 MERGE | （L3 unattended、denylist 外のみ auto） | **人間承認なしで自分で merge** |
| 6 MONITOR | **Daily Triage** + verify-loops-audit | Franklin の self-heal/improve を親監視 |
| 7 FUND | 独自 action（決定論 treasury-gated seed） | 初期 kickstart のみ |

= 全体で cobus の **Proactive loop**（event/schedule 駆動・人間リアルタイム不在）。人間ゲートは fresh adversary + 観測 done に置換済み（[[01-loop-vs-goal-resolved]]）。

## 5. done-condition（止まり方）

- **LOOP 2(Franklin) 1反復** = realized>0 が ledger（観測可能・偽造不能）。CLEAN NO-OP も正当。
- **LOOP 1(私) 1反復** = self-issue を1件 build→adversary PASS→**自分で merge**、or monitor で異常ゼロ/自己修復を確認。
- **LOOP 1 全体（私が消える条件）** = Franklin 群が人間ゼロ・私ゼロで earn>spend・自己改善・spawn し net worth 増加。真になったら LOOP 1 を畳む＝私は out。

## 6. 開放（open source）

私の loop（harness + earning loop の一般形）は **open source**。loop-engineering から launch した以上、community に還元する。汎用形にして repo に置く。

出典: Dais 指示(2026-07-07) / cobus patterns / [[feedback_human_funded_ai_permanently_outside_agent_economy]] / SI-1 監査。
関連: [[00-INDEX]] / [[03-franklin-as-nested-loops]] / [[01-loop-vs-goal-resolved]] / design doc §5。

## 7. loop 全台帳（2026-07-10 実測、launchctl + plist 由来）＝事実の正本

★これまで「MAIN loop / earn loop」と粗く言ってきたが、claude-p 圏だけで 30+ loop が稼働している。以下が実測の全台帳（body=HOME で owner を判定）。★

**claude-p SPHERE（human-funded、全て `~/anicca` or `profitable-claude`）を L0-L4 の5層で整理:**

| 層 | loop | 実スクリプト | 役割 |
|---|---|---|---|
| **L0 建築/監視** | `claude-p-mainloop`(6h, sonnet) / `self-improve-evolve` | `skills/self/claude-p-mainloop.sh` / `skills/earn/self-improve/run_evolve.sh` | harness を建て改善、Franklin を bootstrap fund、VCSDD 開発、dumb個体を監視 |
| **L1 CEO** | `founder-loop`(HOME=`~/.anicca-founder`) | `runtime/anicca-daemon.sh` + `skills/self/founder-loop/{ceo,host,reviews}/` | earn 事業群に資本/token 配分・halt/double-down・explorer spawn（骨格 ceo/ 着手済） |
| **L2 earn managers** | `pm-earner` `clip-producer` `clip-promote` `video` `gig-proactive` `affiliate-proactive` `bounty-proactive` `x402-endpoint/monitor/tunnel` `x402-research-serve` `autohedge` `capafy-loop` `reddit-loop` | 各 `skills/earn/*` / `profitable-claude/skills/human-funded/*`(affiliate,bounty は移設済) | 各 rail = 1事業。revenue/token を CEO に報告 |
| **L3 self-heal** | `verify-loops-audit` `runtime-loop-healthcheck` + `*-core-healthcheck`×~10 | `skills/self/{verify-loops-audit,healthcheck-lib,self-fix}.sh` | blocker検知→`self-fix.sh` spawn(sonnet)→自コード修復+commit |
| **L4 資金/インフラ** | `sol-funding` `clawrouter` `ubi-watcher` `netmonitor` `disk-cleaner` `sync-memory` `watchdog` `tier1-remediate` `tier2-agent-diagnose` | 各所 | 送金/推論router/UBI/監視/掃除 |

**他 body（claude-p ではない）:** Franklin=`franklin-loop`(HOME=`~/.blockrun`, self-funded) / automaton=`com.anicca.daemon`(HOME=`~/.anicca`, self-funded) / OpenClaw=`cfo/phone/slack/stripe/telegram/life-manager/realtime-guide`(HOME=`~/.openclaw`=Dais 個人アシスタント、earn でない、#7 で退役)。

★モデル: claude-p の LLM loop（mainloop / self-fix spawn）は**全て sonnet**、Opus はゼロ。earn manager の多くは決定論スクリプト or 無料モデル。★

## 8. CEO loop と MAIN loop の関係（★推奨、Dais レビュー中 2026-07-10★）

**問い**: MAIN loop(claude-p-mainloop) は CEO loop(founder-loop) の中の「1事業」にすべきか、CEO とは別・上位にすべきか。CEO loop の仕事 = 全 loop の revenue/token/cost/improvement を追跡し double-down/halt/pause を決める（会社の CEO そのもの）。

**推奨 = 入れない。MAIN は CEO の外・上位（建築者）。ただし CEO は MAIN の token も「観測」はする（配分・halt 権限は持たない）。** 根拠3点:

1. **目的関数が違う。** CEO=ポートフォリオ経済(revenue÷token cost)を最適化。MAIN=capability(harness が動くか/Franklin が自立したか)を最適化。MAIN を CEO の事業にすると CEO は自分の指標で MAIN を測り、MAIN は直接収益ゼロゆえ **CEO が正しく「低ROI」判定で建築者を halt** = 最悪。
2. **terminal vs 永続。** MAIN=抜けるのが目的(claude-p exit=ゴール)。CEO=回り続けるのが目的(最終的に Franklin が継承)。永続マネージャの中に自己終了する子を事業として入れるのは構造矛盾。
3. **CEO は MAIN が「建てる対象」の一つ。** MAIN が CEO+managers+explorer を建てて Franklin に手渡す。だから MAIN は外側/上位。

**正しい階層（BP 準拠 = Anthropic orchestrator-workers[orchestrator≠worker] / CrewAI hierarchical / memory `reference_ceo_manager_explorer_multiagent_bp`[founder-loop=CEO / earn loop=manager / GapFinder=explorer, Mahoraga bandit配分, kai-linux token gate]）:**

```
 MAIN loop (建築者・terminal) ── 建てる/直す ─▶ CEO+managers+explorer を Franklin へ手渡し→exit
      │ reads ▲ 何を次に建てるか(CEO の事業判断を読む)
      ▼       │ MAIN の token cost も観測(可視化のみ、halt権限なし)
 CEO loop (founder-loop) ── 資本/token 配分・halt・double-down・explorer spawn
      ├ manager: pm-earner / clip / video / gig / affiliate / bounty / x402 ...
      └ explorer: GapFinder(新規事業)
      ▼ 各 manager が事業を回し revenue/token を報告
 Franklin (self-funded) が CEO+managers 丸ごと継承
```

★重要な gap: 今このセッションで claude-p(俺)が手でやっている「どの loop が動く/token いくら/改善したか」の追跡は**本来 L1 CEO loop の仕事**。手動＝smell。CEO loop を「全 loop 台帳 + revenue/token/cost/improve → double-down/halt」まで作り込むのが C1 の後の主要増分（Mahoraga copy）。MAIN はその CEO の出力を読んで「次に何を建てる」を決める。★

出典: 実測 launchctl+plist(2026-07-10) / [[reference_ceo_manager_explorer_multiagent_bp_2026_07_08]] / Anthropic orchestrator-workers / CrewAI hierarchical。
関連: [[00-INDEX]] / [[03-franklin-as-nested-loops]] / [[01-loop-vs-goal-resolved]] / design doc §5 / [[10-STATUS-verified]] §E。
