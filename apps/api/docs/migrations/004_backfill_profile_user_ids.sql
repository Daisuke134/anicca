-- Backfill internal UUIDs for existing mobile_profiles rows
DO $$

DECLARE
  rec RECORD;
  new_profile_id uuid;
BEGIN
  FOR rec IN SELECT DISTINCT user_id FROM mobile_profiles LOOP
    -- 既存Apple IDに対応するprofiles行を用意
    SELECT id INTO new_profile_id
      FROM profiles
     WHERE metadata->>'apple_user_id' = rec.user_id
     LIMIT 1;

    IF new_profile_id IS NULL THEN
      INSERT INTO profiles (id, metadata)
      VALUES (gen_random_uuid(), jsonb_build_object('apple_user_id', rec.user_id))
      RETURNING id INTO new_profile_id;
    END IF;

    UPDATE mobile_profiles
       SET user_id = new_profile_id::text
     WHERE user_id = rec.user_id;
  END LOOP;
END $$;


