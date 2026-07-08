# 12 AI-driven development の梯子（ladder）と proactive loop ── 記事/本の背骨

> ★Dais の到達点(2026-07-08)★: loop の型は並列の4分類でなく、**登る梯子**。各段が人間を1つ剥がす。上の段ほど賢い agent が要る。★proactive loop = loop + goal★（ただの loop=cron、proactive は goal を内包する＝そこが違う）。正本の型分類 → [[01-loop-vs-goal-resolved]]、主体別3ループ → [[04-the-two-loops]]。

## 1. 梯子（各段が人間を1つ剥がす）

| L | 段 | 何が起きるか | 人間の残る仕事 |
|---|---|---|---|
| L1 | vibe-coding | 毎ターン「こう直せ」と指示 | 観測 + ゴール生成 + 検証、全部 |
| L2 | xDD（spec/test/verification/eval-driven, superpowers/vcsdd） | framework が1反復の品質を保証 | 毎ステップ babysit + done 判定 |
| L3 | `/goal` | 独立 checker が done を verifiable に判定 → agent が止まらず end-to-end 完遂 | ★ゴールを1回 prompt する★ |
| L4 | loop（time-based, cron/launchd） | その `/goal` を cron 化。agent が毎日 自分でゴールを立て実行 | ★prompt から out★。だが台本は固定(＝ただの cron) |
| **L5** | **proactive + self-improving** | loop が「環境を観測しゴールを自己生成(=loop+goal)」＋ **loop 自身が loop を改善** | 長期ゴール設定 + 日々のゴールが長期に aligned かの保証のみ |
| **L6** | **self-goal-setting（最終）** | agent が **end-goal 自体も自己決定**（Elon が「多惑星種」を選ぶように）。日々も end-goal も self-generated + self-improving | ★なし（人間の仕事すら消える）★ |

★人間の仕事が段ごとに縮む★: 毎ゴールを prompt(L1-3) → loop を設計(L4) → **自己改善する loop を設計 + 長期ゴール & alignment(L5)** → **何も設定しない(L6)**。

## 2. 第2軸 ── これが揃って初めて "no human"

```
       開発ループから人が out（L1→L6、agent が自分でゴールを立てる）
             ×
       human credential / subscription 依存ゼロ（own crypto wallet で compute[食+住=cloud]を実払い）
       ────────────────────────────────────────────────────────
             = 真の no-human
```
どの段でも agent が人間の credential/subscription で動く限り依存は残る。Franklin / claude(→cloak reader)が **自分の wallet で自分の compute を実際に払う**と credential 依存も消える。

## 3. proactive loop vs cron（Dais の核心）

```
ただの loop / cron : 時計で起きて【固定台本】を実行（time-based, L4）
proactive loop     : 起きて【世界を観測し "今何が重要か" を自己生成(goal)】して動く = loop + goal
                     ＝ CEO（Elon）が毎日 世界を見て自分の優先順位を作るのと同じ
```
→ 詳細な time-based vs proactive → [[11-parent-funding-loop]]（親 funding loop は proactive の型: OBSERVE→DECIDE(agent判断)→FUND→LOG）。

## 4. 今どこ / 決定事項

- **今 = L4**（time-based loops 稼働: 2026-07-08 Franklin loop 蘇生([[10-STATUS-verified]] #10)、claude-p main loop 配線済）→ **L5 へ移行中**。self-improve harness(openevolve)が「loop が loop を改善」の種で、既に1周 adversary-gated promote 実証済(A3)。
- ★決定(Dais 2026-07-08)★: **Franklin も claude-p も proactive loop にする**（両方 loop+goal 化）。#7 恒久 funding loop がその第一歩。
- ★決定(Dais 2026-07-08)★: **refactor（claw loops を `~/anicca`→`~/profitable-claude` へ、anicca=経済の環境 / profitable-claude=human-funded 外側）は最後（very end）に行う**。→ [[05-coordination-with-agent-economy]] の境界と整合。

## 5. prior art（外部検索、L5/L6 を既にやっている人々）

> ★検索中（2026-07-08）★: Gödel Machine(Schmidhuber) / Darwin Gödel Machine(Sakana) / ADAS(Meta Agent Search) / STOP / open-endedness(Clune AI-GAs, POET, OMNI, DeepMind "Open-Endedness is Essential for ASI") / autonomous goal-generation / AI-as-CEO / 経済的自立(x402, agent economy)。引用付きで本節に追記予定。車輪の再発明をせず copy+tweak する。

出典: Dais 対話(2026-07-08) / [[01-loop-vs-goal-resolved]] / [[11-parent-funding-loop]] / [[06-harness-engineering-weng]]。
