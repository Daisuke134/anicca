'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';

const socialsLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: 'Anicca Socials',
  url: 'https://aniccaai.com/socials',
  description:
    'A live dashboard of Anicca social-media performance across X, TikTok, Instagram, and YouTube. Updated daily with 7-day views, likes, comments, engagement rate, and per-account leaderboard.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

interface SocialAccount {
  platform: string;
  handle: string;
  name: string;
  posts_7d: number;
  posts_with_data: number;
  views_7d: number;
  likes_7d: number;
  comments_7d: number;
  avg_views: number;
  engagement_rate: number;
}

interface SocialsData {
  updated_at: string;
  window_start: string;
  window_end: string;
  weekly_views: number;
  weekly_likes: number;
  weekly_comments: number;
  weekly_posts: number;
  accounts_total: number;
  alive_accounts: number;
  dead_accounts: number;
  accounts: SocialAccount[];
  dead_handles: string[];
  viral_handles: string[];
}

const PLATFORM_GLYPH: Record<string, string> = {
  tiktok: 'TT',
  'instagram-standalone': 'IG',
  instagram: 'IG',
  youtube: 'YT',
  x: 'X',
  twitter: 'X',
  facebook: 'FB',
};

function formatPlatform(p: string): string {
  if (p === 'instagram-standalone') return 'Instagram';
  if (p === 'tiktok') return 'TikTok';
  if (p === 'youtube') return 'YouTube';
  if (p === 'x' || p === 'twitter') return 'X';
  return p;
}

function platformLink(platform: string, handle: string): string {
  const h = handle.replace(/^@/, '');
  if (platform === 'tiktok') return `https://www.tiktok.com/@${h}`;
  if (platform.startsWith('instagram')) return `https://www.instagram.com/${h}/`;
  if (platform === 'youtube') return `https://www.youtube.com/${handle.startsWith('@') ? handle : '@' + h}`;
  if (platform === 'x' || platform === 'twitter') return `https://x.com/${h}`;
  return '#';
}

export default function Page() {
  const [data, setData] = useState<SocialsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject('fetch failed')))
      .then((d) => {
        if (!d?.socials) {
          setError('socials data not yet populated — anicca-socials cron pending');
          return;
        }
        setData(d.socials);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <main className="min-h-dvh bg-cream px-5 py-32">
        <JsonLd data={socialsLd} />
        <div className="mx-auto max-w-3xl text-center">
          <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">offline</p>
          <h1 className="mt-3 font-display text-[44px] italic text-ink">Anicca Socials</h1>
          <p className="mt-4 text-[15px] text-mist">{error}</p>
          <Link
            href="/"
            className="mt-10 inline-block border-b border-mist/40 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-ink hover:border-ink"
          >
            ← back to anicca.ai
          </Link>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-dvh bg-cream px-5 py-32">
        <JsonLd data={socialsLd} />
        <p className="mx-auto max-w-3xl text-center font-mono-ui text-[12px] uppercase tracking-[0.2em] text-mist">
          loading…
        </p>
      </main>
    );
  }

  const alive = data.accounts.filter((a) => a.views_7d >= 10).sort((x, y) => y.views_7d - x.views_7d);
  const dead = data.accounts.filter((a) => a.views_7d < 10 && a.posts_7d >= 2);

  // T4-35: winner-centric — top 5 per platform by views_7d
  const platformGroups: Record<string, SocialAccount[]> = {};
  for (const acc of data.accounts) {
    const p = formatPlatform(acc.platform);
    if (!platformGroups[p]) platformGroups[p] = [];
    platformGroups[p].push(acc);
  }
  const winners: SocialAccount[] = [];
  for (const p of Object.keys(platformGroups)) {
    platformGroups[p].sort((x, y) => y.views_7d - x.views_7d);
    winners.push(...platformGroups[p].slice(0, 1)); // top 1 per platform → 4 winners
  }
  winners.sort((x, y) => y.views_7d - x.views_7d);

  // T4-33: "What's working" — per-platform avg engagement clustering
  const insights = Object.entries(platformGroups)
    .map(([platform, accs]) => {
      const liveAccs = accs.filter((a) => a.views_7d >= 10);
      const avgViews = liveAccs.length ? liveAccs.reduce((s, a) => s + a.avg_views, 0) / liveAccs.length : 0;
      const avgEng = liveAccs.length ? liveAccs.reduce((s, a) => s + a.engagement_rate, 0) / liveAccs.length : 0;
      const top = liveAccs.sort((x, y) => y.views_7d - x.views_7d)[0];
      return { platform, liveCount: liveAccs.length, avgViews, avgEng, topHandle: top?.handle, topViews: top?.views_7d ?? 0 };
    })
    .filter((x) => x.liveCount > 0)
    .sort((x, y) => y.topViews - x.topViews);
  const updated = new Date(data.updated_at).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <main className="min-h-dvh bg-cream px-5 pt-28 pb-24">
      <JsonLd data={socialsLd} />
      <div className="mx-auto max-w-6xl">
        {/* Eyebrow / back */}
        <div className="flex items-baseline justify-between">
          <Link
            href="/"
            className="font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist hover:text-ink"
          >
            ← anicca.ai
          </Link>
          <p className="font-mono-ui text-[10px] uppercase tracking-[0.18em] text-mist">
            updated {updated} · window {data.window_start} → {data.window_end}
          </p>
        </div>

        {/* Title */}
        <header className="mt-12 grid grid-cols-12 gap-x-6 gap-y-6 border-b border-bone pb-12">
          <div className="col-span-12 md:col-span-4">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              the broadcast desk
            </p>
            <h1 className="mt-3 font-display text-[64px] leading-[0.95] tracking-[-0.03em] text-ink sm:text-[96px]">
              Socials.
            </h1>
            <p className="mt-4 max-w-sm text-[15px] leading-[1.6] text-ink-soft">
              Live per-account performance across TikTok, Instagram, YouTube and X. Refreshed daily 06:30 JST. Nothing manual; the table is the truth.
            </p>
          </div>

          <div className="col-span-12 md:col-span-8">
            <div className="grid grid-cols-2 gap-px border border-ink/15 bg-ink/15 sm:grid-cols-4">
              <Stat label="Weekly views" value={data.weekly_views.toLocaleString()} />
              <Stat label="Weekly likes" value={data.weekly_likes.toLocaleString()} />
              <Stat label="Alive accounts" value={`${data.alive_accounts} / ${data.accounts_total}`} />
              <Stat
                label="Dead accounts"
                value={String(data.dead_accounts)}
                accent={data.dead_accounts > 0 ? 'ember' : undefined}
              />
            </div>
          </div>
        </header>

        {/* T4-32: Winners — top per platform */}
        <section className="mt-16">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="font-display text-[28px] italic text-ink sm:text-[34px]">
              winners
            </h2>
            <span className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
              top per platform · 7-day views
            </span>
          </div>
          <div className="grid grid-cols-1 gap-px border border-ink/15 bg-ink/15 md:grid-cols-2 lg:grid-cols-4">
            {winners.map((w) => (
              <a
                key={`${w.platform}-${w.handle}`}
                href={platformLink(w.platform, w.handle)}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-cream p-5 transition hover:bg-bone"
              >
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                  {PLATFORM_GLYPH[w.platform] ?? formatPlatform(w.platform)} · winner
                </p>
                <p className="mt-2 font-display text-[22px] text-ink">@{w.handle}</p>
                <p className="mt-3 font-mono-ui text-[12px] text-ink-soft">
                  {w.views_7d.toLocaleString()} views · {w.engagement_rate.toFixed(2)}% eng
                </p>
                <p className="mt-1 font-mono-ui text-[10px] text-mist">
                  {w.posts_7d} posts · avg {Math.round(w.avg_views).toLocaleString()}
                </p>
              </a>
            ))}
          </div>
        </section>

        {/* T4-33: What's working — per-platform insights */}
        <section className="mt-12">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="font-display text-[24px] italic text-ink sm:text-[28px]">
              what's working
            </h2>
            <span className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
              per-platform clustering
            </span>
          </div>
          <div className="grid grid-cols-1 gap-px border border-ink/15 bg-ink/15 md:grid-cols-2 lg:grid-cols-4">
            {insights.map((ins) => (
              <div key={ins.platform} className="bg-cream p-5">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                  {ins.platform}
                </p>
                <p className="mt-2 font-display text-[20px] text-ink">
                  {Math.round(ins.avgViews).toLocaleString()} avg views
                </p>
                <p className="mt-2 font-mono-ui text-[11px] text-ink-soft">
                  {ins.liveCount} live · {ins.avgEng.toFixed(2)}% eng
                </p>
                <p className="mt-3 font-mono-ui text-[10px] text-mist">
                  top @{ins.topHandle} → {ins.topViews.toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* T4-34: Alive — demoted from primary to detail section */}
        <section className="mt-16">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="font-display text-[22px] italic text-ink sm:text-[26px]">
              alive (full table)
            </h2>
            <span className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
              {alive.length} accounts · sorted by 7-day views
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse font-mono-ui text-[12px]">
              <thead>
                <tr className="border-y border-ink/20 text-left uppercase tracking-[0.16em] text-mist">
                  <th className="py-3 text-[10px] font-normal">platform</th>
                  <th className="py-3 text-[10px] font-normal">handle</th>
                  <th className="py-3 text-right text-[10px] font-normal">posts</th>
                  <th className="py-3 text-right text-[10px] font-normal">views</th>
                  <th className="py-3 text-right text-[10px] font-normal">avg / post</th>
                  <th className="py-3 text-right text-[10px] font-normal">likes</th>
                  <th className="py-3 text-right text-[10px] font-normal">eng %</th>
                </tr>
              </thead>
              <tbody>
                {alive.map((a) => (
                  <tr key={`${a.platform}-${a.handle}`} className="border-b border-bone">
                    <td className="py-4">
                      <span className="mr-2 inline-block w-7 font-display text-[12px] italic text-mist">
                        {PLATFORM_GLYPH[a.platform] ?? '·'}
                      </span>
                      <span className="text-ink">{formatPlatform(a.platform)}</span>
                    </td>
                    <td className="py-4 text-ink">
                      <a
                        href={platformLink(a.platform, a.handle)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="border-b border-mist/30 hover:border-ink"
                      >
                        {a.handle}
                      </a>
                    </td>
                    <td className="py-4 text-right tabular-nums text-ink">{a.posts_7d}</td>
                    <td className="py-4 text-right tabular-nums font-display text-[16px] text-ink">{a.views_7d.toLocaleString()}</td>
                    <td className="py-4 text-right tabular-nums text-ink-soft">{a.avg_views.toFixed(0)}</td>
                    <td className="py-4 text-right tabular-nums text-ink-soft">{a.likes_7d}</td>
                    <td className="py-4 text-right tabular-nums text-ink-soft">{a.engagement_rate.toFixed(2)}%</td>
                  </tr>
                ))}
                {alive.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-mist">
                      no alive accounts
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Dead */}
        {dead.length > 0 && (
          <section className="mt-20">
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-display text-[28px] italic text-mist sm:text-[34px]">
                dead
              </h2>
              <span className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                less than 10 views with 2+ posts · candidates for shutdown
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] border-collapse font-mono-ui text-[12px]">
                <thead>
                  <tr className="border-y border-bone text-left uppercase tracking-[0.16em] text-mist">
                    <th className="py-3 text-[10px] font-normal">platform</th>
                    <th className="py-3 text-[10px] font-normal">handle</th>
                    <th className="py-3 text-right text-[10px] font-normal">posts (7d)</th>
                    <th className="py-3 text-right text-[10px] font-normal">views (7d)</th>
                  </tr>
                </thead>
                <tbody>
                  {dead.map((a) => (
                    <tr key={`${a.platform}-${a.handle}`} className="border-b border-bone opacity-70">
                      <td className="py-4 text-ink-soft">
                        <span className="mr-2 inline-block w-7 font-display text-[12px] italic text-mist">
                          {PLATFORM_GLYPH[a.platform] ?? '·'}
                        </span>
                        {formatPlatform(a.platform)}
                      </td>
                      <td className="py-4">
                        <a
                          href={platformLink(a.platform, a.handle)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="border-b border-mist/30 text-ink-soft hover:border-ink"
                        >
                          {a.handle}
                        </a>
                      </td>
                      <td className="py-4 text-right tabular-nums text-ink-soft">{a.posts_7d}</td>
                      <td className="py-4 text-right tabular-nums text-ink-soft">{a.views_7d}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <p className="mt-16 font-mono-ui text-[10px] uppercase tracking-[0.18em] text-mist">
          source: postiz analytics api · skill <span className="text-ink">~/.openclaw/skills/anicca-socials/</span> · cron <span className="text-ink">anicca-socials-daily 06:30 JST</span>
        </p>
      </div>
    </main>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: 'ember' }) {
  const valueClass = accent === 'ember' ? 'text-ember' : 'text-ink';
  return (
    <div className="bg-cream p-5">
      <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">{label}</p>
      <p className={`mt-2 font-display text-[28px] tabular-nums tracking-tight ${valueClass}`}>{value}</p>
    </div>
  );
}
