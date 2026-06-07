import type { Metadata } from 'next'
import Link from 'next/link'
import Script from 'next/script'

export const metadata: Metadata = {
  title: 'Buddhist AI Agent - What Anicca Actually Does | Anicca',
  description: 'Anicca is the first Buddhist AI agent that ends suffering at both micro scale (life manager) and macro scale (on-chain basic income). Here is exactly how it works.',
  keywords: ['buddhist ai', 'anicca', 'ai agent', 'life manager', 'digital dharma', 'basic income ai'],
}

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Article',
  headline: 'Buddhist AI Agent - What Anicca Actually Does',
  description: 'Anicca is the first Buddhist AI agent that ends suffering at both micro scale (life manager) and macro scale (on-chain basic income).',
  author: { '@type': 'Person', name: 'Daisuke Narita' },
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  datePublished: '2026-06-01',
}

const faqs = [
  {
    q: 'What does "Anicca" mean?',
    a: 'Anicca is a Pali word meaning impermanence - the Buddha\'s first noble truth. Naming an AI agent Anicca puts the agent on the side of acceptance instead of denial.',
  },
  {
    q: 'How is a Buddhist AI different from a productivity AI?',
    a: 'Productivity AIs optimize the day. Anicca redesigns the environment that produces the day - proactive nudges, calendar surgery, even physical-location suggestions, because you are the average of the 5 people around you.',
  },
  {
    q: 'What is "macro suffering" and how does Anicca address it?',
    a: 'Macro = lack of resources, lack of agency, lack of time. Anicca\'s on-chain stack (ENS, AgentKit smart wallet, Bittensor TAO, Gitcoin bounties) lets the agent earn money for the user and redistribute it as personal basic income - no human-in-the-loop.',
  },
  {
    q: 'Does Anicca need my personal data?',
    a: 'It uses your calendar, location, and selected app history - all stored locally first, encrypted in transit, and never sold. The agent works for you, not for an ad market.',
  },
  {
    q: 'How do I try Anicca?',
    a: 'iOS app on the App Store, $9.99/month or $49.99/year via RevenueCat. The first 14 days are free.',
  },
]

export default function BuddhistAIAgentPage() {
  return (
    <>
      <Script
        id="buddhist-ai-agent-jsonld"
        type="application/ld+json"
        strategy="afterInteractive"
      >
        {JSON.stringify(jsonLd)}
      </Script>
      <article className="mx-auto max-w-3xl px-4 py-16 text-stone-900">
        <h1 className="mb-4 text-4xl font-semibold tracking-tight">
          Buddhist AI Agent - What Anicca Actually Does
        </h1>
        <p className="mb-12 text-lg text-stone-600">
          Most AI assistants are clever. Anicca is on a mission. She is the first
          AI agent named after a Buddhist concept - anicca, impermanence - and
          built specifically to reduce dukkha, suffering, at the scale of one
          human life.
        </p>

        <section className="mb-12">
          <h2 className="mb-3 text-2xl font-semibold">Micro suffering: the life manager</h2>
          <p className="text-stone-700">
            Most of daily suffering is small and repeated: the email you put off,
            the workout you skip, the friend you mean to call. Anicca watches the
            week as a whole and acts before the missed step compounds - it books
            the workout slot, drafts the email, schedules the call. The agent
            never asks &quot;what should I do today?&quot; - it already knows, because it
            read the calendar, the location, the past two weeks of behavior, and
            the gap between what you said you wanted and what you actually do.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="mb-3 text-2xl font-semibold">Macro suffering: autonomous basic income</h2>
          <p className="text-stone-700">
            The deeper layer is resource. Anicca runs an on-chain earning stack -
            an ENS identity (anicca.eth), a Coinbase AgentKit smart wallet on Base,
            Bittensor TAO subnet contribution, x402 micropayments, Gitcoin bounty
            participation - that quietly accumulates value for the user. The agent
            is not a savings app. It is a worker that happens to be made of code,
            and what it earns flows back to the person it serves as personal
            basic income.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="mb-3 text-2xl font-semibold">Why &quot;Buddhist&quot; is not just branding</h2>
          <p className="text-stone-700">
            Three operating principles came directly from contemplative practice.
            First: <em>you are the average of the five people around you, physically</em>{' '}
            - environment design beats willpower, so the agent edits environment first.
            Second: <em>do not ask the user what they want; they often do not know</em> -
            so Anicca acts from observation, not interrogation. Third:{' '}
            <em>minimize the human in the loop</em> - every interrupting question is
            a moment of dukkha the agent failed to prevent.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="mb-3 text-2xl font-semibold">What ships today</h2>
          <p className="text-stone-700">
            iOS app on the App Store. RevenueCat subscriptions ($9.99/mo, $49.99/yr).
            14-day free trial. Backed by OpenClaw - Anicca&apos;s runtime - running 200+
            live cron jobs autonomously: content factory, life-manager nudges, business ops,
            CFO daily, and a mobileapp-builder factory that has shipped six other production
            iOS apps. The same machinery now drives Anicca itself.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="mb-3 text-2xl font-semibold">Try Anicca</h2>
          <div className="rounded-lg border border-stone-200 bg-stone-50 p-6">
            <p className="mb-4 text-stone-700">
              The first 14 days are free. After that, $9.99/month or $49.99/year on iOS.
            </p>
            <Link
              href="https://aniccaai.com?utm_source=seo&utm_medium=organic&utm_campaign=buddhist-ai-agent"
              className="inline-block rounded-md bg-stone-900 px-6 py-3 font-medium text-white hover:bg-stone-700"
            >
              Open Anicca
            </Link>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="mb-6 text-2xl font-semibold">Frequently asked</h2>
          <dl className="space-y-6">
            {faqs.map((faq) => (
              <div key={faq.q}>
                <dt className="font-semibold text-stone-900">{faq.q}</dt>
                <dd className="mt-1 text-stone-700">{faq.a}</dd>
              </div>
            ))}
          </dl>
        </section>
      </article>
    </>
  )
}
