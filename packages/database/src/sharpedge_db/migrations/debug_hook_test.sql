-- Test the Custom Access Token Hook directly
-- Should return claims with app_metadata.tier = 'sharp' and app_metadata.is_operator = true

SELECT public.custom_access_token_hook(
  jsonb_build_object(
    'user_id', '4038622e-8472-42cb-9af4-526fb5d788c5',
    'claims', jsonb_build_object(
      'app_metadata', '{}'::jsonb,
      'user_metadata', '{}'::jsonb,
      'sub', '4038622e-8472-42cb-9af4-526fb5d788c5'
    )
  )
) AS result;
