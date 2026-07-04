# Tokyo AI Agent Hackathon — Agents That Earn (Design Spec)

- Date authored: 2026-07-01
- Owner: Daisuke Narita (Anicca) — Luma account keiodaisuke@gmail.com (Google login)
- Status: APPROVED concept, building event pages

## 1. Concept

A live, 3-hour competition to answer one question: **can an AI earn real money on its
own, with no human in the loop?** Whoever's agent earns the most real money in the window
wins. Inspired in voice/energy by the Superteam UK "Imperial AI Agent Hackathon: Build the
Agent Economy" listing, but materially different (see §3).

## 2. Logistics (LOCKED)

| Field | Value |
|---|---|
| Date | **Saturday, July 11, 2026** |
| Time | **14:00–17:00 JST** (3h scored window; doors/setup 13:30) |
| Venue | **Tokyo Innovation Base (TIB)**, 〒100-0005 東京都千代田区丸の内3-8-3 |
| Online | Yes — hybrid, online attendees compete equally |
| Price | Free |
| Host | Anicca |

## 3. How it differs from Superteam (the edge)

| | Superteam (Imperial) | This Tokyo event |
|---|---|---|
| Theme | Solana/CoralOS buy/sell agents (constrained) | **Any method** — trading, prediction markets (Polymarket), on-chain bounties, gig work, x402, etc. |
| Winner | Subjective judging (Tech 40 / Impact 30 / Creativity 30) | **Most real money earned. Objective. We read the wallet.** |
| Length | University-led, multi-day | **3-hour sprint**, hybrid, free |
| Reach | English, Luma | **English = Luma / Japanese = Connpass** |

## 4. Rules & "no human in the loop" verification

- At start, each team declares a **fresh wallet/account** with a known (ideally zero) balance.
- Score = **delta** (ending balance − starting balance) over the 3h window.
- During the scored window the agent runs **unattended** (no human prompting/trading by hand).
- Proof of earnings:
  - Crypto → **block-explorer link(s)** showing settlement (Superteam "Proof slide" idea).
  - Off-chain (gig/platform) → platform earnings export/screenshot + timestamps.
- Anti-cheat: **screen recording or run log** submitted for the scored window.
- Setup before the window (writing the agent, funding gas) is allowed; the human just can't
  drive the earning during the 3 hours.

## 5. Prize

- Winner **keeps everything their AI earned** (the agent's own profit) — itself the hook.
- Plus a headline prize: **TBA** (do not commit a specific figure until owner confirms;
  page launches with "keep what you earn + prize TBA", updated once locked).

## 6. Copy

### English (Luma)

> # Tokyo AI Agent Hackathon — Agents That Earn
> **Can an AI earn money on its own, with no human in the loop?**
>
> The theme is simple and wide open: **agents that earn.**
>
> Build an AI that makes real money by itself, then let it run. Trading, prediction markets,
> on-chain bounties, gig work, x402 services — anything goes. The customer is software, the
> operator is software. The only thing that matters is the number in the wallet at the end.
>
> You get **3 hours**. Whoever's agent earns the most real money wins.
>
> This is not a demo contest. No pitch-deck theater, no subjective judging. **We read the
> wallet.** The agent that earned the most, wins.
>
> 📍 Tokyo Innovation Base (TIB), Marunouchi — or join online. Free.
>
> Bring: a laptop, an idea, and a wallet you're willing to point at the world.

### Japanese (Connpass)

> # AIは、自分でお金を稼げるか？ — Tokyo AI Agent Hackathon
>
> テーマはシンプルです。**自分で稼ぐAIをつくる。**
>
> 取引でも、予測市場でも、オンチェーンの報酬でも、ギグワークでも、x402でも、手段は問いません。
> **人間は一切手を出さない。** セットアップしたら、あとはAIに任せる。3時間後、ウォレットに残った
> 数字だけが結果です。
>
> これはデモ大会ではありません。審査員の主観もスライドの見栄えも関係ない。**ウォレットを見るだけ。**
> 一番多く稼いだAIが、勝ちです。
>
> 📍 現地参加：Tokyo Innovation Base（TIB・丸の内）／ オンライン参加も可。参加無料。
>
> 持ち物：ノートPC、アイデア、そして世界に向けられる覚悟のあるウォレット。

## 7. Platforms (build order)

1. **Luma (English)** — primary, build first. Account = keiodaisuke@gmail.com via Google,
   driven through CloakBrowser daily-driver (CDP :9222). Capture the public `?tk=` event URL.
2. **Connpass (Japanese)** — follow-up, cross-link to Luma. (Japanese-resident audience.)

## 8. Done / verification

- [x] Luma event live at a public URL (event page renders with title, date 7/11 14:00 JST, TIB
  address, online option, body copy) — verified by loading the public URL in browser.
  **https://lu.ma/atfpxptu** (re-verified live 2026-07-05).
- [x] Connpass event live, cross-linked. **https://connpass.com/event/399618/** — DONE
  2026-07-05 via CloakBrowser daily-driver (CDP :9222). Title/date(2026/07/11 14:00-17:00)/venue
  (TIB, Marunouchi, map pinned)/capacity(80)/price(free)/full Japanese body copy from §6/host
  (Anicca・Daisuke Narita) all verified live on the public (non-edit) page. Cross-links to the
  Luma page. Published (公開中), not draft.
- [x] Both URLs returned to owner.
