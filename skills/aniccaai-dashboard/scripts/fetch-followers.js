#!/usr/bin/env node
/**
 * Scrape follower counts via Apify (TT/IG) + Twitter API (X).
 *
 * Source of handles: Postiz /integrations (live, not hardcoded)
 *
 * Auth: APIFY_API_TOKEN, POSTIZ_API_KEY env vars.
 */

const APIFY = process.env.APIFY_API_TOKEN;
const POSTIZ = process.env.POSTIZ_API_KEY;
if (!APIFY) { console.error('ERR: APIFY_API_TOKEN missing'); process.exit(1); }
if (!POSTIZ) { console.error('ERR: POSTIZ_API_KEY missing'); process.exit(1); }

async function postizGet(endpoint) {
  const res = await fetch(`https://api.postiz.com/public/v1${endpoint}`, {
    headers: { 'Authorization': POSTIZ }
  });
  if (!res.ok) throw new Error(`Postiz ${endpoint}: ${res.status}`);
  return res.json();
}

async function apifyRun(actorId, input) {
  const url = `https://api.apify.com/v2/acts/${actorId}/run-sync-get-dataset-items?token=${APIFY}&timeout=120`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input)
  });
  if (!res.ok) throw new Error(`Apify ${actorId}: ${res.status} ${await res.text()}`);
  return res.json();
}

(async () => {
  // 1. Get all integrations from Postiz (live)
  const integrations = await postizGet('/integrations');
  const handles = { tiktok: [], instagram: [], youtube: [] };
  for (const i of integrations) {
    if (!i.profile) continue;
    const platform = i.identifier;
    if (platform === 'tiktok') handles.tiktok.push(i.profile);
    else if (platform === 'instagram-standalone' || platform === 'instagram') handles.instagram.push(i.profile);
    else if (platform === 'youtube') handles.youtube.push(i.profile);
  }

  const byAccount = [];
  let totalFollowers = 0;

  // 2. TikTok bulk scrape (1 actor call for all)
  if (handles.tiktok.length > 0) {
    try {
      const profiles = handles.tiktok.map(p => p.replace(/^@/, ''));
      const items = await apifyRun('clockworks~tiktok-profile-scraper', {
        profiles,
        resultsPerPage: 1
      });
      for (const item of items) {
        // tiktok-profile-scraper returns {authorMeta: {fans, ...}}
        const fans = item.authorMeta?.fans ?? item.fans ?? 0;
        const handle = item.authorMeta?.name ?? item.name ?? 'unknown';
        byAccount.push({ platform: 'tiktok', handle, followers: fans });
        totalFollowers += fans;
      }
    } catch (err) {
      console.error('TikTok scrape error:', err.message);
    }
  }

  // 3. Instagram (per profile, paid actor — light call)
  for (const handle of handles.instagram) {
    try {
      const items = await apifyRun('apify~instagram-profile-scraper', {
        usernames: [handle.replace(/^@/, '')]
      });
      const item = items[0] || {};
      const followers = item.followersCount ?? 0;
      byAccount.push({ platform: 'instagram', handle, followers });
      totalFollowers += followers;
    } catch (err) {
      console.error(`Instagram scrape error for ${handle}:`, err.message);
    }
  }

  // 4. YouTube (light call)
  for (const handle of handles.youtube) {
    try {
      const items = await apifyRun('streamers~youtube-scraper', {
        startUrls: [{ url: `https://www.youtube.com/${handle.startsWith('@') ? handle : '@' + handle}` }],
        maxResults: 1
      });
      const item = items[0] || {};
      const subs = item.numberOfSubscribers ?? 0;
      byAccount.push({ platform: 'youtube', handle, followers: subs });
      totalFollowers += subs;
    } catch (err) {
      console.error(`YouTube scrape error for ${handle}:`, err.message);
    }
  }

  console.log(JSON.stringify({
    total: totalFollowers,
    by_account: byAccount,
    handles_found: handles,
    fetched_at: new Date().toISOString()
  }, null, 2));
})().catch(err => {
  console.error('fetch-followers error:', err.message);
  process.exit(2);
});
