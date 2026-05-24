#!/usr/bin/env node
/**
 * Fetch Postiz posts in last 7 days, aggregate views/likes/comments per post via /analytics/post/{id}.
 * Output: { weekly_total_views, posts_count, avg_views_per_post, target, progress_pct }
 *
 * Auth: POSTIZ_API_KEY env var.
 */

const KEY = process.env.POSTIZ_API_KEY;
if (!KEY) { console.error('ERR: POSTIZ_API_KEY missing'); process.exit(1); }

const fs = require('fs');
const path = require('path');
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'config.json'), 'utf-8'));
const TARGET = config.goals.weekly_views_target;

const BASE = 'https://api.postiz.com/public/v1';

async function api(endpoint) {
  const res = await fetch(`${BASE}${endpoint}`, { headers: { 'Authorization': KEY } });
  if (!res.ok) throw new Error(`Postiz ${endpoint}: ${res.status}`);
  return res.json();
}

(async () => {
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const startDate = weekAgo.toISOString().slice(0, 10);
  const endDate = now.toISOString().slice(0, 10);

  const data = await api(`/posts?startDate=${startDate}&endDate=${endDate}`);
  const posts = data.posts || [];

  let totalViews = 0;
  let totalLikes = 0;
  let totalComments = 0;
  let analyzed = 0;
  const failures = [];

  // Throttle: 5 concurrent
  const concurrency = 5;
  for (let i = 0; i < posts.length; i += concurrency) {
    const batch = posts.slice(i, i + concurrency);
    const results = await Promise.allSettled(batch.map(p => api(`/analytics/post/${p.id}`)));
    for (let j = 0; j < results.length; j++) {
      const r = results[j];
      if (r.status === 'fulfilled') {
        // Postiz returns array of {label, data:[{total,date}]} OR sometimes {} on no-data
        const arr = Array.isArray(r.value) ? r.value : [];
        for (const item of arr) {
          const v = parseInt(item.data?.[0]?.total || '0');
          if (item.label === 'Views') totalViews += v;
          else if (item.label === 'Likes') totalLikes += v;
          else if (item.label === 'Comments') totalComments += v;
        }
        analyzed++;
      } else {
        failures.push({ post_id: batch[j].id, error: r.reason?.message });
      }
    }
  }

  const out = {
    weekly_total_views: totalViews,
    weekly_total_likes: totalLikes,
    weekly_total_comments: totalComments,
    posts_count: posts.length,
    posts_analyzed: analyzed,
    avg_views_per_post: posts.length > 0 ? Math.round(totalViews / posts.length) : 0,
    target: TARGET,
    progress_pct: TARGET > 0 ? Math.round((totalViews / TARGET) * 1000) / 10 : 0,
    failures: failures.length,
    fetched_at: new Date().toISOString()
  };
  console.log(JSON.stringify(out, null, 2));
})().catch(err => {
  console.error('fetch-postiz error:', err.message);
  process.exit(2);
});
