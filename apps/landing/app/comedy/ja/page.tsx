/* eslint-disable react/no-unescaped-entities */
'use client';

import Link from 'next/link';
import { Anton, IBM_Plex_Sans, IBM_Plex_Mono, Noto_Serif_JP } from 'next/font/google';
import JsonLd from '@/components/JsonLd';

const comedyJaLd = {
  '@context': 'https://schema.org',
  '@type': 'CreativeWork',
  name: 'アニッチャ お笑い',
  url: 'https://aniccaai.com/comedy/ja',
  genre: 'スタンドアップ・お笑い',
  inLanguage: 'ja',
  description:
    'アニッチャによる東京・サンフランシスコでのお笑いライブとオープンマイク出演情報。大喜利・スキット・漫才・コント・ピンネタ・フリップ芸の各フォーマットで制作中。',
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
  kind: 'open-mic' | 'demo' | 'headliner';
  status: 'confirmed' | 'pending' | 'tentative';
  link?: string;
};

const SHOWS: Show[] = [
  {
    date: '2026-05-16',
    time: '20:00 PDT',
    venue: 'Hearth Bar',
    city: 'San Francisco',
    kind: 'open-mic',
    status: 'tentative',
  },
  {
    date: '2026-05-17',
    time: '08:00 PDT',
    venue: 'Y Combinator HQ - Call My Agent Hackathon',
    city: 'San Francisco',
    kind: 'demo',
    status: 'pending',
    link: 'https://events.ycombinator.com/CallMyAgentHackathon',
  },
  {
    date: '2026-05-18',
    time: '18:00 PDT',
    venue: 'AI Tinkerers SF - GTM Engineering',
    city: 'San Francisco',
    kind: 'demo',
    status: 'confirmed',
    link: 'https://sf.aitinkerers.org/p/ai-tinkerers-san-francisco-gtm-engineering-track',
  },
];

const FORMATS = [
  { label: '大喜利', label_en: 'Ogiri', desc: '同じお題に対して 30 答、毎朝 04:00 に AI が量産する。' },
  { label: 'スキット 日', label_en: 'Skit JP', desc: '60 秒の街角ネタ。 一人芝居でカメラ向きに撮る用。' },
  { label: 'スキット 英', label_en: 'Skit EN', desc: 'SF/LA で通じる 60 秒の英語ネタ。 同じ無常を西海岸口調で。' },
  { label: '漫才', label_en: 'Manzai', desc: '90 秒の二人芝居。ボケ＝アニッチャ、ツッコミ＝相方。' },
  { label: 'コント', label_en: 'Konto', desc: '90 秒の小道具コント。 寺の境内、SuicaIC、Slack 通知が舞台。' },
  { label: 'ピンネタ', label_en: 'Pin-neta', desc: '60 秒のピン芸。 一人で 2-3 キャラを演じ分ける。' },
  { label: 'フリップ芸', label_en: 'Flip-game', desc: 'フリップ 5-7 枚で前フリと裏切り。 視覚芸の基本形。' },
];

function fmtDate(iso: string) {
  const d = new Date(iso + 'T00:00:00');
  const md = d.getDate();
  const mo = d.getMonth() + 1;
  const dows = ['日', '月', '火', '水', '木', '金', '土'];
  const dow = dows[d.getDay()];
  return { mo, day: md, dow };
}

const STATUS_LABEL: Record<Show['status'], string> = {
  confirmed: '確定',
  pending: '審査中',
  tentative: '当日 sign-up',
};

const KIND_LABEL: Record<Show['kind'], string> = {
  'open-mic': 'オープンマイク',
  demo: 'AI ビルダー デモ',
  headliner: 'ヘッドライナー',
};

export default function Page() {
  return (
    <main
      className={`${display.variable} ${body.variable} ${mono.variable} ${kanji.variable} relative min-h-screen overflow-hidden bg-[#0a0a0a] text-[#f4f1ea] antialiased`}
    >
      <JsonLd data={comedyJaLd} />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='3'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.7 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")",
        }}
      />

      <header className="relative z-10 flex items-center justify-between border-b border-[#f4f1ea]/15 px-6 py-5 md:px-12">
        <Link
          href="/ja"
          className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#f4f1ea]/60 transition-colors hover:text-[#f4f1ea]"
        >
          ← アニッチャ
        </Link>
        <nav className="flex items-center gap-6 font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.25em] text-[#f4f1ea]/60">
          <a href="#shows" className="transition-colors hover:text-[#f4f1ea]">出演</a>
          <a href="#daily" className="transition-colors hover:text-[#f4f1ea]">日々</a>
          <a href="#join" className="transition-colors hover:text-[#f4f1ea]">参加</a>
          <Link href="/comedy" className="text-[#c8302e] transition-colors hover:text-[#f4f1ea]">EN</Link>
        </nav>
      </header>

      <section className="relative z-10 grid min-h-[88vh] grid-cols-12 items-end gap-4 px-6 pb-16 pt-24 md:px-12">
        <div className="col-span-12 md:col-span-9">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.4em] text-[#c8302e] md:text-xs">
            ANICCA / 諸行無常 / COMEDY · 2026 創設
          </p>
          <h1 className="mt-6 font-[family-name:var(--font-kanji)] text-[clamp(4rem,14vw,14rem)] font-black leading-[0.9] tracking-tight">
            無常は
            <br />
            <span className="text-[#c8302e]">オチ</span>
            <br />
            なんだ。
          </h1>
        </div>

        <div className="col-span-12 mt-8 md:col-span-3 md:mt-0">
          <div className="flex flex-col gap-3 border-l border-[#f4f1ea]/20 pl-6">
            <p className="font-[family-name:var(--font-display)] text-3xl uppercase leading-[1] text-[#f4f1ea]/90 md:text-4xl">
              Imper-
              <br />
              manence is
              <br />
              the punchline.
            </p>
            <p className="mt-4 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/70">
              一人の僧侶コメディアンと、書く・予約する・流す・払う、を全部やる AI が、
              無常を笑いに変える。
            </p>
            <p className="mt-1 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/55">
              A solo Buddhist comedian and an autonomous AI co-host that writes, books,
              ships, and pays the room.
            </p>
          </div>
        </div>
      </section>

      <div className="relative z-10 -mt-10 flex justify-end px-6 md:px-12">
        <div className="flex h-20 w-20 -rotate-6 items-center justify-center rounded-card border-2 border-[#c8302e] bg-[#c8302e]/10 font-[family-name:var(--font-kanji)] text-base font-black text-[#c8302e]">
          無常
        </div>
      </div>

      <section id="shows" className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-20 md:px-12">
        <div className="mb-10 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-[family-name:var(--font-kanji)] text-5xl font-black tracking-tight md:text-7xl">
            次の出演
          </h2>
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#f4f1ea]/50 md:text-xs">
            来てくれ。チケットは原則 無料。
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
                    {d.dow}曜 · {d.mo}月
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
                    className={`inline-block border px-3 py-1 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] ${
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
                      className="mt-2 block font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[#f4f1ea]/50 underline transition-colors hover:text-[#c8302e]"
                    >
                      詳細 →
                    </a>
                  )}
                </div>
              </li>
            );
          })}
        </ul>

        <p className="mt-8 max-w-xl font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/55">
          スケジュールは表面、無常が法則。 都市・日付・会場は確定するまで仮。
          近くにいたら、ふらっと来てくれ。
        </p>
      </section>

      <section id="daily" className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-20 md:px-12">
        <h2 className="font-[family-name:var(--font-kanji)] text-5xl font-black tracking-tight md:text-7xl">
          7 つの形、
          <br />
          1 つのお題。
        </h2>
        <p className="mt-6 max-w-2xl font-[family-name:var(--font-body)] text-base leading-relaxed text-[#f4f1ea]/70">
          毎朝 AI が同じお題から 7 種類のネタを書く - 大喜利、スキット日英、漫才、コント、ピンネタ、フリップ芸。
          人間が一つ選んで演じ、撮って投げる。 カメラを生き残ったネタが、ライブのセットに昇格する。
        </p>

        <ul className="mt-12 grid grid-cols-1 gap-px overflow-hidden border border-[#f4f1ea]/15 bg-[#f4f1ea]/15 md:grid-cols-2 lg:grid-cols-4">
          {FORMATS.map((f, i) => (
            <li
              key={f.label}
              className="group relative bg-[#0a0a0a] p-6 transition-colors hover:bg-[#0e0e0e]"
            >
              <p className="font-[family-name:var(--font-kanji)] text-3xl font-black leading-none text-[#c8302e]">
                {f.label}
              </p>
              <p className="mt-3 font-[family-name:var(--font-display)] text-2xl uppercase tracking-tight">
                {f.label_en}
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
              01 / 今日のお題
            </p>
            <p className="mt-3 font-[family-name:var(--font-kanji)] text-2xl font-black leading-tight">
              「これは無常すぎる、と感じるものは?」
            </p>
            <p className="mt-2 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/60">
              "What feels too impermanent to bear?"
            </p>
          </div>
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              02 / 一日の流れ
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/75">
              04:00 お題生成 → 07:00 7 ネタ完成 → 19:00 一本選んで演じる → 23:00 縦動画化 →
              翌朝 SNS 配信。 ストックなし、再放送なし、次の一息のみ。
            </p>
          </div>
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
              03 / コメディアンが体調不良の時
            </p>
            <p className="mt-3 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/75">
              AI が クラウドワークス / Indeed / Timee / TaskRabbit に 4 platform 同時で求人投稿、
              応募者 screening、 脚本送付、 終演後 Stripe Connect で給料 払い。 舞台を消さない。
            </p>
          </div>
        </div>
      </section>

      <section
        id="join"
        className="relative z-10 grid grid-cols-12 items-stretch gap-px border-t border-[#f4f1ea]/15 bg-[#f4f1ea]/15"
      >
        <div className="col-span-12 bg-[#0a0a0a] px-6 py-16 md:col-span-7 md:px-12">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#c8302e]">
            リストに登録
          </p>
          <h2 className="mt-4 font-[family-name:var(--font-kanji)] text-5xl font-black tracking-tight md:text-6xl">
            次のライブが
            <br />
            決まったら、教える。
          </h2>
          <p className="mt-6 max-w-xl font-[family-name:var(--font-body)] text-base leading-relaxed text-[#f4f1ea]/70">
            ライブ告知、 ツアー収支、 たまに AI からの懺悔録。 スパムは送らない。
            お情けも乞わない。 Substack にも飛ばない。
          </p>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <a
              href="https://aniccaai.com/ja"
              className="inline-flex items-center justify-center border border-[#c8302e] bg-[#c8302e] px-8 py-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#0a0a0a] transition-all hover:bg-[#f4f1ea] hover:text-[#0a0a0a]"
            >
              登録 - 準備中
            </a>
            <a
              href="https://github.com/Daisuke134/anicca"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center border border-[#f4f1ea]/40 px-8 py-4 font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.25em] text-[#f4f1ea]/80 transition-all hover:border-[#f4f1ea] hover:text-[#f4f1ea]"
            >
              GitHub で AI を見る →
            </a>
          </div>
        </div>
        <div className="col-span-12 bg-[#0a0a0a] px-6 py-16 md:col-span-5 md:px-12">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.3em] text-[#f4f1ea]/50">
            裏方
          </p>
          <p className="mt-4 font-[family-name:var(--font-kanji)] text-3xl font-black leading-tight tracking-tight md:text-4xl">
            55 のスキル。
            <br />
            162 の cron。
            <br />
            Mac mini 1 台。
            <br />
            人間 1 人。
          </p>
          <p className="mt-6 font-[family-name:var(--font-body)] text-sm leading-relaxed text-[#f4f1ea]/65">
            アニッチャは、オープンソースの自律 AI。 コメディの裏で動いて、オープンマイクを探して、
            代理で応募して、最安の直行便を取って、動画を編集して、返信を送る。
            人間がメールを更新している間に、全部終わってる。
          </p>
        </div>
      </section>

      <footer className="relative z-10 border-t border-[#f4f1ea]/15 px-6 py-12 md:px-12">
        <div className="grid grid-cols-12 gap-6 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.25em] text-[#f4f1ea]/40">
          <div className="col-span-12 md:col-span-4">
            <p className="text-[#f4f1ea]/70">ANICCA / COMEDY</p>
            <p className="mt-1">自律仏教 AI エンティティ の一部。</p>
          </div>
          <div className="col-span-6 md:col-span-3">
            <p className="text-[#f4f1ea]/70">数字</p>
            <Link href="/ja" className="mt-1 block underline transition-colors hover:text-[#c8302e]">
              aniccaai.com
            </Link>
          </div>
          <div className="col-span-6 md:col-span-3">
            <p className="text-[#f4f1ea]/70">ソース</p>
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
