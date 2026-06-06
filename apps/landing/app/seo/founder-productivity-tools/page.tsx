import Link from 'next/link';

export const metadata = {
  title: "Founder Productivity Tools for Focused, Compassionate Work",
  description: "Learn what founder productivity tools means, why it matters, and how a small daily practice can turn it into calmer, more reliable progress.",
  keywords: ["founder productivity tools", "founder productivity tools app", "focus", "habit", "clarity"],
};

const faq = [
  {
    "question": "What is the fastest way to start?",
    "answer": "Pick one problem, one small habit, and one daily reminder. Keep the loop small enough that you can repeat it tomorrow."
  },
  {
    "question": "How does this help people stay consistent?",
    "answer": "It reduces the number of decisions needed before action, which makes follow-through easier on busy days."
  },
  {
    "question": "Is this only for founders?",
    "answer": "No. The structure works for anyone who wants fewer distractions and better momentum."
  },
  {
    "question": "What should I measure?",
    "answer": "Count completions, missed days, and the number of times you used the tool instead of delaying the task."
  },
  {
    "question": "Why does calm matter?",
    "answer": "Because sustainable progress usually depends on a mind that is less reactive and more available."
  }
];
const sections = [
  {
    "heading": "What it is",
    "body": "founder productivity tools is a practical way to turn one intent into repeated action. People usually search for it when they want a clearer routine, a calmer mind, or a simpler way to keep moving."
  },
  {
    "heading": "Why it matters",
    "body": "When founder productivity tools is vague, people treat it like inspiration. When it is concrete, it becomes a system that can survive a stressful week."
  },
  {
    "heading": "How to use it",
    "body": "Start with a single trigger, a single action, and a single reward. That tiny structure is enough to build momentum without adding much friction."
  },
  {
    "heading": "Common mistakes",
    "body": "The usual failure mode is trying to make the system clever. The better move is to make it obvious, visible, and easy to restart after a miss."
  },
  {
    "heading": "Where Anicca fits",
    "body": "Anicca can keep the loop alive with gentle nudges, a clear next step, and a reminder that less suffering is a better goal than more output."
  }
];

export default function Page() {
  return (
    <article className="mx-auto max-w-3xl px-6 py-16 text-slate-900">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: "Founder Productivity Tools for Focused, Compassionate Work",
            description: "Learn what founder productivity tools means, why it matters, and how a small daily practice can turn it into calmer, more reliable progress.",
            mainEntityOfPage: "https://aniccaai.com",
          }),
        }}
      />
      <header className="space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-amber-700">Anicca growth note</p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">founder productivity tools</h1>
        <p className="text-lg leading-8 text-slate-700">Learn what founder productivity tools means, why it matters, and how a small daily practice can turn it into calmer, more reliable progress.</p>
      </header>

      <div className="mt-12 space-y-10">
        {sections.map((section) => (
          <section key={section.heading} className="space-y-3">
            <h2 className="text-2xl font-semibold tracking-tight">{section.heading}</h2>
            <p className="leading-8 text-slate-700">{section.body}</p>
          </section>
        ))}
      </div>

      <section className="mt-12 rounded-3xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="text-2xl font-semibold">Try Anicca</h2>
        <p className="mt-2 text-slate-700">
          If you want a calmer way to keep the habit alive, try a small daily nudge instead of another complicated system.
        </p>
        <Link
          className="mt-4 inline-flex rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white"
          href="https://aniccaai.com/?utm_source=seo&utm_medium=page&utm_campaign=growth"
        >
          Open Anicca
        </Link>
      </section>

      <section className="mt-12 space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">FAQ</h2>
        <div className="space-y-4">
          {faq.map((item) => (
            <details key={item.question} className="rounded-2xl border border-slate-200 p-4">
              <summary className="cursor-pointer font-semibold">{item.question}</summary>
              <p className="mt-2 leading-7 text-slate-700">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </article>
  );
}
