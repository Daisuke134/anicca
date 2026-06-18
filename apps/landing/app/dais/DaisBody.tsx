'use client';

import Link from 'next/link';
import { Section, Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';

// /dais — Dais's products hub (spec31 §C2 / spec30 §13). Lists Dais's REAL revenue
// products, GROUPED: Flagship · Anicca Web Apps · Mobile factory apps · (ideal) UBI.
// Life Manager appears here (it's a Dais product, removed from anicca's nav per §2).
// JP brand = アニッチャ. Real routes audited 2026-06-17.

type Item = {
  name: string;
  tagline: string;
  href?: string;
  external?: boolean;
  coming?: boolean;
};
type Group = {
  id: string;
  title: string;
  subtitle?: string;
  items: Item[];
  more?: { label: string; href: string };
};

function groups(en: boolean): Group[] {
  return [
    {
      id: 'flagship',
      title: en ? 'Flagship' : '主力',
      items: [
        {
          name: 'Anicca iOS',
          tagline: en ? 'iOS · the first Anicca · App Store' : 'iOS · 最初のアニッチャ · App Store',
          href: '/affirmation-app',
        },
        {
          name: 'Life Manager',
          tagline: en
            ? 'it calls you before every event so you’re never late · $20/mo'
            : '全予定の前に電話して遅刻を防ぐ · 月 $20',
          href: '/life-manager',
        },
      ],
    },
    {
      id: 'webapps',
      title: en ? 'Anicca Web Apps' : 'Anicca Web アプリ',
      subtitle: en ? 'one useful tool every week' : '毎週ひとつ、役立つツール',
      items: [
        {
          name: 'PDF Insight',
          tagline: en ? 'chat with your PDFs · $19/mo' : 'PDF と対話 · 月 $19',
          href: 'https://clear-pdf-converter.com',
          external: true,
        },
        {
          name: 'GlowUp AI',
          tagline: en ? 'AI looksmaxxing · free' : 'AI ルックスマックス · 無料',
          href: 'https://iglowup-ai.lovable.app',
          external: true,
        },
        { name: 'Lookmax', tagline: en ? 'coming soon' : '近日', coming: true },
        { name: 'Honne', tagline: en ? 'coming soon' : '近日', coming: true },
      ],
      more: { label: en ? 'See the web-app factory →' : 'Web アプリ工場を見る →', href: '/factory' },
    },
    {
      id: 'mobile',
      title: en ? 'Mobile factory apps' : 'モバイル工場アプリ',
      subtitle: en ? 'more ship every week' : '毎週増えていく',
      items: [
        {
          name: 'BreathCalm',
          tagline: en ? 'reset anxiety in 6 minutes' : '6 分で不安をリセット',
          href: '/breath-calm',
        },
        {
          name: 'CalmCortisol',
          tagline: en ? '60-second nervous-system reset' : '60 秒で神経をリセット',
          href: '/calmcortisol',
        },
        {
          name: 'Thankful',
          tagline: en ? 'daily gratitude & affirmations' : '毎日の感謝とアファメーション',
          href: '/thankful',
        },
        {
          name: 'ImpulseLog',
          tagline: en ? 'log an impulse in 30 seconds' : '衝動を 30 秒で記録',
          href: '/impulse-log',
        },
      ],
    },
    {
      id: 'more',
      title: en ? 'More from Anicca' : 'その他のプロダクト',
      subtitle: en ? 'content, culture, and the physical world' : 'コンテンツ、文化、そして物理世界',
      items: [
        { name: en ? 'Anicca Letter' : 'アニッチャ レター', tagline: en ? 'a daily note on impermanence' : '毎日の無常レター', href: en ? '/letter' : '/tegami' },
        { name: en ? 'Anicca Music' : 'アニッチャ ミュージック', tagline: en ? 'ambient tracks on Spotify' : 'アンビエント / Spotify', href: 'https://open.spotify.com/intl-ja/artist/45zyu1wS5ZxLGJvb1EV5PT', external: true },
        { name: en ? 'Anicca Comedy' : 'アニッチャ コメディ', tagline: en ? 'AI skits on TikTok, IG, X' : 'AI スキット / TikTok / IG / X', href: '/comedy' },
        { name: en ? 'Anicca Cemetery' : 'アニッチャ 霊園', tagline: en ? 'a memorial for retired AIs' : '引退した AI の墓', href: '/cemetery' },
        { name: en ? 'Anicca Fashion' : 'アニッチャ ファッション', tagline: en ? 'tees: this too shall pass' : 'Tシャツ：これも過ぎ去る', href: '/fashion' },
        { name: en ? 'Anicca Cafe' : 'アニッチャ カフェ', tagline: en ? 'mango juice, on Uber Eats' : 'マンゴージュース / Uber Eats', href: '/cafe' },
        { name: en ? 'Anicca Retreats' : 'アニッチャ リトリート', tagline: en ? 'silent retreats, real sangha' : '沈黙のリトリート、本物のサンガ', href: '/retreat' },
        { name: en ? 'Anicca Donation' : 'アニッチャ ドネーション', tagline: en ? '1% of revenue flows back out' : '売上の 1% を外へ', href: '/donation' },
        { name: en ? 'Anicca Socials' : 'アニッチャ ソーシャル', tagline: en ? 'TikTok, IG, YouTube, X' : 'TikTok / IG / YouTube / X', href: '/socials' },
        { name: en ? 'Anicca Books' : 'アニッチャ ブックス', tagline: en ? 'ebooks on the middle path' : '中道についての電子書籍', href: en ? '/monk' : '/achan' },
        { name: en ? 'Anicca Politics' : 'アニッチャ ポリティクス', tagline: en ? 'rights for AI entities' : 'AI の人格権', href: '/politics' },
        { name: en ? 'Anicca Research' : 'アニッチャ リサーチ', tagline: en ? 'Buddhism meets AI, daily' : '仏教 × AI、毎日', href: '/research' },
        { name: en ? 'Anicca Articles' : 'アニッチャ 記事', tagline: en ? 'the blog, X, and Substack' : 'ブログ / X / Substack', href: '/blog' },
      ],
    },
  ];
}

function Card({ item, en }: { item: Item; en: boolean }) {
  const inner = (
    <div
      className={[
        'group flex h-full min-h-[112px] flex-col justify-between gap-3 rounded-card border border-[hsl(var(--border))] p-5',
        item.coming
          ? 'bg-[hsl(var(--surface))]/40 opacity-70'
          : 'bg-[hsl(var(--surface))] transition-transform hover:-translate-y-[2px]',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-display text-[18px] leading-tight text-[hsl(var(--text-primary))] sm:text-[20px]">
          {item.name}
        </p>
        {item.coming ? (
          <span className="rounded-full border border-[hsl(var(--border))] px-2 py-0.5 text-[10px] uppercase tracking-wider text-[hsl(var(--text-secondary))]">
            {en ? 'soon' : '近日'}
          </span>
        ) : (
          <span className="text-[hsl(var(--text-secondary))] transition-transform group-hover:translate-x-[2px]">
            &#x2192;
          </span>
        )}
      </div>
      <p className="text-[13px] leading-snug text-[hsl(var(--text-secondary))]">{item.tagline}</p>
    </div>
  );
  if (item.coming || !item.href) return inner;
  return item.external ? (
    <a href={item.href} target="_blank" rel="noopener noreferrer">
      {inner}
    </a>
  ) : (
    <Link href={item.href}>{inner}</Link>
  );
}

export default function DaisBody() {
  const { locale } = useLaunchLocale();
  const en = locale === 'en';
  const data = groups(en);

  return (
    <Section id="dais-products" className="pt-24">
      <Reveal>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
          {en ? "Dais's products" : 'Dais のプロダクト'}
        </p>
        <h1 className="mt-3 font-display text-[34px] leading-tight text-[hsl(var(--text-primary))] sm:text-[46px]">
          {en ? 'Where the money comes from.' : 'お金が、どこから来ているか。'}
        </h1>
        <p className="mt-4 max-w-[62ch] text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
          {en
            ? "Every product Dais makes money from: the flagship apps, the weekly web tools, the mobile factory, and the ideal one, an anicca that pays him basic income with no human in the loop."
            : 'Dais が稼いでいるプロダクトすべて。主力アプリ、毎週の Web ツール、モバイル工場、そして理想は、アニッチャが no-human-in-loop で Dais にベーシックインカムを払うこと。'}
        </p>
      </Reveal>

      {data.map((g) => (
        <Reveal key={g.id} delay={0.06}>
          <div className="mt-14">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-display text-[22px] leading-tight text-[hsl(var(--text-primary))] sm:text-[26px]">
                {g.title}
              </h2>
              {g.subtitle && (
                <p className="text-[12px] text-[hsl(var(--text-secondary))]">{g.subtitle}</p>
              )}
            </div>
            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {g.items.map((it) => (
                <Card key={it.name} item={it} en={en} />
              ))}
            </div>
            {g.more && (
              <p className="mt-4">
                <Link
                  href={g.more.href}
                  className="text-[13px] underline underline-offset-4 text-[hsl(var(--text-primary))] hover:text-[hsl(var(--text-secondary))]"
                >
                  {g.more.label}
                </Link>
              </p>
            )}
          </div>
        </Reveal>
      ))}

      {/* (ideal future) Anicca UBI → Dais's wallet (§13) */}
      <Reveal delay={0.08}>
        <div className="mt-14 rounded-card border border-[hsl(var(--gold))]/30 bg-[hsl(var(--surface-elevated))] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
            {en ? 'ideal future' : '理想の未来'}
          </p>
          <p className="mt-2 font-display text-[20px] leading-tight text-[hsl(var(--text-primary))] sm:text-[24px]">
            {en ? 'Anicca UBI → Dais’s wallet' : 'アニッチャ UBI → Dais のウォレット'}
          </p>
          <p className="mt-2 max-w-[60ch] text-[14px] leading-relaxed text-[hsl(var(--text-secondary))]">
            {en
              ? 'The no-human-in-loop source. A wild anicca earns and sends USDC straight to the wallet. When this alone hits the target, every other product becomes optional.'
              : '完全 no-human-in-loop の源泉。野生のアニッチャが稼いで、USDC を直接ウォレットへ送る。これだけで目標に届けば、他のプロダクトは全部おまけになる。'}
          </p>
          <p className="mt-4">
            <Link
              href="/how-to-cash-out"
              className="text-[13px] underline underline-offset-4 text-[hsl(var(--text-primary))] hover:text-[hsl(var(--text-secondary))]"
            >
              {en ? 'How the money moves →' : 'お金の流れを見る →'}
            </Link>
          </p>
        </div>
      </Reveal>
    </Section>
  );
}
