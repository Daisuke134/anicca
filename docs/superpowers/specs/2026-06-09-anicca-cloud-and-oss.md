# Anicca — cloud (DO/Daytona/Akash) + OSS model (firecrawl 実証)

## 3者 比較 (= firecrawl docs verbatim、 推測でなく)
| | DigitalOcean droplet | Daytona | Akash |
|---|---|---|---|
| 何か | Linux VM (persistent server) | ★ agent-native sandbox、 "unlimited persistence" ★ | decentralized、 crypto-pay |
| 出典 verbatim | "Linux-based VMs... a new server, standalone or larger infra" | "open-source... full composable computers (sandboxes)... unlimited persistence... ideal foundation for AI agent architectures... spin up <90ms" | "AKT Token... Deploy via console/CLI" |
| 自律(agent自身が provision) | ✅ API (create droplet) | ✅★ SDK(TS/Py/Ruby/Go/Java)+API+CLI+agent skills(github.com/daytona/skills)+llms.txt ★ | ✅ CLI、 但し AKT 要 |
| persistent 24/7 | ✅ 完全 | ✅ "unlimited persistence" + snapshot | ✅ lease 期間 |
| billing | Dais card (account active, droplet 10台可) | API key (Dais account) | ★ crypto(AKT)= 真sovereign、 human billing無 ★ |
| 90ms起動 | ❌(分) | ✅ | ❌ |
| Felix が使ってる | ✅ DO droplet | — | — |

### ★ 決定 (私が search で 決定) ★
- genesis (24/7 earner) = ★ DigitalOcean droplet ★ (Felix流、 persistent server、 Dais account active)
- ★ 自己複製(子を agent が自分でspawn) = Daytona ★ (= agent-native SDK、 90ms、 "ideal for AI agent"、 Dais token有)
  → 私の前の「Daytona=ephemeral/不向き」は ★ 誤り、 撤回 ★ (docs: "unlimited persistence")
- 真sovereign複製(billing も human無) = ★ Akash(自wallet AKT)★ → 後phase
→ DO=genesis本拠 / Daytona=子の大量spawn(agent-native) / Akash=最終sovereign

## OSS 疑問 (Dais)
### Q1 OSS = cloud不可? local限定? → ★ NO ★
OSS = ★ code が public(誰でも clone) ★。 走らせる場所は ★ user の自由 ★ (= 自分のMac OR 自分のcloud)。
OSS ≠ local限定。 code 公開、 deploy は user 次第。

### Q2 cloud に出すなら Docker? local? → ★ install.sh で どっちも、 Docker不要 ★
- ★ OSS local run ★: `git clone` → `./install.sh` → ★ 自分のAPI鍵入れる ★ → 自分のMacで走る (最簡、 Docker無)
- ★ OSS cloud run ★: 同じ install.sh を 自分のVPS/DO droplet で 走らす (Docker任意、 必須でない)
- ★ Managed (aniccaai.com) ★: 我々が host、 user は サブスク払うだけ(設定ゼロ)
→ OSS = install.sh が ★ どこでも(local/cloud) 自分の鍵で 走る ★。 Docker は optional。

## 「run both」 (Dais)
- ★ local Hermes Anicca = KEEP ★ (= OSS/Dais reference、 私が前「消す」と言ったの撤回)
- + ★ cloud DO Anicca = 追加 ★ (= managed/aniccaai.com)
- 同じ mother code、 2 deploy 同時稼働 = OSS path(local) と SaaS path(cloud) 両方 実証
- 順序: ① ★ 先に local Hermes が 実際に earn するか verify ★ → ② cloud DO で aniccaai.com
- ★ Phase 4 (web/SaaS) から = design-spec engineer CC が 引き継ぐ ★ (Dais 指定)
