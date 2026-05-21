-- seed: 20260208_seed_ops_policy.sql
-- Cooldown units: minutes (evaluateReactionMatrix converts to ms)

INSERT INTO ops_policy (key, value) VALUES
  ('auto_approve', '{
    "enabled": true,
    "allowed_step_kinds": ["draft_content", "verify_content", "detect_suffering", "analyze_engagement", "fetch_metrics", "diagnose", "draft_nudge", "evaluate_hook"]
  }'),
  ('x_daily_quota', '{ "limit": 3 }'),
  ('tiktok_daily_quota', '{ "limit": 1 }'),
  ('nudge_daily_quota', '{ "limit": 10 }'),
  ('x_autopost', '{ "enabled": true }'),
  ('tiktok_autopost', '{ "enabled": false }'),
  ('worker_policy', '{ "vps_only": true }'),
  ('buddhist_verification', '{ "enabled": true, "min_score": 3, "max_retries": 3 }'),
  ('stale_threshold_min', '{ "value": 30 }'),
  ('reaction_matrix', '{
    "patterns": [
      {
        "source": "x-poster",
        "tags": ["tweet", "posted"],
        "target": "trend-hunter",
        "type": "analyze_engagement",
        "probability": 0.3,
        "cooldown": 120
      },
      {
        "source": "trend-hunter",
        "tags": ["suffering", "detected"],
        "target": "app-nudge-sender",
        "type": "draft_nudge",
        "probability": 0.5,
        "cooldown": 60
      },
      {
        "source": "*",
        "tags": ["mission", "failed"],
        "target": "x-poster",
        "type": "diagnose",
        "probability": 1.0,
        "cooldown": 60
      },
      {
        "source": "trend-hunter",
        "tags": ["hook_candidate", "found"],
        "target": "x-poster",
        "type": "evaluate_hook",
        "probability": 0.5,
        "cooldown": 240,
        "payload_template": { "eventId": "{{id}}" }
      },
      {
        "source": "x-poster",
        "tags": ["engagement", "high"],
        "target": "tiktok-poster",
        "type": "draft_content",
        "probability": 0.4,
        "cooldown": 480
      }
    ]
  }')
ON CONFLICT (key) DO NOTHING;
