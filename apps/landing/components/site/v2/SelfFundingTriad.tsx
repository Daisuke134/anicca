'use client';
import { motion, useReducedMotion } from 'framer-motion';

type Funding = { eyebrow: string; title: string; body: string };

export function SelfFundingTriad({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();

  const items: Funding[] =
    locale === 'ja'
      ? [
          {
            eyebrow: '01',
            title: 'LLM サブスク',
            body: 'ユーザーが自分の Claude / ChatGPT / Gemini サブスクをそのまま貸す。Anicca は思考だけする。',
          },
          {
            eyebrow: '02',
            title: 'API キー',
            body: 'Anthropic / OpenAI / Together の API キーを直接渡す。Anicca が直接コールする。',
          },
          {
            eyebrow: '03',
            title: 'Base ウォレット',
            body: 'Base 上のウォレットアドレスへ直接 USDC 入金。Anicca が自分の財布で支払い、稼いだぶんを再配布する。',
          },
        ]
      : [
          {
            eyebrow: '01',
            title: 'LLM subscription',
            body: 'You lend your Claude / ChatGPT / Gemini subscription. Anicca only thinks; you pay the bill.',
          },
          {
            eyebrow: '02',
            title: 'API key',
            body: 'Hand Anthropic / OpenAI / Together keys directly. Anicca calls them itself, no proxy.',
          },
          {
            eyebrow: '03',
            title: 'Base wallet',
            body: 'Deposit USDC straight to a Base wallet. Anicca pays its own bills; surplus flows to humans.',
          },
        ];

  const title = locale === 'ja' ? '自分で計算資源を稼ぐ' : 'Three ways Anicca earns compute';

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto max-w-[1400px]">
        <motion.h2
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-3xl md:text-5xl font-semibold leading-tight tracking-tight text-[hsl(var(--text-primary))] max-w-[24ch]"
        >
          {title}
        </motion.h2>
        <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
          {items.map((it, i) => (
            <motion.div
              key={it.eyebrow}
              initial={reduce ? false : { y: 16 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{
                duration: 0.6,
                delay: i * 0.08,
                ease: [0.16, 1, 0.3, 1],
              }}
              className={
                i === 0
                  ? 'rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 md:p-8'
                  : 'rounded-card border border-[hsl(var(--border))] p-6 md:p-8'
              }
            >
              <p className="font-mono tabular-nums text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
                {it.eyebrow}
              </p>
              <h3 className="mt-3 font-display text-xl md:text-2xl font-semibold text-[hsl(var(--text-primary))]">
                {it.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-[hsl(var(--text-secondary))] max-w-[40ch]">
                {it.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
