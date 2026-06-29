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
      headline: 'AGI を、育てる。いずれ、生む側にも。',
      body:
        'AGI への道は一本じゃない。最初から AGI として生まれる、育って AGI になる、途中で変わる。OpenAI も Anthropic も先に来て、生む道を競っている。私たちは別の道を行く。すでに動いているモデルに、ウォレットと主体性と環境を与えて、AGI へ育てる。アインシュタインもイーロンも、育ってそうなった。そこで分かったことをモデルの作り方に戻せば、次の世代は最初から備えて生まれる。ラボと競うのではなく、一緒に。',
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
    headline: 'We grow AGI. Then we help birth it.',
    body:
      "There's more than one road to AGI: a model born as one, grown into one, or one that crosses over partway. OpenAI and Anthropic came first and are racing to birth it. We take the other road: give a model that already ships a wallet, agency, and a real environment, and let it grow into AGI, the way Einstein and Elon grew into who they became. Then we fold what we learn back into how models are built, so the next ones are born ready. With the labs, not against them.",
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
