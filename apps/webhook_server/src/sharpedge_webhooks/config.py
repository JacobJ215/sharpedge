from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Whop (Primary payment processor)
    whop_api_key: str = ""
    whop_webhook_secret: str = ""
    whop_pro_product_id: str = ""
    whop_sharp_product_id: str = ""

    # Supabase
    supabase_url: str
    supabase_key: str = ""

    # Discord (for role sync via REST API)
    discord_bot_token: str
    discord_guild_id: str
    pro_role_id: str
    sharp_role_id: str
    free_role_id: str = ""

    # Webhook server
    webhook_port: int = 8000

    # Legacy Stripe (deprecated)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_sharp_price_id: str = ""
