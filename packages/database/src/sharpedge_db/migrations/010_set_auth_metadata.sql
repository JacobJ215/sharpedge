-- Write tier and is_operator directly into auth.users app_metadata
-- This bypasses the Custom Access Token Hook entirely.
-- The JWT is issued with these values from raw_app_meta_data.

UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"tier": "sharp", "is_operator": true}'::jsonb
WHERE email = 'jacob.johnson2718@gmail.com';

-- Verify
SELECT id, email, raw_app_meta_data
FROM auth.users
WHERE email = 'jacob.johnson2718@gmail.com';
