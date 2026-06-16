# Patch — install-me (A-install/me)

> Subsystem: `install-me` · Branch: `dev` · Author: patch-author agent · Date: 2026-06-16 (rev 2, adversarial-review fixes)
> Scope: `apps/landing/app/install/page.tsx` + `apps/landing/app/me/page.tsx` only.
> Goal: wire the install page's cloud CTA to the REAL live $30/mo Anicca Cloud Stripe link, and strip the dead/disabled "opens at launch" theatre + ALL internal jargon from `/me`.
> Constraint: patch FILE only — NOT applied, NOT committed, NOT deployed.

Spec source: `docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md` line 18:
> **A-install/me**: `app/install/page.tsx`(cloud 製品メイン + OSS self-host の 2 カラム)+ `app/me/page.tsx`(自分の個体管理・引き出し)。Next 静的 export。検証 agent = curl 200 + camofox で copy が spec13/20 と一致。

Wireframe source (action row): `docs/superpowers/specs/anicca/20-complete-artifacts-ui-and-human-in-loop-verification.md` §3 line 124 → `/me` action row = `[Aniccaと話す][一時停止][日次報告]` (all three).

Verified facts (RAW evidence below):
- Real live Anicca Cloud link: `https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U` → HTTP **200**, real Stripe Checkout, **recurring monthly** (product `prod_UiBxI12KjTwfDK`, price `price_1TilZaEeDsUAcaLSLpNvdmDT`).
- Dead placeholder currently in code/site: `https://buy.stripe.com/anicca-cloud` → HTTP **403**.

---

## ★ INTEGRITY CONSTRAINT (READ BEFORE EDITING /me) ★

The boolean at `app/me/page.tsx:93` is an **integrity guard**, not jargon:
```tsx
const GATE0_EXTERNAL = !/swap|liquidat/i.test(`${GATE0_WAKE.source} ${GATE0_WAKE.task}`);
const GATE0_MET = GATE0_EXTERNAL && GATE0_WAKE.status === '0x1' && GATE0_WAKE.netUsdc > 0;
```
It reads the words **"swap"/"liquidat"** out of `GATE0_WAKE.source` (`'swap-eth-usdc'`) and `GATE0_WAKE.task` (`'eth→usdc liquidation for compute runway'`) to FORCE the honest "未達 (not met)" badge — because an ETH→USDC swap is asset liquidation, not external earning (HARD 0.24/0.31; Director correction `:90-92`).

**Trap (regression `6842f48e` repeat):** if de-jargon edits delete the substring `swap`/`liquidat` from `GATE0_WAKE.source` / `GATE0_WAKE.task`, the regex no longer matches → `GATE0_EXTERNAL` flips to `true` → the badge falsely renders **"GATE-0 MET"** = a false external-revenue claim on the live site = HARD 0.24/0.31 violation.

**Mandatory rule for this patch:**
1. De-jargon ONLY the **rendered (DOM-visible) strings** — `CardLabel`, the two badge `<span>` texts, the `{GATE0_WAKE.source}` render site, the `ACTIVITY_LOG.label`, and the caption.
2. **Do NOT touch the const values** `GATE0_WAKE.source` (`'swap-eth-usdc'`) or `GATE0_WAKE.task` — they must keep the words `swap`/`liquidat` so the regex still tests truthy and the honest "未達" badge stays.
3. The `{GATE0_WAKE.source}` render at `:196` is replaced by a hard-coded product label (NOT the raw const), so the literal `swap-eth-usdc` never reaches the DOM while the const stays intact for the boolean.

This is verified end-to-end in the Diff below: every DOM-visible `GATE-0`/`swap-eth` string is replaced, and the regex still sees `swap`/`liquidat` in the untouched const → `GATE0_MET === false` → honest badge.

---

## Gaps

### Gap 1 — install cloud CTA points to a DEAD placeholder (403) — SEVERITY: BLOCKER
- **Spec requires**: `/install` cloud column is the 製品メイン・推奨 path; clicking it must reach a real purchase flow ($30/mo Anicca Cloud).
- **Code**: `apps/landing/app/install/page.tsx:125` → `href="https://buy.stripe.com/anicca-cloud"`.
- **RAW live evidence**:
  ```
  $ curl -sL "https://aniccaai.com/install/" | grep -oE 'href="https://buy\.stripe\.com[^"]*"'
  href="https://buy.stripe.com/anicca-cloud"

  $ curl -s -o /dev/null -w "%{http_code}\n" "https://buy.stripe.com/anicca-cloud"
  403
  $ curl -s -o /dev/null -w "%{http_code}\n" "https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U"
  200
  ```
  The recommended product button is a dead 403 link → zero purchases possible. This is the single most important gap.

### Gap 2 — `/me` shows disabled "opens at launch" theatre — SEVERITY: HIGH
- **Spec requires**: `/me` = 自分の個体管理・引き出し (real instance management + withdraw). No fake/coming/disabled placeholder per HARD 0.24 (NO mock/placeholder/coming). But wireframe spec20 §3:124 lists all three action buttons → see "Trade-off" below for delete-vs-implement.
- **Code**: `apps/landing/app/me/page.tsx`
  - `:444-450` `<button disabled>一時停止</button>`
  - `:451-457` `<button disabled>日次報告</button>`
  - `:459-461` `一時停止 · 日次報告は Stripe 課金後に有効化されます。` (= "opens at launch" theatre)
  - `:266-273` withdraw CTA → `https://billing.stripe.com/p/login/anicca` which is **404** (dead portal) — see Gap 4 (separate finance patch).
- **RAW live evidence**:
  ```
  $ curl -sL "https://aniccaai.com/me/" | grep -ioE '(一時停止|日次報告|Stripe 課金後に有効化|disabled)' | sort | uniq -c
     4 disabled
     4 一時停止
     4 日次報告
     2 Stripe 課金後に有効化
  ```
  Two greyed-out `disabled` buttons + a "活性化されます" caption = disabled theatre.

### Gap 3 — `/me` leaks internal jargon to public site (ALL six DOM sites) — SEVERITY: MEDIUM
- **Spec requires**: public copy must read as product UX (spec13/20), not internal engineering identifiers.
- **Code — every USER-VISIBLE (rendered to DOM) leak site, RAW-confirmed**:
  | Line | Rendered string | Leak |
  |------|-----------------|------|
  | `:173` | `<CardLabel>GATE-0 — 初の実 on-chain wake（外部収益はまだ）</CardLabel>` | `GATE-0` |
  | `:176` | badge `<StatusDot/> GATE-0 MET` | `GATE-0` |
  | `:180` | badge `<StatusDot/> GATE-0 未達（swap = 自資産換金…）` | `GATE-0`, `swap` |
  | `:196` | `{GATE0_WAKE.source}` → renders literal `swap-eth-usdc` | `swap-eth` |
  | `:100` | `ACTIVITY_LOG.label` = `` `${GATE0_WAKE.source} (GATE-0)` `` → renders `swap-eth-usdc (GATE-0)` | `swap-eth`, `GATE-0` |
  | `:219-222` | caption: `EARN_MODE=execute bash skills/earn/run.sh` … `earn-ledger.jsonl` … `GATE-0` …（HARD 0.24/0.31） | raw shell + `GATE-0` + `HARD 0.x` |
- **RAW live evidence**:
  ```
  $ curl -sL "https://aniccaai.com/me/" | grep -ioE '(GATE-0|swap-eth|spec27|HARD 0\.24)' | sort | uniq -c
     9 GATE-0
     5 swap-eth
  ```
  `/install` is clean of this jargon (grep returned 0). The Diff below replaces **all six** rendered sites so Acceptance #5 (grep live `/me` = 0) passes.

### Gap 4 — `/me` withdraw CTA → 404 portal — SEVERITY: HIGH, SCOPED OUT of this patch
- **Code**: `apps/landing/app/me/page.tsx:266-273` → `href="https://billing.stripe.com/p/login/anicca"`.
- **RAW**: `$ curl -s -o /dev/null -w "%{http_code}" "https://billing.stripe.com/p/login/anicca"` → **404**.
- **Decision**: this is a finance/billing-portal wiring gap, not the install-CTA gap this patch targets. **Explicitly scoped to a named separate patch: `docs/superpowers/specs/anicca/patches/me-withdraw-portal.patch.md`** (to wire the real Stripe customer-portal login URL once the portal is configured, task#83 in `me/page.tsx:265` comment). It is intentionally NOT changed here to keep this patch's blast radius to install-CTA + theatre/jargon. Listed here so the director sees it is known and owned, not silently ignored.

> Note: `/install` is already a correct 2-column (CLOUD recommended + OSS self-host) layout with a working OSS path (`bash install.sh`, GitHub link 200). Only the cloud CTA href is broken there — no structural change to `/install` is needed.

---

## Trade-off — DELETE vs IMPLEMENT the `一時停止`/`日次報告` buttons (director chooses)

Wireframe spec20 §3:124 shows the `/me` action row with all three buttons `[Aniccaと話す][一時停止][日次報告]`. Current code renders them but **disabled** = theatre (HARD 0.24 violation). Two honest resolutions; this patch defaults to **Option A (delete)** because it is the smallest change that removes the violation with zero new backend surface, but the director may pick **Option B**:

| | Option A — DELETE (this patch's default) | Option B — IMPLEMENT (wire real actions) |
|---|---|---|
| Change | Remove both disabled buttons + theatre caption; keep only the working `Aniccaと話す` link | Keep all three; wire `一時停止`/`日次報告` to real endpoints |
| Honest? | ✅ no disabled/coming theatre | ✅ if endpoints truly work |
| Wireframe match (spec20 §3:124 = 3 buttons) | ✗ diverges (2 → 1 button) | ✅ matches |
| Cost / risk | minimal, no backend | needs real pause + daily-report endpoints (Telegram bot command for pause; report cron). Larger blast radius; out of this patch's install-CTA scope |
| When | now (ship the install fix without theatre) | follow-up once `/me` instance-control backend exists |

**Default applied below = Option A.** If the director prefers Option B, do NOT apply the "Action buttons" diff below; instead track it under `me-instance-controls.patch.md` and wire `一時停止` → Telegram `pause` command, `日次報告` → report trigger. Either way the disabled-theatre must not ship.

---

## Diff

### File 1 — `apps/landing/app/install/page.tsx` (cloud CTA → real link)

**Before** (lines 123-130):
```tsx
              cta={
                <CTA
                  href="https://buy.stripe.com/anicca-cloud"
                  variant="primary"
                >
                  Googleでログイン / $30/月で始める →
                </CTA>
              }
```

**After**:
```tsx
              cta={
                <CTA
                  href="https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U"
                  variant="primary"
                >
                  Googleでログイン / $30/月で始める →
                </CTA>
              }
```

Only the `href` changes: dead `anicca-cloud` (403) → real Anicca Cloud Payment Link `cNi7sL0dEdVI0iI7ki2880U` (200, $30/mo recurring). No other `/install` change.

### File 2a — `apps/landing/app/me/page.tsx` (remove disabled theatre — Option A default)

**Before** (lines 432-463, the whole "Action buttons" Section):
```tsx
      {/* ── Action buttons ── */}
      <Section>
        <Reveal>
          <div className="flex flex-wrap gap-3">
            <a
              href="https://t.me/AniccaLifeBot"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
            >
              Aniccaと話す
            </a>
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
            >
              一時停止
            </button>
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
            >
              日次報告
            </button>
          </div>
          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
            一時停止 · 日次報告は Stripe 課金後に有効化されます。
          </p>
        </Reveal>
      </Section>
```

**After** (Option A — keep only the real, working action; remove both disabled buttons + the "活性化されます" theatre caption):
```tsx
      {/* ── Action buttons ── */}
      <Section>
        <Reveal>
          <div className="flex flex-wrap gap-3">
            <a
              href="https://t.me/AniccaLifeBot"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
            >
              Aniccaと話す
            </a>
          </div>
        </Reveal>
      </Section>
```

### File 2b — `apps/landing/app/me/page.tsx` (de-jargon ALL six DOM sites; const values UNTOUCHED)

Replace every DOM-visible `GATE-0`/`swap-eth` string. **The `GATE0_WAKE.source`/`GATE0_WAKE.task` const values (`:81-82`) and the `GATE0_EXTERNAL` regex (`:93`) are NOT changed** — see Integrity Constraint above.

**Edit 1 — CardLabel (`:173`)**

Before:
```tsx
              <CardLabel>GATE-0 — 初の実 on-chain wake（外部収益はまだ）</CardLabel>
```
After:
```tsx
              <CardLabel>初の実 on-chain 稼働（外部収益はこれから）</CardLabel>
```

**Edit 2 — the "MET" badge text (`:176`)**

Before:
```tsx
                  <StatusDot status="alive" /> GATE-0 MET
```
After:
```tsx
                  <StatusDot status="alive" /> 外部収益 達成
```

**Edit 3 — the "未達" badge text (`:180`)** — keep the honest meaning, drop the `GATE-0`/`swap` jargon:

Before:
```tsx
                  <StatusDot status="warning" /> GATE-0 未達（swap = 自資産換金、外部収益ではない）
```
After:
```tsx
                  <StatusDot status="warning" /> 外部収益はまだ（自資産の換金のみ）
```

**Edit 4 — the `{GATE0_WAKE.source}` render site (`:196`)** — replace the raw const render with a hard-coded product label so `swap-eth-usdc` never reaches the DOM (the const itself stays for the boolean):

Before:
```tsx
                <p className="text-base font-semibold text-[hsl(var(--text-primary))]">
                  {GATE0_WAKE.source}
                </p>
```
After:
```tsx
                <p className="text-base font-semibold text-[hsl(var(--text-primary))]">
                  ETH→USDC 換金
                </p>
```

**Edit 5 — `ACTIVITY_LOG.label` (`:100`)** — drop `${GATE0_WAKE.source}` and `(GATE-0)`:

Before:
```tsx
    label: `${GATE0_WAKE.source} (GATE-0)`,
```
After:
```tsx
    label: 'ETH→USDC 換金（compute runway 用）',
```

**Edit 6 — the raw-shell caption (`:219-222`)** — remove raw shell + internal file/rule names; keep the verifiable claim:

Before:
```tsx
            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
              automaton loop が毎 beat <code>EARN_MODE=execute bash skills/earn/run.sh</code> を実行 →
              ETH→USDC を Base で実 swap → receipt 0x1 + USDC 差分を検証 → earn-ledger.jsonl に追記。
              narrate だけは GATE-0 にならない（HARD 0.24/0.31）。
            </p>
```
After:
```tsx
            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
              あなたの個体が Base 上で実際に取引し、成功レシート（0x1）と USDC 差分を検証した上で記録した実績です。
              文章だけの主張ではなく、すべてオンチェーンで再確認できます。
            </p>
```

**Edit 7 — the `{GATE0_WAKE.task}` render site (`:199`)** — replace the raw English const render with a hard-coded JP label (the const at `:82` stays UNTOUCHED for the `:93` boolean):

Before:
```tsx
                  {GATE0_WAKE.task}
```
After:
```tsx
                  compute runway 確保のための換金
```

> Post-edit integrity check (must hold): `GATE0_WAKE.source` still === `'swap-eth-usdc'` and `GATE0_WAKE.task` still contains `'liquidation'` → `/swap|liquidat/i.test(...)` === `true` → `GATE0_EXTERNAL === false` → `GATE0_MET === false` → the `:178-182` branch (the now-de-jargoned "未達" badge) renders, NOT the "MET" branch. No false external-revenue claim. Verify command #6 below asserts this.

---

## Commands

### Apply
```bash
cd /Users/anicca/anicca-project
git checkout dev && git pull
# File 1: install/page.tsx:125 href anicca-cloud -> cNi7sL0dEdVI0iI7ki2880U
# File 2a: me/page.tsx Action buttons Section -> Option A (remove 2 disabled buttons + caption)  [OR Option B per Trade-off]
# File 2b: me/page.tsx Edits 1-6 (de-jargon DOM strings ONLY; DO NOT edit GATE0_WAKE.source/.task or the :93 regex)
git checkout -b fix/install-me-cloud-cta
git add apps/landing/app/install/page.tsx apps/landing/app/me/page.tsx
git commit -m "fix(install): wire cloud CTA to real \$30/mo Anicca Cloud link; strip /me disabled theatre + jargon (keep integrity regex)"
git push -u origin fix/install-me-cloud-cta
```

### Deploy (PR → main)
```bash
gh pr create --base main --head fix/install-me-cloud-cta \
  --title "fix(install): real cloud CTA + de-theatre /me" \
  --body "install cloud CTA anicca-cloud(403) -> cNi7sL0dEdVI0iI7ki2880U(200). Remove /me disabled buttons + opens-at-launch caption + ALL internal jargon. GATE0_EXTERNAL integrity regex preserved (still shows honest '未達')."
gh pr merge --merge --delete-branch     # netlify auto-deploys apps/landing on main push
```

### Verify (run after deploy — camofox is fetched & working this session)
```bash
# 1) install CTA now points to the real link (NOT 403 anicca-cloud)
curl -sL "https://aniccaai.com/install/" | grep -oE 'href="https://buy\.stripe\.com[^"]*"'
#   EXPECT: href="https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U"   (and NO anicca-cloud)

# 2) the target reaches Stripe checkout, not 403
curl -s -o /dev/null -w "%{http_code}\n" "https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U"
#   EXPECT: 200

# 3) ★ camofox click-verify (EXECUTABLE — camoufox already fetched this session) ★
#    Open /install, find the CLOUD CTA by its text, click it, confirm we land on a real Stripe
#    Checkout host (buy.stripe.com renders the live Anicca Cloud checkout) — NOT a 403 page.
KEY=installme-verify
TAB=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://aniccaai.com/install/\",\"userId\":\"anicca\",\"sessionKey\":\"$KEY\"}" | jq -r .tabId)
sleep 3
# click the cloud CTA via its visible text
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" -H 'Content-Type: application/json' \
  -d "{\"expression\":\"(()=>{const a=Array.from(document.querySelectorAll('a')).find(a=>/始める|ログイン/.test(a.textContent));if(!a)return 'NO CTA';window.location.href=a.href;return 'click->'+a.href;})()\",\"userId\":\"anicca\",\"sessionKey\":\"$KEY\"}"
sleep 6
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" -H 'Content-Type: application/json' \
  -d "{\"expression\":\"({host:window.location.host,title:document.title,checkout:/Anicca|Cloud|30|month/i.test(document.body.innerText)})\",\"userId\":\"anicca\",\"sessionKey\":\"$KEY\"}"
curl -sS -X DELETE "http://localhost:9377/tabs/$TAB?userId=anicca&sessionKey=$KEY" >/dev/null
#   EXPECT: host == "buy.stripe.com", title "anicca", checkout:true  (real Stripe Checkout, NOT 403)
#   (PRE-FIX baseline proven this session against the real target link directly:
#     {"host":"buy.stripe.com","title":"anicca","hasCheckout":true}  — confirms the link renders checkout.)

# 4) /me has NO disabled theatre and NO jargon
curl -sL "https://aniccaai.com/me/" | grep -ioE '(GATE-0|swap-eth|liquidation|compute runway|eth→usdc|spec27|HARD 0\.24|EARN_MODE|earn-ledger|skills/earn|一時停止|日次報告|有効化されます|disabled)' | sort | uniq -c
#   EXPECT: empty (0 matches)

# 5) /install jargon stays clean
curl -sL "https://aniccaai.com/install/" | grep -ioE '(GATE-0|spec27|swap-eth|coming|opens at launch)' | sort | uniq -c
#   EXPECT: empty

# 6) ★ integrity: the de-jargon did NOT flip the honest badge ★
#    The const still carries swap/liquidat → boolean stays false → "未達/まだ" honest badge, never "達成".
curl -sL "https://aniccaai.com/me/" | grep -ioE '(外部収益 達成|外部収益はまだ)' | sort | uniq -c
#   EXPECT: shows "外部収益はまだ" (honest, swap=liquidation), and ZERO "外部収益 達成".
#   Source-level check (in repo): grep -n "GATE0_WAKE = {" -A3 apps/landing/app/me/page.tsx
#     must still show  source: 'swap-eth-usdc',  task: '...liquidation...'  (UNCHANGED).
```

---

## Acceptance

| # | Criterion | Pass condition |
|---|-----------|----------------|
| 1 | `/install` is 2-column | CLOUD (推奨, 製品メイン) + OSS (self-host) columns both render — already true; unchanged by this patch |
| 2 | Cloud CTA is real | camofox click on the CLOUD CTA (Verify #3) navigates to a real Stripe Checkout (`buy.stripe.com` host, $30/mo Anicca Cloud, price `price_1TilZaEeDsUAcaLSLpNvdmDT`) — NOT a 403, NOT `buy.stripe.com/anicca-cloud` |
| 3 | OSS column works | OSS column shows a working self-host path: GitHub link (`github.com/Daisuke134/anicca`, 200) + `bash install.sh` (install.sh raw 200) |
| 4 | `/me` no disabled theatre | No `disabled` buttons, no "Stripe 課金後に有効化されます", no greyed "opens at launch" copy (Option A default; or Option B with all 3 wired to real actions) |
| 5 | No jargon | Verify #4 grep on live `/me` AND Verify #5 on `/install` both return 0 for GATE-0 / spec27 / swap-eth / EARN_MODE / earn-ledger / skills/earn / HARD 0.x / raw shell |
| 6 | Integrity preserved | Verify #6: live `/me` shows the honest "外部収益はまだ" badge and ZERO "外部収益 達成"; repo `GATE0_WAKE.source`/`task` still contain `swap`/`liquidation` so the `:93` regex still tests true (no false external-revenue claim — HARD 0.24/0.31) |

---

## Evidence appendix (RAW, this session)

```
# install button href on live site
$ curl -sL "https://aniccaai.com/install/" | grep -oE 'href="https://buy\.stripe\.com[^"]*"'
href="https://buy.stripe.com/anicca-cloud"

# link health
$ curl -s -o /dev/null -w "%{http_code}" "https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U"   # -> 200
$ curl -s -o /dev/null -w "%{http_code}" "https://buy.stripe.com/anicca-cloud"               # -> 403

# /me theatre + jargon
$ curl -sL "https://aniccaai.com/me/" | grep -ioE '(GATE-0|swap-eth|disabled|一時停止|日次報告|Stripe 課金後に有効化)' | sort | uniq -c
   4 disabled
   9 GATE-0
   5 swap-eth
   4 一時停止
   4 日次報告
   2 Stripe 課金後に有効化

# /me withdraw portal link (Gap 4, scoped to separate patch)
$ curl -s -o /dev/null -w "%{http_code}" "https://billing.stripe.com/p/login/anicca"        # -> 404

# OSS self-host path exists
$ curl -s -o /dev/null -w "%{http_code}" "https://raw.githubusercontent.com/Daisuke134/anicca/main/install.sh"  # -> 200

# real Stripe link is a recurring monthly Checkout
$ curl -sL "https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U" | grep -i interval   # -> "Interval","interval","month","Month"

# ★ camofox click-verify executed this session (camoufox fetch succeeded) — navigating to the REAL
#   target link (post-fix CTA destination) lands on a live Stripe Checkout, NOT a 403:
$ curl -sS -X POST http://localhost:9377/tabs -d '{"url":"https://aniccaai.com/install/",...}'
  {"tabId":"5dba18e1-...","url":"https://aniccaai.com/install"}
$ curl ... /evaluate  window.location.href='https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U'
  {"ok":true,"result":"navigating"}
$ curl ... /evaluate  {host, title, hasCheckout}
  {"ok":true,"result":{"host":"buy.stripe.com","title":"anicca","hasCheckout":true}}
#   => post-fix CTA destination renders a real Stripe Checkout (buy.stripe.com), hasCheckout=true.

# /me jargon DOM sites confirmed in source (apps/landing/app/me/page.tsx):
#   :173 CardLabel "GATE-0 …" · :176 "GATE-0 MET" · :180 "GATE-0 未達（swap…）"
#   :196 {GATE0_WAKE.source} -> "swap-eth-usdc" · :100 ACTIVITY_LOG.label "...(GATE-0)"
#   :219-222 caption "EARN_MODE=execute bash skills/earn/run.sh … earn-ledger.jsonl … HARD 0.24/0.31"
# integrity guard (DO NOT edit): :81 source:'swap-eth-usdc' · :82 task:'…liquidation…' · :93 /swap|liquidat/i regex
```
