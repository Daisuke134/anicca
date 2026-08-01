"use client";

import { useEffect, useState } from "react";

type AccessModel = "one_time" | "archive" | "both";
type Props = {
  slug: string;
  runId: string;
  artifactId: string;
  lang: "ja" | "en";
  accessModel: AccessModel;
  paidSha256: string;
};

type State = "checking" | "locked" | "checkout" | "unlocking" | "unlocked" | "error";
const CLIENT_KEY = "writer_client_reference_v1";

function clientReference(): string {
  const stored = window.localStorage.getItem(CLIENT_KEY);
  if (stored && /^[A-Za-z0-9_-]{16,64}$/.test(stored)) return stored;
  const created = window.crypto.randomUUID();
  window.localStorage.setItem(CLIENT_KEY, created);
  return created;
}

async function sha256(value: string): Promise<string> {
  const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function PaidMarkdown({ markdown }: { markdown: string }) {
  return (
    <div className="space-y-5 text-[19px] leading-[1.75] text-ink-soft sm:text-[20px]">
      {markdown.split(/\n\s*\n/).map((block, index) => {
        const value = block.trim();
        if (!value) return null;
        const heading = value.match(/^(#{1,6})\s+([\s\S]+)$/);
        if (heading) {
          return <h2 key={index} className="pt-8 font-display text-[28px] leading-tight text-ink sm:text-[34px]">{heading[2]}</h2>;
        }
        const rows = value.split("\n");
        if (rows.every((row) => /^[-*]\s+/.test(row))) {
          return <ul key={index} className="space-y-3 pl-6" style={{ listStyleType: "square" }}>{rows.map((row) => <li key={row}>{row.replace(/^[-*]\s+/, "")}</li>)}</ul>;
        }
        return <p key={index} className="whitespace-pre-wrap">{value}</p>;
      })}
    </div>
  );
}

export default function WriterUnlock({ slug, runId, artifactId, lang, accessModel, paidSha256 }: Props) {
  const ja = lang === "ja";
  const [state, setState] = useState<State>("checking");
  const [paid, setPaid] = useState("");
  const [message, setMessage] = useState("");

  async function acceptContent(response: Response) {
    if (!response.ok) throw new Error("access unavailable");
    const value = await response.json();
    if (typeof value.paid_markdown !== "string" || value.paid_sha256 !== paidSha256) {
      throw new Error("content receipt mismatch");
    }
    if (await sha256(value.paid_markdown) !== paidSha256) throw new Error("content hash mismatch");
    setPaid(value.paid_markdown);
    setState("unlocked");
  }

  useEffect(() => {
    let active = true;
    async function restore() {
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get("session_id");
      const result = params.get("writer_checkout");
      if (result) {
        params.delete("session_id");
        params.delete("writer_checkout");
        const query = params.toString();
        window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
      }
      if (result === "canceled") {
        if (active) { setMessage(ja ? "購入はキャンセルされました。料金は発生していません。" : "Checkout was canceled. You were not charged."); setState("locked"); }
        return;
      }
      try {
        if (result === "success" && sessionId) {
          if (active) setState("unlocking");
          const response = await fetch("/.netlify/functions/writer-content", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, slug, client_reference_id: clientReference() }),
          });
          if (active) await acceptContent(response);
          return;
        }
        const response = await fetch(`/.netlify/functions/writer-content?slug=${encodeURIComponent(slug)}`, {
          credentials: "same-origin",
          cache: "no-store",
        });
        if (response.ok) {
          if (active) await acceptContent(response);
        } else if (active) {
          setState("locked");
        }
      } catch {
        if (active) { setMessage(ja ? "購入状態を確認できませんでした。再読み込みしてください。" : "We could not verify access. Please reload and try again."); setState("error"); }
      }
    }
    void restore();
    return () => { active = false; };
    // Lineage props are immutable for this statically generated article.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  async function begin(product: "writer_article" | "writer_archive") {
    setState("checkout");
    setMessage("");
    try {
      const response = await fetch("/.netlify/functions/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product,
          slug,
          artifact_id: artifactId,
          run_id: runId,
          lang,
          client_reference_id: clientReference(),
        }),
      });
      if (!response.ok) throw new Error("checkout unavailable");
      const value = await response.json();
      const destination = new URL(value.url);
      if (destination.protocol !== "https:" || destination.hostname !== "checkout.stripe.com") {
        throw new Error("checkout destination is invalid");
      }
      window.location.assign(destination.toString());
    } catch {
      setMessage(ja ? "決済画面を開けませんでした。少し後でもう一度お試しください。" : "Checkout could not be opened. Please try again shortly.");
      setState("error");
    }
  }

  if (state === "unlocked") {
    return <section className="mt-10 border-t border-ink/20 pt-10"><p className="mb-8 font-mono-ui text-[10px] uppercase tracking-[0.24em] text-mist">{ja ? "購入確認済み · 有料本文" : "Purchase verified · Paid article"}</p><PaidMarkdown markdown={paid} /></section>;
  }

  const busy = state === "checking" || state === "checkout" || state === "unlocking";
  return (
    <section className="mt-10 min-w-0 max-w-full overflow-hidden border border-border bg-background-alt px-6 py-7 sm:px-8">
      <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-mist">{ja ? "ここから有料本文" : "Paid section begins here"}</p>
      <h2 className="mt-4 font-display text-[27px] leading-tight text-ink">{busy ? (ja ? "購入状態を確認しています" : "Checking your access") : (ja ? "続きを読む" : "Continue reading")}</h2>
      <p className="mt-3 text-[16px] leading-relaxed text-ink-soft">{message || (ja ? "Stripeの安全な決済画面で購入できます。このサイトのアカウント登録は不要です。" : "Pay securely with Stripe. No account on this site is required.")}</p>
      {!busy && <div className="mt-6 flex min-w-0 flex-col gap-3 sm:flex-row">
        {(accessModel === "one_time" || accessModel === "both") && <button type="button" onClick={() => void begin("writer_article")} className="w-full whitespace-normal bg-primary px-5 py-3 text-center font-mono-ui text-[11px] uppercase tracking-[0.18em] text-primary-foreground sm:w-auto">{ja ? "この記事を ¥500 で読む" : "Buy this article — $5"}</button>}
        {(accessModel === "archive" || accessModel === "both") && <button type="button" onClick={() => void begin("writer_archive")} className="w-full whitespace-normal border border-border px-5 py-3 text-center font-mono-ui text-[11px] uppercase tracking-[0.18em] text-foreground sm:w-auto">{ja ? "有料アーカイブを月額 ¥980 で購読" : "Subscribe — $9.99/month"}</button>}
      </div>}
    </section>
  );
}
