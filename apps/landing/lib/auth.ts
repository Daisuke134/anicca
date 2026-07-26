'use client';

// Client-side Supabase Auth (Google provider, PKCE) for the static-export site.
// The Supabase project already backs the site server-side (dashboard-sync / owners);
// this adds the *visitor login* surface. The anon key is public by design — RLS, not
// secrecy, protects rows. NEVER import the service-role key here.
//
// Env (Netlify, build-time, public):
//   NEXT_PUBLIC_SUPABASE_URL       = https://<proj>.supabase.co
//   NEXT_PUBLIC_SUPABASE_ANON_KEY  = eyJ... (anon, RLS-guarded)
// Supabase dashboard: Authentication → Providers → Google = ON, with
//   redirect URL https://aniccaai.com/me (and http://localhost:3000/me for dev).

import { createClient, type SupabaseClient, type Session } from '@supabase/supabase-js';

let _client: SupabaseClient | null = null;

export function supabase(): SupabaseClient | null {
  if (typeof window === 'undefined') return null;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) return null;
  if (!_client) {
    _client = createClient(url, anon, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce' },
    });
  }
  return _client;
}

export async function getSession(): Promise<Session | null> {
  const c = supabase();
  if (!c) return null;
  const { data } = await c.auth.getSession();
  return data.session ?? null;
}

export function onAuthChange(cb: (s: Session | null) => void): () => void {
  const c = supabase();
  if (!c) {
    cb(null);
    return () => {};
  }
  const { data } = c.auth.onAuthStateChange((_evt, session) => cb(session));
  return () => data.subscription.unsubscribe();
}

export async function signInWithGoogle(): Promise<void> {
  const c = supabase();
  if (!c) throw new Error('auth not configured');
  // Return to the CURRENT path (so /lm comes back to /lm, /me to /me). Each path must be
  // allowlisted in Supabase → Auth → URL Configuration → Redirect URLs.
  // Keep the query string: /lm?tg=<chat_id> carries the Telegram binding, and dropping it
  // across the OAuth round-trip left lm_users.telegram_chat_id NULL forever (measured in
  // production: web-onboarded rows with calendar connected and tg_bound=false).
  const path = typeof window !== 'undefined'
    ? window.location.pathname + window.location.search
    : '/me';
  const redirectTo =
    typeof window !== 'undefined' ? `${window.location.origin}${path}` : 'https://aniccaai.com/me';
  await c.auth.signInWithOAuth({ provider: 'google', options: { redirectTo } });
}

export async function signOut(): Promise<void> {
  const c = supabase();
  if (c) await c.auth.signOut();
}
