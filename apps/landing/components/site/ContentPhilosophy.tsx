import { translations, type Locale } from '@/lib/i18n';
import { links } from '@/lib/links';
import {
  TikTokIcon,
  InstagramIcon,
  YouTubeIcon,
  XIcon,
} from '@/components/icons/SocialIcons';

interface ContentPhilosophyProps {
  locale: Locale;
}

export default function ContentPhilosophy({ locale }: ContentPhilosophyProps) {
  const t = translations[locale].contentPhilosophy;
  const l = links[locale];

  const socialLinks = [
    { href: l.tiktok, icon: TikTokIcon, label: 'TikTok' },
    { href: l.instagram, icon: InstagramIcon, label: 'Instagram' },
    { href: l.youtube, icon: YouTubeIcon, label: 'YouTube' },
    { href: l.x, icon: XIcon, label: 'X' },
  ];

  return (
    <section className="bg-background-alt px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground">
        {t.title}
      </h2>
      <p className="mx-auto mt-8 max-w-xl text-center text-muted-foreground text-pretty">
        {t.message}
      </p>

      <div className="mt-8 flex justify-center gap-6">
        {socialLinks.map(({ href, icon: Icon, label }) => (
          <a
            key={label}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={label}
          >
            <Icon className="size-8 text-foreground transition-colors hover:text-muted-foreground" />
          </a>
        ))}
      </div>
    </section>
  );
}
