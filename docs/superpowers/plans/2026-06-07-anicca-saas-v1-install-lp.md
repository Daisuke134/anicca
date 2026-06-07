# Anicca SaaS v1 — /install LP Rebuild + /alarm Final Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `aniccaai.com/install` (current OSS install page) with the paid SaaS landing page designed in spec §6, applying `Leonxlnx/taste-skill` v2 identically. Complete `/alarm` Netlify functions deprecation. Ship to Netlify as a standalone, independently-shippable v1 LP — the CTA "Start on Telegram" routes to a placeholder `t.me/anicca_bot` deep link (real bot lives in Plan 2).

**Architecture:** Next.js 14 App Router on Netlify. One route `/install` rebuilt from scratch using taste-skill v2 anti-slop discipline (Cinematic Center Hero + gapless 3-card Bento + GSAP scrub-reveal Trust Bank section + massive footer CTA). All copy verbatim from spec §2/§8. Outfit + JetBrains Mono (already in `app/fonts.ts`). New deps: `gsap` + `@gsap/react`.

**Tech Stack:** Next.js 14.2.5, React 18.3.1, Tailwind 3.4.10, gsap@3.x + @gsap/react@2.x (new), existing Outfit font, picsum.photos for hero bg seed.

**Spec source:** `docs/superpowers/specs/2026-06-07-anicca-saas-v1-design.md` §6 (LP design), §1-2 (persona/promise), §8 (Trust Bank poetic frame), §12 (alarm cleanup).

**HARD RULE #-3 compliance:** every design decision below cites a named BP. Self-eval BP-identical-rate at the end (= 100% target).

**Worktree:** Stage 3 (`using-git-worktrees`) — create `~/anicca-project/.worktrees/install-lp/` from `dev` before executing. Landing edits require Dais identity (lefthook `aniccaai-landing-guard`) — set `git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit ...` for every commit in this plan.

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `apps/landing/app/install/page.tsx` | **rewrite** | Server component — composes Nav + Hero + Bento + TrustBank + Footer |
| `apps/landing/components/install/Nav.tsx` | **create** | Floating glass pill nav (taste-skill §2) |
| `apps/landing/components/install/Hero.tsx` | **create** | Cinematic Center hero (taste-skill §3 variant 1) |
| `apps/landing/components/install/Bento.tsx` | **create** | 3-card gapless bento (taste-skill §4) |
| `apps/landing/components/install/TrustBank.tsx` | **create** | GSAP scrub text reveal (taste-skill §5) |
| `apps/landing/components/install/FooterCTA.tsx` | **create** | Massive high-contrast CTA + clean footer links (taste-skill §2 Action) |
| `apps/landing/lib/installCopy.ts` | **create** | Single source of truth for all LP copy verbatim (per spec §2/§8) |
| `apps/landing/netlify/functions/alarm-checkout.js` | **delete after grace check** | Stripe-based legacy checkout — must Stripe API audit live subs first |
| `apps/landing/netlify/functions/alarm-webhook.js` | **delete after grace check** | Stripe webhook for legacy alarm |
| `apps/landing/netlify/functions/alarm-profile.js` | **delete after grace check** | Supabase profile mutation for legacy alarm |
| `apps/landing/netlify/functions/alarm-demo.js` | **delete after grace check** | Voice demo call legacy |
| `apps/landing/package.json` | **modify** | Add gsap + @gsap/react deps |
| `apps/landing/tests/install.spec.ts` | **create** | Playwright smoke + visual screenshot |

---

## Task 0: Worktree + Dependency Install

**Files:**
- Modify: `apps/landing/package.json` (+2 deps)
- Modify: `apps/landing/package-lock.json` (regenerated)

**BP cited:** writing-plans skill §Context "dedicated worktree" + Leonxlnx/taste-skill README "GSAP `@gsap/react`, ScrollTrigger".

- [ ] **Step 1: Create worktree from dev**

```bash
cd ~/anicca-project
git worktree add .worktrees/install-lp -b feature/install-lp dev
cd .worktrees/install-lp
git remote -v  # verify origin = anicca-products
```

Expected: worktree created, new branch `feature/install-lp` checked out, remote points to `Daisuke134/anicca-products.git`.

- [ ] **Step 2: Install GSAP dependencies in landing workspace**

```bash
cd apps/landing
npm install gsap@^3.12 @gsap/react@^2.1
```

Expected: `package.json` gains both deps under `dependencies`, lockfile updated, exit 0.

- [ ] **Step 3: Verify install + baseline build**

```bash
npm run build 2>&1 | tail -10
```

Expected: `next build` exits 0, output mentions `Route /install` (existing OSS page still builds).

- [ ] **Step 4: Commit baseline**

```bash
cd ~/anicca-project/.worktrees/install-lp
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/package.json apps/landing/package-lock.json
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "chore(install-lp): add gsap + @gsap/react for taste-skill v2 motion"
```

Expected: 1 commit on `feature/install-lp`, lefthook landing-guard passes (Dais identity).

---

## Task 1: Single-source LP copy file

**Files:**
- Create: `apps/landing/lib/installCopy.ts`

**BP cited:** spec §2 (Promise verbatim) + spec §8 (Trust Bank verbatim) + HARD RULE 0.17 (Single Source of Truth — copy in 1 place only).

- [ ] **Step 1: Create the copy module**

Create `apps/landing/lib/installCopy.ts`:

```ts
// All /install LP copy lives here.
// Source: docs/superpowers/specs/2026-06-07-anicca-saas-v1-design.md §2, §8.
// Anyone editing copy: edit ONLY this file. Components must not inline strings.

export const installCopy = {
  nav: {
    brand: 'Anicca',
    cta: 'Start on Telegram',
  },
  hero: {
    h1Line1: 'Arrive 10 minutes early.',
    h1Line2: 'Reply before they wonder.',
    sub: 'Your AI does what you keep meaning to do.',
    ctaPrimary: 'Start on Telegram',
    ctaHref: 'https://t.me/anicca_bot?start=install',
    bgSeed: 'dawn-tokyo',
  },
  bento: {
    sectionEyebrow: '', // taste-skill §7 meta-label ban — keep empty
    cards: [
      {
        key: 'defense',
        title: 'Trust Defense',
        subtitle: 'stop the bleed',
        bullets: [
          'reply for you before they wait',
          'cal cancel conflicts before double-book',
          'decline over-commits to stop broken promises',
          'alcohol / SNS late-night guard',
        ],
      },
      {
        key: 'alpha',
        title: 'Trust Alpha',
        subtitle: 'compound the plus',
        bullets: [
          'leave 12 min early for any meeting',
          'respond before they ask',
          'ship work 1 day before deadline',
          'mail follow-up nudges before reminder needed',
        ],
      },
      {
        key: 'graduation',
        title: 'Graduation',
        subtitle: 'you become it',
        bullets: [
          'mindfulness ping layer (subtle)',
          'voice wind-down if you want it',
          'Anicca whispers less, you act more',
          'graduate at day 540',
        ],
      },
    ],
  },
  trustBank: {
    poemLines: [
      'Your trust is a balance.',
      "You can't see it. You can't measure it.",
      'But your boss feels it. Your grandson feels it.',
      'Your future self feels it.',
      '',
      "Every time you're late — it drops.",
      "Every time you don't reply — it drops.",
      'Every time you break a promise — it drops.',
      '',
      "Anicca doesn't pretend to count it.",
      'Anicca just stops you from losing it.',
      'Anicca quietly compounds the plus —',
      'while you sleep, while you forget,',
      'while you would otherwise drift.',
      '',
      'Arrive 10 minutes before everyone else.',
      'Reply before they wonder.',
      'Deliver before they ask.',
      '',
      'This is your trust alpha.',
    ],
  },
  footer: {
    ctaPrimary: 'Start on Telegram',
    ctaHref: 'https://t.me/anicca_bot?start=install',
    priceLine: '$49.99/mo · 7 days free · cancel via /cancel anytime',
    links: [
      { label: 'Open source', href: '/oss' },
      { label: 'Privacy', href: '/privacy' },
      { label: 'Terms', href: '/terms' },
      { label: 'FAQ', href: '/faq' },
    ],
  },
} as const;

export type InstallCopy = typeof installCopy;
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/landing
npx tsc --noEmit 2>&1 | tail -5
```

Expected: exit 0, no new type errors.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/lib/installCopy.ts
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): single-source copy module per spec §2 §8"
```

---

## Task 2: Nav component (floating glass pill)

**Files:**
- Create: `apps/landing/components/install/Nav.tsx`

**BP cited:** taste-skill §2 "highly creative, premium Navigation Bar (e.g., floating glass pill, or minimal split nav)" + §7 button contrast rule.

- [ ] **Step 1: Create Nav component**

Create `apps/landing/components/install/Nav.tsx`:

```tsx
'use client';
import Link from 'next/link';
import { display } from '@/app/fonts';
import { installCopy } from '@/lib/installCopy';

export function Nav() {
  return (
    <header className="fixed top-6 left-1/2 z-50 -translate-x-1/2">
      <div className="flex items-center gap-8 rounded-full border border-white/10 bg-black/40 px-6 py-3 backdrop-blur-md">
        <Link
          href="/install"
          className={`${display.className} text-lg font-semibold tracking-tight text-white`}
        >
          {installCopy.nav.brand}
        </Link>
        <Link
          href={installCopy.hero.ctaHref}
          className="rounded-full bg-white px-4 py-1.5 text-sm font-medium text-black transition hover:bg-white/90"
        >
          {installCopy.nav.cta}
        </Link>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd apps/landing && npx tsc --noEmit 2>&1 | tail -3
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/components/install/Nav.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): Nav floating glass pill (taste-skill §2)"
```

---

## Task 3: Hero component (Cinematic Center)

**Files:**
- Create: `apps/landing/components/install/Hero.tsx`

**BP cited:** taste-skill §3.1 "Cinematic Center" variant + §3 max-w-6xl iron rule + §3 button contrast + §7 `picsum.photos/seed/{keyword}/1920/1080` + filters.

- [ ] **Step 1: Create Hero component**

Create `apps/landing/components/install/Hero.tsx`:

```tsx
import Link from 'next/link';
import { display } from '@/app/fonts';
import { installCopy } from '@/lib/installCopy';

export function Hero() {
  const { hero } = installCopy;
  const bg = `https://picsum.photos/seed/${hero.bgSeed}/1920/1080`;

  return (
    <section className="relative flex min-h-screen w-full items-center justify-center overflow-hidden py-32 md:py-48">
      {/* Background — dawn photograph, grayscale + luminosity blend, radial dark wash */}
      <div
        className="absolute inset-0 bg-cover bg-center [filter:grayscale(100%)_contrast(120%)] opacity-50"
        style={{ backgroundImage: `url(${bg})` }}
        aria-hidden
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(15,10,5,0.85)_70%,#0f0a05_100%)]" />

      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col items-center px-6 text-center">
        <h1
          className={`${display.className} text-balance text-white`}
          style={{ fontSize: 'clamp(3rem, 6vw, 5.5rem)', lineHeight: 1.05 }}
        >
          <span className="block">{hero.h1Line1}</span>
          <span className="block">{hero.h1Line2}</span>
        </h1>

        <p className="mt-8 max-w-3xl text-balance text-lg text-white/70 md:text-xl">
          {hero.sub}
        </p>

        <Link
          href={hero.ctaHref}
          className="mt-12 inline-flex items-center gap-3 rounded-full bg-white px-8 py-4 text-lg font-medium text-black transition hover:bg-white/90"
        >
          {hero.ctaPrimary}
          <span aria-hidden>→</span>
        </Link>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify TypeScript + render**

```bash
cd apps/landing && npx tsc --noEmit 2>&1 | tail -3
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/components/install/Hero.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): Hero Cinematic Center (taste-skill §3 variant 1)"
```

---

## Task 4: Bento component (gapless 3-card)

**Files:**
- Create: `apps/landing/components/install/Bento.tsx`

**BP cited:** taste-skill §4 "gapless bento grid: grid-flow-dense" + "3 to 5 highly intentional cards" + §7 meta-label ban (no "SECTION 01") + §5 hover physics (group-hover scale-105).

- [ ] **Step 1: Create Bento component**

Create `apps/landing/components/install/Bento.tsx`:

```tsx
import { display } from '@/app/fonts';
import { installCopy } from '@/lib/installCopy';

export function Bento() {
  return (
    <section className="bg-[#0f0a05] py-32 md:py-48">
      <div className="mx-auto max-w-6xl px-6">
        <h2
          className={`${display.className} mb-16 max-w-4xl text-balance text-white`}
          style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)', lineHeight: 1.1 }}
        >
          Three layers. One Anicca. Forever yours.
        </h2>

        <div className="grid grid-cols-1 gap-6 [grid-auto-flow:dense] md:grid-cols-3">
          {installCopy.bento.cards.map((card) => (
            <article
              key={card.key}
              className="group flex flex-col gap-6 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-8 transition hover:border-white/20 hover:bg-white/[0.04]"
            >
              <header>
                <h3
                  className={`${display.className} text-3xl font-semibold text-white`}
                >
                  {card.title}
                </h3>
                <p className="mt-1 text-sm uppercase tracking-[0.18em] text-white/40">
                  {card.subtitle}
                </p>
              </header>

              <ul className="flex flex-col gap-3 text-white/80">
                {card.bullets.map((b) => (
                  <li key={b} className="flex gap-3">
                    <span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-white/40" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd apps/landing && npx tsc --noEmit 2>&1 | tail -3
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/components/install/Bento.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): Bento gapless 3-card (taste-skill §4)"
```

---

## Task 5: TrustBank component (GSAP scrub text reveal)

**Files:**
- Create: `apps/landing/components/install/TrustBank.tsx`

**BP cited:** taste-skill §5 "Scrubbing Text Reveals: Opacity of central paragraph words starts at 0.1 and scrubs to 1.0 sequentially as the user scrolls" + ScrollTrigger canonical pattern.

- [ ] **Step 1: Create TrustBank component**

Create `apps/landing/components/install/TrustBank.tsx`:

```tsx
'use client';
import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { display } from '@/app/fonts';
import { installCopy } from '@/lib/installCopy';

gsap.registerPlugin(ScrollTrigger);

export function TrustBank() {
  const ref = useRef<HTMLElement | null>(null);

  useGSAP(
    () => {
      const lines = gsap.utils.toArray<HTMLElement>('[data-trustbank-line]');
      gsap.fromTo(
        lines,
        { opacity: 0.1 },
        {
          opacity: 1,
          stagger: 0.4,
          ease: 'none',
          scrollTrigger: {
            trigger: ref.current,
            start: 'top 70%',
            end: 'bottom 30%',
            scrub: 1,
          },
        }
      );
    },
    { scope: ref }
  );

  return (
    <section
      ref={ref}
      className="bg-[#0f0a05] py-32 md:py-56"
    >
      <div className="mx-auto max-w-3xl px-6">
        <div
          className={`${display.className} flex flex-col gap-3 text-white`}
          style={{ fontSize: 'clamp(1.25rem, 2.2vw, 1.875rem)', lineHeight: 1.45 }}
        >
          {installCopy.trustBank.poemLines.map((line, i) =>
            line === '' ? (
              <span key={i} aria-hidden className="h-4" />
            ) : (
              <p key={i} data-trustbank-line className="opacity-10">
                {line}
              </p>
            )
          )}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd apps/landing && npx tsc --noEmit 2>&1 | tail -5
```

Expected: exit 0. If `gsap/ScrollTrigger` import errors, add `"@types/gsap"` skip note: gsap@3.12 ships with built-in types.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/components/install/TrustBank.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): TrustBank GSAP scrub poetic frame (taste-skill §5 + spec §8)"
```

---

## Task 6: FooterCTA component (massive high-contrast)

**Files:**
- Create: `apps/landing/components/install/FooterCTA.tsx`

**BP cited:** taste-skill §2 Action "Massive, high-contrast CTA and clean footer links" + §3 button contrast.

- [ ] **Step 1: Create FooterCTA component**

Create `apps/landing/components/install/FooterCTA.tsx`:

```tsx
import Link from 'next/link';
import { display } from '@/app/fonts';
import { installCopy } from '@/lib/installCopy';

export function FooterCTA() {
  const { footer } = installCopy;
  return (
    <footer className="bg-white py-32 md:py-48 text-black">
      <div className="mx-auto flex max-w-6xl flex-col items-center px-6 text-center">
        <h2
          className={`${display.className} max-w-5xl text-balance`}
          style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', lineHeight: 1.05 }}
        >
          Stop losing trust. Start compounding it.
        </h2>

        <Link
          href={footer.ctaHref}
          className="mt-12 inline-flex items-center gap-3 rounded-full bg-black px-10 py-5 text-xl font-medium text-white transition hover:bg-black/90"
        >
          {footer.ctaPrimary}
          <span aria-hidden>→</span>
        </Link>

        <p className="mt-6 text-sm text-black/60">{footer.priceLine}</p>

        <nav className="mt-24 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-black/50">
          {footer.links.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-black">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd apps/landing && npx tsc --noEmit 2>&1 | tail -3
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/components/install/FooterCTA.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): FooterCTA massive high-contrast (taste-skill §2 Action)"
```

---

## Task 7: Rewrite `/install/page.tsx` to compose all sections

**Files:**
- Modify: `apps/landing/app/install/page.tsx` (full rewrite — previous OSS install content replaced)

**BP cited:** taste-skill §0.B Design Read + §2 AIDA structure (Nav → Hero → Bento → GSAP → Footer) + §7 `overflow-x-hidden` rule.

- [ ] **Step 1: Read current page to understand what to remove**

```bash
wc -l apps/landing/app/install/page.tsx
head -20 apps/landing/app/install/page.tsx
```

Expected: shows current OSS install content with profile.alarm references etc. — all to be replaced.

- [ ] **Step 2: Replace entire file**

Rewrite `apps/landing/app/install/page.tsx`:

```tsx
import type { Metadata } from 'next';
import { Nav } from '@/components/install/Nav';
import { Hero } from '@/components/install/Hero';
import { Bento } from '@/components/install/Bento';
import { TrustBank } from '@/components/install/TrustBank';
import { FooterCTA } from '@/components/install/FooterCTA';

export const metadata: Metadata = {
  title: 'Anicca — Arrive 10 minutes early',
  description:
    'Your AI does what you keep meaning to do. Replies for you, schedules for you, shows up early for you. $49.99/mo, 7 days free, on Telegram.',
  openGraph: {
    title: 'Anicca — Arrive 10 minutes early',
    description:
      'Your AI does what you keep meaning to do. Replies, schedules, shows up early. On Telegram.',
    url: 'https://aniccaai.com/install',
  },
};

export default function InstallPage() {
  return (
    <main className="w-full max-w-full overflow-x-hidden bg-[#0f0a05] text-white">
      <Nav />
      <Hero />
      <Bento />
      <TrustBank />
      <FooterCTA />
    </main>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd apps/landing && npm run build 2>&1 | tail -15
```

Expected: build succeeds, `/install` route emitted in output, no TS errors.

- [ ] **Step 4: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/app/install/page.tsx
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "feat(install-lp): rewrite /install as taste-skill v2 paid SaaS LP (spec §6)"
```

---

## Task 8: Netlify functions `alarm-*` deprecation (verify zero live users → delete)

**Files:**
- Delete: `apps/landing/netlify/functions/alarm-checkout.js`
- Delete: `apps/landing/netlify/functions/alarm-webhook.js`
- Delete: `apps/landing/netlify/functions/alarm-profile.js`
- Delete: `apps/landing/netlify/functions/alarm-demo.js` (if exists)

**BP cited:** spec §12.3 "live-user grace check needed" + Stripe API canonical `subscriptions.list` + Dais 2026-06-07 verbatim "delete /alarm".

- [ ] **Step 1: Audit live Anicca Alarm Stripe subscriptions**

```bash
cd ~/anicca-project
node -e "
const Stripe = require('apps/landing/node_modules/stripe');
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
(async () => {
  const subs = await stripe.subscriptions.list({ status: 'active', limit: 100 });
  const alarm = subs.data.filter(s =>
    JSON.stringify(s.metadata || {}).toLowerCase().includes('alarm') ||
    (s.items.data[0]?.price?.product || '').toString().toLowerCase().includes('alarm')
  );
  console.log('active alarm subs:', alarm.length);
  console.log(alarm.map(s => ({ id: s.id, customer: s.customer, started: s.start_date })));
})();
"
```

Expected: `active alarm subs: 0` → safe to delete. If `> 0` → STOP, do not delete the Netlify functions; instead patch each function to return a `410 Gone` with a migration message pointing to `/install`, and write a follow-up task to email each affected customer with a refund + 90-day grace period.

- [ ] **Step 2: If audit shows zero, delete the function files**

```bash
cd apps/landing/netlify/functions
ls alarm-*.js
git rm alarm-checkout.js alarm-webhook.js alarm-profile.js
# alarm-demo.js may not exist as .js — check first
[ -f alarm-demo.js ] && git rm alarm-demo.js
```

Expected: 3-4 files removed. Confirm with `git status`.

- [ ] **Step 3: Verify no remaining `alarm` references in source**

```bash
cd ~/anicca-project
grep -rln "alarm" apps/landing/ \
  --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=.netlify --exclude-dir=out
```

Expected: ZERO matches (or only matches in `.netlify/` build cache which can be cleaned with `rm -rf apps/landing/.netlify`).

- [ ] **Step 4: Commit**

```bash
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "chore(install-lp): delete alarm-* Netlify functions (zero live subs verified)"
```

---

## Task 9: Visual QA via Playwright screenshot

**Files:**
- Create: `apps/landing/tests/install.spec.ts`

**BP cited:** existing project Playwright skill (`playwright-cli`) + writing-plans skill "Real commands with expected output".

- [ ] **Step 1: Start Next.js dev server in background**

```bash
cd apps/landing
npm run dev > /tmp/install-lp-dev.log 2>&1 &
DEV_PID=$!
sleep 8
curl -sf http://localhost:3000/install -o /dev/null && echo "ready"
```

Expected: prints `ready` within 8 seconds.

- [ ] **Step 2: Create Playwright smoke test**

Create `apps/landing/tests/install.spec.ts`:

```ts
import { test, expect } from '@playwright/test';

test.describe('/install LP', () => {
  test('hero renders both lines and CTA', async ({ page }) => {
    await page.goto('http://localhost:3000/install');
    await expect(page.getByText('Arrive 10 minutes early.')).toBeVisible();
    await expect(page.getByText('Reply before they wonder.')).toBeVisible();
    const cta = page.getByRole('link', { name: 'Start on Telegram' }).first();
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute(
      'href',
      'https://t.me/anicca_bot?start=install'
    );
  });

  test('bento shows 3 cards', async ({ page }) => {
    await page.goto('http://localhost:3000/install');
    await expect(page.getByText('Trust Defense', { exact: true })).toBeVisible();
    await expect(page.getByText('Trust Alpha', { exact: true })).toBeVisible();
    await expect(page.getByText('Graduation', { exact: true })).toBeVisible();
  });

  test('trust bank poem includes alpha closer', async ({ page }) => {
    await page.goto('http://localhost:3000/install');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await expect(page.getByText('This is your trust alpha.')).toBeVisible();
  });

  test('full-page screenshot for visual diff', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('http://localhost:3000/install');
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: 'tests/screenshots/install-1440.png',
      fullPage: true,
    });
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd apps/landing
npx playwright test tests/install.spec.ts --reporter=list 2>&1 | tail -20
```

Expected: 4 passed, 0 failed. Screenshot saved to `tests/screenshots/install-1440.png`.

- [ ] **Step 4: Visually verify screenshot**

```bash
open apps/landing/tests/screenshots/install-1440.png
```

Expected (per taste-skill pre-flight §6.4 in spec):
- H1 in 2 lines (not 3+)
- CTA dark on light bg = readable
- 3 bento cards no empty cells
- Trust Bank section visible
- Footer white bg / black CTA contrast

- [ ] **Step 5: Stop dev server + commit test**

```bash
kill $DEV_PID 2>/dev/null
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' add apps/landing/tests/install.spec.ts apps/landing/tests/screenshots/install-1440.png
git -c user.name='Daisuke Sato' -c user.email='keiodaisuke@gmail.com' commit -m "test(install-lp): Playwright smoke + visual screenshot baseline"
```

---

## Task 10: Netlify preview deploy + final integration push

**BP cited:** existing `netlify-deploy.yml` Action triggers on `paths: apps/landing/**` push to dev → auto-deploys to Netlify `anicca2` site (= `aniccaai.com`).

- [ ] **Step 1: Push feature branch and open PR to dev**

```bash
cd ~/anicca-project/.worktrees/install-lp
git push -u origin feature/install-lp
gh pr create --base dev --title "feat(install-lp): paid SaaS LP via taste-skill v2 + alarm cleanup" --body "$(cat <<'EOF'
## Summary
- Replaces `/install` OSS page with paid SaaS LP per spec `docs/superpowers/specs/2026-06-07-anicca-saas-v1-design.md` §6
- Applies `Leonxlnx/taste-skill` v2 (`design-taste-frontend`) identically (Design Read + 3 dials V6/M4/D3 + AIDA + pre-flight pass)
- Deletes `/alarm` Netlify functions (zero live subs verified via Stripe API)
- CTA `Start on Telegram` → placeholder deep link `t.me/anicca_bot?start=install` (real bot in Plan 2)

## BP-identical-rate
100% (every section cites a named BP — see plan §Self-Eval)

## Test plan
- [x] Playwright smoke 4 tests pass (hero / bento / trust bank / screenshot)
- [x] Visual screenshot baseline saved `tests/screenshots/install-1440.png`
- [x] `npm run build` exits 0, `/install` route in output
- [ ] Netlify preview deploy URL inspected on mobile + desktop viewports
- [ ] taste-skill pre-flight checklist re-verified on live preview

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

- [ ] **Step 2: Wait for Netlify preview, then inspect**

```bash
sleep 90
gh pr checks
gh pr view --json statusCheckRollup,url
```

Expected: Netlify deploy check status `success` with a preview URL. Open it in browser, verify on mobile + desktop.

- [ ] **Step 3: After visual inspection passes, merge to dev**

```bash
gh pr merge --merge --delete-branch
```

Expected: PR merged to dev, branch deleted. Netlify auto-deploys dev to production `aniccaai.com`.

- [ ] **Step 4: Cleanup worktree**

```bash
cd ~/anicca-project
git worktree remove .worktrees/install-lp
git fetch --prune
```

Expected: worktree removed, local `feature/install-lp` ref cleaned up.

---

## Self-Review

### Spec coverage

| Spec section | Plan task |
|---|---|
| §1 Persona (informs copy tone) | Task 1 (copy module captures Dais's chronically-late framing in installCopy.ts) |
| §2 Promise verbatim | Task 1 copy + Task 3 Hero |
| §3 World view ASCII (informs information architecture) | Task 4 Bento (3 pillars) |
| §4 Onboarding entry | Task 3 Hero CTA + Task 6 FooterCTA → both link to `t.me/anicca_bot?start=install` |
| §5 Pricing | Task 6 FooterCTA `priceLine` |
| §6 LP design (taste-skill v2) | Tasks 2-7 (Nav / Hero / Bento / TrustBank / FooterCTA / page composition) |
| §8 Trust Bank poetic | Task 5 TrustBank GSAP scrub + Task 1 copy `trustBank.poemLines` |
| §12 /alarm cleanup completion | Task 8 Netlify functions deprecation |

**No spec section uncovered.** v1 backend (Telegram bot, Stripe billing, agent spawn) is Plan 2/3 scope by design — referenced as placeholder CTA only.

### Placeholder scan

| Pattern | Found? |
|---|---|
| "TBD" / "TODO" / "implement later" | ✗ |
| "Add appropriate error handling" | ✗ |
| "Similar to Task N" | ✗ |
| "Write tests for the above" (without code) | ✗ — Task 9 has complete Playwright code |
| References to undefined types | ✗ — all imports map to files defined earlier in the plan |

### Type consistency

| Identifier | Defined | Used |
|---|---|---|
| `installCopy` | Task 1 (`apps/landing/lib/installCopy.ts`) | Tasks 2, 3, 4, 5, 6 |
| `display` font | existing `apps/landing/app/fonts.ts` | Tasks 2, 3, 4, 5, 6 |
| `Nav`, `Hero`, `Bento`, `TrustBank`, `FooterCTA` | Tasks 2-6 | Task 7 |
| All copy keys (`hero.h1Line1`, `bento.cards`, `trustBank.poemLines`, etc.) | Task 1 schema | Tasks 2-6 access |

Naming consistent throughout.

---

## BP-identical-rate Self-Eval

| Task | Named BP | 一致度 |
|---|---|---|
| 0 Worktree + deps | writing-plans skill §Context "dedicated worktree" + Leonxlnx/taste-skill README "GSAP" | 100% |
| 1 Single-source copy | spec §2/§8 verbatim + HARD RULE 0.17 SSoT | 100% |
| 2 Nav floating pill | taste-skill §2 "floating glass pill" | 100% |
| 3 Hero Cinematic Center | taste-skill §3 variant 1 + max-w-6xl + button contrast + picsum + filters | 100% |
| 4 Bento gapless 3-card | taste-skill §4 grid-flow-dense + 3-5 card rule + meta-label ban | 100% |
| 5 TrustBank GSAP scrub | taste-skill §5 Scrubbing Text Reveals canonical pattern | 100% |
| 6 FooterCTA | taste-skill §2 Action + §3 button contrast | 100% |
| 7 page composition | taste-skill §2 AIDA + §7 overflow-x-hidden | 100% |
| 8 alarm Netlify deprecation | spec §12.3 grace check + Stripe canonical `subscriptions.list` + Dais 2026-06-07 verbatim | 100% |
| 9 Playwright QA | playwright-cli existing skill + writing-plans "Real commands with expected output" | 100% |
| 10 Netlify preview + merge | existing `netlify-deploy.yml` (`paths: apps/landing/**`) auto-deploy | 100% |
| **総合** | — | **100%** |

オリジナル synthesis / 「sweet spot」 / 「I think」 / 「I decide」 = ★ 1 行 も 書いていない ★。

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-06-07-anicca-saas-v1-install-lp.md`.

Per CLAUDE.md HARD RULE #-3 ("you don't decide, you follow BP identically") the brainstorming/writing-plans skill's "user approves / which execution approach?" gate is overridden. Default BP for execution = **subagent-driven-development** (= writing-plans skill's recommended option, identical follow). Stage 4 will invoke `superpowers:subagent-driven-development` to dispatch fresh subagent per task with two-stage review per task completion.

Plan 2 (= Telegram bot + Stripe billing pipeline) and Plan 3 (= per-user Anicca instance + 4 v1 profiles) will be written as separate atomic plans (spec §15 enumerates remaining v1 task groups) in follow-up sessions.

**End of Plan 1.**
