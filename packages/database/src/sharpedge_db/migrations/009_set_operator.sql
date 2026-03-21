-- Set operator status and tier for platform owner
-- Run once in Supabase SQL Editor after migration 008 is applied

INSERT INTO public.users (supabase_auth_id, tier, is_operator)
VALUES (
  (SELECT id FROM auth.users WHERE email = 'jacob.johnson2718@gmail.com'),
  'sharp',
  true
)
ON CONFLICT (supabase_auth_id) DO UPDATE
  SET tier = 'sharp',
      is_operator = true;
