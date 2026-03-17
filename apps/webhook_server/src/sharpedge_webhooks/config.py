from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../../.env", ".env"],  # check project root first, then CWD
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Whop (Primary payment processor)
    whop_api_key: str = ""
    whop_webhook_secret: str = ""
    whop_pro_product_id: str = ""
    whop_sharp_product_id: str = ""

    # Supabase
    supabase_url: str
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Social media
    win_announcements_channel_id: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    # Instagram Graph API
    instagram_access_token: str = ""
    instagram_account_id: str = ""
    instagram_account_handle: str = ""

    # Social posting behaviour
    alert_min_ev_threshold: float = 3.0
    alert_cooldown_minutes: int = 5
    alert_enabled: bool = False
    alert_poll_interval_seconds: int = 60
    social_image_enabled: bool = True
    supabase_storage_bucket: str = "social-cards"

    # Discord (for role sync via REST API)
    discord_bot_token: str
    discord_guild_id: str
    pro_role_id: str
    sharp_role_id: str
    free_role_id: str = ""

    # OpenAI (BettingCopilot)
    openai_api_key: str = ""

    # Line movement monitor
    line_monitor_enabled: bool = False
    line_monitor_interval_seconds: int = 300  # 5 minutes
    line_monitor_ev_threshold: float = 1.0    # min points movement to flag
    odds_api_key: str = ""                    # The Odds API key

    # Webhook server
    webhook_port: int = 8000

    # Firebase / FCM push notifications
    firebase_service_account_json: str = ""   # JSON string of service account credentials
    push_notifications_enabled: bool = False

    # Legacy Stripe (deprecated)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_sharp_price_id: str = ""
