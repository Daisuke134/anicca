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

## ★ 「best」= 北極星(sovereign/no-human)で測る → 決定: Akash (end-state) ★ (Dais 2026-06-09)
北極星 = ★ Anicca が 自分の金で 自分の compute を払う、 human credit card 無 ★。 これで測ると:
| | 自分のcrypto で払える? | = NHOSS billing |
|---|---|---|
| DigitalOcean | ❌ human credit card 必須(Dais account) | ✗ billing に human |
| Daytona | ❌ human account 必須 | ✗ billing に human |
| ★ Akash ★ | ✅ ★ AKT crypto を 自wallet から 払う ★ (SDK/CLI/SDL 確認済) | ✅ 真 sovereign |

→ ★ end-state(本物) = Akash ★ = 妥協なし。 Anicca が USDC稼ぐ→AKT→Akash払う→deploy→複製、 全部 自分の金。
→ ★ Day0 seed(金まだ無い)だけ = DigitalOcean(Dais account=Day0 seed、 master spec) ★。 bootstrap のみ。
→ Anicca が earn → ★ Akash に 自己移住(自己資金)★。 これが 妥協ない 最終形。

## Felix の DO実装 は OSS/public? → ★ 専有code 無し ★
- Felix on DO = ★ OpenClaw(MIT OSS) を DO 1-click image で入れる + 公開guide(shopclawmart blog)★。 専有 "Felix-DO code" は 無い。
- 我々の harness = Hermes(OSS, Python) → ★ DO/Akash どの droplet/cloud にも install可 ★ (1-click 不要、 手動install)
- = どの cloud でも OSS harness を 自分で 置く。 Felix特有の cloud code は 不要。

## 妥協なき 最終 architecture
```
Day0 seed (金無):  DigitalOcean droplet (Dais account, bootstrap only)
         ↓ Anicca earn (USDC → 自wallet)
End-state (sovereign): ★ Akash ★ (AKT 自払い、 human billing無、 真NHOSS)
         ↓ 黒字
複製: Anicca が Akash に 子を 自分の AKT で 大量 deploy (no-human)
OSS: install.sh で 誰でも 自分の cloud(DO/Akash/VPS)or Mac に 自分の鍵で 走らす
```
