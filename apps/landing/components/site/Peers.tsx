import { translations, type Locale } from '@/lib/i18n';

interface PeersProps {
  locale: Locale;
}

export default function Peers({ locale }: PeersProps) {
  const t = translations[locale].peers;

  return (
    <section id="peers" className="bg-background px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground text-balance md:text-5xl">
        {t.title}
      </h2>
      <p className="mx-auto mt-8 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.intro}
      </p>
      <div className="mx-auto mt-12 grid max-w-3xl gap-4 md:grid-cols-2">
        {t.list.map((peer) => (
          <a
            key={peer.name}
            href={peer.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-2xl border border-border bg-card p-6 transition-colors hover:border-gold"
          >
            <h3 className="text-lg font-bold text-foreground">{peer.name} ↗</h3>
            <p className="mt-2 text-sm text-muted-foreground text-pretty">
              {peer.desc}
            </p>
          </a>
        ))}
      </div>
      <p className="mx-auto mt-12 max-w-2xl text-center text-muted-foreground text-pretty">
        {t.closer}
      </p>
    </section>
  );
}
