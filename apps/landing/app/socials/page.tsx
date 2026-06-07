'use client';

import { useEffect, useState } from 'react';

interface AccountDelta {
  platform: string;
  handle: string;
  followers: number;
  delta_7d: number | null;
  pct_7d: number | null;
}

interface Wow {
  computed_at: string;
  baseline_ts: string;
  window_days: number;
  followers_delta: number;
  followers_pct: number;
  views_delta: number;
  views_pct: number;
  mrr_delta: number;
  mrr_pct: number;
  by_account: AccountDelta[];
}

interface Dashboard {
  updated_at: string;
  followers: { total: number; by_account: AccountDelta[] };
  views: { weekly_total: number; posts_count: number };
  mrr: { total_usd: number };
  wow?: Wow;
}

const PLATFORM_EMOJI: Record<string, string> = {
  tiktok: '🎵',
  instagram: '📷',
  youtube: '▶️',
  x: '𝕏',
};

export default function SocialsPage() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => r.json())
      .then(setD)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <main className="min-h-screen bg-[#FBF7EF] p-12 text-center text-red-700">load error: {error}</main>;
  if (!d) return <main className="min-h-screen bg-[#FBF7EF] p-12 text-center text-[#8B7355]">loading…</main>;

  const ranked = [...(d.wow?.by_account ?? d.followers.by_account.map((a) => ({ ...a, delta_7d: null, pct_7d: null })))].sort(
    (a, b) => b.followers - a.followers,
  );

  return (
    <main className="min-h-screen bg-[#FBF7EF] text-[#2A2520] font-serif">
      <section className="max-w-3xl mx-auto px-6 py-16">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-3 text-center">Anicca Socials</p>
        <h1 className="text-3xl md:text-4xl font-light leading-snug mb-2 text-center">
          Where Anicca lives publicly.
        </h1>
        <p className="text-center text-sm text-[#8B7355] mb-12">
          Live counts. Updated 4× daily. {d.wow ? `${d.wow.window_days}d WoW` : 'WoW collecting…'}
        </p>

        <div className="grid grid-cols-3 gap-4 mb-12 text-center">
          <div className="border border-[#E5DCC9] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[#8B7355]">Followers</p>
            <p className="text-2xl font-light mt-1">{d.followers.total.toLocaleString()}</p>
            {d.wow && (
              <p className={`text-xs mt-1 ${d.wow.followers_delta >= 0 ? 'text-[#2A2520]' : 'text-red-700'}`}>
                {d.wow.followers_delta >= 0 ? '+' : ''}
                {d.wow.followers_delta} ({d.wow.followers_pct}%)
              </p>
            )}
          </div>
          <div className="border border-[#E5DCC9] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[#8B7355]">Weekly views</p>
            <p className="text-2xl font-light mt-1">{d.views.weekly_total.toLocaleString()}</p>
            {d.wow && (
              <p className={`text-xs mt-1 ${d.wow.views_delta >= 0 ? 'text-[#2A2520]' : 'text-red-700'}`}>
                {d.wow.views_delta >= 0 ? '+' : ''}
                {d.wow.views_delta} ({d.wow.views_pct}%)
              </p>
            )}
          </div>
          <div className="border border-[#E5DCC9] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[#8B7355]">MRR</p>
            <p className="text-2xl font-light mt-1">${d.mrr.total_usd.toLocaleString()}</p>
            {d.wow && (
              <p className={`text-xs mt-1 ${d.wow.mrr_delta >= 0 ? 'text-[#2A2520]' : 'text-red-700'}`}>
                {d.wow.mrr_delta >= 0 ? '+' : ''}${d.wow.mrr_delta} ({d.wow.mrr_pct}%)
              </p>
            )}
          </div>
        </div>

        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-6">Ranking by followers · WoW Δ</p>
        <div className="border border-[#E5DCC9]">
          {ranked.map((a, i) => (
            <div
              key={`${a.platform}-${a.handle}`}
              className={`flex items-center justify-between px-4 py-3 ${
                i < ranked.length - 1 ? 'border-b border-[#E5DCC9]' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-lg">{PLATFORM_EMOJI[a.platform] ?? a.platform}</span>
                <span className="text-sm">{a.handle}</span>
                <span className="text-[10px] uppercase tracking-[0.15em] text-[#8B7355]">{a.platform}</span>
              </div>
              <div className="text-right">
                <p className="text-sm">{a.followers.toLocaleString()}</p>
                {a.delta_7d != null && (
                  <p className={`text-[10px] ${a.delta_7d >= 0 ? 'text-[#8B7355]' : 'text-red-700'}`}>
                    {a.delta_7d >= 0 ? '+' : ''}
                    {a.delta_7d} ({a.pct_7d}%)
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-[#8B7355] mt-8">
          Last refresh: {new Date(d.updated_at).toLocaleString()}
        </p>
      </section>

      <footer className="text-center text-xs text-[#8B7355] py-8 border-t border-[#E5DCC9]">
        © Anicca · Daily impermanence in every metric.
      </footer>
    </main>
  );
}
