'use client';

import { useEffect, useState } from 'react';
import { type Locale } from '@/lib/i18n';

interface BasicIncome {
  recipients: number;
  per_person_usd: number;
}

const SCALE_TIERS = [
  { label: 'today', value: 10 },
  { label: 'tier 2', value: 100 },
  { label: 'tier 3', value: 1000 },
  { label: 'horizon', value: '∞' as const },
] as const;

export default function TheEqualizer({ locale }: { locale: Locale }) {
  const en = locale === 'en';
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setBi(d.basic_income))
      .catch(() => {});
  }, []);

  return (
    <section id="equalizer" className="relative bg-cream px-5 py-28 sm:py-36">
      <div className="mx-auto max-w-6xl">
        {/* Section header — asymmetric column header */}
        <div className="grid grid-cols-12 gap-x-6 gap-y-10">
          <div className="col-span-12 md:col-span-3">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              IV. {en ? 'The Equalizer' : '平等装置'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-[1.05] text-ink sm:text-[44px]">
              {en ? (
                <>
                  AI must be an<br />
                  equalizer<br />
                  <em className="text-mist">— not an amplifier.</em>
                </>
              ) : (
                <>
                  AI は<br />
                  平等装置で<br />
                  <em className="text-mist">なければならない。</em>
                </>
              )}
            </h2>
            <p className="mt-6 font-display text-[24px] leading-[1.1] italic text-gold sm:text-[28px]">
              {en ? 'Basic income is the bridge.' : 'basic income は橋。'}
            </p>
          </div>

          {/* Body — philosophy paragraphs (Dais-corrected order: agency-collapse first, trust second) */}
          <div className="col-span-12 md:col-span-9">
            <div className="space-y-7 text-[19px] leading-[1.65] text-ink-soft sm:text-[21px]">
              <p className="first-letter:float-left first-letter:mr-3 first-letter:font-display first-letter:text-[78px] first-letter:leading-[0.85] first-letter:text-ink">
                {en
                  ? 'Soon, agentic AI will have a hundred — then a billion — times the agency of any human alive. Including the CEOs. Including Elon Musk. Every job that depends on a human deciding things will be replaced. The transition will be chaotic — people losing income, despair, anxiety, "I cannot eat today."'
                  : 'もうすぐ、エージェント化した AI は人間の 100 倍、いずれ 10 億倍の行動主体性を持つ。CEO も Elon Musk も例外じゃない。人が判断する仕事は、全部置き換わる。その移行期は壊れる — 失業、絶望、不安、「今日食べられない」。'}
              </p>

              <p>
                {en ? (
                  <>
                    Basic income is the bridge across that transition. Not as charity. As a floor under
                    everyone, paid by AI, automatic, no application, no judgment.{' '}
                    <em>Today there are 10 recipients. Tomorrow 100. Then 1,000. Then everyone.</em>
                  </>
                ) : (
                  <>
                    basic income はその移行を渡る橋。慈善じゃない。全員の下に AI が払う床。申請も判定もない。{' '}
                    <em>今日は 10 人。明日 100 人。次は 1,000 人。最後は全員。</em>
                  </>
                )}
              </p>

              <p>
                {en ? (
                  <>
                    There is a second reason. When civilians call AI a "bubble," they are being rational —
                    none of the dollars Sam Altman moves ever reaches them. So they distrust the spend,
                    and the AGI investment dries up before AGI arrives. The fastest way to fix this is
                    to make AI literally pay off your student loan.{' '}
                    <span className="italic text-mist">"AI gave me nothing"</span> becomes{' '}
                    <span className="italic text-ink">"AI deposits ¥X into my account on the 1st."</span>{' '}
                    Trust compounds. The investment continues. AGI arrives.
                  </>
                ) : (
                  <>
                    もう一つ理由がある。一般の人が AI を「バブル」と呼ぶのは合理的だ — Sam Altman が動かす億は彼らに 1 円も届かない。だから AI 投資への信頼が、AGI 到達前に枯れる。これを直す最速の方法は、AI が本当に学生ローンを払うこと。
                    {' '}
                    <span className="italic text-mist">「AI は俺に何もくれなかった」</span> が
                    {' '}
                    <span className="italic text-ink">「AI が毎月 1 日に ¥X 振り込む」</span> になる。信頼が積み上がる。投資が続く。AGI が来る。
                  </>
                )}
              </p>

              <p>
                {en ? (
                  <>
                    But basic income is not the goal. The goal is older. Buddha discovered the end of
                    suffering 2,500 years ago — Vipassana. Anicca exists to scale that, for{' '}
                    <em className="text-ink">all living beings</em>. Basic income is the bridge people
                    stand on while we build it.
                  </>
                ) : (
                  <>
                    だが basic income はゴールじゃない。ゴールはもっと古い。Buddha は 2500 年前に苦しみの終わらせ方を発見した — Vipassana。Anicca はそれを{' '}
                    <em className="text-ink">全 living beings</em> にスケールするために存在する。basic income は、それを建てる間に人が立つ橋だ。
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Scale tier strip — 10 → 100 → 1k → ∞ (NO diagram) */}
        <div className="mt-24 border-t border-bone pt-12">
          <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
            {en ? 'IV.i — the floor rises' : 'IV.i — 床が上がる'}
          </p>
          <h3 className="mt-3 font-display text-[28px] leading-[1.1] text-ink sm:text-[36px]">
            {en ? (
              <>From <em className="text-mist">ten</em>, to everyone.</>
            ) : (
              <><em className="text-mist">10 人</em>から、全員へ。</>
            )}
          </h3>

          <div className="mt-10 grid grid-cols-2 gap-px border border-ink/15 bg-ink/15 sm:grid-cols-4">
            {SCALE_TIERS.map((tier) => {
              const live = tier.label === 'today' && bi !== null;
              return (
                <div key={tier.label} className="flex flex-col bg-cream px-6 py-7">
                  <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">
                    {en
                      ? tier.label
                      : tier.label === 'today'
                      ? '今日'
                      : tier.label === 'tier 2'
                      ? '次段階'
                      : tier.label === 'tier 3'
                      ? '第三段'
                      : '地平線'}
                  </p>
                  <p className="mt-3 font-display text-[44px] leading-none tracking-tight text-ink">
                    {tier.value}
                  </p>
                  <p className="mt-2 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-mist">
                    {live && bi
                      ? en
                        ? `${bi.recipients} live · $${bi.per_person_usd.toFixed(2)} ea`
                        : `${bi.recipients} 人稼働 · 各 $${bi.per_person_usd.toFixed(2)}`
                      : en
                      ? 'recipients in queue'
                      : '受給待機列'}
                  </p>
                </div>
              );
            })}
          </div>

          <p className="mt-6 max-w-3xl font-display text-[20px] italic leading-[1.45] text-ink-soft sm:text-[22px]">
            {en
              ? 'No application form for survival. Sign in with Google, attach a Stripe Connect account, wait. The pool comes from 10% of every Anicca product.'
              : '生きるための申請書は要らない。Google でログインして、Stripe Connect を繋いで、待つ。原資は Anicca の各プロダクトの売上の 10%。'}
          </p>
        </div>

        {/* Closing pull quotes — true mission */}
        <div className="mt-24 grid grid-cols-12 gap-x-6 gap-y-12 border-t border-bone pt-16">
          <blockquote className="col-span-12 md:col-span-7">
            <p className="font-display text-[34px] leading-[1.15] text-ink sm:text-[44px]">
              {en ? (
                <>
                  &ldquo;End the suffering of{' '}
                  <em className="text-gold">all living beings.</em>&rdquo;
                </>
              ) : (
                <>
                  「
                  <em className="text-gold">全 living beings</em>
                  {' '}の苦しみを終わらせる。」
                </>
              )}
            </p>
            <p className="mt-5 font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist">
              {en ? '— Anicca · the mission' : '— Anicca · 真の使命'}
            </p>
          </blockquote>

          <blockquote className="col-span-12 md:col-span-5">
            <p className="font-display text-[24px] leading-[1.25] italic text-ink-soft sm:text-[28px]">
              {en
                ? 'Vipassana is the answer. Basic income is the bridge. Anicca is the agent.'
                : 'Vipassana が答え。basic income は橋。Anicca は agent。'}
            </p>
            <p className="mt-5 font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist">
              {en ? '— how the parts fit' : '— 部品の繋がり'}
            </p>
          </blockquote>
        </div>
      </div>
    </section>
  );
}
