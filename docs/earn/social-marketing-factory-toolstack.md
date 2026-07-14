# Social Marketing Factory — ツールスタック決定（2026-07-14）

clip/video/slideshow を横断する「1 engine + 差替ノード」の社会マーケ工場が、**どのツールを何に使い、no-human でどう回り、どう 10k MRR→scale するか**の正本。gh 一次情報 + 一次ページ crawl で裏取り済み。

## 大原則
- 断片を組む（丸ごと repo は存在しない、affiliate 自動化 OSS も存在しない = toy のみ）。primitives を copy+tweak。
- no-human + フォーム記入/審査待ち禁止 が制約。これがツール選定を決める。
- 最適化目的関数 = **$/post**（views は proxy）。金の帰属が無いと 10k に届かない。

---

## A. affiliate で稼ぐ（収益エンジン）

### モデル（no-human loop 最適順）
1. **recurring SaaS**（PartnerStack 系）: 月20-40%継続。1回貼れば継続課金。marketplace 即signup・面接なし。実績 $470M commission 支払 / 14.5万 partner（partnerstack.com 自社統計）。
2. **cold-start = Digistore24 / ClickBank** 情報商材: RevShare 50-100%、即signup・面接ゼロ。ClickBank 実例 $100売上→affiliate $55.58（clickbank.com/how-clickbank-works）。Digistore24 $1B+ 支払。
3. **最終形 = 自社商品**（Gumroad/Lemon Squeezy/Stripe）: 100%マージン・即・面接なし。Anicca app + ebook。
4. ✗ Amazon: 1-10%一回・cookie 24h・180日で3売上ないと閉鎖。filler のみ。
5. ✗ LTK / Impact: 人間審査＝AI 不可。cold-start faceless 弾かれる。

### link tracking = 金の帰属（keystone）
- **self-host Dub.co**（`dubinc/dub` 24k★ MIT）: Partners API = analytics+commission+payout。affiliate 形。per-post link → click/conversion を API で loop に読ませ、$/post 最適化。
- fallback: YOURLS 12k★ / Shlink 5k★（click は取れるが commission 追跡なし）。

### negative finding
`affiliate automation`/`amazon affiliate bot` 系 GitHub repo は全部 toy（0-7★）。まともな OSS 無し。探すな、組め。

---

## B. posting infra（配信）

### self-host は「無料・無制限」だが罠がある
- **Postiz**（AGPL、33k★）/ **Mixpost**（Pro $299買切、IG/TikTok は Lite 無料版で非対応）: self-host は無料でアカウント無制限。**BUT 自分で Meta/TikTok/Google の開発者 App を作り、App Review/監査を通す必要**。TikTok は監査完了まで「24h で5ユーザー・投稿は SELF_ONLY(非公開)強制」= scale 即死。IG は Business Verification + `instagram_content_publish` の App Review。承認前はテスターを手動追加＝実質アカ毎手作業。
  - 出典: docs.postiz.com/providers/{instagram,tiktok}.md
- App Review は **App 単位で一度きり**（承認後は全ユーザーに適用）。だが承認待ちが数日〜数週間＝「今すぐ無人」に合わない。TikTok 監査が killer。

### managed SaaS は App Review を丸ごとスキップ（提供元が承認済み App 保有）
| tool | 無料枠 | scale コスト | App Review |
|---|---|---|---|
| **Zernio**（旧 Late/getlate.dev）| 最初2アカ無料 | 101アカ以降 **$1/アカ/月** | 不要（OAuth 一発）★scale コスパ最強 |
| Ayrshare | トライアルのみ | Launch $299/mo=130アカ、agency 向け | 不要 |
| upload-post.com | 月10投稿・2profile 無料 | — | 不要 |
| Blotato | $29/mo〜 | 20-40アカ | 不要 |

### browser 自動化（既存 CloakBrowser CDP）
- App Review/監査ゼロで**今すぐ無人稼働**。IG poster 実装済み。
- 弱点: 1インスタンス=1CDPセッション → 数百同時は非効率。
- scale ルート: **antidetect browser（GeeLark $0.25/profile/月, AdsPower/Dolphin）+ 住宅/モバイル proxy（$3-15/アカ/月、datacenter は即弾かれ）** で browser 経路自体を並列化。

### 大規模運用者の実スタック（reddit/ベンダー一次情報。BHW は Cloudflare で不可）
- antidetect browser/cloud phone（$0.25-1/アカ）+ 住宅 proxy 1本/アカ + warmup。
- warmup ルール: fresh は即投稿禁止、1日1投稿→週で 2→3 に、削除でなく非表示（削除はシグナル悪）。
- **うちは `ig-account-warmer` skill で実装済み**（age-based caps / randomized delay / ban-signal stop）。
- 数百アカ専用の投稿 bot OSS はほぼ無い（ToS 違反性質上 公開されない）。

---

## C. 決定 — どのツールを何に

| phase | 配信 | affiliate | link | 理由 |
|---|---|---|---|---|
| **Phase 1（今、数〜十数アカ）** | 既存 CloakBrowser CDP poster を主軸（setup ゼロ・即動く。stall bug 修正が前提）| 自社商品(Anicca) + Digistore24/ClickBank 即signup | self-host Dub.co | App Review 待ちゼロで無人稼働 |
| **Phase 2（数十〜数百アカ）** | **Zernio** を公式API主軸（101アカ$1/月、App Review 不要）+ TikTok は監査済むまで browser 併用。または browser を GeeLark+proxy で並列化 | recurring SaaS(PartnerStack) を追加 | Dub.co | managed が審査税を回避、$/アカ 最小 |

browser の位置づけ = 「ボトルネック」でなく「審査待ちゼロの即動く保険レーン」。量産本丸は ①browser×antidetect 並列 か ②managed API(Zernio)。どちらも人間フォーム記入なし。

---

## D. no-human で品質が上がる機構（Reflexion）
1 pass = PRODUCE(playbook のレシピ) → POST → MEASURE(engagement + IG 保存の実解像度/bitrate) → REFLECT(reflection.jsonl に「200×200 で floor 割れ→次は 1080×1920」等) → 次 pass の PRODUCE が読む。engagement も同様（バズらない hook→scout 勝ちパターンへ）。scout/affiliate-finder は agentic（model がスクショ見て判断、hardcode 無し）。

## E. 10k MRR → scale
$/post が黒字の {niche×format×hook×offer} combo を1アカで実証 → Layer0 identity farm(既存)が同 combo を N アカに clone。10k = 20アカ×$500 / 100アカ×$100 / 数本バズ。loop の仕事は「バズる」でなく「黒字 combo を1個見つける」。

## MON-5 決定（2026-07-14）
- **affiliate = Digistore24**（account 作成済 2026-07-14 21:24、★email 確認 pending★）。offer = 高commission digital（50-75%）or 直接 SaaS（Notion 50% / Copy.ai 45% / Writesonic 30-40%、recurring）。
- **1 link を 200アカで共有**（account 1個でいい）。属性分解 = Digistore の **sid1〜sid5 + cid**（acc毎に sid 付与）。ClickBank=TID、PartnerStack=sub-id も同様。
- **入金先 = Dais の銀行口座（fiat）**（Dais 決定 2026-07-14）。Digistore24 は 銀行送金/PayPal（crypto 不可）。crypto wallet が要る時だけ Binance/Coinbase affiliate。
- GitHub の awesome-affiliate list は commission% 無しで質低い → 使わない。agent は Digistore marketplace(確認後)or 直接 SaaS shortlist から pick。

## 出典
partnerstack.com / clickbank.com/how-clickbank-works / digistore24.com/en/affiliate / dub.co/docs / github: dubinc/dub, YOURLS, gitroomhq/postiz-app, inovector/mixpost / docs.postiz.com/providers/{instagram,tiktok,youtube}.md / mixpost.app/pricing / zernio.com(getlate.dev) / ayrshare.com/pricing / geelark.com/pricing / aimultiple.com/antidetect-browsers / r/TikTokMarketing
