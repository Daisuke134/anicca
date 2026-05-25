"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

// aniccaai.com/alarm/setup — post-purchase connect dashboard.
// Reads ?session_id from Stripe success redirect, resolves the subscriber's token,
// then lets them connect calendar (ICS), location (OwnTracks), and stakeholders (報連相)
// so the "never be late" engine becomes real for them.

const fade = (d = 0): any => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay: d, ease: [0.16, 1, 0.3, 1] },
});

type Stakeholder = { match: string; channel: string; toField: string; senderType: string };

function Card({ n, t, sub, children }: { n: string; t: string; sub: string; children: React.ReactNode }) {
  return (
    <motion.section {...fade(Number(n) * 0.08)} className="border-t border-white/10 pt-7">
      <span className="font-mono text-xs tracking-[0.3em] text-amber-500/80">{n}</span>
      <h2 className="mt-3 font-soft text-2xl text-white">{t}</h2>
      <p className="mt-1.5 font-serif-jp text-[14px] leading-relaxed text-white/50">{sub}</p>
      <div className="mt-5">{children}</div>
    </motion.section>
  );
}

const inputCls =
  "w-full rounded-lg border border-white/15 bg-white/[0.03] px-4 py-3 font-mono text-[13px] text-white placeholder-white/30 outline-none focus:border-amber-500/60";

export default function SetupPage() {
  const [token, setToken] = useState<string | null>(null);
  const [loco, setLoco] = useState<string | null>(null);
  const [icsUrl, setIcsUrl] = useState("");
  const [calConnecting, setCalConnecting] = useState(false);
  const [calConnected, setCalConnected] = useState(false);

  async function connectCalendar() {
    if (!token) return;
    setCalConnecting(true);
    try {
      const r = await fetch(`/.netlify/functions/calendar-connect?token=${encodeURIComponent(token)}`);
      const d = await r.json();
      if (d.connected) { setCalConnected(true); setCalConnecting(false); return; }
      if (d.redirect_url) window.location.href = d.redirect_url;
      else throw new Error("no redirect");
    } catch {
      setCalConnecting(false);
      alert("接続できませんでした。少し待って、もう一度お試しください。");
    }
  }
  const [home, setHome] = useState("");
  const [wake, setWake] = useState("07:00");
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([
    { match: "", channel: "sms", toField: "", senderType: "stage" },
  ]);
  const [loadErr, setLoadErr] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get("session_id");
    if (!sid) { setLoadErr(true); return; }
    fetch(`/.netlify/functions/alarm-profile?session_id=${encodeURIComponent(sid)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        setToken(d.owntracks_token || null);
        setLoco(d.locoUrl || null);
        if (d.ics_url) setIcsUrl(d.ics_url);
        if (d.home_address) setHome(d.home_address);
        if (d.wake_time) setWake(d.wake_time);
        if (Array.isArray(d.stakeholders) && d.stakeholders.length) setStakeholders(d.stakeholders);
      })
      .catch(() => setLoadErr(true));
  }, []);

  async function save() {
    if (!token) return;
    setSaving(true);
    setSaved(false);
    try {
      const r = await fetch("/.netlify/functions/alarm-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          ics_url: icsUrl.trim() || null,
          home_address: home.trim() || null,
          wake_time: wake,
          stakeholders: stakeholders.filter((s) => s.match.trim() && s.toField.trim()),
        }),
      });
      if (!r.ok) throw new Error();
      setSaved(true);
    } catch {
      alert("保存に失敗しました。少し待って再度お試しください。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white selection:bg-amber-500 selection:text-black">
      <div className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-[70vh] bg-[radial-gradient(80%_60%_at_50%_-10%,rgba(255,107,53,0.18),transparent_70%)]" />

      <header className="mx-auto flex max-w-3xl items-center justify-between px-6 py-6">
        <span className="font-soft text-lg tracking-tight">Anicca</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-white/40">Setup</span>
      </header>

      <section className="mx-auto max-w-3xl px-6 pt-10 pb-28">
        <motion.p {...fade(0)} className="font-mono text-xs tracking-[0.3em] text-amber-500/90">
          ご登録ありがとうございます
        </motion.p>
        <motion.h1 {...fade(0.06)} className="mt-5 font-soft text-[clamp(2rem,6vw,3.4rem)] font-light leading-[1.02] tracking-tight">
          あと3つ繋ぐだけで、<br />二度と遅刻しない。
        </motion.h1>
        <motion.p {...fade(0.12)} className="mt-5 max-w-xl font-serif-jp text-[15px] leading-relaxed text-white/55">
          カレンダーと位置を繋ぐと、Anicca が予定から逆算した出発時刻を見張り、間に合わなくなりそうな瞬間に電話します。遅れる時は、あなたの代わりに関係者へ連絡します。
        </motion.p>

        {loadErr && (
          <p className="mt-8 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 font-serif-jp text-sm text-red-300/80">
            このページは決済完了後のリンクから開いてください。リンクが見つからない場合は support@aniccaai.com へご連絡ください。
          </p>
        )}

        <div className="mt-14 space-y-12">
          {/* 01 — Calendar (Composio managed OAuth, real-time) */}
          <Card n="01" t="カレンダーを繋ぐ" sub="Google カレンダーをワンタップで接続。予定はリアルタイムで反映されます。">
            {calConnected ? (
              <span className="inline-flex items-center gap-2 font-serif-jp text-[15px] text-emerald-300/90">✓ Google カレンダー接続済み</span>
            ) : (
              <button type="button" onClick={connectCalendar} disabled={!token || calConnecting}
                className="flex items-center gap-3 rounded-lg border border-white/20 bg-white/[0.04] px-5 py-3.5 font-soft text-[15px] text-white transition hover:border-amber-500/60 disabled:opacity-50">
                <span className="text-lg">📅</span>
                {calConnecting ? "接続ページへ…" : "Google カレンダーを接続"}
              </button>
            )}
          </Card>

          {/* 02 — Location */}
          <Card n="02" t="位置を繋ぐ" sub="iPhone の OwnTracks アプリ（無料）に、下の URL を登録。動いていない＝まだ家にいると分かると催促します。">
            {loco ? (
              <div className="rounded-lg border border-white/15 bg-white/[0.03] p-4">
                <p className="font-mono text-[11px] uppercase tracking-widest text-white/40">あなた専用の取り込み URL</p>
                <code className="mt-2 block break-all font-mono text-[12px] text-amber-300/90">{loco}</code>
                <ol className="mt-4 space-y-1.5 font-serif-jp text-[13px] leading-relaxed text-white/55">
                  <li>1. App Store で「OwnTracks」を入れる</li>
                  <li>2. Settings → Mode を「HTTP」にする</li>
                  <li>3. URL に上の値を貼り、Mode は「Move」に</li>
                  <li>4. 位置情報の許可を「常に許可」にする</li>
                </ol>
              </div>
            ) : (
              <p className="font-mono text-[12px] text-white/30">読み込み中…</p>
            )}
          </Card>

          {/* 03 — Stakeholders (報連相) */}
          <Card n="03" t="関係者を登録（報連相）" sub="遅れそうな予定ごとに、誰へ連絡するか。例: 予定名に『MTG』が含まれたら 上司の携帯へ SMS。電話に出られない時、Anicca が代わりに知らせます。">
            <div className="space-y-3">
              {stakeholders.map((s, i) => (
                <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_1.4fr]">
                  <input className={inputCls} placeholder="予定名に含まれる語（例: MTG）"
                    value={s.match} onChange={(e) => setStakeholders((p) => p.map((x, j) => j === i ? { ...x, match: e.target.value } : x))} />
                  <select className={inputCls + " sm:w-28"} value={s.channel}
                    onChange={(e) => setStakeholders((p) => p.map((x, j) => j === i ? { ...x, channel: e.target.value } : x))}>
                    <option value="sms">SMS</option>
                    <option value="email">メール</option>
                    <option value="slack">Slack</option>
                  </select>
                  <input className={inputCls} placeholder="送信先（携帯番号 / メール / Slack ID）"
                    value={s.toField} onChange={(e) => setStakeholders((p) => p.map((x, j) => j === i ? { ...x, toField: e.target.value } : x))} />
                </div>
              ))}
              <button type="button" onClick={() => setStakeholders((p) => [...p, { match: "", channel: "sms", toField: "", senderType: "stage" }])}
                className="font-mono text-[12px] text-amber-400/80 hover:text-amber-300">+ 連絡先を追加</button>
            </div>
          </Card>

          {/* wake time */}
          <Card n="04" t="起こす時刻" sub="毎朝この時刻に電話します。起きるまで、かけ直します。">
            <input type="time" className={inputCls + " w-40"} value={wake} onChange={(e) => setWake(e.target.value)} />
            <div className="mt-4">
              <input className={inputCls} placeholder="自宅の住所（移動時間の基準・任意）" value={home} onChange={(e) => setHome(e.target.value)} />
            </div>
          </Card>
        </div>

        <motion.div {...fade(0.2)} className="mt-14">
          <button onClick={save} disabled={!token || saving}
            className="w-full rounded-xl bg-amber-500 px-6 py-4 font-soft text-lg text-black transition hover:bg-amber-400 disabled:opacity-40 sm:w-auto sm:px-12">
            {saving ? "保存中…" : "この設定で始める"}
          </button>
          {saved && (
            <p className="mt-4 font-serif-jp text-[14px] text-emerald-300/80">
              ✓ 保存しました。明朝から電話が始まります。設定はこのページからいつでも変更できます。
            </p>
          )}
        </motion.div>
      </section>
    </main>
  );
}
