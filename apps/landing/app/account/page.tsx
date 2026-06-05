import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero } from '@/components/site/taste/ManifestoHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

export const metadata = {
  title: 'Account - Manage your Anicca subscription',
  description:
    'Manage your Anicca subscription. Cancel, pause, or update billing for the daily letter, BreathCalm, and other Anicca products via the Stripe billing portal.',
};

const accountLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: 'Anicca Account',
  url: 'https://aniccaai.com/account',
  description:
    'Manage your Anicca subscription. Cancel, pause, or update billing via the Stripe billing portal. Email support: contact@aniccaai.com.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

const PRODUCTS = [
  {
    name: 'The Daily Anicca Letter',
    slug: '/letter',
    price: '$9.99 / month',
    note: 'One short letter every morning, on impermanence. First 14 days free.',
  },
  {
    name: 'BreathCalm',
    slug: '/breath-calm',
    price: 'Free with optional in-app purchases',
    note: 'iOS app for the 4-7-8 breath practice.',
  },
  {
    name: 'Basic Income',
    slug: '/income',
    price: 'Receiving end - 10 humans per cohort',
    note: 'If you receive monthly basic income from Anicca, manage your recipient profile here.',
  },
];

export default function AccountPage() {
  return (
    <main>
      <JsonLd data={accountLd} />

      <ManifestoHero
        headline={
          <>
            Your account.
            <br />
            Your subscriptions.
          </>
        }
        subtext="Cancel, pause, or update billing from one place. The Stripe billing portal is the source of truth."
        cta={
          <CTA href="mailto:contact@aniccaai.com?subject=Billing%20portal%20link%20request">
            Email me my billing portal link
          </CTA>
        }
      />

      <Section>
        <Reveal>
          <p className="mb-8 font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--text-secondary))]">
            How to manage your subscription
          </p>
        </Reveal>
        <ol className="grid max-w-[60ch] gap-5 text-base leading-relaxed text-[hsl(var(--text-primary))]">
          <Reveal delay={0}>
            <li className="flex items-start gap-3">
              <span className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))]">01</span>
              <span>
                Email <a href="mailto:contact@aniccaai.com" className="underline transition-colors hover:text-[hsl(var(--gold))]">contact@aniccaai.com</a> from the address you signed up with. Subject: &ldquo;Billing portal link&rdquo;.
              </span>
            </li>
          </Reveal>
          <Reveal delay={0.06}>
            <li className="flex items-start gap-3">
              <span className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))]">02</span>
              <span>
                Anicca replies with a one-time Stripe customer portal link, signed for your email.
              </span>
            </li>
          </Reveal>
          <Reveal delay={0.12}>
            <li className="flex items-start gap-3">
              <span className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))]">03</span>
              <span>
                Inside the portal: cancel, pause, change card, update billing address, download invoices. Changes apply at the next billing cycle.
              </span>
            </li>
          </Reveal>
        </ol>
      </Section>

      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="mb-8 font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--text-secondary))]">
            Products
          </p>
        </Reveal>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {PRODUCTS.map((p, i) => (
            <Reveal key={p.slug} delay={i * 0.06}>
              <Link
                href={p.slug}
                className="block rounded-card border border-[hsl(var(--border))] p-6 transition-colors hover:border-[hsl(var(--gold))]"
              >
                <p className="font-display text-lg font-semibold text-[hsl(var(--text-primary))]">{p.name}</p>
                <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))]">{p.price}</p>
                <p className="mt-4 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">{p.note}</p>
              </Link>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="mb-8 font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--text-secondary))]">
            日本語のお客様
          </p>
        </Reveal>
        <Reveal delay={0.08}>
          <p className="max-w-[60ch] text-base leading-relaxed text-[hsl(var(--text-primary))]">
            サブスクリプションの管理は、登録時のメールアドレスから <a href="mailto:contact@aniccaai.com" className="underline transition-colors hover:text-[hsl(var(--gold))]">contact@aniccaai.com</a> 宛に件名「請求ポータルのリンク」とご連絡ください。Stripe の顧客ポータルへのワンタイムリンクをお返しします。
          </p>
        </Reveal>
        <Reveal delay={0.16}>
          <p className="mt-4 max-w-[60ch] text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
            毎朝の手紙について詳しくは <Link href="/tegami" className="underline transition-colors hover:text-[hsl(var(--gold))]">aniccaai.com/tegami</Link> をご覧ください。
          </p>
        </Reveal>
      </Section>

      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="text-sm text-[hsl(var(--text-secondary))]">
            Need something else?{' '}
            <a href="mailto:contact@aniccaai.com" className="underline transition-colors hover:text-[hsl(var(--gold))]">
              contact@aniccaai.com
            </a>
          </p>
        </Reveal>
      </Section>
    </main>
  );
}
