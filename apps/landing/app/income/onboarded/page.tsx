/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Basic Income — Application received',
  description: 'Your Stripe Connect onboarding is complete. You are on the waitlist.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-20 text-center text-foreground">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">You're on the waitlist.</h1>

      <p className="mt-6 text-lg text-muted-foreground">
        Stripe Connect onboarding complete. KYC processing happens in the background.
      </p>

      <div className="mt-10 rounded-xl border border-border px-6 py-6 text-left">
        <h2 className="text-lg font-semibold">What happens next</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-6 text-base">
          <li>Stripe verifies your identity (usually instant, sometimes 1–2 days).</li>
          <li>Anicca reviews waitlist entries weekly. We accept 10 humans per cohort.</li>
          <li>If accepted, you'll get an email titled "You're in — Anicca Basic Income."</li>
          <li>On the 1st of the next month, your share lands in your bank, automatically.</li>
        </ol>
      </div>

      <p className="mt-10 text-sm text-muted-foreground">
        No need to check back. The work is on Anicca's side now.
      </p>

      <Link
        href="/en"
        className="mt-8 inline-block rounded-xl bg-foreground px-6 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-90"
      >
        Watch the live numbers →
      </Link>
    </main>
  );
}
