import AgentClient from "./AgentClient";

// Static export needs the set of agent pages known at build time. Fetch the currently-live
// instances from the deployed telemetry so every active anicca (by name and by wallet id) gets
// its own /<name> page. New agents get a page on the next deploy. Always include the local agent
// so a fresh clone builds. (dynamicParams stays default-true at request time is N/A under export;
// only these paths are generated — redeploy adds more as the colony grows.)
export async function generateStaticParams() {
  const ids = new Set<string>(["anicca-local"]);
  try {
    const r = await fetch("https://aniccaai.com/.netlify/functions/dashboard-sync");
    const d = await r.json();
    for (const x of d.leaderboard || []) {
      if (x.host) ids.add(String(x.host));
      if (x.id) ids.add(String(x.id));
    }
  } catch {
    // build offline / function down — still ship the known agent page
  }
  return [...ids].map((id) => ({ id }));
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AgentClient id={id} />;
}
