-- seed: 20260208_seed_ops_trigger_rules.sql

INSERT INTO ops_trigger_rules (name, event_kind, condition, proposal_template, cooldown_min, enabled) VALUES
  (
    'engagement_analysis_24h',
    'tweet_posted',
    '{ "delay_min": 1440 }',
    '{ "skill_name": "x-poster", "title": "24h後エンゲージメント分析", "steps": [{ "kind": "fetch_metrics", "order": 0 }, { "kind": "analyze_engagement", "order": 1 }] }',
    1440,
    true
  ),
  (
    'suffering_nudge',
    'suffering_detected',
    '{ "min_severity": 0.6 }',
    '{ "skill_name": "app-nudge-sender", "title": "苦しみ検出→Nudge送信", "steps": [{ "kind": "draft_nudge", "order": 0 }, { "kind": "send_nudge", "order": 1 }] }',
    60,
    true
  ),
  (
    'mission_failure_diagnosis',
    'mission:failed',
    '{}',
    '{ "skill_name": "x-poster", "title": "ミッション失敗診断", "steps": [{ "kind": "diagnose", "order": 0 }] }',
    60,
    true
  ),
  (
    'tiktok_content_check_24h',
    'tiktok_posted',
    '{ "delay_min": 1440 }',
    '{ "skill_name": "tiktok-poster", "title": "24h後TikTokメトリクス取得", "steps": [{ "kind": "fetch_metrics", "order": 0 }, { "kind": "analyze_engagement", "order": 1 }] }',
    1440,
    true
  )
ON CONFLICT (name) DO NOTHING;
