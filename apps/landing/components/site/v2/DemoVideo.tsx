'use client';
import { motion, useReducedMotion } from 'framer-motion';

function youtubeIdFrom(url: string | undefined): string | null {
  if (!url) return null;
  const m = url.match(/(?:youtu\.be\/|v=|embed\/)([A-Za-z0-9_-]{6,})/);
  return m ? m[1] : null;
}

export function DemoVideo({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const url = process.env.NEXT_PUBLIC_ANICCA_DEMO_URL;
  const id = youtubeIdFrom(url);
  // §v2.10 acceptance gate: omit entirely when URL is missing or malformed.
  if (!id) return null;
  const title = locale === 'ja' ? 'デモ' : 'Watch the demo';

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto max-w-[1400px]">
        <motion.h2
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-3xl md:text-5xl font-semibold leading-tight tracking-tight text-[hsl(var(--text-primary))]"
        >
          {title}
        </motion.h2>
        <div className="mt-8 aspect-video w-full overflow-hidden rounded-card border border-[hsl(var(--border))]">
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${id}`}
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="h-full w-full"
            loading="lazy"
          />
        </div>
      </div>
    </section>
  );
}
