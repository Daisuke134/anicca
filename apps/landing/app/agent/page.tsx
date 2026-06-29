"use client";

// Flexible agent page — works for ANY instance name, no rebuild needed. Static export only
// pre-generates pages for names known at build time, so a freshly-spawned or renamed anicca would
// 404. This page is the Netlify catch-all fallback: it reads the instance name from the URL path at
// runtime and renders the live client view, which fetches that instance from dashboard-sync. So
// /anicca-<anything> always resolves — names can change or appear and the page follows.
import { useEffect, useState } from "react";
import AgentClient from "../[id]/AgentClient";

export default function AgentFallback() {
  const [id, setId] = useState<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("id");
    const fromPath = window.location.pathname.replace(/^\/+|\/+$/g, "");
    setId((fromQuery || fromPath || "anicca").toLowerCase());
  }, []);
  if (!id) return <div className="min-h-screen bg-background" />;
  return <AgentClient id={id} />;
}
