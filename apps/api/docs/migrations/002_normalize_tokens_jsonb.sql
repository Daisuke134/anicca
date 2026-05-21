-- 正規化: JSONB列に文字列JSONが入っている場合のみ、オブジェクトへ変換
-- 影響範囲: tokens.access_token_enc / refresh_token_enc

BEGIN;

UPDATE tokens
SET access_token_enc = (access_token_enc #>> '{}')::jsonb
WHERE jsonb_typeof(access_token_enc) = 'string';

UPDATE tokens
SET refresh_token_enc = (refresh_token_enc #>> '{}')::jsonb
WHERE refresh_token_enc IS NOT NULL
  AND jsonb_typeof(refresh_token_enc) = 'string';

COMMIT;

-- 検証（任意）
-- SELECT jsonb_typeof(access_token_enc) AS t, COUNT(*) FROM tokens GROUP BY 1;
-- SELECT jsonb_typeof(refresh_token_enc) AS t, COUNT(*) FROM tokens GROUP BY 1;

