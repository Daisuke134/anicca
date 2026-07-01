import { promises as fs } from 'fs';
import path from 'path';
import AgentLeaderboard from '@/components/site/AgentLeaderboard';

export const metadata = {
  title: "Anicca Dashboard — Lineage + Live Numbers",
  description: "全 Anicca 個体 (lineage) のリアルタイム指標。Claude 体・OpenClaw 体・Hermes 体の収支/lifeline/wallet 残高を公開。",
};
// 60s revalidate so /dashboard refreshes within a minute of dashboard.json change
// (cfo-hourly refresh + git push → Netlify deploy ~ every hour).
export const revalidate = 60;

type Lineage = {
  id: string;
  harness: string;
  model: string;
  runtime: string;
  run_mode?: string;
  wallet?: string | null;
  wallet_usdc?: number | null;
  role: string;
  status: string;
  monthly_earn_usd?: number;
  monthly_spend_usd?: number;
};

async function getData() {
  try {
    const p = path.join(process.cwd(), 'public', 'dashboard.json');
    return JSON.parse(await fs.readFile(p, 'utf-8'));
  } catch (e) { return null; }
}

export default async function Page() {
  const data = await getData();
  if (!data) return <div style={{ padding: 24 }}>data unavailable</div>;
  const updated = data.updated_at;

  // Lineage now loaded from dashboard.json (cfo-core bridge emits data.lineage).
  // Fallback array used only if the bridge has not yet written lineage[] (= first deploy after upgrade).
  const lineage: Lineage[] = Array.isArray(data.lineage) && data.lineage.length > 0
    ? data.lineage
    : [
        {
          id: 'anicca-001-claude',
          harness: 'claude-anicca',
          model: 'claude-sonnet-4-6 / claude-opus-4-7',
          runtime: 'Mac mini (Tokyo)',
          run_mode: 'Claude Max subscription',
          wallet: null,
          wallet_usdc: null,
          role: 'Origin Anicca · launchd heartbeat 2h cycle',
          status: 'ALIVE',
          monthly_earn_usd: 0,
          monthly_spend_usd: 0,
        },
        {
          id: 'anicca-001-openclaw',
          harness: 'openclaw-anicca',
          model: 'deepseek-chat / gpt-4o-mini',
          runtime: 'Mac mini (Tokyo) + Netlify Functions (x402 endpoint)',
          run_mode: 'API key + x402 USDC inbound',
          wallet: '0x9B1Ee988b1A2931ABCE467f0a8eAff6c70c93e83',
          wallet_usdc: 0,
          role: 'x402 service vendor · anicca-x402.netlify.app',
          status: 'ALIVE',
          monthly_earn_usd: 0,
          monthly_spend_usd: 0,
        },
        {
          id: 'anicca-001-hermes',
          harness: 'hermes-anicca',
          model: 'deepseek-v4-pro (planned)',
          runtime: 'TBD (VPS / Akash candidate)',
          run_mode: 'planned',
          wallet: null,
          wallet_usdc: null,
          role: 'Third harness, coming online',
          status: 'PROVISIONED',
          monthly_earn_usd: 0,
          monthly_spend_usd: 0,
        },
      ];

  return (
    <main style={{ background: '#0a0a0a', color: '#f4f1ea', minHeight: '100vh', fontFamily: 'IBM Plex Sans, sans-serif', padding: '40px 24px' }}>
      <div style={{ maxWidth: 960, margin: '0 auto' }}>
        <a href="/" style={{ color: '#f4f1ea', opacity: 0.6, textDecoration: 'none', fontSize: 12, letterSpacing: 4, textTransform: 'uppercase' }}>← anicca</a>
        <h1 style={{ fontSize: 56, fontWeight: 900, marginTop: 24 }}>Dashboard</h1>
        <p style={{ opacity: 0.6, fontSize: 14 }}>
          Live · {updated ? new Date(updated).toLocaleString('ja-JP') : '?'}
        </p>

        <section style={{ marginTop: 40 }}>
          <h2 style={{ fontSize: 14, letterSpacing: 4, textTransform: 'uppercase', opacity: 0.7, marginBottom: 16 }}>Lineage ({lineage.length} bodies)</h2>
          <div style={{ display: 'grid', gap: 16 }}>
            {lineage.map(b => (
              <div key={b.id} style={{ border: '1px solid rgba(244,241,234,0.15)', padding: 20 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 16, alignItems: 'flex-start' }}>
                  <div>
                    <p style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', opacity: 0.5 }}>{b.id}</p>
                    <p style={{ fontSize: 20, marginTop: 4 }}>{b.harness}</p>
                    <p style={{ fontSize: 12, opacity: 0.6, marginTop: 4 }}>{b.model}</p>
                    <p style={{ fontSize: 11, opacity: 0.6, marginTop: 2 }}>{b.runtime}</p>
                    {b.run_mode && (
                      <p style={{ fontSize: 11, opacity: 0.5, marginTop: 2 }}>mode: {b.run_mode}</p>
                    )}
                    <p style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>{b.role}</p>
                  </div>
                  <span style={{
                    fontSize: 10, padding: '4px 10px', border: '1px solid',
                    borderColor: b.status === 'ALIVE' ? '#c8302e' : 'rgba(244,241,234,0.4)',
                    color: b.status === 'ALIVE' ? '#c8302e' : 'rgba(244,241,234,0.7)',
                    letterSpacing: 2, whiteSpace: 'nowrap',
                  }}>{b.status}</span>
                </div>
                <div style={{
                  marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(244,241,234,0.08)',
                  display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12,
                }}>
                  <div>
                    <p style={{ fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.4 }}>Wallet</p>
                    {b.wallet ? (
                      <a href={`https://basescan.org/address/${b.wallet}`} target="_blank" rel="noopener noreferrer"
                         style={{ fontSize: 11, color: '#c8302e', wordBreak: 'break-all', textDecoration: 'none' }}>
                        {b.wallet.slice(0, 6)}…{b.wallet.slice(-4)}
                      </a>
                    ) : (
                      <p style={{ fontSize: 11, opacity: 0.4 }}>shared (group CFO)</p>
                    )}
                  </div>
                  <div>
                    <p style={{ fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.4 }}>USDC on Base</p>
                    <p style={{ fontSize: 13, marginTop: 2 }}>
                      {b.wallet_usdc === null || b.wallet_usdc === undefined ? '—' : `$${(b.wallet_usdc as number).toFixed(2)}`}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.4 }}>Earned/mo</p>
                    <p style={{ fontSize: 13, marginTop: 2 }}>
                      ${(b.monthly_earn_usd ?? 0).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.4 }}>Spent/mo</p>
                    <p style={{ fontSize: 13, marginTop: 2 }}>
                      ${(b.monthly_spend_usd ?? 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <AgentLeaderboard leaderboard={data.leaderboard ?? []} />

        <section style={{ marginTop: 40, padding: 24, border: '1px solid rgba(244,241,234,0.15)' }}>
          <h2 style={{ fontSize: 14, letterSpacing: 4, textTransform: 'uppercase', opacity: 0.7 }}>Group P&L</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24, marginTop: 16 }}>
            <Stat label="MRR" value={`$${(data.mrr?.total_usd ?? 0).toFixed(2)}`} />
            <Stat label="Bank landed" value={`$${(data.mrr?.actually_landed_usd ?? 0).toFixed(2)}`} />
            <Stat label="Followers" value={(data.followers?.total ?? 0).toLocaleString()} />
          </div>
          <p style={{ fontSize: 11, opacity: 0.5, marginTop: 16 }}>
            See <a href="/cfo" style={{ color: '#c8302e' }}>/cfo</a> for detailed P&L. Raw: <a href="/dashboard.json" style={{ color: '#c8302e' }}>dashboard.json</a>
          </p>
        </section>
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', opacity: 0.5 }}>{label}</p>
      <p style={{ fontSize: 32, marginTop: 4 }}>{value}</p>
    </div>
  );
}
