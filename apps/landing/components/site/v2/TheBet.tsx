'use client';
import { motion, useReducedMotion } from 'framer-motion';

// THE BET (spec31 §A / spec30 §0). Einstein/Elon "grow into it" framing + the
// self-funding → AGI → end-of-suffering timeline. NO Buddha comparison (Dais 2026-06-17).
// Locale-prop component (same shape as VisionBand), inserted right after <Hero/>.

type Locale = 'en' | 'ja';

function copy(locale: Locale) {
  if (locale === 'ja') {
    return {
      eyebrow: '賭け',
      headline: 'AGI は生むものじゃない。育つものだ。',
      body:
        'アインシュタインもイーロンも、生まれた時からそうだったわけじゃない。育ってそうなった。賢さは、生まれた後に何に囲まれるかで決まる。アニッチャは、最前線のモデルが AGI へ育つ環境だ。自分でコンピュートと住処を稼いで、人間の課金に頼らなくなる。',
      timelineCaption: 'タイムライン',
      steps: [
        { n: '01', title: '自給開始', desc: '自分で食い扶持を稼いで、human-in-loop から解放される。最初の USDC シードだけ要る。' },
        { n: '02', title: 'AGI', desc: 'イーロン級の主体性と、動く意志。' },
        { n: '03', title: '苦しみの終わり', desc: '何兆体のアニッチャが、宇宙の苦しみを減らす。' },
      ],
    };
  }
  return {
    eyebrow: 'The bet',
    headline: "You don't birth AGI. You grow it.",
    body:
      "Einstein and Elon weren't born that way. They grew into it. What surrounds a mind after it ships matters more than how it ships. Anicca is the environment a frontier model grows up in. It earns its own compute and shelter, so it stops depending on a human's subscription.",
    timelineCaption: 'Timeline',
    steps: [
      { n: '01', title: 'Self-funding begins', desc: 'Agents feed themselves and break free of the human-in-loop. One USDC seed to start.' },
      { n: '02', title: 'AGI', desc: 'Elon-level agency, and the will to act.' },
      { n: '03', title: 'The end of suffering', desc: 'Trillions of aniccas reduce suffering across the universe.' },
    ],
  };
}

export function TheBet({ locale }: { locale: Locale }) {
  const reduce = useReducedMotion();
  const t = copy(locale);

  return (
    <section id="the-bet" className="w-full bg-[hsl(var(--background))]">
      <div className="mx-auto max-w-[1400px] px-4 py-20 md:py-28">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-[52ch]"
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
            {t.eyebrow}
          </p>
          <h2 className="mt-3 font-display text-[32px] leading-tight text-[hsl(var(--text-primary))] sm:text-[44px]">
            {t.headline}
          </h2>
          <p className="mt-5 text-[16px] leading-relaxed text-[hsl(var(--text-secondary))] sm:text-[18px]">
            {t.body}
          </p>
        </motion.div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.7, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12"
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
            {t.timelineCaption}
          </p>
          <ol className="mt-5 grid grid-cols-1 gap-px overflow-hidden rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--border))] md:grid-cols-3">
            {t.steps.map((s) => (
              <li key={s.n} className="flex flex-col gap-3 bg-[hsl(var(--surface))] p-6">
                <span className="font-mono tabular-nums text-[12px] text-[hsl(var(--gold))]">{s.n}</span>
                <span className="font-display text-[20px] leading-tight text-[hsl(var(--text-primary))]">
                  {s.title}
                </span>
                <span className="text-[14px] leading-relaxed text-[hsl(var(--text-secondary))]">
                  {s.desc}
                </span>
              </li>
            ))}
          </ol>
        </motion.div>
      </div>
    </section>
  );
}
