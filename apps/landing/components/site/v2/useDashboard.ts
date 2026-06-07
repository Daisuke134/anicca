'use client';
import { useEffect, useState } from 'react';

/**
 * Subset of /dashboard.json we read on the homepage.
 * Unknown fields are not faked (§v2.7, §v2.10). Optional everywhere.
 */
export type DashboardData = {
  updated_at?: string;
  mrr?: {
    total_usd?: number;
    actually_landed_usd?: number;
  };
  instances_count?: number;
  avg_revenue_usd?: number;
  avg_cost_usd?: number;
  distributed_usd?: number;
  basic_income?: {
    distributed_usd?: number;
    recipients?: number;
  };
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
    fetch('/dashboard.json', { signal: ctrl.signal })
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
          console.warn('[v2/useDashboard] /dashboard.json fetch failed:', String(e));
        }
        setState({ data: null, loading: false, error: true });
      });
    return () => ctrl.abort();
  }, []);

  return state;
}
