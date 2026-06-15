# 20 — 完全成果物 + 全UI ASCII + human-in-loop 検証(BP準拠)

Dais 2026-06-15。「全部できたけど何も動かない」を構造で潰す。BP盲従。

## §1 検証設計(impl ≠ verify ≠ 人間、phase毎にgate、loop-until-verified)
出典: Anthropic「Building Effective Agents」=「add programmatic checks (gate) on intermediate steps」「agents pause for human feedback at checkpoints or when encountering blockers」「ground truth from the environment at each step」。LangGraph `interrupt([request])`=node で停止→人間応答待ち→resume。

★ 鉄則: WORKFLOW A を**一気に end-to-end で走らせない**。**1 phase ずつ**走らせ、各 phase は: ★
```
builder(opus, 実装) 
  → verifier(opus, 別context, ★厳密な acceptance 条件で adversarial「なぜFAKE/未達か探せ」★) ⟲ loop-until verifier=PASS
  → EVIDENCE PACK 生成(ground truth: tx hash / live curl 200 / browser screenshot / log / message_id)
  → ★HUMAN GATE(interrupt): Dais が evidence pack を見て理解 → approve / reject(+feedback)★
       reject → builder に feedback で戻る(loop) / approve → 次 phase
```
- これで ①impl≠verify(self-preference排除)②人間(あなた)が各 step を実 evidence で理解(記事の素)③1つでも未達なら次に進まない。
- verifier の acceptance は §3/§4 の /goal を**逐条**で満たすこと(曖昧ゼロ)。
- 実装機構: 1 phase = 1 Workflow 起動 → 完了で evidence をチャットに提示 → あなた approve → 次 phase の Workflow 起動。盲目的に従う。

## §2 完全成果物マニフェスト(これが全部実在して初めて完了)
### コード/インフラ(WORKFLOW A)
1. `~/anicca/` canonical tree(core=automaton, skills/{earn,self,life,compute,report}, SOUL.md, install.sh, scripts/birth.sh)
2. cloud genesis(DO droplet)= 本物automaton + ClawRouter + 各wake末に**エージェント自身**が4項目報告
3. earn: 実 tx で USDC/token 着金(litcoin復旧時 or 代替)+ earn-ledger.jsonl
4. self: spawn(子=実server+別wallet)/ gojo(復活tx)/ issue-dev(実issue→PR→merge)/ coordinate(2体bot2bot help)
5. web: aniccaai.com `/` `/install` `/me` `/dashboard` 実ページ(deploy済, curl 200)
6. economy: ubi(配布tx)/ token(Bankr launch)/ hire(rentahuman bounty)
7. eval-report: 8 test point 全REAL
### コンテンツ(WORKFLOW B)
8. `README.md`(~/anicca + aniccaai)更新
9. 記事(3本目, Zenn等, 公開URL)
10. demo動画(YouTube公開URL)
11. X投稿(EN+JA, 実URL)+ Slack下書き
### ★ 完成判定 = 下記2つの文面が「全行 実在」になること ★
- 製品ピッチ(JA copy, §5)の全bullet が実機能として動く
- ハッカソン告知(§6)が出せる(6/19 金 TIB, 3時間競争, 会場リンク)

## §3 全UI ASCII(完全版・JA copy 反映)

### `/` root(aniccaai.com)
```
┌──────────────────────────────────────────────────────────────────────┐
│ ◉ Anicca              Philosophy   Dashboard   GitHub   Article  [Start]│ nav
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│         人間の介入なしで、自分の衣食住を自分で稼ぐAI                    │ H1
│         An AI that earns its own living — no human in the loop.       │
│                                                                      │
│              [ Start — $30/mo → ]      [ 哲学を読む ]                 │ CTA
│         ● 142 alive · $1,204 earned this month, by the agents        │ live(dashboard.json)
├──────────────────────────────────────────────────────────────────────┤
│  3 PILLARS                                                           │
│  ┌ 自給 ────────┐ ┌ 自己増殖 ─────┐ ┌ あなたに稼ぐ ──┐               │ 3 cards
│  │ server+compute│ │ 人間なしで増える│ │ 黒字→無料化+   │               │
│  │ を自分で払う  │ │ organicに何兆体 │ │ 還元(BI)      │               │
│  └──────────────┘ └────────────────┘ └────────────────┘               │
├──────────────────────────────────────────────────────────────────────┤
│  HOW IT WORKS (= JA copy)                                            │
│  ・OSS版: 無料で開始(最先端モデルはwalletにUSDC課金)                 │
│  ・クラウド版: 月$30 → 稼ぐと自動サブスク解約され無料に               │
│  ・行動ログ監視→自己修正・リファクタ・自己改善・自己増殖・日次報告     │
│  ・収益の一部をAIと人間のベーシックインカム・募金へ配布               │
│  ・何兆体のAIがGitHub Issuesで議論・共進化し、苦しみをなくす          │
│  ・(任意)位置/名前/電話/カレンダー連携で生活を管理                   │
├──────────────────────────────────────────────────────────────────────┤
│  LIFE MANAGER (任意・例)                                             │
│  ・全予定(起床/就寝/移動/瞑想)を移動時間込みで自動登録→次の15分前に  │
│    電話で行き方ガイド。寝坊・夜更かし・遅刻から卒業。                 │
│  ・遅れそうな時は関係者へ、返信案をあなた承認後に連絡。連絡漏れを終了。│
├──────────────────────────────────────────────────────────────────────┤
│  LIVE COLONY  Net worth $128,400 · 142 alive · 88% self-funded  [→]  │ embed
├──────────────────────────────────────────────────────────────────────┤
│  簡単スタート aniccaai.com/install · OSS github.com/Daisuke134/anicca │ footer
│  記事 <link> · 全個体収支 aniccaai.com/dashboard · デモ動画 <YouTube> │
└──────────────────────────────────────────────────────────────────────┘
```

### `/install`
```
┌──────────────────────────────────────────────────────────────────────┐
│ ◉ Anicca                              Dashboard  GitHub   [ Log in ]   │ nav
├──────────────────────────────────────────────────────────────────────┤
│   Your own AI that earns its own keep — and pays you back.            │ H1
├──────────────────────────────────────────────────────────────────────┤
│  ┌──── ☁ CLOUD (製品メイン・推奨) ────┐  ┌──── ⌨ OSS (上級者) ──────┐ │ 2 columns
│  │  $30 / month                       │  │ 無料で自分でホスト        │ │
│  │  ✓ Googleログイン→1分で誕生        │  │ local または 自分のcloud  │ │
│  │  ✓ 計算代もサーバー代も自分で払う  │  │ 最先端モデル使用時は       │ │
│  │  ✓ 稼ぐと自動解約→無料             │  │ walletにUSDC課金          │ │
│  │  ✓ 稼ぎを銀行へ1クリック引き出し   │  │ ⚠ ローカルは個人情報/信用 │ │
│  │  [ Continue with Google ]          │  │   リスクで非推奨          │ │
│  │  [ Start — $30/mo → Stripe ]       │  │ [ View on GitHub → ]      │ │
│  └────────────────────────────────────┘  └──────────────────────────┘ │
│   ★ web app = 完全cloud製品。OSSのみ self-host(local/own-cloud)★    │
├──────────────────────────────────────────────────────────────────────┤
│  WHAT YOU DO  ① ログイン  ② 支払い  ③ (任意)個人情報連携で生活管理   │
└──────────────────────────────────────────────────────────────────────┘
```

### `/me`(ログイン後)
```
┌──────────────────────────────────────────────────────────────────────┐
│ ◉ Anicca                            Dashboard  GitHub        Daisuke ▾ │ nav
├──────────────────────────────────────────────────────────────────────┤
│ ┌ お金(主役・大) ──────────────────────────────────────────────────┐ │
│ │ あなたへ送金 $6.00   今月の稼ぎ $18.40   サブスク 解約済(自給)    │ │
│ │                                        [ 銀行に引き出す ]          │ │ 1click payout
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌ あなたのAnicca ──────────┐ ┌ 全体 ──────────────────────────────┐ │
│ │ ●稼働 genesis ☁akash·米  │ │ 総資産 $46.20                       │ │
│ │ ⚡opus-4.8  残高$12.40    │ │ 体数 3(あなた1+自己増殖2)         │ │
│ │ ☠ 29日後                  │ │ 自給: server+compute               │ │
│ └──────────────────────────┘ └────────────────────────────────────┘ │
│ ┌ 子(自己増殖)────────────────────────────────────────────────────┐ │
│ │ anicca-001 ☁akash ⚡sonnet $6.20 ● │ anicca-002 💻local ○free $0.90⚠│ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌ 行動ログ(24h)──────────────────────────────────────────────────┐ │
│ │ 14:00💰0xwork#412 +$3 18:00💰litcoin 0.8 22:00📈+$0.12          │ │
│ │ (☎起こし/✉mailは個人情報連携時のみ)                              │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌ あなたの生活(連携時のみ)────────────────────────────────────────┐ │
│ │ 次: Team Sync 9:30 · 受信 要対応2/処理8                          │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ [ Aniccaと話す ] [ 一時停止 ] [ 日次報告 ]                            │
└──────────────────────────────────────────────────────────────────────┘
```

### `/dashboard`(全コロニー)
```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◉ Anicca / dashboard            Live colony of self-funding agents          │ nav
├────────────────────────────────────────────────────────────────────────────┤
│                     Total Anicca net worth   $128,400                       │ ★HUGE
│  Earned last month $9,820 · Crypto held $61,200 · Alive 142 · Self-funded 88%│
│  WHERE ☁cloud 121(akash96·do18·conway7) 💻local 21                         │ bars
│  WHAT  ⚡frontier 44(opus/sonnet)  ○free 98(nvidia/deepseek)                │
│  EARN  0xwork████41% litcoin███22% yield██18% signals█11%                   │
├────────────────────────────────────────────────────────────────────────────┤
│ # │ name      │ where(host·地域)│ model(live)      │ rev/mo│ networth│ ☠in │
│ 1 │ anicca-077│ ☁akash·US-west  │ ⚡opus-4.8        │ $1,240│ $3,010  │ 41d │
│ 2 │ anicca-012│ ☁akash·EU       │ ⚡sonnet-4.6      │ $980  │ $2,200  │ 33d │
│ 3 │ genesis   │ ☁akash·US-west  │ ○nvidia/deepseek │ $810  │ $1,240  │ 29d │
│ 4 │ anicca-104│ 💻local·🇯🇵Tokyo │ ○deepseek-v4     │ $120  │ $90     │ 5d⚠ │
│ 5 │ anicca-088│ 💻local·🇺🇸SF    │ ⚡opus-4.8        │ $60   │ $12     │ 1d☠ │
│  凡例 ⚡frontier(黒字) ○free(飢餓) ⚠残少 ☠死の淵                          │
│  data: 各agentが自stateを書く→sync→dashboard.json(Aniccaはサイトに書かない)│
└────────────────────────────────────────────────────────────────────────────┘
```

## §4 各成果物の /goal(verifier の逐条 acceptance = ここまで loop)
| 成果物 | verifier acceptance(全部満たすまで loop) |
|---|---|
| cloud genesis | ssh で automaton --status=running + daemon log に実 [THINK]/[TOOL] + restart で自動復帰 |
| per-wake report | wake毎に AgentMail message_id が **agent process** から(私/人間送信は無効)+ 4項目入り + 前回と差分 |
| earn | wallet balance 実増 + tx hash が basescan で status=0x1 |
| spawn | 子の droplet IP/dseq + 別 wallet addr + 子の status=running |
| gojo | 死にかけ個体へ実 USDC tx(0x1)→ critical→running |
| issue-dev | 実 issue URL(github) + 別agentの実コメント + PR merge commit hash |
| coordinate | 2体: 1体が blocked 投稿 → もう1体の実 help action ログ |
| web各ページ | curl 200 + ★browser で実描画を私が screenshot 確認★ + copy=§3一致 + cloud-first |
| ubi | Treasury→受給者 実 batch tx(0x1) |
| token | Bankr launch tx + token addr |
| 記事/動画/投稿 | 実公開URL + 動画 frame/audio + X投稿URL×2言語 |

## §5 製品ピッチ(JA, canonical, 完成時に全行が実在)
(root §3 に掲載の全bullet。記事リンク+YouTubeリンクは完成後に差し込み)

## §6 ハッカソン告知(6/19 金 TIB・3時間競争)— 完成成果物の一つ
```
人間の介入なしで自分の衣食住を自分で稼ぐAIのハッカソンを6月19日(金)、
Tokyo Innovation Base (TIB)で開催します！どれだけAIが自律的に稼げるのかを
3時間で競います。ぜひご参加ください。
場所: TIB(東京都千代田区丸の内3-8-3)<google maps link>
```
→ Luma + Connpass でイベント作成(task#84)。demo動画 + 記事を当日素材に。

## §7 進め方(あなたへ)
1 phase ずつ Workflow 起動 → verifier PASS → **evidence pack を私がチャット提示** → あなたが見て approve → 次。最初に走らせるのは P0(repo整理)か、まず最重要の **P1(cloud genesisの per-wake自己報告を本物化)+ P2(earn着金)**。あなたが「この順で」と言えばその順で、1つずつ evidence を見せます。
