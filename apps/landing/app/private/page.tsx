import { promises as fs } from 'fs';
import path from 'path';

export const metadata = {
  title: "Anicca Private CFO — Dais's runway dashboard",
  description: "Dais 個人 (founder) の financial runway + private CFO. Behind Netlify basic-auth.",
};
export const revalidate = 600;

async function getPrivate() {
  try {
    const p = path.join(process.cwd(), 'public', 'private-cfo.json');
    return JSON.parse(await fs.readFile(p, 'utf-8'));
  } catch (e) { return null; }
}

export default async function Page() {
  const p = await getPrivate();
  return (
    <main style={{ background: '#0a0a0a', color: '#f4f1ea', minHeight: '100vh', fontFamily: 'IBM Plex Sans, sans-serif', padding: '40px 24px' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <a href="/" style={{ color: '#f4f1ea', opacity: 0.6, textDecoration: 'none', fontSize: 12, letterSpacing: 4, textTransform: 'uppercase' }}>← anicca</a>
        <h1 style={{ fontSize: 56, fontWeight: 900, marginTop: 24 }}>Private CFO</h1>
        <p style={{ opacity: 0.6, fontSize: 12, marginBottom: 32 }}>
          Dais (founder) の financial runway. Behind Netlify basic-auth. 
          For Dais and inner circle only.
        </p>
        {!p ? (
          <p style={{ opacity: 0.6 }}>
            private-cfo.json not yet generated. Run <code>cfo-private</code> skill.
          </p>
        ) : (
          <>
            <Stat label="Bank balance (JPY)" value={`¥${(p.bank_balance_jpy ?? 0).toLocaleString()}`} />
            <Stat label="Monthly burn (JPY)" value={`¥${(p.monthly_burn_jpy ?? 0).toLocaleString()}`} />
            <Stat label="Runway (months)" value={`${(p.runway_months ?? 0).toFixed(1)}`} />
            <Stat label="Next NAIST tuition" value={`¥${(p.naist_tuition_jpy ?? 0).toLocaleString()}`} />
            <p style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
              Updated: {p.updated_at ?? '?'}
            </p>
          </>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: '16px 0', borderBottom: '1px solid rgba(244,241,234,0.15)' }}>
      <p style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', opacity: 0.5 }}>{label}</p>
      <p style={{ fontSize: 32, marginTop: 4 }}>{value}</p>
    </div>
  );
}
