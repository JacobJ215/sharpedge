import logging
import os
import sys

from sharpedge_bot.bot import SharpEdgeBot
from sharpedge_bot.config import load_config


def setup_logging() -> None:
    """Configure logging for the bot."""
    log_level = logging.DEBUG if os.getenv("NODE_ENV") == "development" else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress noisy discord.py logs in production
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def main() -> None:
    """Entry point for the SharpEdge bot."""
    setup_logging()
    logger = logging.getLogger("sharpedge")

    try:
        config = load_config()
    except Exception as e:
        logger.critical("Failed to load configuration: %s", e)
        sys.exit(1)

    # Set environment variables that packages need
    os.environ["SUPABASE_URL"] = config.supabase_url
    os.environ["SUPABASE_SERVICE_KEY"] = config.supabase_service_key

    if config.openai_api_key:
        os.environ["OPENAI_API_KEY"] = config.openai_api_key

    bot = SharpEdgeBot(config)
    logger.info("Starting SharpEdge bot...")
    bot.run(config.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
