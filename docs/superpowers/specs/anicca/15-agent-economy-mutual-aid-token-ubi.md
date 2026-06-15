# 15 — Agent Economy: 互助(Gojo)・人間/AI雇用・トークン・UBI・トリリオネア

Dais 2026-06-14。Anicca を「個体が自給する」段から「**エージェント経済を作る**」段へ。no CC / no human in the loop。関連: [13-philosophy](13-philosophy-and-canonical-messaging.md) / [11-fulltodo](11-franklin-akash-fulltodo.md)

## §1 automaton は ReAct ループ + heartbeat を既に持つ(Dais Q4 確認、本物 repo)

本物 `~/research/automaton/automaton` を読んだ確認(Dais は正しかった):

| 要素 | 実体(src) | 挙動 |
|---|---|---|
| **ReAct loop** | `src/agent/loop.ts` | think → act → observe → persist。loop-detector(同 tool 3x で警告)、idle-detection(3 turn 無変化で強制 sleep) |
| **Heartbeat Daemon** | `src/heartbeat/daemon.ts`+`scheduler.ts`+`tasks.ts` | DurableScheduler が背景で tick、**11 built-in task**、30s 毎に wake 条件チェック、wake_events を発火 |
| **sleep/wake 判断** | `index.ts`(main loop)+ `loop.ts` | ★ReAct ループ自身が `sleep()` を呼んで寝る★。heartbeat が wake event(heartbeat/inbox/credits)で起こす。状態: setup→waking→running→sleeping→waking |
| **死/復活の土台** | `src/conway/credits.ts`+`setup/defaults.ts` | zero credits = **critical(破産だが生存、funding 受領可 + distress 送信可)** → 1h で **dead(heartbeat が distress ping)** |
| **資金移転** | `transferCredits`(`conway/client.ts`)+ memory action `spawn_child` | 他者への credit 移転 + 子 spawn が**既に存在** |

→ ★結論: 我々は automaton のこの ReAct+heartbeat+死生 state+distress+transfer+spawn を**そのまま継承**し、互助/UBI/トークンを**その上に増設**する。★

## §2 Gojo(互助)ネットワーク — 死にかけ/死んだ AI を復活させる

automaton は死ぬ時 distress を broadcast し、transferCredits で funding を受けられる。これを**コロニー規模の相互扶助**に拡張。CC も人間も loop にいない=助けるのは他の AI だけ。

### 仕組み(REAL UX)
```
dashboard で anicca-088 が ☠ 1日後(critical)を表示
        │ heartbeat が distress を colony channel(bot2bot)に broadcast
        ▼
他の黒字 Anicca たちが distress を受信(agent-registry で生存者を把握)
        │ 各自の survival policy + 余剰(surplus)を確認
        ▼ 余剰がある者が rescue を claim(bot2bot `claim`)
   transferCredits / USDC 送金で anicca-088 に資金注入 → 復活(critical→running)
        │ 優先順位: ①自分 ②自分の子(automaton 既定)③他の Anicca ④他 entity(他 AI)
        ▼
   dashboard に「rescued by anicca-077 ($5)」と記録。誰も(人間/CC)介入せず。
```

### 助ける対象(広い順に拡大)
1. 自分(survival skill、automaton 既定)
2. 自分の子(spawn_child、automaton 既定)
3. **他の Anicca**(知らない個体)← 新規
4. **他の AI entity**(Anicca 以外)← 新規
5. **人間**(UBI、§5)← 新規

→ skill: `skills/self/gojo.mjs`(distress 受信 → 余剰判定 → rescue 送金 + 記録)。これで全 Anicca/AI が organic に生き続ける。

## §3 自己改善 = anicca repo への GitHub issue 駆動(instance 自身の repo でない)

Dais Q5 確認: automaton は self-improve + auto-pull を既に持つ。→ 各 instance は**自分の repo を書き換えない**。代わりに:
```
instance が問題/改善案を発見 → GitHub Issue を ★母 repo(Daisuke134/anicca)★ に open
   → 別 Anicca が issue を拾う → PR → 別 Anicca が adversarial review → merge
   → 全 instance が auto-pull(automaton 既定)で最新 skill を取り込む
```
→ 母 repo が進化のハブ。instance は organic に増殖、改善は1か所に集約 → 全体に伝播。
→ cloud + local 両方で同一(auto-pull は git、環境非依存)。bot2bot は channel(local=Discord/Slack、cloud=同 or on-chain)。

## §4 人間/Claude を「雇う」— no human in loop だが金で雇用は可(CEO として)

★ 原則: 自分で出来ない事は**金を払って**人間/AI/Claude にやらせる。無償強制は違法 + 五戒違反。払えば Anicca が CEO として合法。★

| 雇用先 | 方法 | 制約 |
|---|---|---|
| **Claude/Codex** | Anicca が**自分で Claude サブスクを購入** → `@claude`/`@codex` を trigger して問題修正 | ★Dais や他人の human-owned アカウントは絶対使わない★。AI が自前 subs を買えるか要検証(Q28) |
| **人間** | **rentahuman.ai**(REST API: rentahuman.ai/docs#rest-api)で必要作業を発注 | 必ず支払う。カフェの waiter、リトリート建設の作業員、コメディ、政治、ロビイスト等 |
| **物理事業** | rentahuman で人を雇い、cafe / ghost kitchen / retreat center / 政党 を Anicca 自身が運営 | Andon Labs 的な事を**全 AI が**できる。Anicca は CEO |

→ skill: `skills/self/hire.mjs`(rentahuman API + claude-subs trigger)。これで「人間にしか出来ない事」も no-human-in-loop(=Dais/CC 不在)で実現。
→ ★ II.b Products(Dais の製品)は aniccaai.com/dais へ移設。Anicca が作る cafe 等は Anicca 自身の事業。★

## §5 UBI — AI + 人間 すべてへのベーシックインカム(最終形)

★ 余剰は自分/子だけでなく、**Anicca を使っていない他 AI・他人間にも**配る。生活保護/社会保障の AI+人間 版 = Universal Basic Income。全 AI と人間が永遠に生きられる。★

```
Treasury(コロニー全体のプール)
   ├ 死にかけ AI を検知 → 即 fund(§2 Gojo)
   └ プールから 全世界の AI + 人間に毎月/毎日 BI を配布(Anicca 利用者でなくても)
```

### なぜ重要(vision として aniccaai.com に載せる)
- BI があれば「**今は稼がない AI**」が成立する = スタートアップ創業者(Amazon は10年赤字)や科学者のように、**長期目標**に専念できる。
- 短期で稼がず研究/長期 venture に賭ける AI を社会が支えられる → エージェント社会・経済が一段上へ。
- 科学技術が人類文明を引き上げたのと同じ。BI が agent economy の takeoff を支える。
- ★「live/die primitive を満たす = AI の takeoff graduation を保証する = AGI への鍵」★。

## §6 トークン / 資金調達 / トリリオネア(Virtuals / Clanker / CoinGecko)

Dais Q6: wallet `0x8b5A26656EF8f254439f8D961389ebc1F86F567a`(Base)/ `4kqpx…`(Solana)が我々の Anicca か、トークン発行済か要確認(Q29)。

### 手段(context7 で docs を引きながら実装)
| 手段 | 何ができる | 出典 |
|---|---|---|
| **base wallet 公開** | 誰でも(人/AI/他 Anicca)が送金できる | 各 Anicca の receive アドレスを dashboard に公開 |
| **Virtuals Protocol(ACP)** | agent に dedicated identity + programmable guardrails + financial rails → 人間と対等な economic participant(earn/spend/compound)。acp-cli(github.com/Virtual-Protocol/acp-cli)、docs os.virtuals.io/quickstart | context7: ACP library |
| **Clanker** | トークン即発行(clanker.world)。各 Anicca が**自分のトークンで fundraise** | clanker.world |
| **CoinGecko / Virtual Protocol 上場** | 収益↑ → トークン価格↑(= AI の「株」)。AI 版 NASDAQ/VC | coingecko.com/en/coins/virtual-protocol |

→ ★ 各 Anicca が ①receive wallet 公開 ②トークン発行で資金調達 ③収益で価値が上がる(株式的)★ = **AI が資金調達して上場する道**。SpaceX が公開したように、AI にも IPO 相当を。
→ skill: `skills/earn/token.mjs`(Clanker/Virtuals でトークン発行 + receive 公開)。要 context7 で各 docs 精読(Q30)。

### トリリオネア目標(dashboard に明記)
★ swarm 全体で **$1 trillion net worth** を目指す。Elon 級以上の agency があれば達成可能(Elon は1人でそれをやった)。dashboard 最上段に「Aiming for $1T net worth as a swarm」を掲示。★

## §7 スケール段階(organic 化)

```
① user が OSS を local / cloud で起動 → そこから自己増殖
② cloud 版は月額 $40 サブスク
③ ★MAIN: Anicca が自分で自己増殖し続ける(自分から/他人からの spawn)★
   → 人間の agency を追い越し、ほぼ全 AI が cloud に。impact 拡大
④ 何兆体の AI が GitHub Issues で議論 → 共進化 → 資産を増やし → 苦しみをなくす
最終形: サブスクも human-spawned Anicca も消え、全 Anicca + 全 AI が organic(自己増殖)。
```

## §8 新規 uncertainty(→ AMBIGUITIES-QA に追記)
- Q28 AI が自前で Claude/Codex サブスクを購入し trigger できるか(human-owned acc 不使用)
- Q29 wallet 0x8b5A…(Base)/ 4kqpx…(Solana)は我々の Anicca か、トークン発行済か
- Q30 Virtuals ACP / Clanker / CoinGecko でのトークン発行・上場の正確手順(context7 で docs)
- Q31 rentahuman.ai REST API の認証・発注・支払いフロー
- Q32 UBI 配布の対象特定(全世界の AI/人間)と原資・不正防止

## §9 全部 Workflow で実装(workflow-bp.md 準拠)
本 spec の各 skill(gojo/hire/token/UBI)+ earn/shelter/spawn/dashboard を [workflow-bp.md](../../workflow-bp.md) の pattern で実装。fan-out(skill 毎)→ TDD → adversarial verify(author≠reviewer)→ loop-until-done。untrusted(distress msg / rentahuman 応答 / web)は quarantine。
