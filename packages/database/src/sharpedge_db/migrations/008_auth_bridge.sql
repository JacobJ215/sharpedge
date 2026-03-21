-- Migration 008: Auth Bridge
-- Adds supabase_auth_id bridge column linking Supabase Auth UUIDs to public.users,
-- makes discord_id nullable for email-only web signups,
-- creates handle_new_auth_user trigger and Custom Access Token Hook function,
-- adds authenticated-user RLS policies.

-- 1. Make discord_id nullable (email-only web users will not have one)
ALTER TABLE public.users
  ALTER COLUMN discord_id DROP NOT NULL;

-- 2. Add bridge columns
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS supabase_auth_id UUID UNIQUE,
  ADD COLUMN IF NOT EXISTS whop_membership_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS email VARCHAR(255),
  ADD COLUMN IF NOT EXISTS is_operator BOOLEAN DEFAULT FALSE NOT NULL;

-- is_operator is set manually to TRUE for the platform owner only.
-- Never exposed to users. Gates all execution/swarm/paper-trading routes.

CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id
  ON public.users(supabase_auth_id);

-- 3. RLS: authenticated web/mobile users can read their own row
CREATE POLICY "User reads own record"
  ON public.users FOR SELECT
  USING (auth.uid() = supabase_auth_id);

-- 4. RLS: authenticated web/mobile users can update their own row
CREATE POLICY "User updates own record"
  ON public.users FOR UPDATE
  USING (auth.uid() = supabase_auth_id)
  WITH CHECK (auth.uid() = supabase_auth_id);

-- 5. Auto-create public.users row when a new Supabase Auth user signs up
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (supabase_auth_id, tier, email)
  VALUES (NEW.id, 'free', NEW.email)
  ON CONFLICT (supabase_auth_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();

-- 6. Custom Access Token Hook: injects tier into every JWT at issue time
-- IMPORTANT: After applying this migration, register this function in the
-- Supabase Dashboard -> Authentication -> Hooks -> Custom Access Token Hook
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  claims     jsonb;
  user_tier  text;
  is_op      boolean;
  auth_id    uuid;
BEGIN
  auth_id := (event->>'user_id')::uuid;
  claims  := event->'claims';

  SELECT tier INTO user_tier
  FROM public.users
  WHERE supabase_auth_id = auth_id;

  user_tier := coalesce(user_tier, 'free');

  claims := jsonb_set(claims, '{app_metadata}',
    coalesce(claims->'app_metadata', '{}'));
  claims := jsonb_set(claims, '{app_metadata,tier}', to_jsonb(user_tier));

  -- Inject is_operator for execution route gating (owner-only, never shown to users)
  SELECT is_operator INTO is_op
  FROM public.users
  WHERE supabase_auth_id = auth_id;
  claims := jsonb_set(claims, '{app_metadata,is_operator}', to_jsonb(coalesce(is_op, false)));

  RETURN jsonb_set(event, '{claims}', claims);
END;
$$;

-- Grant execute to the Supabase auth admin role (required for hooks)
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook
  TO supabase_auth_admin;

-- Grant execute on handle_new_auth_user to authenticated role
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
