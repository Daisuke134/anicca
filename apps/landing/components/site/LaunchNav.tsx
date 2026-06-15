import Link from 'next/link';

// LaunchNav — the ONE shared top-level nav for the launch surfaces (/install /me
// /dashboard /life-manager). Foundation pre-wires EVERY launch route link here so
// each subsystem builder only adds its own route page and NEVER edits this nav
// (structural collision-prevention, spec26 §1.7 / spec27 §1).
//
// Server-component safe (no hooks, no locale dependency — these are top-level
// routes, not the /en /ja locale tree). Builders: import this, do not modify it.

type NavItem = { href: string; label: string };

// EVERY launch route, pre-wired. Order = product funnel: get it -> your instance
// -> the whole colony -> the life-manager feature.
const LAUNCH_ROUTES: readonly NavItem[] = [
  { href: '/install', label: 'Install' },
  { href: '/me', label: 'Me' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/life-manager', label: 'Life Manager' },
];

const LINK_CLASS =
  'text-sm text-[hsl(var(--text-secondary))] transition-colors hover:text-[hsl(var(--text-primary))] ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]';

export default function LaunchNav({ active }: { active?: string }) {
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
          {LAUNCH_ROUTES.map((r) => {
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
                {r.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
