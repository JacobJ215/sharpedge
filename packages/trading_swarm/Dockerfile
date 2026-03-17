FROM python:3.12-slim

WORKDIR /app

# Install system deps (httpx needs these for async SSL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package manifest first (layer caching)
COPY pyproject.toml ./

# Install the package and its dependencies
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[default]" 2>/dev/null \
    || pip install --no-cache-dir \
        "anthropic>=0.25.0" \
        "numpy>=1.26" \
        "joblib>=1.3" \
        "httpx>=0.27" \
        "praw>=7.7" \
        "supabase>=2.0" \
    && pip install --no-cache-dir -e .

# Model files volume mount point
RUN mkdir -p /data/models/pm

# Non-root user
RUN useradd -m -u 1000 swarm
USER swarm

ENV PYTHONUNBUFFERED=1 \
    TRADING_MODE=paper \
    MODEL_DIR=/data/models/pm \
    PAPER_BANKROLL=10000 \
    LIVE_BANKROLL=2000

CMD ["python", "-m", "sharpedge_trading.daemon"]
