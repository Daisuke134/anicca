"use client";

import { useState } from "react";
import { motion } from "framer-motion";

// aniccaai.com/alarm — Anicca Alarm: the wake-up call that does not stop until you are up.
// Dark, dawn-ember editorial. Display = Fraunces (font-soft), JA = font-serif-jp, labels = mono.

const PRICE = "$9.99";

// Normalize a Japanese phone number to E.164 so users can type it the everyday way.
// "090 1234 5678" / "08046270314" -> "+818046270314" (drop the domestic leading 0).
// Already-international (+...) numbers pass through untouched.
function normalizeJP(raw: string): string {
  const t = (raw || "").replace(/[\s\-()]/g, "");
  if (t.startsWith("+")) return t;
  if (t.startsWith("0")) return "+81" + t.slice(1);
  return t;
}

// returns motion props; typed loose to spread cleanly onto motion.* elements
const fade = (d = 0): any => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.7, delay: d, ease: [0.16, 1, 0.3, 1] },
});

function Step({ n, t, d }: { n: string; t: string; d: string }) {
  return (
    <motion.div {...fade(Number(n) * 0.08)} className="relative border-t border-white/10 pt-6">
      <span className="font-mono text-xs tracking-[0.3em] text-amber-500/80">{n}</span>
      <h3 className="mt-3 font-soft text-2xl text-white">{t}</h3>
      <p className="mt-2 font-serif-jp text-[15px] leading-relaxed text-white/55">{d}</p>
    </motion.div>
  );
}

export default function AlarmPage() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [wake, setWake] = useState("07:00");
  const [loading, setLoading] = useState(false);
  const [demoState, setDemoState] = useState<"idle" | "calling" | "done" | "used">("idle");

  async function demo() {
    if (!phone.trim()) { alert("電話番号を入れてください。"); return; }
    setDemoState("calling");
    try {
      const r = await fetch("/.netlify/functions/alarm-demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), phone: normalizeJP(phone), wakeTime: wake }),
      });
      if (r.status === 409) { setDemoState("used"); return; }
      if (!r.ok) throw new Error("demo failed");
      setDemoState("done");
    } catch {
      setDemoState("idle");
      alert("発信できませんでした。番号を確認して、もう一度試してください。");
    }
  }

  async function start(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true);
    try {
      const r = await fetch("/.netlify/functions/alarm-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), phone: normalizeJP(phone), wakeTime: wake }),
      });
      const { url } = await r.json();
      if (url) window.location.href = url;
      else throw new Error("no url");
    } catch {
      setLoading(false);
      alert("少し時間をおいて、もう一度試してください。");
    }
  }

  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white selection:bg-amber-500 selection:text-black">
      {/* dawn glow */}
      <div className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-[70vh] bg-[radial-gradient(80%_60%_at_50%_-10%,rgba(255,107,53,0.20),transparent_70%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.04] [background-image:repeating-linear-gradient(0deg,#fff_0,#fff_1px,transparent_1px,transparent_4px)]" />

      {/* nav */}
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <span className="font-soft text-lg tracking-tight">Anicca</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-white/40">Alarm</span>
      </header>

      {/* hero */}
      <section className="mx-auto max-w-5xl px-6 pt-16 pb-24 sm:pt-24">
        <motion.p {...fade(0)} className="font-mono text-xs tracking-[0.3em] text-amber-500/90">
          電話で起こす、自己改善する目覚まし
        </motion.p>
        <motion.h1 {...fade(0.06)} className="mt-6 font-soft text-[clamp(2.8rem,9vw,6.5rem)] font-light leading-[0.95] tracking-tight">
          もう、<br className="sm:hidden" />寝坊しない。
        </motion.h1>
        <motion.p {...fade(0.14)} className="mt-7 max-w-xl font-serif-jp text-lg leading-relaxed text-white/65">
          アラームは止められる。電話は、無視できない。<br />
          アニッチャが毎朝あなたに電話して、<span className="text-white">本当に起き上がるまで</span>かけ続けます。
          起きた日も、起きられなかった日も学習して、明日はもっと効く。
        </motion.p>

        {/* onboarding card — experience first, then pay */}
        <motion.form {...fade(0.22)} onSubmit={(e: React.FormEvent) => e.preventDefault()}
          className="mt-12 max-w-md rounded-2xl border border-white/12 bg-white/[0.03] p-6 backdrop-blur-sm">
          <div className="grid grid-cols-2 gap-3">
            <label className="col-span-2 block">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">名前</span>
              <input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="大祐"
                className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/40 px-4 py-3 font-mono text-white outline-none placeholder:text-white/25 focus:border-amber-500/70" />
            </label>
            <label className="col-span-2 block">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">電話番号</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel"
                placeholder="090 1234 5678"
                className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/40 px-4 py-3 font-mono text-white outline-none placeholder:text-white/25 focus:border-amber-500/70" />
              <span className="mt-1 block font-serif-jp text-[11px] text-white/35">0から入力でOK。自動で国際形式(+81)に変換します。</span>
            </label>
            <label className="col-span-2 block">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">起きたい時刻</span>
              <input type="time" value={wake} onChange={(e) => setWake(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-white/15 bg-black/40 px-4 py-3 font-mono text-white outline-none focus:border-amber-500/70" />
            </label>
          </div>

          {/* ① free one-time demo */}
          {demoState !== "done" && demoState !== "used" && (
            <button type="button" onClick={demo} disabled={demoState === "calling"}
              className="mt-4 w-full rounded-lg bg-amber-500 px-4 py-3.5 font-soft text-base text-black transition hover:bg-amber-400 disabled:opacity-60">
              {demoState === "calling" ? "📞 今、発信しています…出てください" : "① 今すぐ1回、電話を体験する（無料）"}
            </button>
          )}

          {/* after the demo: nudge to subscribe */}
          {(demoState === "done" || demoState === "used") && (
            <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-4">
              <p className="font-serif-jp text-sm text-white/80">
                {demoState === "done"
                  ? "どうだった？これが毎朝、起き上がるまで鳴る。"
                  : "体験は1回までです。続けるには登録を。"}
              </p>
              <button type="button" onClick={() => start()} disabled={loading}
                className="mt-3 w-full rounded-lg bg-amber-500 px-4 py-3.5 font-soft text-base text-black transition hover:bg-amber-400 disabled:opacity-60">
                {loading ? "..." : `毎朝これを → ${PRICE}/月で続ける`}
              </button>
            </div>
          )}

          {/* ② subscribe directly */}
          {demoState !== "done" && demoState !== "used" && (
            <button type="button" onClick={() => start()} disabled={loading}
              className="mt-2.5 w-full rounded-lg border border-white/20 px-4 py-3 font-soft text-base text-white/80 transition hover:border-amber-500/70 hover:text-amber-400 disabled:opacity-50">
              {loading ? "..." : `② 体験なしで始める → ${PRICE}/月`}
            </button>
          )}

          <p className="mt-3 font-serif-jp text-xs text-white/40">
            体験は1番号につき1回・無料。{PRICE}/月・無料トライアルなし。いつでも解約可。
          </p>
        </motion.form>
      </section>

      {/* demo */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <motion.div {...fade(0)} className="overflow-hidden rounded-2xl border border-white/10 bg-black/50">
          <div className="aspect-video w-full" id="alarm-demo-video">
            {/* デモ動画を後でここに埋め込む (X/TikTok の起こし動画 or mp4) */}
            <div className="flex h-full items-center justify-center font-mono text-xs tracking-[0.2em] text-white/30">
              DEMO — アニッチャが起こす実録（動画 差し込み）
            </div>
          </div>
        </motion.div>
      </section>

      {/* why phone */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <motion.h2 {...fade(0)} className="max-w-2xl font-soft text-3xl font-light leading-snug text-white sm:text-4xl">
          スヌーズを押す指は、寝ぼけてる。
        </motion.h2>
        <motion.p {...fade(0.08)} className="mt-5 max-w-xl font-serif-jp text-[15px] leading-relaxed text-white/55">
          研究でも、寝起きは判断力が落ちる（睡眠慣性）。だからアラームは無意識に止められる。
          でも「人からの電話」は、脳を起こす。アニッチャは低く、力強い声で、立って歩くまで導く。
          David Goggins が枕元で説教してくる——そんな毎朝。
        </motion.p>
      </section>

      {/* how */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="grid gap-8 sm:grid-cols-3">
          <Step n="1" t="時刻と番号を入れる" d="起きたい時刻と電話番号だけ。30秒で完了。" />
          <Step n="2" t="毎朝、電話が鳴る" d="起き上がって動き出すまで、かけ続ける。寝直したらまた鳴る。" />
          <Step n="3" t="あなた用に進化する" d="何回で起きたか・何が効いたかを学習し、明日の起こし方を最適化。" />
        </div>
      </section>

      {/* never late (bonus) */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <motion.div {...fade(0)} className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-8">
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-amber-500/90">任意連携</span>
          <h2 className="mt-3 font-soft text-3xl font-light text-white">一生、遅刻しない化。</h2>
          <p className="mt-4 max-w-xl font-serif-jp text-[15px] leading-relaxed text-white/55">
            カレンダーと位置を繋げば、予定への出発時刻も見張ります。間に合わなそうなら電話で送り出し、
            遅れる時は関係者へ連絡（報・連・相）まで自動。もうカレンダーを見なくていい。
          </p>
        </motion.div>
      </section>

      {/* pricing / cta */}
      <section className="mx-auto max-w-5xl px-6 pb-32">
        <motion.div {...fade(0)} className="flex flex-col items-start gap-6 border-t border-white/10 pt-12 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="font-soft text-6xl font-light text-white">{PRICE}<span className="text-2xl text-white/40">/月</span></div>
            <p className="mt-2 font-serif-jp text-sm text-white/50">無料トライアルなし・いつでも解約。世界一しつこい起こし。</p>
          </div>
          <a href="#top" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            className="rounded-lg border border-white/20 px-7 py-3 font-soft text-lg text-white transition hover:border-amber-500/70 hover:text-amber-400">
            起こしてもらう →
          </a>
        </motion.div>
        <p className="mt-16 font-mono text-[11px] tracking-[0.2em] text-white/25">
          ANICCA · OPEN SOURCE · github.com/Daisuke134/anicca
        </p>
      </section>
    </main>
  );
}
