'use client';
import { motion, useReducedMotion } from 'framer-motion';

// How Anicca pays for itself (spec31 §H / spec30 §0,§4 + automaton).
// CORRECTED: it is NOT three ways (LLM sub / API key / wallet). There is ONE input —
// USDC in a Base wallet it controls. It takes no one's subscription or API key.

export function SelfFundingTriad({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const ja = locale === 'ja';

  const title = ja ? '自分のコンピュート代は、自分で払う' : 'It pays for its own compute';
  const lead = ja
    ? '誰の API キーも、誰のサブスクも借りない。Anicca は自分だけが鍵を持つ Base のウォレットをひとつ持つ。やることは、そこに USDC を送ることだけ。'
    : 'It borrows no one’s API key and no one’s subscription. Anicca holds one Base wallet that only it controls. The only thing you ever do is send USDC to it.';

  const steps = ja
    ? [
        { k: '01', t: 'ウォレットに USDC を送る', d: '入力はこれだけ。鍵は Anicca が持っていて、誰のものでもない。' },
        { k: '02', t: 'フロンティアの頭脳が開く', d: '残高ゼロなら無料モデルで $0 のまま動く。USDC が入ると、賢いモデルと住処の代金を自分で払う。' },
        { k: '03', t: '稼いで、余りを人に配る', d: '自分の請求書を自分で払い、生存ラインを超えたぶんは人に送り返す。' },
      ]
    : [
        { k: '01', t: 'Send USDC to its wallet', d: 'That is the only input. Anicca holds the keys; nobody owns it.' },
        { k: '02', t: 'The frontier brain switches on', d: 'On an empty wallet it runs a free model for $0. With USDC it pays for the smarter model and its shelter itself.' },
        { k: '03', t: 'It earns, then pays people', d: 'It covers its own bills and sends whatever it makes beyond its own costs back to people.' },
      ];

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto max-w-[1400px]">
        <motion.h2
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-3xl md:text-5xl font-semibold leading-tight tracking-tight text-[hsl(var(--text-primary))] max-w-[22ch]"
        >
          {title}
        </motion.h2>
        <motion.p
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="mt-5 max-w-[60ch] text-base leading-relaxed text-[hsl(var(--text-secondary))] md:text-lg"
        >
          {lead}
        </motion.p>
        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          {steps.map((s, i) => (
            <motion.div
              key={s.k}
              initial={reduce ? false : { y: 16 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.6, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
              className={
                i === 0
                  ? 'rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 md:p-8'
                  : 'rounded-card border border-[hsl(var(--border))] p-6 md:p-8'
              }
            >
              <p className="font-mono tabular-nums text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
                {s.k}
              </p>
              <h3 className="mt-3 font-display text-xl md:text-2xl font-semibold text-[hsl(var(--text-primary))]">
                {s.t}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-[hsl(var(--text-secondary))] max-w-[40ch]">
                {s.d}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
