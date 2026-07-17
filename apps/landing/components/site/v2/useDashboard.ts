'use client';
import { useEffect, useState } from 'react';

/**
 * The home reads the SAME real source as /dashboard: the dashboard-sync function,
 * which reports the live Anicca colony state (net worth, earnings, how many are
 * alive). We do NOT read /dashboard.json here — that file mixes in iOS/RevenueCat
 * MRR, which is NOT an anicca's revenue (spec31 R3-4). Unknown fields are never faked.
 */
export type DashboardData = {
  total_net_worth_usd?: number;
  earned_mo_usd?: number;
  alive?: number;
  self_funded_pct?: number;
  frontier_pct?: number;
};

export type DashboardState = {
  data: DashboardData | null;
  loading: boolean;
  error: boolean;
};

export function useDashboard(): DashboardState {
  const [state, setState] = useState<DashboardState>({
    data: null,
    loading: true,
    error: false,
  });

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/.netlify/functions/dashboard-sync', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then((d: DashboardData) => {
        setState({ data: d, loading: false, error: false });
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === 'AbortError') return;
        if (typeof window !== 'undefined') {
          console.warn('[v2/useDashboard] dashboard-sync fetch failed:', String(e));
        }
        setState({ data: null, loading: false, error: true });
      });
    return () => ctrl.abort();
  }, []);

  return state;
}
