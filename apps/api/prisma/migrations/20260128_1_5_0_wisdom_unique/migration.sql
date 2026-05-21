-- Add UNIQUE constraint on pattern_name for wisdom_patterns
-- Required for ON CONFLICT upsert in wisdomExtractor.js
ALTER TABLE wisdom_patterns ADD CONSTRAINT wisdom_patterns_pattern_name_key UNIQUE (pattern_name);
