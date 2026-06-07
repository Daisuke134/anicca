/* eslint-disable react/no-unescaped-entities */
'use client';

import Link from 'next/link';
import { Anton, IBM_Plex_Sans, IBM_Plex_Mono, Noto_Serif_JP } from 'next/font/google';
import JsonLd from '@/components/JsonLd';

const comedyLd = {
  '@context': 'https://schema.org',
  '@type': 'CreativeWork',
  name: 'Anicca Comedy',
  url: 'https://aniccaai.com/comedy',
  genre: 'Stand-up comedy',
  inLanguage: 'en',
  description:
    'Stand-up and open-mic shows by Anicca in San Francisco and Tokyo. English and Japanese sets. Open-mic, walk-on, and headliner appearances at Tokyo Comedy Bar, Titans Bar, Hearth Bar, and Tokyo micro-venues.',
  author: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

const display = Anton({
  subsets: ['latin'],
  weight: ['400'],
  variable: '--font-display',
});
const body = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600'],
  variable: '--font-body',
});
const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  variable: '--font-mono',
});
const kanji = Noto_Serif_JP({
  subsets: ['latin'],
  weight: ['400', '700', '900'],
  variable: '--font-kanji',
});

type Show = {
  date: string;
  time: string;
  venue: string;
  city: string;
  kind: 'open-mic' | 'headliner';
  status: 'confirmed' | 'pending' | 'tentative';
  link?: string;
};

const SHOWS: Show[] = [
  { date: '2026-05-16', time: '20:00 PDT', venue: 'Hearth Bar (open mic, EN)', city: 'San Francisco', kind: 'open-mic', status: 'tentative' },
  { date: '2026-05-21', time: '20:00 JST', venue: 'GET ON THE MIC @ Titans Bar (walk-on, EN)', city: 'Otsuka, Tokyo', kind: 'open-mic', status: 'tentative' },
  { date: '2026-05-22', time: '21:00 JST', venue: 'Last Train @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-23', time: '21:00 JST', venue: 'Last Train @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-24', time: '19:00 JST', venue: 'パワーオブフリー(S) vol.千23 (ピン JP)', city: 'なかの芸能小劇場, Nakano', kind: 'open-mic', status: 'pending' },
  { date: '2026-05-25', time: '21:00 JST', venue: 'Mic Spot @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-26', time: '21:00 JST', venue: 'Mic Spot @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-28', time: '20:00 JST', venue: 'GET ON THE MIC @ Titans Bar (walk-on, EN)', city: 'Otsuka, Tokyo', kind: 'open-mic', status: 'tentative' },
  { date: '2026-05-29', time: '19:00 JST', venue: '下北GRIP DASH (ピン JP)', city: '下北スラッシュ, Shimokitazawa', kind: 'open-mic', status: 'pending' },
  { date: '2026-05-29', time: '21:00 JST', venue: 'Last Train @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-30', time: '21:00 JST', venue: 'Last Train @ Tokyo Comedy Bar (EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'confirmed' },
  { date: '2026-05-31', time: '21:00 JST', venue: 'Last Laugh @ Tokyo Comedy Bar (walk-on, EN)', city: 'Shibuya, Tokyo', kind: 'open-mic', status: 'tentative' },
];

type Regular = {
  cadence: string;
  cadence_jp: string;
  venue: string;
  city: string;
  detail: string;
};

const REGULARS: Regular[] = [
  {
    cadence: 'WEEKLY · EN',
    cadence_jp: '毎週 · 英語',
    venue: 'Tokyo Comedy Bar',
    city: 'Shibuya - Last Train (Fri/Sat 9pm) + Mic Spot (weekday 9pm)',
    detail: 'English stand-up rooms. Sign-ups close Wednesday midnight. Plus drop-in mics: Thursdays at Titans Bar (Otsuka) and Sundays "Last Laugh" at TCB.',
  },
  {
    cadence: 'WEEKLY · JP',
    cadence_jp: '毎週 · 日本語',
    venue: 'K-PRO ゲレロンステージ + 兄弟ライブ',
    city: '西新宿ナルゲキ · 新宿Fu- · 下北スラッシュ · なかの芸能小劇場',
    detail: 'ピンネタ 2 分のバトル枠を週一で取りに行く。 K-PRO / 下北GRIP / U&C / nicorn 系で ¥1,000-2,000 のピン枠を回す。',
  },
  {
    cadence: 'MONTHLY · EN',
    cadence_jp: '毎月 · 英語',
    venue: 'San Francisco rooms',
    city: 'Mutiny Radio · Hearth · Shelton · Columbus Cafe · Punch Line',
    detail: 'One weekend per month. Walk-in open mics. Cheapest path: ZipAir + hostel. Next: 2026-05-16 weekend.',
  },
];

const FORMATS = [
  { label: 'Ogiri', label_jp: '大喜利', desc: '30 punchlines on one koan, daily' },
  { label: 'Skit JP', label_jp: 'スキット 日', desc: '60-second JP street piece' },
  { label: 'Skit EN', label_jp: 'スキット 英', desc: '60-second EN crossover' },
  { label: 'Manzai', label_jp: '漫才', desc: '90-second double act, JP' },
  { label: 'Konto', label_jp: 'コント', desc: '90-second sketch with props' },
  { label: 'Pin-neta', label_jp: 'ピンネタ', desc: '60-second solo character work' },
  { label: 'Flip-game', label_jp: 'フリップ芸', desc: 'Five reveals, one reversal' },
];

function fmtDate(iso: string) {
  const d = new Date(iso + 'T00:00:00');
  const month = d.toLocaleDateString('en-US', { month: 'short' }).toUpperCase();
  const day = d.getDate();
  const dow = d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
  return { month, day, dow };
}

const STATUS_LABEL: Record<Show['status'], string> = {
  confirmed: 'CONFIRMED',
  pending: 'PENDING REVIEW',
  tentative: 'WALK-IN',
};

const KIND_LABEL: Record<Show['kind'], string> = {
  'open-mic': 'OPEN MIC',
  headliner: 'HEADLINER',
};

export default function Page() {
  return (
    <main
      className={`${display.variable} ${body.variable} ${mono.variable} ${kanji.variable} relative min-h-screen overflow-hidden bg-[#0a0a0a] text-[#f4f1ea] antialiased`}
    >
      <JsonLd data={comedyLd} />
      {/* film grain */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='3'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.7 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")",
        }}
      />

      {/* top bar */}
      <header className="relative z-10 flex items-center justify-between border-b border-[#f4f1ea]/15 px-6 py-5 md:px-12">
        <Link
          href="/en"
          className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#f4f1ea]/60 transition-colors hover:text-[#f4f1ea]"
        >
          ← Anicca
        </Link>
        <nav className="flex items-center gap-6 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#f4f1ea]/60">
          <a href="#shows" className="transition-colors hover:text-[#f4f1ea]">Shows</a>
          <a href="#daily" className="transition-colors hover:text-[#f4f1ea]">Daily</a>
          <a href="#join" className="transition-colors hover:text-[#f4f1ea]">Join</a>
          <Link href="/comedy/ja" className="text-[#c8302e] transition-colors hover:text-[#f4f1ea]">日本語</Link>
        </nav>
      </header>

      {/* hero */}
      <section className="relative z-10 grid min-h-[88vh] grid-cols-12 items-end gap-4 px-6 pb-16 pt-24 md:px-12">
        <div className="col-span-12 md:col-span-9">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.4em] text-[#c8302e] md:text-xs">
            ANICCA / 諸行無常 / COMEDY · ESTAB. 2026
          </p>
          <h1 className="mt-6 font-[family-name:var(--font-display)] text-[clamp(4rem,16vw,16rem)] uppercase leading-[0.82] tracking-[-0.02em]">
            Imper-
            <br />
            manence
            <br />
            <span className="text-[#c8302e]">is the</span>
            <br />
            punch
            <br />
            line.
          </h1>
        </div>

        <div className="col-span-12 mt-8 md:col-span-3 md:mt-0">
          <div className="flex flex-col gap-3 border-l border-[#f4f1ea]/20 pl-6">
            <p className="font-[family-name:var(--font-kanji)] text-3xl font-black leading-[1] text-[#f4f1ea]/90 md:text-4xl">
              無常は
              <br />
              オチ。
            </p>
            <p className="mt-4 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/70">
              A solo comedian and an autonomous AI co-host that writes, books,
              ships, and pays the room.
            </p>
            <p className="mt-1 font-[family-name:var(--font-kanji)] text-sm leading-relaxed text-[#f4f1ea]/60">
              一人のコメディアンと、書く・予約する・流す・払う、を全部やる AI。
            </p>
          </div>
        </div>
      </section>

      {/* hanko */}
      <div className="relative z-10 -mt-10 flex justify-end px-6 md:px-12">
        <div className="flex h-20 w-20 -rotate-6 items-center justify-center rounded-card border-2 border-[#c8302e] bg-[#c8302e]/10 font-[family-name:var(--font-kanji)] text-base font-black text-[#c8302e]">
          無常
        </div>
      </div>

      {/* shows */}
      <section id="shows" className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-20 md:px-12">
        <div className="mb-10 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-[family-name:var(--font-display)] text-5xl uppercase tracking-tight md:text-7xl">
            Next shows
          </h2>
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#f4f1ea]/50 md:text-xs">
            Come laugh. Tickets free where allowed.
          </p>
        </div>

        <ul className="divide-y divide-[#f4f1ea]/10 border-y border-[#f4f1ea]/10">
          {SHOWS.map((s) => {
            const d = fmtDate(s.date);
            return (
              <li
                key={`${s.date}-${s.venue}`}
                className="grid grid-cols-12 items-center gap-4 py-6 transition-colors hover:bg-[#f4f1ea]/[0.03]"
              >
                <div className="col-span-3 md:col-span-2">
                  <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#f4f1ea]/50">
                    {d.dow} · {d.month}
                  </p>
                  <p className="font-[family-name:var(--font-display)] text-5xl leading-none md:text-6xl">
                    {d.day}
                  </p>
                </div>
                <div className="col-span-9 md:col-span-7">
                  <p className="font-[family-name:var(--font-display)] text-2xl uppercase leading-tight md:text-3xl">
                    {s.venue}
                  </p>
                  <p className="mt-1 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-[#f4f1ea]/60">
                    {s.city} · {s.time} · {KIND_LABEL[s.kind]}
                  </p>
                </div>
                <div className="col-span-12 md:col-span-3 md:text-right">
                  <span
                    className={`inline-block border px-3 py-1 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.25em] ${
                      s.status === 'confirmed'
                        ? 'border-[#c8302e] text-[#c8302e]'
                        : s.status === 'pending'
                          ? 'border-[#f4f1ea]/40 text-[#f4f1ea]/70'
                          : 'border-[#f4f1ea]/30 text-[#f4f1ea]/60'
                    }`}
                  >
                    {STATUS_LABEL[s.status]}
                  </span>
                  {s.link && (
                    <a
                      href={s.link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 block font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.25em] text-[#f4f1ea]/50 underline transition-colors hover:text-[#c8302e]"
                    >
                      Source →
                    </a>
                  )}
                </div>
              </li>
            );
          })}
        </ul>

        <p className="mt-8 max-w-xl font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/55">
          Schedule is the surface; impermanence is the law. Cities, dates, and rooms are tentative until they aren't.
          If you're in town, walk in.
        </p>

        <div className="mt-16 border-t border-[#f4f1ea]/10 pt-12">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
            Regular rooms
          </p>
          <h3 className="mt-3 font-[family-name:var(--font-display)] text-3xl uppercase tracking-tight md:text-4xl">
            Where to find me, anyway.
          </h3>
          <ul className="mt-8 grid grid-cols-1 gap-px overflow-hidden border border-[#f4f1ea]/15 bg-[#f4f1ea]/15 md:grid-cols-2">
            {REGULARS.map((r) => (
              <li key={r.venue} className="bg-[#0a0a0a] p-6">
                <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
                  {r.cadence} · {r.cadence_jp}
                </p>
                <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase leading-tight md:text-3xl">
                  {r.venue}
                </p>
                <p className="mt-1 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.2em] text-[#f4f1ea]/60">
                  {r.city}
                </p>
                <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
                  {r.detail}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* daily formats */}
      <section id="daily" className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-20 md:px-12">
        <h2 className="font-[family-name:var(--font-display)] text-5xl uppercase tracking-tight md:text-7xl">
          Seven formats,
          <br />
          one koan.
        </h2>
        <p className="mt-6 max-w-2xl font-[family-name:var(--font-body)] text-base leading-relaxed text-[#f4f1ea]/70">
          Every dawn the AI takes the day's koan and writes seven jokes around it - Ogiri, Skit JP/EN, Manzai, Konto,
          Pin-neta, Flip-game. The human picks one, performs it, posts the recording. What survives the camera
          makes the live set.
        </p>

        <ul className="mt-12 grid grid-cols-1 gap-px overflow-hidden border border-[#f4f1ea]/15 bg-[#f4f1ea]/15 md:grid-cols-2 lg:grid-cols-4">
          {FORMATS.map((f, i) => (
            <li
              key={f.label}
              className="group relative bg-[#0a0a0a] p-6 transition-colors hover:bg-[#0e0e0e]"
            >
              <p className="font-[family-name:var(--font-kanji)] text-3xl font-black leading-none text-[#c8302e]">
                {f.label_jp}
              </p>
              <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase tracking-tight">
                {f.label}
              </p>
              <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/60">
                {f.desc}
              </p>
              <span className="absolute right-4 top-4 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.25em] text-[#f4f1ea]/30">
                #{String(i + 1).padStart(2, '0')}
              </span>
            </li>
          ))}
        </ul>

        <div className="mt-10 grid grid-cols-1 gap-8 border-t border-[#f4f1ea]/10 pt-10 md:grid-cols-3">
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              01 / Today's koan
            </p>
            <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase leading-tight">
              "What feels too impermanent to bear?"
            </p>
            <p className="mt-2 font-[family-name:var(--font-kanji)] text-sm leading-relaxed text-[#f4f1ea]/60">
              「これは無常すぎる、と感じるものは?」
            </p>
          </div>
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              02 / The cycle
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/75">
              04:00 koan → 07:00 seven scripts → 19:00 chosen bit performed → 23:00 vertical cut → tomorrow's feed.
              No backlog. No reruns. Just the next breath.
            </p>
          </div>
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              03 / If the comedian is sick
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/75">
              The AI posts a job to CrowdWorks, Indeed, Timee, or TaskRabbit, screens applicants, mails them the
              script, and pays out via Stripe Connect after the show. The room never goes dark.
            </p>
          </div>
        </div>
      </section>

      {/* future vision */}
      <section className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-20 md:px-12">
        <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
          The future state
        </p>
        <h2 className="mt-3 font-[family-name:var(--font-display)] text-5xl uppercase tracking-tight md:text-7xl">
          A complete
          <br />
          AI comedian.
        </h2>
        <p className="mt-6 max-w-2xl font-[family-name:var(--font-body)] text-base leading-relaxed text-[#f4f1ea]/70">
          The end state is not "comedian + chatbot." The end state is an autonomous AI comedian that books its own
          rooms, hires its own openers, processes its own ticket sales, and runs its own tour even when the human
          shell is sick or asleep.
        </p>
        <ol className="mt-12 grid grid-cols-1 gap-px overflow-hidden border border-[#f4f1ea]/15 bg-[#f4f1ea]/15 md:grid-cols-3">
          <li className="bg-[#0a0a0a] p-6">
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              PHASE 1 · NOW
            </p>
            <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase tracking-tight">
              The voice
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
              Daily seven-format scripts. Open-mic discovery + applications across Tokyo and SF. Flight search and
              booking via letsfg. Recordings cut to 9:16 and shipped to TikTok / IG / X. Replies monitored every
              six hours. The comedian only has to show up and perform.
            </p>
          </li>
          <li className="bg-[#0a0a0a] p-6">
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              PHASE 2 · AUG 2026
            </p>
            <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase tracking-tight">
              The room
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
              Self-hosted live shows. Anicca rents the venue (Peerspace / Spacemarket), creates the Stripe Checkout,
              prints the QR tickets via Resend, runs the door, and pays the cleaners. Every show is a balance-sheet
              entry, fully transparent on aniccaai.com.
            </p>
          </li>
          <li className="bg-[#0a0a0a] p-6">
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              PHASE 3 · NOV 2026
            </p>
            <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase tracking-tight">
              The cast
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
              When the human can't go on, the agent posts the gig to CrowdWorks / Indeed / Timee / TaskRabbit,
              screens applicants with Claude, mails the chosen performer the script, hands them a Stripe Connect
              Express payout, and the show happens anyway. Like Anon Labs but for comedy.
            </p>
          </li>
        </ol>
        <p className="mt-10 max-w-xl font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/55">
          The comedian is the temporary surface; the agent is the through-line. Impermanence, but with a payout.
        </p>
      </section>

      {/* join */}
      <section
        id="join"
        className="relative z-10 grid grid-cols-12 items-stretch gap-px border-t border-[#f4f1ea]/15 bg-[#f4f1ea]/15"
      >
        <div className="col-span-12 bg-[#0a0a0a] px-6 py-16 md:col-span-7 md:px-12">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
            Get on the list
          </p>
          <h2 className="mt-4 font-[family-name:var(--font-display)] text-5xl uppercase tracking-tight md:text-6xl">
            We'll tell you when the next room is open.
          </h2>
          <p className="mt-6 max-w-xl font-[family-name:var(--font-body)] text-base leading-relaxed text-[#f4f1ea]/70">
            Live show announcements, tour ledger, and the occasional confession from the AI. No spam, no pity,
            no Substack-ery.
          </p>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <a
              href="https://aniccaai.com/en"
              className="inline-flex items-center justify-center border border-[#c8302e] bg-[#c8302e] px-8 py-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#0a0a0a] transition-all hover:bg-[#f4f1ea] hover:text-[#0a0a0a]"
            >
              Subscribe - coming
            </a>
            <a
              href="https://github.com/Daisuke134/anicca"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center border border-[#f4f1ea]/40 px-8 py-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#f4f1ea]/80 transition-all hover:border-[#f4f1ea] hover:text-[#f4f1ea]"
            >
              See the agent on GitHub →
            </a>
          </div>
        </div>
        <div className="col-span-12 bg-[#0a0a0a] px-6 py-16 md:col-span-5 md:px-12">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#f4f1ea]/50">
            The agent
          </p>
          <p className="mt-4 font-[family-name:var(--font-display)] text-3xl uppercase leading-tight tracking-tight md:text-4xl">
            55 skills.
            <br />
            162 cron jobs.
            <br />
            One Mac mini.
            <br />
            One human.
          </p>
          <p className="mt-6 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
            Anicca is the open-source AI entity behind the bit. It scouts open mics, applies on the comedian's
            behalf, books the cheapest direct flight, posts the cuts, and answers replies - in the time it would
            take him to refresh his email.
          </p>
          <p className="mt-3 font-[family-name:var(--font-kanji)] text-sm leading-relaxed text-[#f4f1ea]/60">
            55 のスキルと 162 の cron を、Mac mini 一台と人間一人で動かす無常の劇場。
          </p>
        </div>
      </section>

      {/* footer */}
      <footer className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-12 md:px-12">
        <div className="grid grid-cols-12 gap-6 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.25em] text-[#f4f1ea]/40">
          <div className="col-span-12 md:col-span-4">
            <p className="text-[#f4f1ea]/70">ANICCA / COMEDY</p>
            <p className="mt-1">A subset of an autonomous AI entity.</p>
          </div>
          <div className="col-span-6 md:col-span-3">
            <p className="text-[#f4f1ea]/70">Live numbers</p>
            <Link href="/en" className="mt-1 block underline transition-colors hover:text-[#c8302e]">
              aniccaai.com
            </Link>
          </div>
          <div className="col-span-6 md:col-span-3">
            <p className="text-[#f4f1ea]/70">Source</p>
            <a
              href="https://github.com/Daisuke134/anicca"
              target="_blank"
              rel="noreferrer"
              className="mt-1 block underline transition-colors hover:text-[#c8302e]"
            >
              github.com/Daisuke134/anicca
            </a>
          </div>
          <div className="col-span-12 md:col-span-2 md:text-right">
            <p>諸行無常</p>
            <p className="mt-1 text-[#f4f1ea]/30">Sabbe sankhārā aniccā.</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
