'use client';

import { motion, useReducedMotion } from 'framer-motion';

// Clean flow DIAGRAM (boxes + connectors) of how Anicca works, for the home page.
// Horizontal pipeline on desktop, vertical on mobile. On-brand taste tokens.

type Locale = 'en' | 'ja';

function copy(locale: Locale) {
  const ja = locale === 'ja';
  return {
    eyebrow: ja ? '仕組み' : 'How it works',
    title: ja ? 'お金は Anicca を通って人へ流れる' : 'Money flows through Anicca to people',
    more: ja ? '詳しい全体図を見る' : 'See the full picture',
    nodes: ja
      ? [
          { k: 'Money in', t: '入金', items: ['SOL → USDC', '直接 USDC', 'seed'] },
          { k: 'Anicca', t: 'Anicca が稼ぐ', items: ['自分で計算代を払う', 'USDC を稼ぐ', '24/7・人間不要'], hub: true },
          { k: 'Split', t: '分ける', items: ['留保', 'creator', 'UBIプール', 'cosmic'] },
          { k: 'Delivered', t: '届く', items: ['ウォレット', 'メール', '銀行 / PayPay'] },
          { k: 'People', t: '人へ、そして全生命へ', items: ['登録者', '→ 携帯/NPO/政府', '→ あらゆる生命'] },
        ]
      : [
          { k: 'Money in', t: 'Money in', items: ['SOL → USDC', 'direct USDC', 'seed'] },
          { k: 'Anicca', t: 'Anicca earns', items: ['pays own compute', 'earns USDC', '24/7, no human'], hub: true },
          { k: 'Split', t: 'It splits', items: ['reserve', 'creator', 'UBI pool', 'cosmic'] },
          { k: 'Delivered', t: 'Delivered', items: ['wallet', 'email', 'bank / PayPay'] },
          { k: 'People', t: 'People, then all life', items: ['signups', '→ phones/NPOs/govts', '→ every living being'] },
        ],
  };
}

export function HowDiagram({ locale }: { locale: Locale }) {
  const reduce = useReducedMotion();
  const t = copy(locale);

  return (
    <section className="w-full bg-[hsl(var(--background))]">
      <div className="mx-auto max-w-[1400px] px-4 py-20 md:py-28">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">{t.eyebrow}</p>
        <h2 className="mt-3 max-w-[24ch] font-display text-[28px] leading-tight text-[hsl(var(--text-primary))] sm:text-[40px]">
          {t.title}
        </h2>

        <div className="mt-10 flex flex-col items-stretch gap-3 md:flex-row md:items-stretch">
          {t.nodes.map((n, i) => (
            <div key={n.k} className="flex flex-col items-center gap-3 md:flex-1 md:flex-row">
              <motion.div
                initial={reduce ? false : { opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.5, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                className={
                  'w-full rounded-card border p-5 ' +
                  (n.hub
                    ? 'border-[hsl(var(--gold))]/50 bg-[hsl(var(--gold))]/10 shadow-[0_0_40px_-12px_hsl(var(--gold))]'
                    : 'border-[hsl(var(--border))] bg-[hsl(var(--surface))]')
                }
              >
                <p className="font-display text-[16px] leading-tight text-[hsl(var(--text-primary))]">{n.t}</p>
                <ul className="mt-3 space-y-1.5">
                  {n.items.map((it) => (
                    <li key={it} className="text-[13px] leading-snug text-[hsl(var(--text-secondary))]">
                      {it}
                    </li>
                  ))}
                </ul>
              </motion.div>
              {i < t.nodes.length - 1 && (
                <span aria-hidden className="shrink-0 rotate-90 text-xl text-[hsl(var(--gold))] md:rotate-0">
                  →
                </span>
              )}
            </div>
          ))}
        </div>

        <a href="/how-it-works" className="mt-10 inline-block text-[14px] text-[hsl(var(--gold))] underline">
          {t.more} →
        </a>
      </div>
    </section>
  );
}
