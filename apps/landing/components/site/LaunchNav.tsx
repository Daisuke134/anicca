'use client';

import Link from 'next/link';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';

// LaunchNav — the ONE shared top-level nav for the launch surfaces (/install /me
// /dashboard /life-manager). Foundation pre-wires EVERY launch route link here so
// each subsystem builder only adds its own route page and NEVER edits the route list
// (structural collision-prevention, spec26 §1.7 / spec27 §1).
//
// spec29 + Dais 2026-06-16: launch surfaces are fully localized EN/JA. This nav reads
// labels from launchStrings[locale] and exposes the EN/日本語 toggle. It is a client
// component because locale is resolved in the browser (static export — no server
// Accept-Language). It MUST render inside a <LaunchLocaleProvider> (provided by
// <LaunchFrame>).

// spec31 §G / spec30 §10: no anicca web app, no /install, no /me login. The launch
// surfaces (/lm /life-manager /dais /how-to-cash-out) share only the brand + locale
// toggle; "getting started" lives on the home (#start → GitHub).
const ROUTE_KEYS: ReadonlyArray<{ href: string; key: 'install' | 'me' | 'dashboard' | 'lifeManager' }> = [];

const LINK_CLASS =
  'text-sm text-[hsl(var(--text-secondary))] transition-colors hover:text-[hsl(var(--text-primary))] ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]';

export default function LaunchNav({ active }: { active?: string }) {
  const { locale, setLocale } = useLaunchLocale();
  const nav = launchStrings[locale].nav;

  return (
    <nav
      aria-label="Anicca launch navigation"
      className="sticky top-0 z-50 h-14 w-full border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/85 backdrop-blur"
    >
      <div className="container mx-auto flex h-full items-center justify-between gap-6 px-6 lg:px-8">
        <Link
          href="/"
          className="text-lg font-bold text-[hsl(var(--text-primary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
        >
          Anicca
        </Link>
        <div className="flex items-center gap-5">
          {ROUTE_KEYS.map((r) => {
            const isActive = active === r.href;
            return (
              <Link
                key={r.href}
                href={r.href}
                aria-current={isActive ? 'page' : undefined}
                className={
                  isActive
                    ? 'text-sm font-semibold text-[hsl(var(--text-primary))] underline underline-offset-4 decoration-[hsl(var(--gold))]'
                    : LINK_CLASS
                }
              >
                {nav[r.key]}
              </Link>
            );
          })}

          {/* EN / 日本語 locale toggle */}
          <div
            role="group"
            aria-label={nav.langLabel}
            className="ml-1 flex items-center overflow-hidden rounded-full border border-[hsl(var(--border))] text-xs"
          >
            <button
              type="button"
              onClick={() => setLocale('en')}
              aria-pressed={locale === 'en'}
              className={`px-2.5 py-1 transition-colors ${
                locale === 'en'
                  ? 'bg-[hsl(var(--gold))] font-semibold text-[#18181b]'
                  : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
              }`}
            >
              {nav.en}
            </button>
            <button
              type="button"
              onClick={() => setLocale('ja')}
              aria-pressed={locale === 'ja'}
              className={`px-2.5 py-1 transition-colors ${
                locale === 'ja'
                  ? 'bg-[hsl(var(--gold))] font-semibold text-[#18181b]'
                  : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
              }`}
            >
              {nav.ja}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
