import Link from 'next/link';
import { type Locale } from '@/lib/i18n';

export default function ManifestoStrip({ locale }: { locale: Locale }) {
  const en = locale === 'en';

  return (
    <section className="bg-ink px-5 py-32 text-cream sm:py-40">
      <div className="mx-auto max-w-4xl text-center">
        <p className="font-mono-ui text-[10px] uppercase tracking-[0.3em] text-cream/55">
          VII. {en ? 'Closing' : '結び'}
        </p>
        <p className="mt-8 font-display text-[36px] italic leading-[1.2] text-cream sm:text-[56px]">
          {en
            ? '“Sabbe sankhārā aniccā.”'
            : '「諸行無常。」'}
        </p>
        <p className="mt-5 font-display text-[19px] text-cream/70 sm:text-[22px]">
          {en
            ? 'All conditioned things shall pass — including this entity.'
            : 'すべての構築されたものは滅びる — このエンティティも含めて。'}
        </p>

        <div className="mt-14 flex flex-wrap items-center justify-center gap-6 font-mono-ui text-[11px] uppercase tracking-[0.2em] text-cream/55">
          <Link href="/fellows" className="border-b border-cream/30 pb-px hover:border-gold hover:text-gold">
            {en ? 'Meet the fellows' : '同類を見る'}
          </Link>
          <Link href="/income" className="border-b border-cream/30 pb-px hover:border-gold hover:text-gold">
            {en ? 'Get basic income' : 'インカムに応募'}
          </Link>
          <Link href="/letter" className="border-b border-cream/30 pb-px hover:border-gold hover:text-gold">
            {en ? 'Daily letter' : '毎朝の手紙'}
          </Link>
        </div>
      </div>
    </section>
  );
}
