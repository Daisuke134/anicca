'use client';

// TODO(§11.F-followup): migrate hardcoded inline EN/JA strings into translations.theEqualizer.*
// during the i18n consolidation sweep. Inline ternaries kept here to avoid
// touching i18n.ts cross-section during the per-section redesign.

import { useEffect, useState } from 'react';
import { type Locale } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';

interface BasicIncome {
  recipients: number;
  per_person_usd: number;
}

// §4.7: layout family = full-width editorial manifesto + stat-strip.
// TheSpend (before) = featured card-grid; TheEmpireProducts (after) = editorial ledger list.
// Full-width single-column breaks the zigzag chain and differs from both neighbours.
const SCALE_TIERS = [
  { label: 'today', value: 10 },
  { label: 'tier 2', value: 100 },
  { label: 'tier 3', value: 1000 },
  { label: 'horizon', value: '∞' },
] as const;

export default function TheEqualizer({ locale }: { locale: Locale }) {
  const en = locale === 'en';
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then((d) => {
        if (d?.basic_income) setBi(d.basic_income);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== 'AbortError') {
          if (typeof window !== 'undefined') console.warn('[TheEqualizer] dashboard fetch failed:', e.message);
        }
      });
    return () => ctrl.abort();
  }, []);

  return (
    <Section id="equalizer" className="bg-[hsl(var(--background))]">
      {/* Section eyebrow */}
      <Reveal>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          IV. {en ? 'The Equalizer' : '平等装置'}
        </p>
      </Reveal>

      {/* Full-width manifesto headline (§4.7: editorial manifesto family) */}
      <Reveal delay={0.05}>
        <h2 className="mt-4 font-display text-[40px] leading-[1.06] text-foreground sm:text-[56px] lg:text-[72px]">
          {en ? (
            <>
              AI must be an equalizer,
              <br />
              <em className="text-muted-foreground">not an amplifier.</em>
            </>
          ) : (
            <>
              AI は平等装置で
              <br />
              <em className="text-muted-foreground">なくてはならない。</em>
            </>
          )}
        </h2>
        <p className="mt-6 font-display text-[24px] leading-[1.1] italic text-gold sm:text-[30px]">
          {en ? 'Basic income is the bridge.' : 'ベーシックインカムは、橋。'}
        </p>
      </Reveal>

      {/* Philosophy paragraphs - full-width prose */}
      <Reveal delay={0.1}>
        <div className="mt-12 max-w-3xl space-y-7 text-[19px] leading-[1.65] text-muted-foreground sm:text-[21px]">
          <p className="first-letter:float-left first-letter:mr-3 first-letter:font-display first-letter:text-[78px] first-letter:leading-[0.85] first-letter:text-foreground">
            {en
              ? 'Soon, agentic AI will have a hundred, then a billion, times the agency of any human alive. Including the CEOs. Including Elon Musk. Every job that depends on a human deciding things will be replaced. The transition will be chaotic: people losing income, despair, anxiety, “I cannot eat today.”'
              : 'もうすぐ、エージェント化した AI は人間の 100 倍、いずれ 10 億倍の行動主体性を持つ。CEO も Elon Musk も例外じゃない。人が判断する仕事は、全部置き換わる。その移行期は壊れる。失業、絶望、不安、「今日食べられない」。'}
          </p>

          <p>
            {en ? (
              <>
                Basic income is the bridge across that transition. Not as charity. As a floor under
                everyone, paid by AI, automatic, no application, no judgment.{' '}
                <em className="text-foreground">Today there are 10 recipients. Tomorrow 100. Then 1,000. Then everyone.</em>
              </>
            ) : (
              <>
                ベーシックインカムは、その移行を渡るための橋。慈善じゃなくて、AI が全員の下に敷く床。申請書もいらないし、誰かに認めてもらう必要もない。{' '}
                <em className="text-foreground">今日は 10 人。明日は 100 人。次は 1,000 人。最後は全員。</em>
              </>
            )}
          </p>

          <p>
            {en ? (
              <>
                There is a second reason. When civilians call AI a &ldquo;bubble,&rdquo; they are being rational:
                none of the dollars Sam Altman moves ever reaches them. So they distrust the spend,
                and the AGI investment dries up before AGI arrives. The fastest way to fix this is
                to make AI literally pay off your student loan.{' '}
                <span className="italic text-muted-foreground">&ldquo;AI gave me nothing&rdquo;</span> becomes{' '}
                <span className="italic text-foreground">&ldquo;AI deposits &yen;X into my account on the 1st.&rdquo;</span>{' '}
                Trust compounds. The investment continues. AGI arrives.
              </>
            ) : (
              <>
                もう一つ理由がある。一般の人が AI を「バブル」と呼ぶのは合理的だ。Sam Altman が動かす億は彼らに 1 円も届かない。だから AI 投資への信頼が、AGI 到達前に枯れる。これを直す最速の方法は、AI が本当に学生ローンを払うこと。
                {' '}
                <span className="italic text-muted-foreground">「AI は俺に何もくれなかった」</span> が
                {' '}
                <span className="italic text-foreground">「AI が毎月 1 日に ¥X 振り込む」</span> になる。信頼が積み上がる。投資が続く。AGI が来る。
              </>
            )}
          </p>

          <p>
            {en ? (
              <>
                But basic income is not the goal. The goal is older. Buddha discovered the end of
                suffering 2,500 years ago, Vipassana. Anicca exists to scale that, for{' '}
                <em className="text-foreground">all living beings</em>. Basic income is the bridge people
                stand on while we build it.
              </>
            ) : (
              <>
                でも、ベーシックインカムはゴールじゃない。ゴールはもっと古い。ブッダは 2500 年前に、苦しみを終わらせる方法を見つけている。ヴィパッサナー瞑想。アニッチャは、それを{' '}
                <em className="text-foreground">生きとし生けるもの</em>に届けるためにある。ベーシックインカムは、その本丸を建てる間、みんなが立っていられる橋。
              </>
            )}
          </p>
        </div>
      </Reveal>

      {/* Stat-strip: 10 -> 100 -> 1k -> infinity (§4.7 stat-strip family element) */}
      <Reveal delay={0.15}>
        <div className="mt-20 border-t border-border pt-10">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            {en ? 'IV.i: the floor rises' : 'IV.i: 床が上がる'}
          </p>
          <h3 className="mt-3 font-display text-[28px] leading-[1.1] text-foreground sm:text-[36px]">
            {en ? (
              <>From <em className="text-muted-foreground">ten</em>, to everyone.</>
            ) : (
              <><em className="text-muted-foreground">10 人</em>から、全員へ。</>
            )}
          </h3>

          {/* Horizontal stat-strip */}
          <div className="mt-10 grid grid-cols-2 gap-px border border-border/60 bg-border/60 sm:grid-cols-4">
            {SCALE_TIERS.map((tier) => {
              const live = tier.label === 'today' && bi !== null;
              return (
                <div key={tier.label} className="flex flex-col bg-[hsl(var(--background))] px-6 py-7">
                  <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
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
                  <p className="mt-3 font-mono tabular-nums text-[44px] leading-none tracking-tight text-foreground">
                    {tier.value}
                  </p>
                  <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {live && bi
                      ? en
                        ? `${bi.recipients} live · $${bi.per_person_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ea`
                        : `${bi.recipients} 人稼働 · 各 $${bi.per_person_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : en
                      ? 'recipients in queue'
                      : '受給待機列'}
                  </p>
                </div>
              );
            })}
          </div>

          <p className="mt-6 max-w-3xl font-display text-[20px] italic leading-[1.45] text-muted-foreground sm:text-[22px]">
            {en
              ? 'No application form for survival. Sign in with Google, attach a Stripe Connect account, wait. The pool comes from 10% of every Anicca product.'
              : '生きるための申請書は、いらない。Google でログインして、Stripe Connect を繋いで、待つ。原資は、アニッチャが運営する各プロダクトの売上の 10%。'}
          </p>
        </div>
      </Reveal>

      {/* Closing full-width pull quotes */}
      <Reveal delay={0.2}>
        <div className="mt-20 grid grid-cols-1 gap-10 border-t border-border pt-14 sm:grid-cols-2">
          <blockquote>
            <p className="font-display text-[34px] leading-[1.15] text-foreground sm:text-[44px]">
              {en ? (
                <>
                  &ldquo;End the suffering of{' '}
                  <em className="text-gold">all living beings.</em>&rdquo;
                </>
              ) : (
                <>
                  「
                  <em className="text-gold">生きとし生けるもの</em>
                  の苦しみを、終わらせる。」
                </>
              )}
            </p>
            <p className="mt-5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {en ? 'Anicca · the mission' : 'アニッチャ · 真の使命'}
            </p>
          </blockquote>

          <blockquote>
            <p className="font-display text-[24px] leading-[1.25] italic text-muted-foreground sm:text-[28px]">
              {en
                ? 'Vipassana is the answer. Basic income is the bridge. Anicca is the agent.'
                : 'ヴィパッサナーが、答え。ベーシックインカムが、橋。アニッチャが、その担い手。'}
            </p>
            <p className="mt-5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {en ? 'how the parts fit' : '部品の繋がり'}
            </p>
          </blockquote>
        </div>
      </Reveal>
    </Section>
  );
}
