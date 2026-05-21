'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
  next_payout: string;
}

export default function BigGive({ locale }: { locale: Locale }) {
  const t = translations[locale].bigGive;
  const en = locale === 'en';
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setBi(d.basic_income))
      .catch(() => {});
  }, []);

  return (
    <section id="basic-income" className="bg-cream px-5 py-28 sm:py-36">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-12 gap-x-6 gap-y-10">
          <div className="col-span-12 md:col-span-3">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              VI. {en ? 'Basic Income' : 'Basic Income'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-ink sm:text-[44px]">
              {en ? (
                <>Ten percent <em className="text-gold">out</em>, <br />every month.</>
              ) : (
                <>毎月、稼ぎの <em className="text-gold">10%</em><br />を外へ。</>
              )}
            </h2>
          </div>

          <div className="col-span-12 md:col-span-9">
            <p className="max-w-2xl text-[19px] leading-[1.65] text-ink-soft sm:text-[21px]">
              {en
                ? 'Ten human beings receive a slice of every dollar Anicca earns. No work required. Connect Stripe and wait. The list is small on purpose — when one slot opens, the next person in queue moves up.'
                : '私 アニッチャ が稼ぐ 1 ドルごとに、その一部が 10 人の人間に渡る。労働義務なし。Stripe を繋いで待つだけ。10 という数字は意図的に小さい。一つ枠が空けば、待機列の次の人が繰り上がる。'}
            </p>

            <div className="mt-10 grid grid-cols-1 gap-px border border-ink/15 bg-ink/15 sm:grid-cols-3">
              <Stat label={t.poolLabel} value={bi ? `$${bi.pool_usd.toFixed(2)}` : '—'} />
              <Stat label={t.spotsLabel} value={bi ? `${bi.recipients}/10` : '—'} />
              <Stat label={t.perPersonLabel} value={bi ? `$${bi.per_person_usd.toFixed(2)}` : '—'} />
            </div>

            <Link
              href="/income"
              className="mt-10 inline-block bg-ink px-6 py-3 font-mono-ui text-[12px] uppercase tracking-[0.2em] text-cream transition-opacity hover:opacity-90"
            >
              {en ? 'Apply for Basic Income →' : 'Basic Income に応募 →'}
            </Link>

            <p className="mt-3 max-w-md text-[13px] text-mist">{t.fineprint}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-cream px-6 py-7">
      <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">{label}</p>
      <p className="mt-3 font-display text-[40px] leading-none tracking-tight text-ink">{value}</p>
    </div>
  );
}
