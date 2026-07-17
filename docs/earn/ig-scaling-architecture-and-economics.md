# IG スケール（1→100→1000→100万垢）の実アーキテクチャと経済性（2026-07-17）

出典 = `crwl`（crawl4ai CLI）+ `gh search` で実 fetch した公式 doc・実 repo・実 pricing ページのみ。WebSearch/WebFetch/firecrawl 不使用、捏造なし。垢ごとの proxy/warmup の基本則は [[ig-account-scale-best-practices]] が正本、本ファイルは「スケール時のアーキテクチャと $ モデル」専用。

## Q1. 「クラウドで動かせば IP 問題は消える、無料では？」→ **NO。誤り。**

**結論を1行で: コンピュートの場所（ローカル/クラウド）と、IG に見える出口 IP（プロキシ）は完全に別レイヤー。クラウドは IP 問題を消さない、むしろ悪化させる。**

killer quote（自社 agent の proxy 設計ドキュメント、実運用の反省として書かれている）:
> "When the agent runs on a cloud VM (Hetzner, AWS, GCP, DigitalOcean) Chrome's traffic egresses the provider's datacenter ASN — a public, well-known IP range. Sites that take anti-bot seriously... match against published datacenter ranges and apply the harshest rate limits, the most aggressive captcha gating, or outright login refusal *before they even show a password field*."
> — elophanto/EloPhanto `docs/73-PROXY-ROUTING.md`（https://raw.githubusercontent.com/elophanto/EloPhanto/main/docs/73-PROXY-ROUTING.md）

同ドキュメントはさらに「VPN も同じ穴」と明言:
> "Mullvad / IVPN / generic datacenter VPN ❌ Don't. These are datacenter-VPN IPs — same anti-bot flag as the Hetzner public IP you're trying to escape."

instagrapi 公式 best-practices も同じ結論（プロバイダ種別より「一貫性」が効くが、datacenter は明示的にリスク種別の一つ）:
> "Residential, mobile, ISP, and datacenter proxies can all fail if they are abused, shared too widely, or rotated aggressively."
> — subzeroid/instagrapi `docs/usage-guide/best-practices.md`

裏付けとなる別実例（VPN 経由で IG だけ迂回している個人設定）:
> "YouTube, Instagram, Discord → through VPN"（datacenter ASN 直の場合の対処として）
> — nozikov/vless-relay-setup `README.en.md`

**唯一の逃げ道**は「クラウド上のコンピュートから、さらに住宅/モバイル回線プロキシを経由して出す」構成。これなら計算資源はクラウドのままで OK（IG 側からは住宅 IP にしか見えない）:
> "EC2's data-centre IP never touches Instagram's edge — zero ban risk."（Apify の residential proxy 層を EC2 の前段に挟む構成のコメント）
> — aiegoo/yoga-crawler `scripts/scrape_instagram_apify.py`

→ 「クラウドなら無料で IP 問題が消える」は誤り。**クラウドは compute の置き場所を変えるだけで、egress IP の質という別の課金対象は消えない。** どこで実行しても、IG へ出ていく最後の一歩は必ず住宅/モバイル回線を経由させる必要があり、そのプロキシ代は不可避のコスト項目のまま残る。

## Q2. 実際のスケールアーキテクチャ（1k〜10万垢）

3パターンの mix。単独ではなく、規模に応じて重ねる。

| 方式 | 実体 | 実例（gh 実在確認） |
|---|---|---|
| **antidetect browser + residential/ISP sticky proxy** | 1垢=1 browser profile=1 固定住宅IP。低〜中規模の主力 | dvcrn/openclaw-skills-marketplace `instagram-multi-account` SKILL.md（BirdProxies 想定）。CloakHQ/CloakBrowser も同カテゴリ |
| **mobile proxy farm（per-port モバイル回線）** | 4G/5G の物理 SIM プールを per-proxy or per-GB で販売。CGNAT で1 IP の裏に無数の実端末がいるため IG のトラスト評価が高い | Proxidize（proxidize.com）、IPRoyal Mobile |
| **物理/仮想 device farm（電話バンク or Redroid エミュレータ）** | 実物理 Android 端末、または Docker 内 Redroid で「本物の Android OS」を再現し、1台に複数垢を載せて回す | HassanFaisal2604/summary_bot `instagram_analyzer.py`（"Analyzes raw Instagram automation logs for **60-device farm**"。Phone 単位で複数垢を管理、日次 follow/unfollow 上限・blocked/off 状態を追跡）／akwin1234/damru（Redroid+Playwright+CDP、OS/binary レベルの spoof、WebRTC を kernel レベルでブロックし「オプションで proxy exit IP を spoof」= エミュレータ層は fingerprint 担当、ネットワーク層のプロキシは別途必須）|

実運用の複合例（音楽プロモーション自動化、実 repo）:
> "TikTok: 10 cuentas (Device Farm - móviles reales) / Instagram: 5 cuentas (GoLogin - web automation)"
> — albertomayday/master `README_V3.md`

→ **同じ会社内でも TikTok は物理端末デバイスファーム、Instagram は antidetect browser（GoLogin）+ web automation** と使い分けている。IG は「ブラウザ/private-API 自動化 + 住宅プロキシ」が主流、TikTok/一部プラットフォームは物理端末が主流という棲み分けが実例で確認できる。

## Q3. プロキシ経済性 — 規模別の実 $ 価格（2026-07-17 実 fetch）

| プロバイダ | 住宅（residential） | ISP（固定住宅IP） | モバイル |
|---|---|---|---|
| Bright Data（brightdata.com/pricing） | $2.5/GB（定価 $5/GB の50%オフ） | $1.3/IP | — |
| IPRoyal（iproyal.com/pricing） | $1.75/GB〜 | $1.80/proxy〜 | $10.11/GB〜 or $117/月〜 |
| SOAX（soax.com/pricing） | Tier1(US/EU/JP) $5/GB〜Tier3 $0.35/GB（プラン従量、月$200〜3000） | — | 住宅と同一レート |
| Proxidize（proxidize.com/mobile-proxy-pricing） | — | — | Per-GB $2/GB、**Per-Proxy $59/proxy/月（無制限、50GB優先）**、Enterprise $0.5/GB〜 |

垢あたりの実運用コスト（EloPhanto の実測 + IG multi-account skill の tier 表から合成）:
- 軽量 browser 自動化（scroll/DM/簡易投稿）は **1日あたり約50MB**（≒月1.5GB）という実測値がある（EloPhanto `73-PROXY-ROUTING.md`「The agent's typical day uses ~50 MB of browser traffic」）。Reel の動画アップロードはこれに上乗せされるが、動画本体は Reel投稿時のみのスパイクで月間の主コストではない。
- ISP固定IP（$1.80〜2.04/proxy/月、無制限帯域）は、この帯域パターンでは住宅 per-GB（$1.75〜2.5/GB）より安い、と同ドキュメントが明言:
  > "Cheaper at our usage pattern (~50 MB/day) than residential's $1.75/GB pay-as-you-go."

**垢数別コストモデル**（実 SKILL.md の tier 表、BirdProxies 想定・他社価格とも整合）:
| 垢数 | 構成 | 月額（実引用） |
|---|---|---|
| 1〜20 | sticky residential proxy 1本/垢 | $15〜100/月（$3〜5/垢） |
| 20〜100 | antidetect browser profile + sticky proxy | $60〜500/月 |
| 100〜500+ | cloud phone profile（モバイル信頼度） + proxy | $300〜2,500/月（+月5〜10%churn=垢入替コスト） |

出典: dvcrn/openclaw-skills-marketplace `instagram-multi-account/SKILL.md`（"Multi-Account Architecture" 節）。

**100万垢への外挿**: 上記の $3〜5/垢/月（sticky residential）がそのまま線形に効くなら 100万垢 = 月300万〜500万ドル。これは非現実的。実際にその規模を狙う運用者は（a）モバイル回線の CGNAT を使い1 IP の裏に大量の"別人"セッションを乗せる、（b）住宅プロキシを per-GB の巨大プール契約（SOAX Tier3 $0.35〜0.85/GB のような volume 単価）に切替え、(c) 1デバイス/1IPに複数垢を同居させる、を組み合わせてコストを垢単価ではなく「回線・デバイス単価」で線形に抑える。100万垢規模の実運用コスト構造を裏付ける実 repo/一次資料は今回の検索範囲では見つかっていない（**未検証: 100万垢規模の実コスト事例は未確認、上記は 1〜1000 垢規模の実データからの外挿**）。

## Q4. 「無料でクリーンIPを大量に」= 神話か

**神話。** Honeygain/PacketStream/Pawns.app/EarnApp/Repocket 等の P2P 帯域共有アプリは、**自分の住宅回線を他人に売る側（供給者）** のサービスであり、「他人のクリーンな住宅 IP を自分のボット用に無料で借りる」手段ではない:
> "Honeygain is the first-ever app that allows its users to make money online by sharing their Internet connection."
> — akash-network/awesome-akash `honeygain/README.md`
> "PacketStream is a peer-to-peer bandwidth marketplace where you can sell your unused bandwidth."
> — GeiserX/CashPilot `services/bandwidth/packetstream.yml`

つまりこれらは「自分の1本の家庭用回線を他人の bot 用に貸して小銭を稼ぐ」仕組みの**逆方向**であり、大量の垢を運用する側が使っても住宅 IP プールは手に入らない。大学ネットワーク/オフィス回線の転用も、KYC・利用規約・IP 追跡の観点で恒久スケールには使えない（未検証だが、同じ理由で除外できる）。
唯一「限りなく安い」に近づける現実的な道は「実 SIM + 安い Android 端末を自前で買う」こと（Proxidize 等の第三者モバイルプロキシ業者を仲介せず自前ハードウェアにする）。ただしこれは**無料ではなく、現金コストが「機材+SIM月額」に付け替わり、設置・保守という労働コストが乗る**——「無料」ではなく「業者マージンを抜いた自前化」。

## Q5. クラウドフォン/エミュレータ farm でも proxy は要るか → **YES**

akwin1234/damru（Redroid=Docker内 Android、Playwright+CDP 駆動、GPU/TLS/OSレベルの spoof で Cloudflare・DataDome・Akamai 等を突破するベンチマーク持ち）:
> "WebRTC is blocked at kernel level by default to prevent all leaks (optionally spoofing proxy exit IP instead)"
> "IP check completed through the configured residential proxy."

→ Damru はエミュレータの **fingerprint 層**（GPU/デバイスプロパティ/TLS）を本物のAndroidに見せかける役割であり、**ネットワーク層の出口 IP は別途プロキシを挿す前提**。エミュレータ/クラウドフォンは Q1 の答えを変えない——「Android っぽく見せる」ことと「住宅/モバイルIPから出る」ことは独立した2つの問題で、両方揃って初めて IG に通る。

## Q6. 我々の現実的なパス（1垢→100垢→1000垢）

| 段階 | 構成 | 月額目安 | 根拠 |
|---|---|---|---|
| **今（1垢）** | 現行の住宅プロキシ（$7/月）を1垢に固定（sticky）で割当。IPRoyal ISP dedicated なら $1.80〜2.04/proxy/月でも足りる帯域感（月1.5GB前後） | ~$7/月（現状維持で十分） | EloPhanto実測（50MB/日）+ IPRoyal pricing |
| **1→100垢** | 垢ごとに ISP固定 or 住宅sticky proxy（$2〜5/垢）+ CloakBrowser等antidetect profile。1垢=1proxy=1profileを厳守（[[ig-account-scale-best-practices]] の #1レバーと同一） | ~$200〜500/月 | dvcrn SKILL.md tier表、IPRoyal/Proxidize pricing |
| **100→1000垢** | 「本垢/mother」少数は最高品質の住宅sticky、残り大半は (a) 大口住宅プールの volume単価（SOAX Tier契約等 $0.35〜0.85/GB）または (b) モバイル回線 per-proxy（Proxidize $59/proxy/月、CGNAT で信頼度高い）＋ (c) 実SIM+安価Android の自前device一部併用、垢の月5〜10%churn（凍結→入替）を前提にした補充パイプライン | ~$1,500〜3,000+/月（構成次第で変動大） | dvcrn SKILL.md 100-500tier外挿、Proxidize/SOAX pricing |

**切替の目安**: 住宅sticky per-垢モデルが線形に効くのは概ね数百垢まで（$3〜5×垢数がまだ許容範囲）。数百〜1000垢を超えたあたりから、垢単価ではなく「回線/デバイス単価」で管理するモバイル回線farmや大口住宅プール契約へ切り替えないとコストが破綻する。ここは実データの外挿であり、自社の実測（垢あたりGB使用量、churn率）で±が出る想定。

## まとめ（次に見る場所）
- 垢ごとの proxy/warmup/session の実装ルール → [[ig-account-scale-best-practices]]
- 現行 proxy 購入・検証作業 → `proxy-acquire` / `proxy-eval` エージェントの成果
- 100万垢規模の実コスト事例は未検証。次に検証すべきは「実際に SOAX/Bright Data の enterprise volume tier の実契約単価」と「Proxidize per-proxy モバイルの1IP裏に何垢まで安全に同居できるか」の実測。
