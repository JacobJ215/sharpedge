from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Discord
    discord_bot_token: str
    discord_client_id: str
    discord_guild_id: str

    # Supabase
    supabase_url: str
    supabase_key: str = ""  # Alias for supabase_service_key

    # OpenAI
    openai_api_key: str = ""
    openai_default_model: str = "gpt-5-mini"  # Default model for agents
    openai_research_model: str = "gpt-5-mini"  # Model for research (can use gpt-5 for complex tasks)

    # The Odds API
    odds_api_key: str = ""

    # Whop (Payments)
    whop_api_key: str = ""
    whop_webhook_secret: str = ""
    whop_pro_product_id: str = ""
    whop_sharp_product_id: str = ""
    whop_company_slug: str = "sharpedge"

    # Prediction Markets
    kalshi_api_key: str = ""
    kalshi_private_key: str = ""  # PEM-encoded RSA key (RSA-PSS signing)
    kalshi_live_trading: bool = False  # Safety gate: must be true for live orders
    kalshi_bankroll: float = 10000.0  # Bankroll used for sizing
    kalshi_max_leg_pct: float = 0.05  # Max fraction of bankroll per arb leg
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_passphrase: str = ""

    # Data Enrichment
    weather_api_key: str = ""
    sportsdata_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Discord Role IDs
    pro_role_id: str = ""
    sharp_role_id: str = ""
    free_role_id: str = ""

    # Channel IDs
    value_alerts_channel_id: str = ""
    line_movement_channel_id: str = ""
    arb_alerts_channel_id: str = ""
    pm_alerts_channel_id: str = ""

    # Environment
    environment: str = "development"

    # Legacy Stripe (deprecated, kept for migration)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_sharp_price_id: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_config() -> BotConfig:
    """Load bot configuration from environment."""
    return BotConfig()  # type: ignore[call-arg]
